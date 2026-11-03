import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { Layout } from "@/components/layout/Layout";
import { useAuth } from "@/hooks/useAuth";
import { loginSearch } from "@/lib/safe-redirect";
import { MySubmissionsList } from "@/features/submissions/components/MySubmissionsList";

export const Route = createFileRoute("/mis-chollos")({
  component: MySubmissionsPage,
  head: () => ({
    meta: [
      { title: "Mis chollos · BuenChollo Tech" },
      { name: "robots", content: "noindex, nofollow" },
    ],
  }),
});

function MySubmissionsPage() {
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
        {user ? <MySubmissionsList /> : null}
      </div>
    </Layout>
  );
}
