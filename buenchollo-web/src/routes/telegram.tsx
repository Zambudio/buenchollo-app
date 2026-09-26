import { createFileRoute, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/telegram")({
  beforeLoad: () => {
    throw redirect({
      href: "/?utm_source=telegram&utm_medium=social&utm_campaign=canal",
      replace: true,
    });
  },
});
