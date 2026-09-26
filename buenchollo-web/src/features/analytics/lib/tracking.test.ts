import { describe, expect, it } from "vitest";
import {
  getOrCreateSession,
  getOrCreateVisitor,
  isAnalyticsExcluded,
  setAnalyticsExcluded,
  resolveAttribution,
  SESSION_IDLE_MS,
  VISITOR_TTL_MS,
} from "./tracking";

class MemoryStorage implements Storage {
  private values = new Map<string, string>();

  get length() {
    return this.values.size;
  }

  clear() {
    this.values.clear();
  }

  getItem(key: string) {
    return this.values.get(key) ?? null;
  }

  key(index: number) {
    return [...this.values.keys()][index] ?? null;
  }

  removeItem(key: string) {
    this.values.delete(key);
  }

  setItem(key: string, value: string) {
    this.values.set(key, value);
  }
}

describe("resolveAttribution", () => {
  it("prioriza la etiqueta de Telegram sobre cualquier referente", () => {
    expect(
      resolveAttribution(
        new URL(
          "https://buenchollotech.com/?utm_source=telegram&utm_medium=social&utm_campaign=canal",
        ),
        "https://www.google.com/search?q=chollos",
        "buenchollotech.com",
      ),
    ).toEqual({
      source: "telegram",
      sourceDetail: "telegram",
      medium: "social",
      campaign: "canal",
      referrerHost: "google.com",
    });
  });

  it("clasifica como orgánica una entrada desde buscadores", () => {
    expect(
      resolveAttribution(
        new URL("https://buenchollotech.com/blog/guia-portatiles"),
        "https://www.google.es/search?q=portatiles",
        "buenchollotech.com",
      ),
    ).toMatchObject({ source: "organic", sourceDetail: "google", medium: "organic" });
  });

  it("no convierte la navegación interna en una nueva referencia", () => {
    expect(
      resolveAttribution(
        new URL("https://buenchollotech.com/blog"),
        "https://buenchollotech.com/",
        "buenchollotech.com",
      ),
    ).toMatchObject({ source: "direct", sourceDetail: "direct", medium: "none" });
  });
});

describe("identidades de analítica", () => {
  it("permite excluir y volver a incluir el dispositivo", () => {
    const storage = new MemoryStorage();

    setAnalyticsExcluded(storage, true);
    expect(isAnalyticsExcluded(storage)).toBe(true);

    setAnalyticsExcluded(storage, false);
    expect(isAnalyticsExcluded(storage)).toBe(false);
  });

  it("reutiliza el visitante hasta trece meses y lo renueva al expirar", () => {
    const storage = new MemoryStorage();
    const ids = ["visitor-a", "visitor-b"];
    const createId = () => ids.shift() as string;

    expect(getOrCreateVisitor(storage, 1_000, createId)).toBe("visitor-a");
    expect(getOrCreateVisitor(storage, 1_000 + VISITOR_TTL_MS - 1, createId)).toBe("visitor-a");
    expect(getOrCreateVisitor(storage, 1_000 + VISITOR_TTL_MS, createId)).toBe("visitor-b");
  });

  it("mantiene origen durante la sesión y crea otra tras treinta minutos", () => {
    const storage = new MemoryStorage();
    const ids = ["session-a", "session-b"];
    const telegram = {
      source: "telegram" as const,
      sourceDetail: "telegram",
      medium: "social",
      campaign: "canal",
      referrerHost: null,
    };
    const organic = {
      source: "organic" as const,
      sourceDetail: "google",
      medium: "organic",
      campaign: null,
      referrerHost: "google.com",
    };

    const first = getOrCreateSession(storage, telegram, 5_000, () => ids.shift() as string);
    const same = getOrCreateSession(
      storage,
      organic,
      5_000 + SESSION_IDLE_MS - 1,
      () => ids.shift() as string,
    );
    const renewed = getOrCreateSession(
      storage,
      organic,
      5_000 + SESSION_IDLE_MS * 2,
      () => ids.shift() as string,
    );

    expect(first).toMatchObject({ id: "session-a", attribution: telegram });
    expect(same).toMatchObject({ id: "session-a", attribution: telegram });
    expect(renewed).toMatchObject({ id: "session-b", attribution: organic });
  });
});
