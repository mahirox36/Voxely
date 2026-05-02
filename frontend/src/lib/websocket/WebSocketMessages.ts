import { WebSocketClient } from "./WebSocketClient";

interface MessageHandlerDeps {ws: WebSocketClient;}

export function createMessageHandler(deps: MessageHandlerDeps) {
  const {ws} = deps;

  return function handleMessage(data: Record<string, any>) {
    switch (data.t) {
      case "connection_success": {
        ws.emit("ping");
        const baseInterval = data.signal * 1000;
        const jitter = baseInterval * 0.2;

        function startPingLoop() {
          const interval = baseInterval + (Math.random() * jitter * 2 - jitter);
          setTimeout(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.emit("ping");
              startPingLoop();
            }
          }, interval);
        }

        startPingLoop();
        break;
      }
      
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
