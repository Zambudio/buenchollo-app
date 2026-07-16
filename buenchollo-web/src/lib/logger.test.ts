import { afterEach, describe, expect, it, vi } from "vitest";

const { init, captureException, captureMessage } = vi.hoisted(() => ({
  init: vi.fn(),
  captureException: vi.fn(),
  captureMessage: vi.fn(),
}));
vi.mock("@sentry/react", () => ({ init, captureException, captureMessage }));

/** El módulo guarda estado (SDK inicializado o no): cada test carga una copia limpia. */
async function freshLogger() {
  vi.resetModules();
  return await import("./logger");
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.clearAllMocks();
});

describe("logError sin error tracking inicializado", () => {
  it("escribe en consola y no toca Sentry", async () => {
    const { logError } = await freshLogger();
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    logError("algo falló", new Error("boom"));
    expect(spy).toHaveBeenCalledWith("algo falló", expect.any(Error));
    expect(captureException).not.toHaveBeenCalled();
    spy.mockRestore();
  });
});

describe("initErrorTracking", () => {
  it("sin DSN queda inerte: no inicializa el SDK", async () => {
    vi.stubEnv("VITE_SENTRY_DSN", "");
    const { initErrorTracking } = await freshLogger();
    await initErrorTracking();
    expect(init).not.toHaveBeenCalled();
  });

  it("con DSN inicializa sin PII ni traces", async () => {
    vi.stubEnv("VITE_SENTRY_DSN", "https://key@sentry.test/1");
    const { initErrorTracking } = await freshLogger();
    await initErrorTracking();
    expect(init).toHaveBeenCalledWith(
      expect.objectContaining({
        dsn: "https://key@sentry.test/1",
        sendDefaultPii: false,
        tracesSampleRate: 0,
      }),
    );
  });

  it("tras inicializar, logError envía Error a captureException y strings a captureMessage", async () => {
    vi.stubEnv("VITE_SENTRY_DSN", "https://key@sentry.test/1");
    const mod = await freshLogger();
    await mod.initErrorTracking();
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    const err = new Error("boom");
    mod.logError("fallo cargando", err);
    expect(captureException).toHaveBeenCalledWith(err, { extra: { message: "fallo cargando" } });

    mod.logError("solo mensaje");
    expect(captureMessage).toHaveBeenCalledWith("solo mensaje", "error");

    mod.logError("con detalle", "detalle-no-error");
    expect(captureMessage).toHaveBeenCalledWith("con detalle — detalle-no-error", "error");
    spy.mockRestore();
  });
});
