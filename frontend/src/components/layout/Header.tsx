/* Top bar: mobile menu button, security tagline, theme toggle, user menu. */
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronDown, LogOut, Menu, Moon, ShieldCheck, Sun, UserCircle2 } from "lucide-react";
import { useAuth } from "@/providers/AuthProvider";
import { useTheme } from "@/providers/ThemeProvider";
import { useToast } from "@/providers/ToastProvider";

const ROLE_LABELS: Record<string, string> = { admin: "Administrator", punonjes: "Punonjës" };

export function Header({ onOpenMenu }: { onOpenMenu: () => void }) {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const onClick = (e: MouseEvent) => {
      if (!menuRef.current?.contains(e.target as Node)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [menuOpen]);

  const onLogout = async () => {
    try {
      await logout();
      navigate("/login", { replace: true });
    } catch {
      toast("error", "Dalja dështoi", "Provo përsëri.");
    }
  };

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-3 border-b border-slate-200 bg-white/90 px-4 backdrop-blur dark:border-slate-800 dark:bg-slate-900/90">
      <div className="flex items-center gap-3">
        <button onClick={onOpenMenu} aria-label="Hap menynë"
                className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 lg:hidden dark:hover:bg-slate-800">
          <Menu className="h-5 w-5" aria-hidden />
        </button>
        <div className="hidden items-center gap-1.5 text-xs text-slate-400 sm:flex dark:text-slate-500">
          <ShieldCheck className="h-4 w-4" aria-hidden />
          I sigurt. Konfidencial. Institucional.
        </div>
      </div>

      <div className="flex items-center gap-1.5">
        <button onClick={toggle}
                aria-label={theme === "dark" ? "Kalo në modalitet të çelët" : "Kalo në modalitet të errët"}
                className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800">
          {theme === "dark" ? <Sun className="h-5 w-5" aria-hidden /> : <Moon className="h-5 w-5" aria-hidden />}
        </button>

        <div className="relative" ref={menuRef}>
          <button onClick={() => setMenuOpen((v) => !v)}
                  aria-haspopup="menu" aria-expanded={menuOpen}
                  className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-slate-100 dark:hover:bg-slate-800">
            <UserCircle2 className="h-6 w-6 text-brand-700 dark:text-brand-300" aria-hidden />
            <span className="hidden text-left sm:block">
              <span className="block text-sm font-semibold leading-tight text-slate-800 dark:text-slate-100">
                {user?.full_name || user?.username}
              </span>
              <span className="block text-[11px] leading-tight text-slate-400 dark:text-slate-500">
                {ROLE_LABELS[user?.role ?? ""] ?? user?.role}
              </span>
            </span>
            <ChevronDown className="h-4 w-4 text-slate-400" aria-hidden />
          </button>
          {menuOpen && (
            <div role="menu"
                 className="absolute right-0 mt-1.5 w-48 overflow-hidden rounded-xl border border-slate-200 bg-white py-1 shadow-pop dark:border-slate-700 dark:bg-slate-900">
              <div className="border-b border-slate-100 px-3 py-2 sm:hidden dark:border-slate-800">
                <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                  {user?.full_name || user?.username}
                </p>
                <p className="text-xs text-slate-400">{ROLE_LABELS[user?.role ?? ""]}</p>
              </div>
              <button role="menuitem" onClick={onLogout}
                      className="flex w-full items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950">
                <LogOut className="h-4 w-4" aria-hidden />
                Dil nga sistemi
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
