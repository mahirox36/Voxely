"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { FaCheck, FaTimes } from "react-icons/fa";
import AuthMiddleware from "@/components/AuthMiddleware";
import { apiRequest } from "@/utils/api";

// Import components
import { ServerHeader } from "@/components/server/ServerHeader";
import { TabNavigation } from "@/components/server/TabNavigation";
import { ServerStats } from "@/components/server/ServerStats";
import { ConnectionInfo } from "@/components/server/ConnectionInfo";
import { PlayerList } from "@/components/server/PlayerList";
import { ConsoleOutput } from "@/components/server/ConsoleOutput";
import {
  FileManagerTab,
  PluginsTab,
  BackupsTab,
  LogsTab,
  SettingsTab,
} from "@/components/server/tabs";

interface ServerDetails {
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

// Extend the Window interface to include _apiCache
declare global {
  interface Window {
    _apiCache?: Record<string, unknown>;
  }
}

export default function ServerDetail() {
  const params = useParams();
  const router = useRouter();
  const serverName = params.name as string;

  const [serverDetails, setServerDetails] = useState<ServerDetails | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionInProgress, setActionInProgress] = useState("");
  const [consoleOutput, setConsoleOutput] = useState<string[]>([]);
  const [consoleConnected, setConsoleConnected] = useState(false);
  const [command, setCommand] = useState("");
  const [showEulaModal, setShowEulaModal] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const socket = useRef<WebSocket | null>(null);
  const isPolling = useRef(false);
  const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const consoleEndRef = useRef<HTMLDivElement>(null);

  const fetchServerDetails = useCallback(async () => {
    if (isPolling.current) return;

    isPolling.current = true;
    try {
      const data = await apiRequest(`/servers/${serverName}`);
      setServerDetails(data);

      const eulaStatus = await apiRequest(`/servers/${serverName}/eula/status`);
      if (!eulaStatus.accepted && data.status === "offline") {
        setShowEulaModal(true);
      }
    } catch (err) {
      console.error("Failed to fetch server details:", err);
      setError("Failed to load server details");
    } finally {
      setLoading(false);
      isPolling.current = false;
    }
  }, [serverName]);

