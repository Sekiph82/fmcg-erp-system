"use client";

import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { getMe, login as apiLogin, logout as apiLogout, User } from "@/lib/auth";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  hasPermission: (code: string) => boolean;
  completeTwoFA: (accessToken?: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const loadUser = useCallback(async () => {
    try {
      const me = await getMe();
      setUser(me);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadUser(); }, [loadUser]);

  const login = async (username: string, password: string) => {
    const res = await apiLogin(username, password);
    if (res.two_fa_required && res.session_token) {
      sessionStorage.setItem("2fa_session_token", res.session_token);
      sessionStorage.setItem("2fa_method", res.method || "totp");
      router.push("/auth/2fa");
      return;
    }
    const me = await getMe();
    setUser(me);
    router.push(res.must_change_password || me.must_change_password ? "/auth/change-password" : "/dashboard");
  };

  const completeTwoFA = async (_accessToken?: string) => {
    sessionStorage.removeItem("2fa_session_token");
    sessionStorage.removeItem("2fa_method");
    const me = await getMe();
    setUser(me);
    router.push(me.must_change_password ? "/auth/change-password" : "/dashboard");
  };

  const logout = async () => {
    try {
      await apiLogout();
    } catch {
      // Local cleanup still matters if the server session is already gone.
    }
    setUser(null);
    router.push("/login");
  };

  const hasPermission = (code: string): boolean => {
    if (!user) return false;
    if (user.is_superuser) return true;
    return user.permission_codes.includes(code);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, hasPermission, completeTwoFA }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
