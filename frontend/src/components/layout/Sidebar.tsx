/* Navigation sidebar: brand, role-aware nav sections, live system status.
 * Desktop: fixed column. Mobile: sliding drawer (state owned by AppShell). */
import { NavLink } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BarChart3, ClipboardList, FileText, FlaskConical, History, LayoutDashboard,
  ListTodo, MessageSquareText, Users, X,
} from "lucide-react";
import { ApiError } from "@/api/client";
import { metaApi } from "@/api/endpoints";
import { useAuth } from "@/providers/AuthProvider";
import { useToast } from "@/providers/ToastProvider";
import { cx } from "@/lib/format";

const EMPLOYEE_ITEMS = [
  { to: "/", label: "Paneli Kryesor", icon: LayoutDashboard, end: true },
  { to: "/biseda", label: "Biseda", icon: MessageSquareText },
  { to: "/permbledhje", label: "Përmbledhje", icon: ListTodo },
  { to: "/historiku", label: "Historiku", icon: History },
];

const ADMIN_ITEMS = [
  { to: "/admin/dokumentet", label: "Dokumentet", icon: FileText },
  { to: "/admin/perdoruesit", label: "Përdoruesit", icon: Users },
  { to: "/admin/raportet", label: "Raporte & Statistika", icon: BarChart3 },
  { to: "/admin/audit", label: "Audit Log", icon: ClipboardList },
  { to: "/admin/eksperimentet", label: "Eksperimentet", icon: FlaskConical },
];

function NavSection({ title, items, onNavigate }: {
  title: string;
  items: typeof EMPLOYEE_ITEMS;
  onNavigate: () => void;
}) {
  return (
    <div>
      <p className="px-3 pb-1.5 pt-4 text-[11px] font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
        {title}
      </p>
      <ul className="space-y-0.5">
        {items.map(({ to, label, icon: Icon, end }) => (
          <li key={to}>
            <NavLink to={to} end={end} onClick={onNavigate}
                     className={({ isActive }) => cx(
                       "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                       isActive
                         ? "bg-brand-50 text-brand-800 dark:bg-brand-950 dark:text-brand-100"
                         : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100")}>
              <Icon className="h-4.5 w-4.5 shrink-0" aria-hidden />
              {label}
            </NavLink>
          </li>
        ))}
      </ul>
    </div>
  );
}

function SystemStatus({ isAdmin }: { isAdmin: boolean }) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { data } = useQuery({
    queryKey: ["system-status"],
    queryFn: metaApi.systemStatus,
    refetchInterval: 60_000,
  });

  // Admin-only model switching (parity with the legacy sidebar, but no longer
  // open to every user — the model affects everyone's answers).
  const setModel = useMutation({
    mutationFn: metaApi.setModel,
    onSuccess: (r) => {
      queryClient.invalidateQueries({ queryKey: ["system-status"] });
      toast("success", "Modeli u ndryshua", r.active_model);
    },
    onError: (err) => toast("error", "Ndërrimi i modelit dështoi",
                            err instanceof ApiError ? err.message : undefined),
  });

  return (
    <div className="mx-3 mb-3 rounded-xl border border-slate-200 p-3 text-xs dark:border-slate-800">
      <p className="font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
        Statusi i sistemit
      </p>
      <div className="mt-2 flex items-center gap-2">
        <span className={cx("h-2 w-2 rounded-full",
          data ? (data.ollama_online ? "bg-emerald-500" : "bg-red-500") : "bg-slate-300")}
          aria-hidden />
        <span className="text-slate-600 dark:text-slate-300">
          {data ? (data.ollama_online ? "Modeli lokal aktiv" : "Ollama jo aktiv") : "Duke kontrolluar…"}
        </span>
      </div>
      {data?.ollama_online && (
        isAdmin && data.models.length > 0 ? (
          <label className="mt-2 block">
            <span className="sr-only">Modeli i gjuhës</span>
            <select
              value={data.active_model}
              disabled={setModel.isPending}
              onChange={(e) => setModel.mutate(e.target.value)}
              className="w-full rounded-md border border-slate-200 bg-white px-1.5 py-1 text-xs text-slate-600 disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300"
              title="Ndrysho modelin lokal (ndikon përgjigjet e reja për të gjithë)">
              {data.models.map((m) => <option key={m}>{m}</option>)}
            </select>
          </label>
        ) : (
          <p className="mt-1.5 truncate text-slate-400 dark:text-slate-500" title={data.active_model}>
            Modeli: <span className="font-medium text-slate-500 dark:text-slate-400">{data.active_model}</span>
          </p>
        )
      )}
    </div>
  );
}

export function Sidebar({ mobileOpen, onClose }: { mobileOpen: boolean; onClose: () => void }) {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const content = (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-4 py-4">
        <div className="flex items-center gap-2.5">
          <img src="/doku.svg" alt="" className="h-8 w-8" />
          <div>
            <p className="text-lg font-extrabold leading-none tracking-tight text-brand-800 dark:text-brand-100">
              DOKU
            </p>
            <p className="mt-0.5 text-[10px] leading-tight text-slate-400 dark:text-slate-500">
              Analizë Inteligjente<br />Dokumentesh
            </p>
          </div>
        </div>
        <button onClick={onClose} aria-label="Mbyll menynë"
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 lg:hidden dark:hover:bg-slate-800">
          <X className="h-5 w-5" aria-hidden />
        </button>
      </div>

      <nav className="min-h-0 flex-1 overflow-y-auto px-3" aria-label="Navigimi kryesor">
        <NavSection title="Navigimi" items={EMPLOYEE_ITEMS} onNavigate={onClose} />
        {isAdmin && (
          <NavSection title="Administrimi" items={ADMIN_ITEMS} onNavigate={onClose} />
        )}
      </nav>

      <SystemStatus isAdmin={isAdmin} />
    </div>
  );

  return (
    <>
      {/* Desktop */}
      <aside className="hidden w-64 shrink-0 border-r border-slate-200 bg-white lg:block dark:border-slate-800 dark:bg-slate-900">
        {content}
      </aside>
      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-slate-950/50" onClick={onClose} aria-hidden />
          <aside className="absolute inset-y-0 left-0 w-72 max-w-[85vw] bg-white shadow-pop dark:bg-slate-900">
            {content}
          </aside>
        </div>
      )}
    </>
  );
}
