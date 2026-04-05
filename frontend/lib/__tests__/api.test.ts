import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// We need to import the module after mocking fetch
let api: (typeof import("../api"))["api"];
let getCsrfTokenModule: typeof import("../api");

beforeEach(async () => {
  vi.stubGlobal("fetch", vi.fn());
  // Dynamically import to get fresh module
  const mod = await import("../api");
  api = mod.api;
  getCsrfTokenModule = mod;
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

// ---------- getCsrfToken ----------
describe("getCsrfToken (tested indirectly via request)", () => {
  it("returns token from cookie and attaches it on POST", async () => {
    Object.defineProperty(document, "cookie", {
      value: "csrftoken=abc123; other=val",
      writable: true,
      configurable: true,
    });

    const mockResponse = new Response(JSON.stringify({ user: { id: "1" } }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
    vi.mocked(fetch).mockResolvedValue(mockResponse);

    await api.login("test@test.com", "pass");

    expect(fetch).toHaveBeenCalledTimes(1);
    const [, options] = vi.mocked(fetch).mock.calls[0];
    expect((options?.headers as Record<string, string>)["X-CSRFToken"]).toBe("abc123");
  });

  it("does not attach CSRF header on GET", async () => {
    Object.defineProperty(document, "cookie", {
      value: "csrftoken=abc123",
      writable: true,
      configurable: true,
    });

    const mockResponse = new Response(JSON.stringify({ user: null }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
    vi.mocked(fetch).mockResolvedValue(mockResponse);

    await api.getSession();

    const [, options] = vi.mocked(fetch).mock.calls[0];
    expect((options?.headers as Record<string, string>)["X-CSRFToken"]).toBeUndefined();
  });

  it("returns null when no csrf cookie exists", async () => {
    Object.defineProperty(document, "cookie", {
      value: "",
      writable: true,
      configurable: true,
    });

    const mockResponse = new Response(JSON.stringify({ user: null }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
    vi.mocked(fetch).mockResolvedValue(mockResponse);

    await api.getSession();

    // GET doesn't send CSRF anyway, but let's also test a POST with no cookie
    const mockResponse2 = new Response(JSON.stringify({}), { status: 200 });
    vi.mocked(fetch).mockResolvedValue(mockResponse2);

    await api.logout();
    const [, options] = vi.mocked(fetch).mock.calls[1];
    expect((options?.headers as Record<string, string>)["X-CSRFToken"]).toBeUndefined();
  });
});

// ---------- request ----------
describe("request", () => {
  it("includes credentials: include", async () => {
    const mockResponse = new Response(JSON.stringify([]), { status: 200 });
    vi.mocked(fetch).mockResolvedValue(mockResponse);

    await api.listProjects();

    const [, options] = vi.mocked(fetch).mock.calls[0];
    expect(options?.credentials).toBe("include");
  });

  it("adds CSRF header on POST/PUT/PATCH/DELETE", async () => {
    Object.defineProperty(document, "cookie", {
      value: "csrftoken=tok123",
      writable: true,
      configurable: true,
    });

    const methods = [
      () => api.login("a@b.com", "p"),
      () => api.updateAgent("1", { status: "active" }), // PATCH
      () => api.logout(), // POST (delete-like)
    ];

    for (const fn of methods) {
      const mockResponse = new Response(JSON.stringify({ user: { id: "1" } }), { status: 200 });
      vi.mocked(fetch).mockResolvedValue(mockResponse);
      await fn();
    }

    for (const call of vi.mocked(fetch).mock.calls) {
      const [, options] = call;
      expect((options?.headers as Record<string, string>)["X-CSRFToken"]).toBe("tok123");
    }
  });

  it("throws ApiError on non-ok response", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response("Not Found", { status: 404, statusText: "Not Found" }),
    );
    await expect(api.listProjects()).rejects.toThrow("Not Found");

    vi.mocked(fetch).mockResolvedValue(
      new Response("Not Found", { status: 404, statusText: "Not Found" }),
    );
    await expect(api.listProjects()).rejects.toMatchObject({ status: 404 });
  });

  it("retries once on network error", async () => {
    const mockResponse = new Response(JSON.stringify([]), { status: 200 });
    vi.mocked(fetch)
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce(mockResponse);

    vi.useFakeTimers();
    const promise = api.listProjects();
    // The retry has a 2s delay
    await vi.advanceTimersByTimeAsync(2000);
    const result = await promise;
    vi.useRealTimers();

    expect(fetch).toHaveBeenCalledTimes(2);
    expect(result).toEqual([]);
  });

  it("retries once on 503", async () => {
    const resp503 = new Response("Service Unavailable", {
      status: 503,
      statusText: "Service Unavailable",
    });
    const respOk = new Response(JSON.stringify([]), { status: 200 });
    vi.mocked(fetch).mockResolvedValueOnce(resp503).mockResolvedValueOnce(respOk);

    vi.useFakeTimers();
    const promise = api.listProjects();
    await vi.advanceTimersByTimeAsync(2000);
    const result = await promise;
    vi.useRealTimers();

    expect(fetch).toHaveBeenCalledTimes(2);
    expect(result).toEqual([]);
  });

  it("returns undefined for 204 responses", async () => {
    Object.defineProperty(document, "cookie", {
      value: "csrftoken=tok",
      writable: true,
      configurable: true,
    });
    const mockResponse = new Response(null, { status: 204 });
    Object.defineProperty(mockResponse, "ok", { value: true });
    vi.mocked(fetch).mockResolvedValue(mockResponse);

    const result = await api.logout();
    expect(result).toBeUndefined();
  });
});

// ---------- uploadFile ----------
describe("uploadFile", () => {
  it("rejects files with wrong extension", () => {
    const file = new File(["data"], "test.exe", { type: "application/octet-stream" });
    expect(() => api.uploadFile("proj1", file)).toThrow("File type 'exe' not allowed");
  });

  it("rejects files over 50MB", () => {
    const bigBuffer = new ArrayBuffer(51 * 1024 * 1024);
    const file = new File([bigBuffer], "big.pdf", { type: "application/pdf" });
    expect(() => api.uploadFile("proj1", file)).toThrow("File exceeds maximum size of 50MB");
  });

  it("sends FormData with correct fields for valid files", async () => {
    const file = new File(["hello"], "doc.pdf", { type: "application/pdf" });
    const mockResponse = new Response(JSON.stringify({ id: "s1" }), { status: 200 });
    vi.mocked(fetch).mockResolvedValue(mockResponse);

    await api.uploadFile("proj1", file);

    const [url, options] = vi.mocked(fetch).mock.calls[0];
    expect(url).toContain("/api/projects/proj1/sources/");
    expect(options?.body).toBeInstanceOf(FormData);
    const fd = options?.body as FormData;
    expect(fd.get("file")).toBeInstanceOf(File);
    expect(fd.get("source_type")).toBe("file");
    // FormData body should NOT get Content-Type header set (browser sets it with boundary)
    expect((options?.headers as Record<string, string>)["Content-Type"]).toBeUndefined();
  });
});

// ---------- api.login / api.logout ----------
describe("api.login", () => {
  it("sends POST to /api/auth/login/", async () => {
    const mockResponse = new Response(JSON.stringify({ user: { id: "1" } }), { status: 200 });
    vi.mocked(fetch).mockResolvedValue(mockResponse);

    await api.login("user@test.com", "secret");

    const [url, options] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("http://localhost:8000/api/auth/login/");
    expect(options?.method).toBe("POST");
    expect(JSON.parse(options?.body as string)).toEqual({
      email: "user@test.com",
      password: "secret",
    });
  });
});

describe("api.logout", () => {
  it("sends POST to /api/auth/logout/", async () => {
    const mockResponse = new Response(null, { status: 204 });
    Object.defineProperty(mockResponse, "ok", { value: true });
    vi.mocked(fetch).mockResolvedValue(mockResponse);

    await api.logout();

    const [url, options] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("http://localhost:8000/api/auth/logout/");
    expect(options?.method).toBe("POST");
  });
});
