import { createFileRoute, redirect } from "@tanstack/react-router";

// Enlace de los posts de la página de Facebook: cuenta las visitas como fuente «facebook».
export const Route = createFileRoute("/facebook")({
  beforeLoad: () => {
    throw redirect({
      href: "/?utm_source=facebook&utm_medium=social&utm_campaign=pagina",
      replace: true,
    });
  },
});
