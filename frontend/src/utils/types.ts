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

export interface Project {
  id: string;
  slug: string;
  title: string;
  description: string;
  downloads: number;
  followers: number;
  license?: License | null;
  versions: string[];
  categories: string[];
  client_side: "required" | "optional" | "unsupported" | "unknown";
  server_side: "required" | "optional" | "unsupported" | "unknown";
  body: string;
  status: string;
  requested_status?: string | null;
  additional_categories: string[];
  issues_url?: string | null;
  source_url?: string | null;
  wiki_url?: string | null;
  discord_url?: string | null;
  donation_urls: DonationUrl[];
  icon_url?: string | null;
  color?: string | null;
  game_versions: string[];
  loaders: string[];
  gallery: GalleryItem[];
}

export interface License {
  id: string;
  name: string;
  url?: string | null;
}

export interface GalleryItem {
  url: string;
  featured: boolean;
  title?: string | null;
  description?: string | null;
  created: string;
  ordering: number;
}

export interface DonationUrl {
  id: string;
  platform: string;
  url: string;
}

export interface Dependency {
  version_id: string;
  project_id: string;
  file_name?: string | null;
  dependency_type: DependencyType;
}

export interface Version {
  id: string;
  name: string;
  version_number: string;
  changelog?: string | null;
  dependencies: Dependency[];
  game_versions: string[];
  version_type: VersionType;
  loaders: string[];
  featured: boolean;
  status: string;
  requested_status?: string | null;
  project_id: string;
  author_id: string;
  date_published: string; // ISO 8601 format
  downloads: number;
  changelog_url?: string | null;
  files: File[];
}

export type DependencyType =
  | "required"
  | "optional"
  | "incompatible"
  | "embedded";
export type VersionType = "release" | "snapshot" | "beta" | "alpha";
// export type VersionStatus = "approved" | "rejected" | "pending";

export interface File {
  id: string;
  name: string;
  size: number;
  url: string;
}

export interface SearchResult {
  hits: Project[];
  total_hits: number;
  offset: number;
  limit: number;
}

export interface Category {
  icon: string;
  name: string;
  project_type: string;
  header: string;
}

export interface Addon {
  project: Project;
  path: string;
  version: Version;
}

export interface SearchRequest {
  query: string;
  limit: number;
  offset: number;
  sort: string;
  project_type: "mod" | "plugin";
  versions?: Array<string>;
  categories?: Array<string>;
}
