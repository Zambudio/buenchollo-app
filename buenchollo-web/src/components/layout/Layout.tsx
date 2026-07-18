import { ReactNode } from "react";
import { Header } from "./Header";
import { CategoryBar } from "./CategoryBar";
import { Footer } from "./Footer";
import { ScrollNav } from "./ScrollNav";
import { CookieBanner } from "./CookieBanner";

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-dvh flex flex-col bg-background text-foreground">
      <Header />
      <CategoryBar />
      <main className="flex-1">{children}</main>
      <Footer />
      <ScrollNav />
      <CookieBanner />
    </div>
  );
}
