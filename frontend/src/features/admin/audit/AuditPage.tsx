/* Admin — audit log: searchable, filterable table of every recorded action. */
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { auditApi } from "@/api/endpoints";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Input, Select } from "@/components/ui/fields";
import { EmptyState, Skeleton } from "@/components/ui/misc";
import { TableShell, Td, Th, Tr } from "@/components/shared/DataTable";
import { PageHeader } from "@/components/shared/PageHeader";
import { formatDateTime } from "@/lib/format";

/** Visual grouping of audit actions (colour only — data stays raw). */
function actionVariant(action: string): "success" | "danger" | "warning" | "brand" | "neutral" {
  if (action.startsWith("login") || action === "logout") {
    return action === "login_failed" ? "danger" : "success";
  }
  if (action.includes("delete") || action.includes("deactivate")) return "warning";
  if (action.includes("password") || action.includes("user") || action.includes("role")) return "brand";
  return "neutral";
}

export default function AuditPage() {
  const [search, setSearch] = useState("");
  const [action, setAction] = useState("");
  const audit = useQuery({ queryKey: ["audit"], queryFn: () => auditApi.list(500) });

  const actions = useMemo(
    () => [...new Set((audit.data ?? []).map((r) => r.action))].sort(),
    [audit.data]);

  const filtered = useMemo(() => {
    if (!audit.data) return [];
    const kw = search.trim().toLowerCase();
    return audit.data.filter((r) =>
      (!action || r.action === action) &&
      (!kw || (r.username ?? "").toLowerCase().includes(kw) ||
        (r.details ?? "").toLowerCase().includes(kw)));
  }, [audit.data, search, action]);

  return (
    <>
      <PageHeader title="Audit Log"
                  subtitle="Regjistri i plotë i veprimeve në sistem — hyrje, dokumente, pyetje, administrim." />

      <div className="mb-4 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden />
          <Input aria-label="Kërko në log" placeholder="Kërko përdorues ose detaje…"
                 className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <div className="sm:w-64">
          <Select aria-label="Filtro sipas veprimit" value={action}
                  onChange={(e) => setAction(e.target.value)}>
            <option value="">Të gjitha veprimet</option>
            {actions.map((a) => <option key={a}>{a}</option>)}
          </Select>
        </div>
      </div>

      <Card>
        {audit.isPending ? (
          <div className="space-y-3 p-5">
            {[0, 1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-7 w-full" />)}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState title={audit.data?.length ? "Asnjë rezultat për filtrat" : "Ende pa veprime të regjistruara"} />
        ) : (
          <TableShell ariaLabel="Regjistri i veprimeve">
            <thead>
              <tr>
                <Th>Koha</Th>
                <Th>Përdoruesi</Th>
                <Th>Veprimi</Th>
                <Th className="hidden md:table-cell">Detaje</Th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r, i) => (
                <Tr key={i}>
                  <Td className="whitespace-nowrap tabular-nums text-xs">
                    {formatDateTime(r.created_at)}
                  </Td>
                  <Td className="font-medium text-slate-800 dark:text-slate-100">
                    {r.username ?? "—"}
                  </Td>
                  <Td><Badge variant={actionVariant(r.action)}>{r.action}</Badge></Td>
                  <Td className="hidden max-w-[24rem] truncate text-xs md:table-cell"
                      title={r.details ?? undefined}>
                    {r.details || "—"}
                  </Td>
                </Tr>
              ))}
            </tbody>
          </TableShell>
        )}
      </Card>
      <p className="mt-3 text-xs text-slate-400 dark:text-slate-500">
        {filtered.length} nga {audit.data?.length ?? 0} veprime (max 500 të fundit)
      </p>
    </>
  );
}
