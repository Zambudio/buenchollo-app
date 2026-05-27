// Edge function: publica un chollo en el canal de Telegram configurado.
// Requiere los secretos TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID.
// Si no están configurados, devuelve un error claro pero no rompe el guardado.

import "https://deno.land/x/xhr@0.1.0/mod.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

interface DealPayload {
  title: string;
  current_price: number;
  previous_price?: number | null;
  discount_percentage?: number | null;
  short_description?: string | null;
  image_url?: string | null;
  affiliate_url: string;
  public_url?: string | null;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });

  try {
    const TOKEN = Deno.env.get("TELEGRAM_BOT_TOKEN");
    const CHAT_ID = Deno.env.get("TELEGRAM_CHAT_ID");
    if (!TOKEN || !CHAT_ID) {
      return new Response(
        JSON.stringify({ ok: false, error: "Faltan los secretos TELEGRAM_BOT_TOKEN y/o TELEGRAM_CHAT_ID" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } },
      );
    }

    const deal = (await req.json()) as DealPayload;

    const price = `${deal.current_price.toFixed(2).replace(".", ",")}€`;
    const prev = deal.previous_price ? ` <s>${deal.previous_price.toFixed(2).replace(".", ",")}€</s>` : "";
    const disc = deal.discount_percentage ? ` (-${deal.discount_percentage}%)` : "";

    const lines = [
      `🔥 <b>${escapeHtml(deal.title)}</b>`,
      "",
      `💰 <b>${price}</b>${prev}${disc}`,
    ];
    if (deal.short_description) lines.push("", escapeHtml(deal.short_description));
    lines.push("", `🛒 <a href="${deal.affiliate_url}">Ver chollo</a>`);
    if (deal.public_url) lines.push(`💬 <a href="${deal.public_url}">Comentarios</a>`);

    const text = lines.join("\n");

    // Si hay imagen, mandamos foto; si no, mensaje normal
    const endpoint = deal.image_url
      ? `https://api.telegram.org/bot${TOKEN}/sendPhoto`
      : `https://api.telegram.org/bot${TOKEN}/sendMessage`;

    const body = deal.image_url
      ? { chat_id: CHAT_ID, photo: deal.image_url, caption: text, parse_mode: "HTML" }
      : { chat_id: CHAT_ID, text, parse_mode: "HTML", disable_web_page_preview: false };

    const tg = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await tg.json();
    if (!tg.ok || !data.ok) {
      return new Response(JSON.stringify({ ok: false, error: data.description ?? "Error de Telegram" }), {
        status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    return new Response(JSON.stringify({ ok: true, message_id: data.result?.message_id }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    return new Response(JSON.stringify({ ok: false, error: (e as Error).message }), {
      status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});

function escapeHtml(s: string) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
