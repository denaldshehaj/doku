"""Raporte & Statistika (admin-only).

Everything is aggregated from data the system already records — chat_history,
audit_logs, documents, experiment_results — so the module needs no schema
change and can never show fabricated numbers. Refusals are detected by the
exact REFUSAL_MESSAGE prefix the pipeline writes; citations are unpacked from
sources_json with SQLite's json_each.

One composite endpoint feeds the whole page (a local single-user dashboard
doesn't benefit from seven round-trips), plus a CSV export for Excel.
"""
import csv
import io
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

import config
from api import deps
from modules import database as db, vector_store

router = APIRouter(prefix="/api/reports", tags=["reports"])

# Prefix long enough to be unambiguous, short enough to survive small edits.
_REFUSAL_PREFIX = config.REFUSAL_MESSAGE[:40] + "%"

ALLOWED_PERIODS = (7, 30, 90, 365)


def _clamp_days(days: int) -> int:
    return days if days in ALLOWED_PERIODS else 30


def _since(days: int) -> str:
    return f"-{int(days)} days"


def _fill_days(rows: dict[str, dict], days: int, keys: tuple[str, ...]) -> list[dict]:
    """Zero-fill missing dates so charts get a continuous series."""
    out = []
    today = datetime.now(timezone.utc).date()
    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        row = rows.get(d, {})
        out.append({"date": d, **{k: row.get(k, 0) for k in keys}})
    return out


def _delta_pct(current: int | float, previous: int | float) -> float | None:
    if not previous:
        return None
    return round((current - previous) / previous * 100, 1)


def _user_filter(username: str | None) -> tuple[str, list]:
    if username:
        return " AND username = ?", [username]
    return "", []


def _questions_kpis(conn, days: int, username: str | None) -> dict:
    uf, up = _user_filter(username)

    def window_counts(shift: str) -> dict:
        row = conn.execute(
            f"SELECT COUNT(*) AS total, "
            f"SUM(CASE WHEN answer LIKE ? THEN 1 ELSE 0 END) AS refused, "
            f"AVG(response_time) AS avg_t "
            f"FROM chat_history WHERE mode = 'rag' AND created_at >= datetime('now', ?) "
            f"AND created_at < datetime('now', ?){uf}",
            [_REFUSAL_PREFIX, f"-{2 * days} days" if shift == "prev" else _since(days),
             _since(days) if shift == "prev" else "+1 day", *up]).fetchone()
        return {"total": row["total"] or 0, "refused": row["refused"] or 0,
                "avg_t": row["avg_t"]}

    cur, prev = window_counts("cur"), window_counts("prev")

    # P95 over the current window (computed in Python — SQLite has no percentile).
    times = [r[0] for r in conn.execute(
        f"SELECT response_time FROM chat_history WHERE mode = 'rag' "
        f"AND response_time IS NOT NULL AND created_at >= datetime('now', ?){uf} "
        f"ORDER BY response_time", [_since(days), *up]).fetchall()]
    p95 = times[max(0, int(len(times) * 0.95) - 1)] if times else None

    summaries_cur = conn.execute(
        f"SELECT COUNT(*) AS c FROM chat_history WHERE mode = 'summary' "
        f"AND created_at >= datetime('now', ?){uf}", [_since(days), *up]).fetchone()["c"]
    summaries_prev = conn.execute(
        f"SELECT COUNT(*) AS c FROM chat_history WHERE mode = 'summary' "
        f"AND created_at >= datetime('now', ?) AND created_at < datetime('now', ?){uf}",
        [f"-{2 * days} days", _since(days), *up]).fetchone()["c"]

    exports = conn.execute(
        f"SELECT COUNT(*) AS c FROM chat_history WHERE exported_to_word = 1 "
        f"AND created_at >= datetime('now', ?){uf}", [_since(days), *up]).fetchone()["c"]

    active_users = conn.execute(
        "SELECT COUNT(DISTINCT username) AS c FROM chat_history "
        "WHERE created_at >= datetime('now', ?)", [_since(days)]).fetchone()["c"]

    answered = cur["total"] - cur["refused"]
    return {
        "questions": {"value": cur["total"],
                      "delta_pct": _delta_pct(cur["total"], prev["total"])},
        "answered": {"value": answered},
        "refused": {"value": cur["refused"],
                    "delta_pct": _delta_pct(cur["refused"], prev["refused"])},
        "refusal_rate": round(cur["refused"] / cur["total"], 3) if cur["total"] else None,
        "summaries": {"value": summaries_cur,
                      "delta_pct": _delta_pct(summaries_cur, summaries_prev)},
        "exports_docx": {"value": exports},
        "active_users": {"value": active_users},
        "avg_response_time": round(cur["avg_t"], 2) if cur["avg_t"] else None,
        "p95_response_time": round(p95, 2) if p95 else None,
    }


