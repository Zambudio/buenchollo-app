import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "@/services/api/client";

function lastCall(fetchMock: ReturnType<typeof vi.fn>, index = 0) {
  const [url, init] = fetchMock.mock.calls[index] as [string, RequestInit];
  return { url, init, headers: init.headers as Record<string, string> };
}

const headerNames = (headers: Record<string, string>) =>
  Object.keys(headers).map((k) => k.toLowerCase());

describe("apiClient FormData", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    fetchMock.mockImplementation(() =>
      Promise.resolve(new Response(JSON.stringify({ ok: 1 }), { status: 200 })),
    );
    vi.stubGlobal("fetch", fetchMock);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("upload no fija Content-Type y envía el FormData por POST", async () => {
    const fd = new FormData();
    fd.append("file", new Blob(["x"]), "a.png");
    await apiClient.upload("/submissions/images", fd);
    const { url, init, headers } = lastCall(fetchMock);
    expect(url).toMatch(/\/v1\/submissions\/images$/);
    expect(init.method).toBe("POST");
    expect(init.body).toBe(fd);
    expect(headerNames(headers)).not.toContain("content-type");
  });

  it("upload usa timeout de 60 s salvo que se pase signal", async () => {
    const spy = vi.spyOn(AbortSignal, "timeout");
    await apiClient.upload("/x", new FormData());
    expect(spy).toHaveBeenCalledWith(60_000);
    spy.mockClear();
    const ctrl = new AbortController();
    await apiClient.upload("/x", new FormData(), { signal: ctrl.signal });
    expect(spy).not.toHaveBeenCalledWith(60_000);
    expect(lastCall(fetchMock, 1).init.signal).toBe(ctrl.signal);
  });

  it("post JSON sigue enviando Content-Type application/json", async () => {
    await apiClient.post("/x", { a: 1 });
    expect(lastCall(fetchMock).headers["Content-Type"]).toBe("application/json");
  });

  it("un body FormData en una petición cualquiera no lleva JSON content-type", async () => {
    await apiClient.get("/x", { method: "POST", body: new FormData() });
    expect(headerNames(lastCall(fetchMock).headers)).not.toContain("content-type");
  });
});
