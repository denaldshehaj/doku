/* Route guards — the UI mirror of the server-side deps (require_user /
 * require_admin). Real enforcement lives in the API; these only shape UX. */
import type { ReactNode } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/providers/AuthProvider";
import { Spinner } from "@/components/ui/misc";

function FullScreenLoading() {
  return (
    <div className="flex h-full items-center justify-center">
      <Spinner label="Duke ngarkuar sesionin…" />
    </div>
  );
}

/** Logged-in + password already changed → app; otherwise redirect. */
export function RequireAuth({ children }: { children?: ReactNode }) {
  const { user } = useAuth();
  const location = useLocation();
  if (user === undefined) return <FullScreenLoading />;
  if (user === null) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  if (user.must_change_password) {
    return <Navigate to="/ndrysho-fjalekalimin" replace />;
  }
  return children ?? <Outlet />;
}

export function RequireAdmin() {
  const { user } = useAuth();
  if (user === undefined) return <FullScreenLoading />;
  if (user === null) return <Navigate to="/login" replace />;
  if (user.role !== "admin") return <Navigate to="/" replace />;
  return <Outlet />;
}

/** Login page: bounce straight to the app when a session already exists. */
export function RedirectIfAuthenticated({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  if (user === undefined) return <FullScreenLoading />;
  if (user) {
    return <Navigate to={user.must_change_password ? "/ndrysho-fjalekalimin" : "/"} replace />;
  }
  return children;
}

/** Forced password change: needs a session, but only shows when required. */
export function RequirePasswordChange({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  if (user === undefined) return <FullScreenLoading />;
  if (user === null) return <Navigate to="/login" replace />;
  if (!user.must_change_password) return <Navigate to="/" replace />;
  return children;
}
