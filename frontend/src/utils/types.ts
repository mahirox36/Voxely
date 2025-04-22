/**
 * Type definitions for API requests
 */

// RequestOptions interface for apiRequest function
export interface RequestOptions extends RequestInit {
  requiresAuth?: boolean;
}

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