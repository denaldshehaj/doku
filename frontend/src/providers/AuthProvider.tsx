/* Session state: loads /api/auth/me once on mount, exposes login/logout/refresh.
 * A global 401 event (fired by the API client) clears the user, so an expired
 * session anywhere in the app lands on /login without bespoke handling. */
import { createContext, useCallback, useContext, useEffect, useState,
  type ReactNode } from "react";
import { UNAUTHORIZED_EVENT } from "@/api/client";
import { authApi } from "@/api/endpoints";
import type { User } from "@/api/types";

interface AuthContextValue {
  /** undefined = still loading, null = not logged in */
  user: User | null | undefined;
  login: (username: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  setUser: (u: User | null) => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null | undefined>(undefined);

  useEffect(() => {
    authApi.me().then(setUser).catch(() => setUser(null));
  }, []);

  useEffect(() => {
    const onUnauthorized = () => setUser(null);
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const u = await authApi.login(username, password);
    setUser(u);
    return u;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setUser(null);
    }
  }, []);

  const refresh = useCallback(async () => {
    setUser(await authApi.me().catch(() => null));
  }, []);

  return (
    <AuthContext.Provider value={{ user, login, logout, refresh, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth duhet përdorur brenda AuthProvider.");
  return ctx;
}
