import { describe, expect, it } from "vitest";

import { whatsappNotice } from "./whatsapp-notice";

describe("whatsappNotice", () => {
  it("explica adónde va la versión WhatsApp", () => {
    expect(whatsappNotice({ whatsapp_queued: true, whatsapp_sent: false })).toMatch(
      /Canal de WhatsApp/,
    );
    expect(whatsappNotice({ whatsapp_sent: true })).toMatch(/canal Admin, lista/);
    expect(whatsappNotice({})).toMatch(/no llegó/);
  });
});
