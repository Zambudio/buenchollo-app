/**
 * Dominios permitidos para enlaces de afiliado manuales, mostrados en el
 * editor como ayuda inmediata al admin. La autoridad final es el backend
 * (`app/modules/blog/domain/affiliate_domains.py`); esta lista es solo para
 * dar feedback antes de guardar, sin viaje al servidor.
 */
export const ALLOWED_AFFILIATE_DOMAINS = [
  "amazon.es",
  "amzn.to",
  "amazon.com",
  "pccomponentes.com",
  "elcorteingles.es",
  "mediamarkt.es",
  "aliexpress.com",
  "s.click.aliexpress.com",
] as const;

export function extractDomain(url: string): string {
  try {
    const host = new URL(url).hostname.toLowerCase();
    return host.startsWith("www.") ? host.slice(4) : host;
  } catch {
    return "";
  }
}

export function isAllowedAffiliateDomain(url: string): boolean {
  const domain = extractDomain(url);
  return ALLOWED_AFFILIATE_DOMAINS.includes(domain as (typeof ALLOWED_AFFILIATE_DOMAINS)[number]);
}
