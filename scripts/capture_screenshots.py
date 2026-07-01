"""Kap screenshot-e reale te aplikacionit DOKU me Playwright, per tezen.

Kerkohet qe aplikacioni te jete duke ekzekutuar ne http://localhost:8501 dhe
qe admin-i te kete nje fjalekalim te njohur (shih ADMIN_USER/ADMIN_PASS).

Perdorim:
    .venv\\Scripts\\python.exe scripts\\capture_screenshots.py
Dalja:
    docs/screenshots/NN_*.png
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8501"
ADMIN_USER = "admin"
ADMIN_PASS = "DokuDemo2026"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "screenshots")
os.makedirs(OUT, exist_ok=True)

saved = []


def shot(page, name, full=True):
    path = os.path.join(OUT, name)
    try:
        page.screenshot(path=path, full_page=full)
        saved.append(name)
        print("OK", name)
    except Exception as e:
        print("FAIL", name, e)


def settle(page, secs=2.0):
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    time.sleep(secs)


def goto_page(page, link_name):
    """Click a sidebar nav link by its visible title."""
    try:
        page.locator('[data-testid="stSidebarNav"]').get_by_role("link", name=link_name, exact=True).click(timeout=8000)
    except Exception:
        # fallback: any link with that name
        page.get_by_role("link", name=link_name, exact=True).first.click(timeout=8000)
    settle(page, 2.5)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        # 1) Login page (pre-auth)
        page.goto(BASE, wait_until="domcontentloaded")
        settle(page, 3.0)
        shot(page, "01_login.png")

        # Fill credentials and submit
        try:
            page.locator('input[aria-label="Përdoruesi"]').fill(ADMIN_USER, timeout=8000)
            page.locator('input[aria-label="Fjalëkalimi"]').fill(ADMIN_PASS, timeout=8000)
            page.get_by_role("button", name="Hyr").click(timeout=8000)
        except Exception as e:
            print("login fill failed:", e)
        settle(page, 4.0)

        # 2) Dashboard
        shot(page, "02_dashboard.png")

        # 3) Ask interface
        goto_page(page, "Pyet Dokumentet")
        shot(page, "03_ask_interface.png")

        # 4) Ask -> out-of-corpus refusal (fast, no LLM call)
        try:
            page.locator('textarea').first.fill("Kush e fitoi Kupën e Botës në futboll në vitin 2018?", timeout=8000)
            page.get_by_role("button", name="Kërko përgjigje").click(timeout=8000)
            settle(page, 5.0)
        except Exception as e:
            print("ask submit failed:", e)
        shot(page, "04_ask_refusal.png")

        # 5) Summary interface
        goto_page(page, "Përmbledhje")
        shot(page, "05_summary.png")

        # 6) History
        goto_page(page, "Historiku im")
        shot(page, "06_history.png")

        # 7) Documents (admin)
        goto_page(page, "Dokumentet")
        shot(page, "07_documents.png")

        # 8) Users (admin)
        goto_page(page, "Përdoruesit")
        shot(page, "08_users.png")

        # 9) Audit log (admin)
        goto_page(page, "Audit Log")
        shot(page, "09_audit.png")

        # 10) Experiments (admin) - has real results table
        goto_page(page, "Eksperimente")
        shot(page, "10_experiments.png")

        ctx.close()
        browser.close()

    print("\nSAVED", len(saved), "screenshots ->", OUT)
    for s in saved:
        print(" -", s)


if __name__ == "__main__":
    main()
