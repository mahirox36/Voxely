// Standard server response type
export interface ServerResponse {
  name: string;
  status: string;
  type: string;
  version: string;
  metrics: {
    cpu_usage: string;
    memory_usage: string;
    player_count: string;
    uptime: string;
  };
  port: number;
  maxPlayers: number;
  players?: string[];
  ip?: {
    private: string;
    public: string;
  };
}

// Server creation request
export interface CreateServerRequest {
  name: string;
  type: string;
  version: string;
  minRam: number;
  maxRam: number;
  port: number;
  maxPlayers: number;
}

export interface ServerFile {
  path: string;
  name: string;
  type: "directory" | "file";
  size?: number | null;
  modified: string;
}

// The change event sent from backend
export interface FileChangeEvent {
  event: "added" | "modified" | "deleted";
  path: string;
}

// Message types that can arrive through the websocket
export type SocketMessage =
  | {
      type: "file_init";
      data: ServerFile[];
    }
  | {
      type: "file_update";
      data: ServerFile[];
      changes: FileChangeEvent[];
    }
  | {
      type: "error";
      data: string;
    }
  | {
      type: "need_eula";
    }
  | {
      type: "ping";
    }
  | {
      type: "console";
      data: ConsoleMessage;
    }
  | {
      type: "status";
      data: string;
    }
  | {
      type: "player_update";
      data: string[];
    }
  | {
      type: "info";
      data: ServerDetails;
    };

export interface ServerDetails {
  name: string;
  status: string;
  type: string;
  version: string;
  metrics: {
    cpu_usage: string;
    memory_usage: string;
    player_count: string;
    uptime: string;
  };
  port: number;
  maxPlayers: number;
  players: string[];
  ip: {
    private: string;
    public: string;
  };
}

export interface ConsoleMessage {
  type: string;
  timestamp?: string;
  text?: string;
  data?: string;
}