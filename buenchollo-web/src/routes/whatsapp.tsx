import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/whatsapp")({
  beforeLoad: () => {
    throw redirect({
      href: "/?utm_source=whatsapp&utm_medium=social&utm_campaign=canal",
      replace: true,
    });
  },
});
