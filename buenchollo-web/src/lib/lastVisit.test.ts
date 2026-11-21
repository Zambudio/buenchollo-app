import { beforeEach, describe, expect, it } from "vitest";
import {
  VISIT_GAP_MS,
  VISIT_KEY,
  nextVisitState,
  resetVisitBaselineCache,
  touchVisit,
  visitBaseline,
} from "./lastVisit";

const at = (iso: string) => new Date(iso);

describe("nextVisitState", () => {
  it("la primera visita no tiene referencia", () => {
    expect(nextVisitState(null, at("2026-11-21T10:00:00Z"))).toEqual({
      baseline: null,
      lastSeen: "2026-11-21T10:00:00.000Z",
    });
  });

  it("dentro de la misma visita conserva la referencia", () => {
    const stored = { baseline: "2026-11-20T08:00:00.000Z", lastSeen: "2026-11-21T10:00:00.000Z" };
    const next = nextVisitState(stored, at("2026-11-21T10:20:00Z"));
    expect(next.baseline).toBe("2026-11-20T08:00:00.000Z");
    expect(next.lastSeen).toBe("2026-11-21T10:20:00.000Z");
  });

  it("tras 30 minutos sin actividad la referencia pasa a ser el final de la visita anterior", () => {
    const stored = { baseline: "2026-11-20T08:00:00.000Z", lastSeen: "2026-11-21T10:00:00.000Z" };
    const later = new Date(at("2026-11-21T10:00:00Z").getTime() + VISIT_GAP_MS);
    expect(nextVisitState(stored, later).baseline).toBe("2026-11-21T10:00:00.000Z");
  });

  it("un reloj que va hacia atrás cuenta como visita nueva", () => {
    const stored = { baseline: null, lastSeen: "2026-11-21T10:00:00.000Z" };
    expect(nextVisitState(stored, at("2026-11-21T09:00:00Z")).baseline).toBe(
      "2026-11-21T10:00:00.000Z",
    );
  });
});

describe("visitBaseline", () => {
  beforeEach(() => {
    window.localStorage.clear();
    resetVisitBaselineCache();
  });

  it("guarda la visita y devuelve la referencia de la anterior", () => {
    window.localStorage.setItem(
      VISIT_KEY,
      JSON.stringify({ baseline: null, lastSeen: "2026-11-20T08:00:00.000Z" }),
    );
    expect(visitBaseline(at("2026-11-21T10:00:00Z"))?.toISOString()).toBe(
      "2026-11-20T08:00:00.000Z",
    );
    const saved = JSON.parse(window.localStorage.getItem(VISIT_KEY) ?? "{}");
    expect(saved.lastSeen).toBe("2026-11-21T10:00:00.000Z");
  });

  it("navegar mantiene viva la visita y no cambia la referencia", () => {
    window.localStorage.setItem(
      VISIT_KEY,
      JSON.stringify({
        baseline: "2026-11-19T08:00:00.000Z",
        lastSeen: "2026-11-21T10:00:00.000Z",
      }),
    );
    // Navegación a los 25 min y a los 50 min: nunca hay 30 min seguidos sin actividad.
    touchVisit(at("2026-11-21T10:25:00Z"));
    touchVisit(at("2026-11-21T10:50:00Z"));
    const saved = JSON.parse(window.localStorage.getItem(VISIT_KEY) ?? "{}");
    expect(saved).toEqual({
      baseline: "2026-11-19T08:00:00.000Z",
      lastSeen: "2026-11-21T10:50:00.000Z",
    });
  });

  it("ignora un valor guardado corrupto", () => {
    window.localStorage.setItem(VISIT_KEY, "{no es json");
    expect(visitBaseline(at("2026-11-21T10:00:00Z"))).toBeNull();
  });
});
