"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Plus } from "lucide-react";
import ServerCard from "@/components/ServerCard";
import AuthMiddleware from "@/components/AuthMiddleware";
import { useWebSocket } from "@/lib/websocket/WebSocket";

interface Server {
  id?: string;
  name: string;
  status: "online" | "offline" | "starting" | "stopping";
  type: string;
  version: string;
  metrics?: {
    cpu_usage?: string;
    memory_usage?: string;
    player_count?: string;
    uptime?: string;
  };
  port?: number;
  maxPlayers?: number;
}

export default function Dashboard() {
  const [servers, setServers] = useState<Server[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const { socket, connect, disconnect } = useWebSocket({});

  useEffect(() => {
    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
    connect();

    const handleServerList = (event: CustomEvent) => {
      console.log("FULL SERVER EVENT:", event.detail);

      const incomingServers = event.detail?.servers || [];

      const formattedServers = incomingServers.map((server: any) => ({
        id: server.id || server.server_id || crypto.randomUUID(),
        name: server.name || "Unnamed Server",
        status: server.status || "offline",
        type: server.type || "paper",
        version: server.version || "Unknown",
        metrics: {
          cpu_usage: server.metrics?.cpu_usage || "0%",
          memory_usage: server.metrics?.memory_usage || "0 MB",
          player_count: server.metrics?.player_count || "0/20",
          uptime: server.metrics?.uptime || "0m",
        },
        port: server.port || 25565,
        maxPlayers: server.maxPlayers || 20,
      }));

      setServers(formattedServers);
      setLastUpdated(new Date());
      setError("");
      setIsLoading(false);
    };

    const handleServerError = (event: CustomEvent) => {
      console.error("Server list error:", event.detail);

      setError("Failed to load servers");
      setIsLoading(false);
    };

    setTimeout(() => {
      socket.current?.on("server.list.success", handleServerList);
      socket.current?.on("server.list.error", handleServerError);

      console.log("Requesting server list...");
      socket.current?.emit("server.list");
    }, 500);

    return () => {
      socket.current?.off("server.list.success", handleServerList);
      socket.current?.off("server.list.error", handleServerError);

      disconnect();
    };
  }, []);

  return (
    <AuthMiddleware>
      <div className="min-h-screen">
        <div className="container mx-auto px-4 py-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="flex justify-between items-center mb-8"
          >
            <div>
              <h1 className="text-4xl font-bold text-white">My Servers</h1>

              {lastUpdated && (
                <p className="text-white/50 text-sm mt-1">
                  Last updated: {lastUpdated.toLocaleTimeString()}
                </p>
              )}
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setIsLoading(true);
                  socket.current?.emit("server.list");
                }}
                disabled={isLoading}
                className="btn btn-secondary"
              >
                Refresh
              </button>

              <Link
                href="/dashboard/create"
                className="btn btn-primary flex items-center gap-2"
              >
                <Plus />
                New Server
              </Link>
            </div>
          </motion.div>

          {isLoading ? (
            <div className="flex justify-center items-center h-64">
              <div className="loader"></div>
            </div>
          ) : error ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-red-400 bg-red-500/20 text-center p-6 glass-card flex flex-col items-center"
            >
              <p className="mb-4">{error}</p>

              <button
                onClick={() => {
                  setIsLoading(true);
                  socket.current?.emit("server.list");
                }}
                className="btn btn-secondary mt-2"
              >
                Try Again
              </button>
            </motion.div>
          ) : servers.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center py-16 glass-card"
            >
              <h3 className="text-2xl font-semibold text-white mb-4">
                No Servers Yet
              </h3>

              <p className="text-white/60 mb-8">
                Create your first Minecraft server to get started!
              </p>

              <Link
                href="/dashboard/create"
                className="btn btn-primary inline-flex items-center gap-2"
              >
                <Plus />
                Create Server
              </Link>
            </motion.div>
          ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6 }}
              className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
            >
              <AnimatePresence>
                {servers.map((server) => (
                  <motion.div
                    key={server.id || server.name}
                    layout
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.9 }}
                    transition={{ duration: 0.3 }}
                  >
                    <ServerCard
                      {...server}
                      onClick={() =>
                        (window.location.href = `/dashboard/server/${server.name}`)
                      }
                    />
                  </motion.div>
                ))}
              </AnimatePresence>
            </motion.div>
          )}
        </div>
      </div>
    </AuthMiddleware>
  );
}
