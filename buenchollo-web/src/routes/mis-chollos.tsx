import { createFileRoute } from "@tanstack/react-router";
import { MySubmissionsPage } from "@/features/submissions/components/MySubmissionsPage";

export const Route = createFileRoute("/mis-chollos")({
  component: MySubmissionsPage,
  head: () => ({
    meta: [
      { title: "Mis chollos · BuenChollo Tech" },
      { name: "robots", content: "noindex, nofollow" },
    ],
  }),
});
