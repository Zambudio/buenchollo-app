/** Motores de IA que acepta la API (`provider`: autocompletado y publicación de Telegram).
 *  Para añadir uno, basta con sumarlo aquí y en el Literal del backend. */
export const AI_PROVIDER_OPTIONS = [
  { value: "omniroute", label: "OmniRoute (Modelos Gratuitos)" },
  { value: "openai", label: "OpenAI (GPT-4o Oficial)" },
  { value: "auto", label: "Automático (OmniRoute + Fallback)" },
] as const;

export type AiProvider = (typeof AI_PROVIDER_OPTIONS)[number]["value"];

export const DEFAULT_AI_PROVIDER: AiProvider = "omniroute";

export function isAiProvider(value: unknown): value is AiProvider {
  return AI_PROVIDER_OPTIONS.some((o) => o.value === value);
}
