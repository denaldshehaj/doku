/* Authenticated application frame: sidebar + header + routed content + footer. */
import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { Header } from "./Header";

export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex h-full">
      <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header onOpenMenu={() => setMobileOpen(true)} />
        <main className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-6xl p-4 sm:p-6">
            <Outlet />
          </div>
          <footer className="border-t border-slate-200 py-4 text-center text-xs text-slate-400 dark:border-slate-800 dark:text-slate-600">
            DOKU — Sistem lokal për analizë dokumentesh institucionale · Asnjë e dhënë nuk del nga ky kompjuter
          </footer>
        </main>
      </div>
    </div>
  );
}
