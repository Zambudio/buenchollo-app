import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from "react";
import { supabase } from "@/integrations/supabase/client";
import type { Session, User } from "@supabase/supabase-js";
import { authApi, type MeResponse } from "@/services/api/auth";

interface AuthContextValue {
  user: User | null;
  session: Session | null;
  me: MeResponse | null;
  isAdmin: boolean;
  loading: boolean;
  refreshMe: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [me, setMe] = useState<MeResponse | null>(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadMe = useCallback(async (sess: Session | null) => {
    if (!sess?.user) {
      setMe(null);
      setIsAdmin(false);
      return;
    }

    try {
      const nextMe = await authApi.me();
      setMe(nextMe);
      setIsAdmin(nextMe.is_admin);
    } catch {
      setMe(null);
      setIsAdmin(false);
    }
  }, []);

  const refreshMe = useCallback(async () => {
    await loadMe(session);
  }, [loadMe, session]);

  useEffect(() => {
    // 1) Listener primero
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, sess) => {
      setSession(sess);
      setUser(sess?.user ?? null);
      // diferimos para evitar carreras con el cliente HTTP
      setTimeout(() => {
        void loadMe(sess);
      }, 0);
    });

    // 2) Sesión existente
    supabase.auth.getSession().then(({ data: { session: sess } }) => {
      setSession(sess);
      setUser(sess?.user ?? null);
      void loadMe(sess).finally(() => setLoading(false));
    });

    return () => subscription.unsubscribe();
  }, [loadMe]);

  const signOut = async () => {
    await supabase.auth.signOut();
  };

  return (
    <AuthContext.Provider value={{ user, session, me, isAdmin, loading, refreshMe, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