@router.get("")
def reports(days: int = Query(default=30),
            username: str | None = Query(default=None),
            admin=Depends(deps.require_admin)):
    days = _clamp_days(days)
    uf, up = _user_filter(username)

    with db.get_conn() as conn:
        kpi = _questions_kpis(conn, days, username)

        # Questions per day (answered vs refused) — line chart.
        per_day = {
            r["d"]: {"questions": r["total"], "refused": r["refused"] or 0}
            for r in conn.execute(
                f"SELECT date(created_at) AS d, COUNT(*) AS total, "
                f"SUM(CASE WHEN answer LIKE ? THEN 1 ELSE 0 END) AS refused "
                f"FROM chat_history WHERE mode = 'rag' "
                f"AND created_at >= datetime('now', ?){uf} GROUP BY d",
                [_REFUSAL_PREFIX, _since(days), *up]).fetchall()
        }

        # Average response time per day — trend chart.
        rt_day = {
            r["d"]: {"avg": round(r["avg_t"], 2) if r["avg_t"] else 0}
            for r in conn.execute(
                f"SELECT date(created_at) AS d, AVG(response_time) AS avg_t "
                f"FROM chat_history WHERE mode = 'rag' AND response_time IS NOT NULL "
                f"AND created_at >= datetime('now', ?){uf} GROUP BY d",
                [_since(days), *up]).fetchall()
        }

        # Citations grouped by document type — donut chart.
        by_type = [
            {"label": r["t"] or "Të tjera", "count": r["c"]}
            for r in conn.execute(
                f"SELECT json_extract(j.value, '$.document_type') AS t, COUNT(*) AS c "
                f"FROM chat_history ch, json_each(ch.sources_json) j "
                f"WHERE ch.mode = 'rag' AND ch.created_at >= datetime('now', ?){uf} "
                f"GROUP BY t ORDER BY c DESC", [_since(days), *up]).fetchall()
        ]

        # Most-cited documents — horizontal bars.
        top_documents = [
            {"title": r["t"] or "(pa titull)", "count": r["c"]}
            for r in conn.execute(
                f"SELECT json_extract(j.value, '$.title') AS t, COUNT(*) AS c "
                f"FROM chat_history ch, json_each(ch.sources_json) j "
                f"WHERE ch.mode = 'rag' AND ch.created_at >= datetime('now', ?){uf} "
                f"GROUP BY t ORDER BY c DESC LIMIT 8", [_since(days), *up]).fetchall()
        ]

        # Per-user activity table (window-scoped).
        by_user = [
            {"username": r["username"],
             "questions": r["q"], "refused": r["r"] or 0, "summaries": r["s"],
             "last_activity": r["last"]}
            for r in conn.execute(
                "SELECT username, "
                "SUM(CASE WHEN mode = 'rag' THEN 1 ELSE 0 END) AS q, "
                "SUM(CASE WHEN mode = 'rag' AND answer LIKE ? THEN 1 ELSE 0 END) AS r, "
                "SUM(CASE WHEN mode = 'summary' THEN 1 ELSE 0 END) AS s, "
                "MAX(created_at) AS last "
                "FROM chat_history WHERE created_at >= datetime('now', ?) "
                "GROUP BY username ORDER BY q DESC LIMIT 20",
                [_REFUSAL_PREFIX, _since(days)]).fetchall()
        ]

        # Corpus snapshot (documents by type and status).
        corpus = [
            {"label": r["t"] or "Të tjera", "active": r["a"], "inactive": r["i"]}
            for r in conn.execute(
                "SELECT document_type AS t, "
                "SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) AS a, "
                "SUM(CASE WHEN status != 'active' THEN 1 ELSE 0 END) AS i "
                "FROM documents GROUP BY document_type ORDER BY a + i DESC").fetchall()
        ]

        # System activity from the audit log — grouped by action.
        activity = [
            {"action": r["action"], "count": r["c"]}
            for r in conn.execute(
                "SELECT action, COUNT(*) AS c FROM audit_logs "
                "WHERE created_at >= datetime('now', ?) "
                "GROUP BY action ORDER BY c DESC LIMIT 15", [_since(days)]).fetchall()
        ]

        usernames = [r["username"] for r in conn.execute(
            "SELECT DISTINCT username FROM chat_history ORDER BY username").fetchall()]

    return {
        "period_days": days,
        "filter_username": username,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "kpi": kpi,
        "documents_total": _count_documents(),
        "chunks_total": vector_store.count(),
        "questions_per_day": _fill_days(per_day, days, ("questions", "refused")),
        "response_time_per_day": _fill_days(rt_day, days, ("avg",)),
        "citations_by_type": by_type,
        "top_documents": top_documents,
        "by_user": by_user,
        "corpus_by_type": corpus,
        "activity_by_action": activity,
        "usernames": usernames,
    }


