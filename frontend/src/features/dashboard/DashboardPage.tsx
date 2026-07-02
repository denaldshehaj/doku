/* Dashboard: role-aware stat cards, quick actions, recent personal activity. */
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight, FileStack, FileText, History as HistoryIcon, Layers,
  MessageSquareText, MessagesSquare, NotebookPen, Users,
} from "lucide-react";
import { historyApi, metaApi } from "@/api/endpoints";
import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Alert, EmptyState, Skeleton } from "@/components/ui/misc";
import { StatCard } from "@/components/shared/StatCard";
import { PageHeader } from "@/components/shared/PageHeader";
import { useAuth } from "@/providers/AuthProvider";
import { formatDateTime, truncate } from "@/lib/format";

const MODE_LABEL: Record<string, string> = {
  rag: "Pyetje", no_rag: "Pa RAG", summary: "Përmbledhje",
};

const QUICK_ACTIONS = [
  {
    to: "/biseda", icon: MessageSquareText, title: "Bëj një pyetje",
    text: "Pyet korpusin dhe merr përgjigje me citime të verifikueshme.",
  },
  {
    to: "/permbledhje", icon: NotebookPen, title: "Gjenero përmbledhje",
    text: "Përmbledh një dokument në 4 formate të ndryshme.",
  },
  {
    to: "/historiku", icon: HistoryIcon, title: "Shiko historikun",
    text: "Rishiko pyetjet, përgjigjet dhe përmbledhjet e tua.",
  },
];

export default function DashboardPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const stats = useQuery({ queryKey: ["dashboard"], queryFn: metaApi.dashboard });
  const status = useQuery({ queryKey: ["system-status"], queryFn: metaApi.systemStatus });
  const recent = useQuery({ queryKey: ["history", 5], queryFn: () => historyApi.list(5) });

  return (
    <>
      <PageHeader
        title={`Mirë se erdhe, ${user?.full_name || user?.username}!`}
        subtitle={isAdmin
          ? "Këtu ke një përmbledhje të aktivitetit dhe gjendjes së sistemit DOKU."
          : "Si punonjës mund të analizosh dokumente, të bësh pyetje dhe të marrësh përgjigje të bazuara në burime."} />

      {status.data && !status.data.ollama_online && (
        <div className="mb-5">
          <Alert variant="danger" title="Modeli lokal (Ollama) nuk po përgjigjet">
            Pyetjet dhe përmbledhjet nuk mund të gjenerohen derisa Ollama të jetë aktiv
            në këtë kompjuter. Kërkimi dhe shfletimi i dokumenteve funksionojnë normalisht.
          </Alert>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Dokumente aktive" value={stats.data?.active_documents}
                  icon={FileText} loading={stats.isPending} />
        <StatCard label="Dokumente gjithsej" value={stats.data?.total_documents}
                  icon={FileStack} loading={stats.isPending} />
        <StatCard label="Copëza në indeks" value={stats.data?.chunks?.toLocaleString("sq-AL")}
                  icon={Layers} loading={stats.isPending} />
        {isAdmin ? (
          <StatCard label="Përdorues" value={stats.data?.users_count} icon={Users}
                    loading={stats.isPending} />
        ) : (
          <StatCard label="Pyetjet e mia" value={stats.data?.my_questions}
                    icon={MessagesSquare} loading={stats.isPending} />
        )}
      </div>

      <h2 className="mb-3 mt-8 text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
        Veprime të shpejta
      </h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {QUICK_ACTIONS.map(({ to, icon: Icon, title, text }) => (
          <Link key={to} to={to}
                className="group rounded-2xl border border-slate-200 bg-white p-5 shadow-card transition-shadow hover:shadow-pop dark:border-slate-800 dark:bg-slate-900">
            <span className="inline-flex rounded-xl bg-brand-50 p-2.5 text-brand-700 dark:bg-brand-950 dark:text-brand-300">
              <Icon className="h-5 w-5" aria-hidden />
            </span>
            <p className="mt-3 font-semibold text-slate-800 dark:text-slate-100">{title}</p>
            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{text}</p>
            <span className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-brand-700 group-hover:gap-2 dark:text-brand-300"
                  style={{ transition: "gap 150ms" }}>
              Vazhdo <ArrowRight className="h-4 w-4" aria-hidden />
            </span>
          </Link>
        ))}
      </div>

      <div className="mt-8">
        <Card>
          <CardHeader title="Aktiviteti im i fundit"
                      actions={
                        <Link to="/historiku"
                              className="text-sm font-medium text-brand-700 hover:underline dark:text-brand-300">
                          Shiko të gjithë historikun
                        </Link>
                      } />
          <CardBody className="p-0">
            {recent.isPending ? (
              <div className="space-y-3 p-5">
                {[0, 1, 2].map((i) => <Skeleton key={i} className="h-6 w-full" />)}
              </div>
            ) : recent.data && recent.data.length > 0 ? (
              <ul className="divide-y divide-slate-100 dark:divide-slate-800">
                {recent.data.map((r) => (
                  <li key={r.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 sm:px-5">
                    <span className="min-w-0 flex-1 truncate text-sm text-slate-700 dark:text-slate-300">
                      {truncate(r.question, 90)}
                    </span>
                    <span className="flex shrink-0 items-center gap-2">
                      <Badge variant={r.mode === "summary" ? "brand" : "neutral"}>
                        {MODE_LABEL[r.mode] ?? r.mode}
                      </Badge>
                      <span className="text-xs tabular-nums text-slate-400 dark:text-slate-500">
                        {formatDateTime(r.created_at)}
                      </span>
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyState title="Ende pa aktivitet"
                          description="Fillo duke bërë pyetjen e parë mbi dokumentet."
                          action={
                            <Link to="/biseda"
                                  className="text-sm font-medium text-brand-700 hover:underline dark:text-brand-300">
                              Bëj një pyetje →
                            </Link>
                          } />
            )}
          </CardBody>
        </Card>
      </div>
    </>
  );
}
