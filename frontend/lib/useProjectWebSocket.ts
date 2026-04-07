"use client";

import { useEffect, useRef } from "react";
import { api } from "./api";

const WS_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000")
  .replace("http://", "ws://")
  .replace("https://", "wss://");

const MAX_RETRIES = 20;
const BACKOFF_CAP_MS = 30_000;

function backoffMs(attempt: number): number {
  return Math.min(1000 * 2 ** attempt, BACKOFF_CAP_MS);
}

/**
 * Manages a reconnecting WebSocket connection for a project.
 * Fetches a fresh ticket on each connection attempt.
 * Logs every state transition to the console.
 */
export function useProjectWebSocket(
  projectId: string | null,
  onMessage: (data: Record<string, unknown>) => void,
): void {
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    if (!projectId) return;

    let ws: WebSocket | null = null;
    let attempt = 0;
    let timer: ReturnType<typeof setTimeout> | null = null;
    let stopped = false;

    const path = `/ws/project/${projectId}/`;

    async function connect() {
      if (stopped) return;

      console.log(`[WS] connecting to ${path}... (attempt ${attempt + 1}/${MAX_RETRIES})`);

      let ticket: string;
      try {
        const resp = await api.getWsTicket();
        ticket = resp.ticket;
      } catch (err) {
        console.warn(`[WS] ticket fetch failed:`, err);
        scheduleReconnect();
        return;
      }

      if (stopped) return;

      const url = `${WS_URL}${path}?ticket=${ticket}`;
      ws = new WebSocket(url);

      ws.onopen = () => {
        console.log(`[WS] connected to ${path}`);
        attempt = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onMessageRef.current(data);
        } catch {
          // ignore non-JSON messages
        }
      };

      ws.onclose = (event) => {
        if (stopped) return;
        console.warn(`[WS] disconnected (code: ${event.code}), scheduling reconnect`);
        ws = null;
        scheduleReconnect();
      };

      ws.onerror = () => {
        // onerror is always followed by onclose — let onclose handle reconnect
      };
    }

    function scheduleReconnect() {
      if (stopped) return;
      attempt += 1;
      if (attempt > MAX_RETRIES) {
        console.error(`[WS] max retries (${MAX_RETRIES}) reached, giving up`);
        return;
      }
      const delay = backoffMs(attempt - 1);
      console.log(`[WS] reconnecting in ${delay}ms (attempt ${attempt}/${MAX_RETRIES})`);
      timer = setTimeout(connect, delay);
    }

    connect();

    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
      console.log(`[WS] cleanup for ${path}`);
    };
  }, [projectId]);
}
