import { createFileRoute, redirect } from "@tanstack/react-router";

// Enlace de la bio de Instagram: cuenta las visitas como fuente «instagram».
export const Route = createFileRoute("/instagram")({
  beforeLoad: () => {
    throw redirect({
      href: "/?utm_source=instagram&utm_medium=social&utm_campaign=bio",
      replace: true,
    });
  },
});
