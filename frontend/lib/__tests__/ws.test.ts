import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock the api module
vi.mock("../api", () => ({
  api: {
    getWsTicket: vi.fn().mockResolvedValue({ ticket: "test-ticket-123" }),
  },
}));

// Mock WebSocket
class MockWebSocket {
  url: string;
  onopen: ((ev: Event) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  sent: string[] = [];

  constructor(url: string) {
    this.url = url;
    // Store for later triggering
    MockWebSocket.instances.push(this);
  }

  send(data: string) {
    this.sent.push(data);
  }

  close() {}

  // Simulate open
  simulateOpen() {
    this.onopen?.(new Event("open"));
  }

  simulateMessage(data: unknown) {
    this.onmessage?.(new MessageEvent("message", { data: JSON.stringify(data) }));
  }

  simulateError() {
    this.onerror?.(new Event("error"));
  }

  static instances: MockWebSocket[] = [];
  static clear() {
    MockWebSocket.instances = [];
  }
}

beforeEach(() => {
  MockWebSocket.clear();
  vi.stubGlobal("WebSocket", MockWebSocket);
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("connectWs", () => {
  it("connects to correct WS URL (http→ws replacement)", async () => {
    const { connectWs } = await import("../ws");

    const onMessage = vi.fn();
    const promise = connectWs("/ws/test/", onMessage);

    // Allow the promise to resolve (getWsTicket is async)
    const ws = await promise;

    expect(ws.url).toBe("ws://localhost:8000/ws/test/");
  });

  it("sends authenticate message with ticket as first message on open", async () => {
    const { connectWs } = await import("../ws");

    const onMessage = vi.fn();
    const ws = await connectWs("/ws/test/", onMessage);
    const mockWs = MockWebSocket.instances[MockWebSocket.instances.length - 1];

    // Simulate open
    mockWs.simulateOpen();

    expect(mockWs.sent).toHaveLength(1);
    expect(JSON.parse(mockWs.sent[0])).toEqual({
      type: "authenticate",
      ticket: "test-ticket-123",
    });
  });

  it("calls onMessage callback with parsed JSON data", async () => {
    const { connectWs } = await import("../ws");

    const onMessage = vi.fn();
    const ws = await connectWs("/ws/test/", onMessage);
    const mockWs = MockWebSocket.instances[MockWebSocket.instances.length - 1];

    mockWs.simulateMessage({ type: "update", payload: "hello" });

    expect(onMessage).toHaveBeenCalledWith({ type: "update", payload: "hello" });
  });

  it("calls onError callback on error", async () => {
    const { connectWs } = await import("../ws");

    const onMessage = vi.fn();
    const onError = vi.fn();
    const ws = await connectWs("/ws/test/", onMessage, onError);
    const mockWs = MockWebSocket.instances[MockWebSocket.instances.length - 1];

    mockWs.simulateError();

    expect(onError).toHaveBeenCalledTimes(1);
  });

  it("ignores non-JSON messages without crashing", async () => {
    const { connectWs } = await import("../ws");

    const onMessage = vi.fn();
    const ws = await connectWs("/ws/test/", onMessage);
    const mockWs = MockWebSocket.instances[MockWebSocket.instances.length - 1];

    // Send non-JSON
    mockWs.onmessage?.(new MessageEvent("message", { data: "not json" }));

    expect(onMessage).not.toHaveBeenCalled();
  });
});
