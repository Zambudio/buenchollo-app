/** Espejo en TypeScript de `blog.domain.utils.slugify` del backend, para que
 * los anchors de la tabla de contenidos generados en el cliente coincidan
 * con los ids que devuelve la API (`toc[].id`). */
export function slugify(title: string): string {
  let slug = title.toLowerCase().trim();
  const accentMap: [string, string][] = [
    ["áàäâ", "a"],
    ["éèëê", "e"],
    ["íìïî", "i"],
    ["óòöô", "o"],
    ["úùüû", "u"],
    ["ñ", "n"],
  ];
  for (const [chars, replacement] of accentMap) {
    for (const ch of chars) slug = slug.split(ch).join(replacement);
  }
  slug = slug.replace(/[^a-z0-9\s-]/g, "");
  slug = slug.replace(/[\s_]+/g, "-").replace(/^-+|-+$/g, "");
  return slug;
}
