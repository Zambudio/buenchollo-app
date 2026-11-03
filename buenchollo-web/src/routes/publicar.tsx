import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { z } from "zod";
import { Layout } from "@/components/layout/Layout";
import { useAuth } from "@/hooks/useAuth";
import { SITE_URL } from "@/lib/site";
import { AuthRequiredDialog } from "@/features/submissions/components/AuthRequiredDialog";
import { LinkCheckStep } from "@/features/submissions/components/LinkCheckStep";
import type { LinkCheckResult } from "@/services/api/submissions";

const search = z.object({
  url: z.string().max(2048).optional(),
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

interface CheckedLink {
  url: string;
  result: LinkCheckResult;
}

function PublishPage() {
  const { user, me, loading: authLoading } = useAuth();
  const { url } = Route.useSearch();
  const [checked, setChecked] = useState<CheckedLink | null>(null);
  const [profileIncomplete, setProfileIncomplete] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(true);

  const prevNeeds = useRef(false);
  const needsOnboarding = Boolean(me?.needs_onboarding);
  useEffect(() => {
    if (prevNeeds.current && !needsOnboarding) setProfileIncomplete(false);
    prevNeeds.current = needsOnboarding;
  }, [needsOnboarding]);

  const redirectTo = url ? `/publicar?url=${encodeURIComponent(url)}` : "/publicar";
  const needsProfile = needsOnboarding || profileIncomplete;

  return (
    <Layout>
      <div className="max-w-2xl mx-auto px-4 sm:px-6 py-8">
        <div className="font-mono text-cyan-glow text-xs mb-2">&gt; PUBLICAR_CHOLLO</div>
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tighter mb-6">Comparte un chollo</h1>

        {authLoading ? null : !user ? (
          <>
            <p className="text-muted-foreground">
              Para compartir chollos con la comunidad necesitas una cuenta.
            </p>
            <AuthRequiredDialog
              open={dialogOpen}
              onOpenChange={setDialogOpen}
              redirectTo={redirectTo}
            />
          </>
        ) : needsProfile ? (
          <p role="status" className="border border-surface-700 bg-surface-800 p-4 text-sm">
            Completa tu perfil para poder compartir chollos
          </p>
        ) : checked ? (
          <div>Paso 2</div>
        ) : (
          <LinkCheckStep
            initialUrl={url ?? ""}
            onContinue={(result, checkedUrl) => setChecked({ url: checkedUrl, result })}
            onProfileIncomplete={() => setProfileIncomplete(true)}
          />
        )}
      </div>
    </Layout>
  );
}
