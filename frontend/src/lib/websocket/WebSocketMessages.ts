import {
  Dispatch,
  RefObject,
  SetStateAction,
  useCallback,
  useEffect,
} from "react";

import { WebSocketClient } from "./WebSocketClient";

const MAX_CACHED_MESSAGES = 300;

interface MessageHandlerDeps {}

export function createMessageHandler(deps: MessageHandlerDeps) {
  const {} = deps;

  return function handleMessage(data: Record<string, any>) {
    switch (data.t) {
      case "example_event":
        // Handle the example_event message type
        console.log("Received example_event:", data);
        break;

      default:
        
        console.log("Unhandled WebSocket message:", data);
        break;
    }
  };
}
