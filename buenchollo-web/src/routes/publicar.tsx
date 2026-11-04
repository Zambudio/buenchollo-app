import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { z } from "zod";
import { Layout } from "@/components/layout/Layout";
import { useAuth } from "@/hooks/useAuth";
import { SITE_URL } from "@/lib/site";
import { loginSearch } from "@/lib/safe-redirect";
import { AuthRequiredDialog } from "@/features/submissions/components/AuthRequiredDialog";
import { LinkCheckStep } from "@/features/submissions/components/LinkCheckStep";
import { SubmissionForm } from "@/features/submissions/components/SubmissionForm";
import type { LinkCheckResult } from "@/services/api/submissions";

// TanStack parsea los search params como JSON (`?url=123` llega como número):
// cualquier valor que no sea un string válido se ignora en vez de romper la ruta.
const search = z.object({
  url: z.string().max(2048).optional().catch(undefined),
});

export const Route = createFileRoute("/publicar")({
  component: PublishPage,
  validateSearch: (s) => search.parse(s),
  head: () => ({
    meta: [
      { title: "Publicar chollo · BuenChollo Tech" },
      {
        name: "description",
        content: "Comparte un chollo de tecnología con la comunidad de BuenChollo Tech.",
      },
      { property: "og:title", content: "Publicar chollo · BuenChollo Tech" },
      { property: "og:url", content: `${SITE_URL}/publicar` },
      { name: "robots", content: "noindex, nofollow" },
    ],
    links: [{ rel: "canonical", href: `${SITE_URL}/publicar` }],
  }),
});

type Step =
  | { kind: "check"; url: string; result: LinkCheckResult | null; key: number }
  | { kind: "form"; url: string; result: LinkCheckResult; key: number };

function PublishPage() {
  const { user, me, loading: authLoading, refreshMe } = useAuth();
  const { url } = Route.useSearch();
  const nav = useNavigate();
  const [step, setStep] = useState<Step | null>(null);
  // `me` en el momento del 403 PROFILE_INCOMPLETE. El aviso se mantiene
  // mientras `me` no se refresque; después manda `me.needs_onboarding`.
  const [incompleteFor, setIncompleteFor] = useState<object | null | undefined>(undefined);
  const [dialogOpen, setDialogOpen] = useState(true);

  const redirectTo = url ? `/publicar?url=${encodeURIComponent(url)}` : "/publicar";
  const needsOnboarding = Boolean(me?.needs_onboarding);
  const needsProfile = needsOnboarding || (incompleteFor !== undefined && incompleteFor === me);
  const current: Step = step ?? { kind: "check", url: url ?? "", result: null, key: 0 };
  const authSearch = loginSearch(redirectTo);

  const goToCheck = (checkUrl: string, result: LinkCheckResult | null) =>
    setStep({ kind: "check", url: checkUrl, result, key: current.key + 1 });

  const publishAnother = () => {
    setStep({ kind: "check", url: "", result: null, key: current.key + 1 });
    void nav({ to: "/publicar", search: {}, replace: true });
  };

  const markIncomplete = () => setIncompleteFor(me);

  return (
    <Layout>
      <div
        className={`${current.kind === "form" ? "max-w-6xl" : "max-w-2xl"} mx-auto px-4 sm:px-6 py-8`}
      >
        <div className="font-mono text-cyan-glow text-xs mb-2">&gt; PUBLICAR_CHOLLO</div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tighter mb-6">Comparte un chollo</h1>

        {authLoading ? null : !user ? (
          <div className="space-y-4">
            <p className="text-muted-foreground">
              Para compartir chollos con la comunidad necesitas una cuenta.
            </p>
            <div className="flex flex-col sm:flex-row gap-2">
              <Link
                to="/registro"
                search={authSearch}
                className="text-center bg-cyan-glow text-surface-900 font-mono text-xs font-bold px-6 py-3 hover:bg-foreground transition-colors"
              >
                Crear cuenta
              </Link>
              <Link
                to="/login"
                search={authSearch}
                className="text-center border border-surface-600 bg-surface-900 text-foreground font-mono text-xs font-bold px-6 py-3 hover:border-cyan-glow transition-colors"
              >
                Iniciar sesión
              </Link>
            </div>
            <AuthRequiredDialog
              open={dialogOpen}
              onOpenChange={setDialogOpen}
              redirectTo={redirectTo}
            />
          </div>
        ) : needsProfile ? (
          <div
            role="status"
            className="border border-surface-700 bg-surface-800 p-4 text-sm space-y-3"
          >
            <p>Completa tu perfil para poder compartir chollos</p>
            <button
              type="button"
              onClick={() => {
                setIncompleteFor(undefined);
                void refreshMe();
              }}
              className="font-mono text-xs font-bold text-cyan-glow hover:underline"
            >
              Ya lo he completado, reintentar
            </button>
          </div>
        ) : current.kind === "form" ? (
          <SubmissionForm
            key={current.key}
            url={current.url}
            result={current.result}
            onBack={() => goToCheck(current.url, null)}
            onDuplicate={(result) => goToCheck(current.url, result)}
            onPublishAnother={publishAnother}
            onProfileIncomplete={() => {
              void refreshMe();
              markIncomplete();
            }}
          />
        ) : (
          <LinkCheckStep
            key={current.key}
            initialUrl={current.url}
            initialResult={current.result}
            onContinue={(result, checkedUrl) =>
              setStep({ kind: "form", url: checkedUrl, result, key: current.key + 1 })
            }
            onProfileIncomplete={markIncomplete}
          />
        )}
      </div>
    </Layout>
  );
}
