import { useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { Layout } from "@/components/layout/Layout";
import { useAuth } from "@/hooks/useAuth";
import { loginSearch } from "@/lib/safe-redirect";
import { MySubmissionsList } from "./MySubmissionsList";

export function MySubmissionsPage() {
  const { user, loading } = useAuth();
  const nav = useNavigate();

  useEffect(() => {
    if (!loading && !user) {
      nav({ to: "/login", search: loginSearch("/mis-chollos"), replace: true });
    }
  }, [loading, user, nav]);

  return (
    <Layout>
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
        <div className="font-mono text-cyan-glow text-xs mb-2">&gt; MIS_CHOLLOS</div>
        <h1 className="text-3xl font-bold tracking-tighter mb-6">Mis chollos</h1>
        {loading ? (
          <div role="status" aria-label="Cargando" className="space-y-3">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="h-24 bg-surface-800 border border-surface-700 animate-pulse"
              />
            ))}
          </div>
        ) : user ? (
          <MySubmissionsList />
        ) : null}
      </div>
    </Layout>
  );
}
