import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FACEBOOK_URL, INSTAGRAM_URL, TELEGRAM_URL, WHATSAPP_URL } from "@/lib/site";
import { SocialLinks } from "./SocialLinks";

describe("SocialLinks", () => {
  it("enlaza los cuatro canales propios solo con el icono", () => {
    render(<SocialLinks />);
    const links = screen.getAllByRole("link");
    expect(links.map((a) => a.getAttribute("href"))).toEqual([
      FACEBOOK_URL,
      INSTAGRAM_URL,
      TELEGRAM_URL,
      WHATSAPP_URL,
    ]);
    for (const link of links) {
      expect(link).toHaveAttribute("target", "_blank");
      expect(link).toHaveAccessibleName(/BuenChollo Tech en/);
      expect(link.textContent).toBe("");
    }
  });
});
