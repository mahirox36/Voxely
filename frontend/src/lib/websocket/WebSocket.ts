import { useRef, RefObject } from "react";
import { createMessageHandler } from "./WebSocketMessages";
import { Dispatch, SetStateAction } from "react";
import { WebSocketClient } from "./WebSocketClient";
import { baseURL } from "@/utils/api";

const MAX_RECONNECT_ATTEMPTS = 8;
const BASE_RECONNECT_DELAY_MS = 1000;



interface UseWebSocketOptions {}

interface UseWebSocketReturn {
  socket: RefObject<WebSocketClient | null>;
  connect: () => void;
  disconnect: () => void;
}

export function useWebSocket({}: UseWebSocketOptions): UseWebSocketReturn {
  const socket = useRef<WebSocketClient | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldReconnect = useRef(true);

  const connect = () => {
    if (socket.current?.readyState === WebSocket.OPEN) return;

    const wsProtocol = window.location.protocol === "https:" ? "wss" : "ws";
    const token = localStorage.getItem("token")
    const ws = new WebSocketClient(
      new WebSocket(`${wsProtocol}://${baseURL}/ws?token=${token}`),
    );

    const handleMessage = createMessageHandler({ws});

    ws.onopen = () => {
      socket.current = ws;
      reconnectAttempts.current = 0;
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleMessage(data);
    };

    ws.onclose = (event) => {
      socket.current = null;
      if (!shouldReconnect.current) return;
      if (!window.location.pathname.startsWith("/app")) return;
      if (reconnectAttempts.current >= MAX_RECONNECT_ATTEMPTS) {
        console.error("WebSocket max reconnect attempts reached. Giving up.");
        return;
      }


      const delay = Math.min(
        BASE_RECONNECT_DELAY_MS * 2 ** reconnectAttempts.current +
          Math.random() * 500,
        30_000,
      );
      reconnectAttempts.current += 1;

      console.log(
        `WebSocket closed (code ${event.code}). Reconnecting in ${Math.round(delay)}ms… ` +
          `(attempt ${reconnectAttempts.current}/${MAX_RECONNECT_ATTEMPTS})`,
      );

      reconnectTimeout.current = setTimeout(connect, delay);
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  };

  const disconnect = () => {
    shouldReconnect.current = false;
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }
    if (socket.current) {
      socket.current.close();
      socket.current = null;
    }
  };

  return { socket, connect, disconnect };
}