def _count_documents() -> int:
    with db.get_conn() as conn:
        return conn.execute("SELECT COUNT(*) AS c FROM documents").fetchone()["c"]


@router.get("/export.csv")
def export_csv(days: int = Query(default=30),
               username: str | None = Query(default=None),
               admin=Depends(deps.require_admin)):
    """All report tables stacked into one CSV (utf-8-sig so Excel opens it
    with correct Albanian diacritics)."""
    data = reports(days=days, username=username, admin=admin)
    buf = io.StringIO()
    w = csv.writer(buf)

    w.writerow([f"DOKU — Raport statistikash ({data['period_days']} ditët e fundit)"])
    w.writerow([f"Gjeneruar: {data['generated_at']}"])
    if data["filter_username"]:
        w.writerow([f"Filtruar për përdoruesin: {data['filter_username']}"])

    def section(title: str, header: list[str], rows: list[list]):
        w.writerow([])
        w.writerow([title])
        w.writerow(header)
        w.writerows(rows)

    k = data["kpi"]
    section("Treguesit kryesorë (KPI)", ["Treguesi", "Vlera"], [
        ["Pyetje gjithsej", k["questions"]["value"]],
        ["Përgjigje të bazuara", k["answered"]["value"]],
        ["Refuzime", k["refused"]["value"]],
        ["Norma e refuzimit", k["refusal_rate"]],
        ["Përmbledhje", k["summaries"]["value"]],
        ["Eksporte Word", k["exports_docx"]["value"]],
        ["Përdorues aktivë", k["active_users"]["value"]],
        ["Koha mesatare e përgjigjes (s)", k["avg_response_time"]],
        ["Koha P95 (s)", k["p95_response_time"]],
        ["Dokumente gjithsej", data["documents_total"]],
        ["Copëza në indeks", data["chunks_total"]],
    ])
    section("Pyetje sipas ditës", ["Data", "Pyetje", "Refuzime"],
            [[r["date"], r["questions"], r["refused"]] for r in data["questions_per_day"]])
    section("Citime sipas tipit të dokumentit", ["Tipi", "Citime"],
            [[r["label"], r["count"]] for r in data["citations_by_type"]])
    section("Dokumentet më të cituara", ["Dokumenti", "Citime"],
            [[r["title"], r["count"]] for r in data["top_documents"]])
    section("Aktiviteti sipas përdoruesit",
            ["Përdoruesi", "Pyetje", "Refuzime", "Përmbledhje", "Aktiviteti i fundit"],
            [[r["username"], r["questions"], r["refused"], r["summaries"], r["last_activity"]]
             for r in data["by_user"]])
    section("Korpusi sipas tipit", ["Tipi", "Aktive", "Joaktive"],
            [[r["label"], r["active"], r["inactive"]] for r in data["corpus_by_type"]])
    section("Aktiviteti i sistemit (audit)", ["Veprimi", "Numri"],
            [[r["action"], r["count"]] for r in data["activity_by_action"]])

    filename = f"raport_doku_{date.today().isoformat()}_{days}d.csv"
    # Explicit UTF-8 BOM so Excel detects the encoding (Albanian diacritics).
    return StreamingResponse(
        iter([("\ufeff" + buf.getvalue()).encode("utf-8")]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'})
