// Edge function: autocompleta datos de un producto desde una URL de Amazon.
// Estrategia ligera (sin necesidad de API key de afiliado): hace fetch a la URL
// y extrae datos básicos del HTML (Open Graph + JSON-LD + selectores comunes).
// Si tienes acceso a la PA-API de Amazon, puedes sustituir esto por una llamada real.

import "https://deno.land/x/xhr@0.1.0/mod.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: corsHeaders });

  try {
    const { url } = await req.json();
    if (!url || typeof url !== "string") {
      return json({ ok: false, error: "URL no válida" }, 400);
    }

    const res = await fetch(url, {
      headers: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
      },
    });
    if (!res.ok) return json({ ok: false, error: `Amazon devolvió ${res.status}` }, 502);
    const html = await res.text();

    const pick = (re: RegExp) => {
      const m = html.match(re);
      return m ? decodeHtml(m[1].trim()) : null;
    };

    const title = pick(/<meta\s+property="og:title"\s+content="([^"]+)"/i)
      ?? pick(/<span[^>]+id="productTitle"[^>]*>([^<]+)</i);

    const image = pick(/<meta\s+property="og:image"\s+content="([^"]+)"/i)
      ?? pick(/"hiRes":"([^"]+)"/);

    const description = pick(/<meta\s+name="description"\s+content="([^"]+)"/i);

    const brand = pick(/"brand"\s*:\s*"([^"]+)"/)
      ?? pick(/id="bylineInfo"[^>]*>([^<]+)</i);

    // Precio: intentamos varias estructuras
    const priceWhole = pick(/class="a-price-whole"[^>]*>([\d.,]+)/);
    const priceFraction = pick(/class="a-price-fraction"[^>]*>(\d+)/);
    let current_price: number | null = null;
    if (priceWhole) {
      const whole = priceWhole.replace(/[.,]/g, "");
      current_price = parseFloat(`${whole}.${priceFraction ?? "00"}`);
    } else {
      const meta = pick(/"price"\s*:\s*"?(\d+[.,]?\d*)"?/);
      if (meta) current_price = parseFloat(meta.replace(",", "."));
    }

    const previousRaw = pick(/data-a-strike="true"[^>]*>.*?<span[^>]*>([\d.,]+\s*€?)/i)
      ?? pick(/class="a-text-strike"[^>]*>([\d.,]+\s*€?)/);
    let previous_price: number | null = null;
    if (previousRaw) {
      const num = previousRaw.replace(/[^\d,\.]/g, "").replace(",", ".");
      const v = parseFloat(num);
      if (!isNaN(v)) previous_price = v;
    }

    return json({
      ok: true,
      data: {
        title,
        short_description: description?.slice(0, 280) ?? null,
        image_url: image,
        brand,
        current_price,
        previous_price,
      },
    });
  } catch (e) {
    return json({ ok: false, error: (e as Error).message }, 500);
  }
});

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status, headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

function decodeHtml(s: string) {
  return s
    .replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&nbsp;/g, " ")
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(+n));
}
