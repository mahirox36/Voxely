export class WebSocketClient extends EventTarget {
  private ws: WebSocket;

  constructor(ws: WebSocket) {
    super();
    this.ws = ws;

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const type = data.t;
        this.dispatchEvent(new CustomEvent(type, { detail: data }));
      } catch {
        // ignore invalid messages
      }
    };
  }

  emit(type: string, payload?: Record<string, unknown>) {
    if (this.ws.readyState !== WebSocket.OPEN) {
      console.warn(`[ws.emit] Socket not open, dropping event: ${type}`);
      return;
    }
    this.ws.send(JSON.stringify({ t: type, ...payload }));
  }

  on(type: string, handler: (event: CustomEvent) => void) {
    this.addEventListener(type, handler as EventListener);
  }

  once(type: string, handler: (event: CustomEvent) => void) {
    const wrapper = (event: Event) => {
      this.removeEventListener(type, wrapper as EventListener);
      handler(event as CustomEvent);
    };

    this.addEventListener(type, wrapper as EventListener);
  }

  off(type: string, handler: (event: CustomEvent) => void) {
    this.removeEventListener(type, handler as EventListener);
  }

  get readyState() {
    return this.ws.readyState;
  }

  set onopen(h: typeof this.ws.onopen) {
    this.ws.onopen = h;
  }
  set onmessage(h: typeof this.ws.onmessage) {
    this.ws.onmessage = h;
  }
  set onclose(h: typeof this.ws.onclose) {
    this.ws.onclose = h;
  }
  set onerror(h: typeof this.ws.onerror) {
    this.ws.onerror = h;
  }
  close() {
    this.ws.close();
  }
}