  const connectConsole = useCallback(() => {
    if (socket.current) {
      console.log("WebSocket already exists, not creating a new one");
      return;
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/v1/servers/${serverName}/console`;

    console.log("Creating new WebSocket connection to:", wsUrl);
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("Console connection established");
      setConsoleConnected(true);
    };

    ws.onmessage = (event) => {
      setConsoleOutput((prev) => [...prev, event.data]);
      if (consoleEndRef.current) {
        consoleEndRef.current.scrollIntoView({ behavior: "smooth" });
      }
    };

    ws.onclose = (event) => {
      console.log(
        `Console connection closed: code=${event.code}, reason=${event.reason}`
      );
      setConsoleConnected(false);
      socket.current = null;

      console.log("Reconnecting in 5 seconds...");
      setTimeout(() => {
        connectConsole();
      }, 5000);
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    socket.current = ws;
  }, [serverName]);

  useEffect(() => {
    connectConsole();

    return () => {
      if (socket.current) {
        console.log("Cleaning up WebSocket on effect cleanup");
        socket.current.close(1000, "Component cleanup");
        socket.current = null;
      }
    };
  }, [connectConsole]);

  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [consoleOutput]);

  useEffect(() => {
    fetchServerDetails();

    const scheduleNextRefresh = () => {
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }

      refreshTimeoutRef.current = setTimeout(() => {
        if (!actionInProgress) {
          fetchServerDetails();
        }
        scheduleNextRefresh();
      }, 5000);
    };

    scheduleNextRefresh();

    return () => {
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current);
      }
    };
  }, [fetchServerDetails, actionInProgress]);

  const acceptEula = async () => {
    try {
      setActionInProgress("accepting_eula");
      await apiRequest(`/servers/${serverName}/eula/accept`, { method: "POST" });

      setShowEulaModal(false);

      if (window._apiCache) {
        Object.keys(window._apiCache).forEach((key) => {
          if (key.includes(serverName)) {
            delete window._apiCache?.[key];
          }
        });
      }

      await new Promise((resolve) => setTimeout(resolve, 1000));

      await fetchServerDetails();
      setActionInProgress("");
    } catch (err) {
      console.error("Failed to accept EULA:", err);
      setError("Failed to accept EULA");
      setActionInProgress("");
    }
  };

  const startServer = async () => {
    if (actionInProgress) return;

    setActionInProgress("starting");
    try {
      await apiRequest(`/servers/${serverName}/start`, { method: "POST" });
      await fetchServerDetails();
    } catch (err) {
      setError("Failed to start server");
      console.error(err);
    } finally {
      setActionInProgress("");
    }
  };

  const stopServer = async () => {
    if (actionInProgress) return;

    setActionInProgress("stopping");
    try {
      await apiRequest(`/servers/${serverName}/stop`, { method: "POST" });
      await fetchServerDetails();
    } catch (err) {
      setError("Failed to stop server");
      console.error(err);
    } finally {
      setActionInProgress("");
    }
  };

  const restartServer = async () => {
    if (actionInProgress) return;

    setActionInProgress("restarting");
    try {
      await apiRequest(`/servers/${serverName}/restart`, { method: "POST" });
      await fetchServerDetails();
    } catch (err) {
      setError("Failed to restart server");
      console.error(err);
    } finally {
      setActionInProgress("");
    }
  };

  const sendWebSocketCommand = (cmd: string) => {
    if (socket.current && socket.current.readyState === WebSocket.OPEN) {
      socket.current.send(`cmd:${cmd}`);
      setCommand("");
    }
  };

  const OverviewTab = () => (
    <motion.div
      key="overview"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="grid grid-cols-1 lg:grid-cols-3 gap-6"
    >
      <div className="lg:col-span-2 space-y-6">
        {serverDetails && <ServerStats metrics={serverDetails.metrics} />}
      </div>
      <div className="space-y-6">
        {serverDetails && (
          <ConnectionInfo ip={serverDetails.ip} port={serverDetails.port} />
        )}
        <PlayerList
          players={serverDetails?.players || []}
          maxPlayers={serverDetails?.maxPlayers || 0}
        />
      </div>
    </motion.div>
  );

  if (loading) {
    return (
      <AuthMiddleware>
        <div className="min-h-screen flex items-center justify-center">
          <div className="loader"></div>
        </div>
      </AuthMiddleware>
    );
  }

  if (error || !serverDetails) {
    return (
      <AuthMiddleware>
        <div className="min-h-screen flex items-center justify-center">
          <div className="glass-card p-8 text-center max-w-md">
            <h2 className="text-2xl text-white mb-4">Error</h2>
            <p className="text-red-300">{error || "Failed to load server details"}</p>
            <button onClick={() => router.back()} className="btn btn-primary mt-4">
              Go Back
            </button>
          </div>
        </div>
      </AuthMiddleware>
    );
  }

  const isOnline = serverDetails.status === "online";
  const isStarting =
    serverDetails.status === "starting" || actionInProgress === "starting";
  const isStopping =
    serverDetails.status === "stopping" || actionInProgress === "stopping";
  const isRestarting = actionInProgress === "restarting";

  return (
    <AuthMiddleware>
      <div className="min-h-screen">
        <div className="container mx-auto px-4 py-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6"
          >
            <ServerHeader
              name={serverDetails.name}
              status={serverDetails.status}
              type={serverDetails.type}
              version={serverDetails.version}
              actionInProgress={actionInProgress}
              isOnline={isOnline}
              isStarting={isStarting}
              isStopping={isStopping}
              isRestarting={isRestarting}
              onStart={startServer}
              onStop={stopServer}
              onRestart={restartServer}
              onBack={() => router.back()}
            />

            <TabNavigation
              activeTab={activeTab}
              onTabChange={setActiveTab}
            />
          </motion.div>

          <AnimatePresence mode="wait">
            {activeTab === "overview" && <OverviewTab />}
            
            {activeTab === "console" && (
              <ConsoleOutput
                consoleOutput={consoleOutput}
                consoleConnected={consoleConnected}
                command={command}
                setCommand={setCommand}
                sendCommand={(cmd) => sendWebSocketCommand(cmd)}
                isOnline={isOnline}
              />
            )}

            {activeTab === "files" && <FileManagerTab />}
            {activeTab === "plugins" && <PluginsTab />}
            {activeTab === "backups" && <BackupsTab />}
            {activeTab === "logs" && <LogsTab />}
            {activeTab === "settings" && <SettingsTab />}
          </AnimatePresence>
        </div>
      </div>

      <AnimatePresence>
        {showEulaModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
          >
            <motion.div
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              className="glass-card max-w-2xl w-full"
            >
              <div className="text-center mb-6">
                <h2 className="text-2xl font-bold text-white mb-2">
                  Minecraft EULA Agreement Required
                </h2>
                <p className="text-white/70">
                  Before starting your Minecraft server, you need to accept the
                  Minecraft End User License Agreement (EULA).
                </p>
              </div>

              <div className="bg-white/10 rounded-lg p-6 mb-6">
                <p className="text-white mb-4">
                  By clicking &quot;Accept&quot; below, you agree to the{" "}
                  <a
                    href="https://account.mojang.com/documents/minecraft_eula"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-400 hover:underline"
                  >
                    Minecraft End User License Agreement
                  </a>
                  .
                </p>

                <p className="text-white/80 text-sm">
                  The Minecraft EULA is an agreement between you and Mojang AB which
                  governs your use of the Minecraft software. By accepting, you are
                  agreeing to the terms and conditions set forth by Mojang.
                </p>
              </div>

              <div className="flex justify-center gap-4">
                <button
                  onClick={() => setShowEulaModal(false)}
                  className="btn btn-secondary"
                  disabled={actionInProgress === "accepting_eula"}
                >
                  <FaTimes className="mr-2" />
                  Decline
                </button>

                <button
                  onClick={acceptEula}
                  className="btn btn-primary"
                  disabled={actionInProgress === "accepting_eula"}
                >
                  {actionInProgress === "accepting_eula" ? (
                    <>Loading...</>
                  ) : (
                    <>
                      <FaCheck className="mr-2" />
                      Accept
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </AuthMiddleware>
  );
}
