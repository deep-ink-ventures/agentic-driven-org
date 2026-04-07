import { api } from "./api";

export const WS_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
  .replace("http://", "ws://")
  .replace("https://", "wss://");

/**
 * Connect to a WebSocket endpoint with ticket-based auth.
 * Returns the WebSocket instance. Caller is responsible for closing.
 */
export async function connectWs(
  path: string,
  onMessage: (data: Record<string, unknown>) => void,
  onError?: (e: Event) => void,
): Promise<WebSocket> {
  const { ticket } = await api.getWsTicket();
  const url = `${WS_URL}${path}?ticket=${ticket}`;
  const ws = new WebSocket(url);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage(data);
    } catch {
      // ignore non-JSON messages
    }
  };

  ws.onerror = (e) => {
    onError?.(e);
  };

  return ws;
}
