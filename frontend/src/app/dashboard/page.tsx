"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Plus } from "lucide-react";
import ServerCard from "@/components/ServerCard";
import AuthMiddleware from "@/components/AuthMiddleware";
import { api } from "@/utils/api";

interface Server {
  name: string;
  status: "online" | "offline" | "starting" | "stopping";
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
}

export default function Dashboard() {
  const [servers, setServers] = useState<Server[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const isMounted = useRef(true);
  const pollingInterval = useRef<NodeJS.Timeout | null>(null);

  // Memoized fetch function to avoid recreating it on each render
  const fetchServers = useCallback(async (showLoading = false) => {
    if (showLoading) setIsLoading(true);

    try {
      // Corrected the API endpoint path to ensure it matches the backend
      const data: Server[] = await api.get("/servers/get");

      console.log("Fetched servers data:", data);

      setServers(data);
      setLastUpdated(new Date());
      setError("");
    } catch (err: unknown) {
      if (isMounted.current) {
        const errorMessage = err instanceof Error ? err.message : String(err);
        setError(errorMessage || "Failed to load servers");
        console.error("Error fetching servers:", err);
      }
    } finally {
      if (showLoading) {
        setIsLoading(false);
      }
    }
  }, []);

  // Set up polling with proper cleanup
  useEffect(() => {
    // Initial fetch
    fetchServers(true);

    // Set up polling interval for server updates - 30 seconds
    pollingInterval.current = setInterval(() => {
      // Only poll if the page is visible
      if (document.visibilityState === "visible") {
        fetchServers(false);
      }
    }, 30000); // Poll every 30 seconds instead of 10

    // Handle visibility change events to refresh data when tab becomes visible
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        fetchServers(false);
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    // Clean up interval and event listener on unmount
    return () => {
      isMounted.current = false;
      if (pollingInterval.current) {
        clearInterval(pollingInterval.current);
      }
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [fetchServers]);

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
                onClick={() => fetchServers(true)}
                disabled={isLoading}
                className="btn btn-secondary"
                aria-label="Refresh servers"
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
                onClick={() => fetchServers(true)}
                className="btn btn-secondary mt-2"
              >
                Try Again
              </button>
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
                    key={server.name}
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

          {!isLoading && !error && servers.length === 0 && (
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
          )}
        </div>
      </div>
    </AuthMiddleware>
  );
}
