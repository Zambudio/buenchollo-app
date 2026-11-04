import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useCallback } from "react";
import { SubmissionsAdminPage } from "@/features/admin/components/SubmissionsAdminPage";

export const Route = createFileRoute("/admin/propuestas")({
  validateSearch: (search: Record<string, unknown>): { id?: string } => ({
    id: typeof search.id === "string" && search.id ? search.id : undefined,
  }),
  component: AdminSubmissions,
});

function AdminSubmissions() {
  const { id } = Route.useSearch();
  const nav = useNavigate({ from: "/admin/propuestas" });
  const select = useCallback(
    (next: string | undefined) => {
      void nav({ search: { id: next } });
    },
    [nav],
  );
  return <SubmissionsAdminPage selectedId={id} onSelect={select} />;
}
