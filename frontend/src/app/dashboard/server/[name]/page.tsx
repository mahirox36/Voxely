"use client";

import { useState, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Check, Timer } from "lucide-react";
import AuthMiddleware from "@/components/AuthMiddleware";
import { api } from "@/utils/api";

// Import components
import { ServerHeader } from "@/components/server/ServerHeader";
import { TabNavigation } from "@/components/server/TabNavigation";
import { ServerStats } from "@/components/server/ServerStats";
import { ConnectionInfo } from "@/components/server/ConnectionInfo";
import { PlayerList } from "@/components/server/PlayerList";
import { ConsoleOutput } from "@/components/server/ConsoleOutput";
import {
  PluginsTab,
  BackupsTab,
  LogsTab,
  SettingsTab,
} from "@/components/server/tabs";
import {
  ConsoleMessage,
  ServerDetails,
  ServerFile,
  SocketMessage,
} from "@/utils/types";
import { FilesExplorer } from "@/components/server/Files";

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
  const [consoleOutput, setConsoleOutput] = useState<ConsoleMessage[]>([]);
  const [command, setCommand] = useState("");
  const [showEulaModal, setShowEulaModal] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [files, setFiles] = useState<ServerFile[]>([]);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isReconnectingRef = useRef(false);

  useEffect(() => {
    // Don't create a new socket if one already exists or if we're reconnecting
    if (socket || isReconnectingRef.current) {
      return;
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = "localhost:25401";
    let token = localStorage.getItem("token");
    if (!token) token = "";
    const wsUrl = `${protocol}//${host}/api/v1/servers/ws/${serverName}?token=${encodeURIComponent(
      token
    )}`;

    console.log("Creating new WebSocket connection to:", wsUrl);
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("WebSocket connection established");
      setSocket(ws);
      isReconnectingRef.current = false;
    };

    ws.onmessage = (event) => {
      try {
        const data: SocketMessage = JSON.parse(event.data);
        switch (data.type) {
          case "console":
            // Handle nested console data structure
            setConsoleOutput((prev) => [...prev, data.data]);
            break;
          case "info":
            setServerDetails(data.data);
            setLoading(false);
            break;
          case "ping":
            ws.send(JSON.stringify({ action: "pong" }));
            break;
          case "need_eula":
            setShowEulaModal(true);
            break;
          case "error":
            console.error("Server error:", data.data);
            setError(data.data || "An error occurred");
            break;
          case "status":
            // Update server status
            setServerDetails((prev) =>
              prev ? { ...prev, status: data.data } : null
            );
            if (data.data === "online" || data.data === "offline") {
              setActionInProgress("");
            }
            break;
          case "player_update":
            setServerDetails((prev) =>
              prev ? { ...prev, players: data.data } : null
            );
            break;
          case "file_init":
            setFiles(data.data);
            break;
          case "file_update":
            setFiles(data.data);
            // Optionally handle file changes if needed
            break;
        }
      } catch (err) {
        console.error("Error parsing WebSocket message:", err);
      }
    };

    ws.onclose = (event) => {
      console.log(
        `WebSocket connection closed: code=${event.code}, reason=${event.reason}`
      );
      setSocket(null);

      // Only reconnect if it wasn't a normal closure
      if (event.code !== 1000 && !isReconnectingRef.current) {
        isReconnectingRef.current = true;
        console.log("Reconnecting in 5 seconds...");
        reconnectTimeoutRef.current = setTimeout(() => {
          isReconnectingRef.current = false;
          // Trigger re-render to create new connection
          setSocket(null);
        }, 5000);
      }
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    // Cleanup function
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (ws.readyState === WebSocket.OPEN) {
        ws.close(1000, "Component unmounting");
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [serverName]);

  // Auto-scroll console
  // useEffect(() => {
  //   if (consoleEndRef.current) {
  //     consoleEndRef.current.scrollIntoView({ behavior: "smooth" });
  //   }
  // }, [consoleOutput]);

  const acceptEula = async () => {
    try {
      setActionInProgress("accepting_eula");
      await api.post(`/servers/${serverName}/eula/accept`);

      setShowEulaModal(false);

      if (window._apiCache) {
        Object.keys(window._apiCache).forEach((key) => {
          if (key.includes(serverName)) {
            delete window._apiCache?.[key];
          }
        });
      }

      await new Promise((resolve) => setTimeout(resolve, 1000));

      setActionInProgress("");
    } catch (err) {
      console.error("Failed to accept EULA:", err);
      setError("Failed to accept EULA");
      setActionInProgress("");
    }
  };

  const startServer = async () => {
    if (actionInProgress || !socket) return;

    setActionInProgress("starting");
    try {
      socket.send(JSON.stringify({ action: "start" }));
    } catch (err) {
      setError("Failed to start server");
      console.error(err);
      setActionInProgress("");
    }
  };

  const stopServer = async () => {
    if (actionInProgress || !socket) return;

    setActionInProgress("stopping");
    try {
      socket.send(JSON.stringify({ action: "stop" }));
    } catch (err) {
      setError("Failed to stop server");
      console.error(err);
      setActionInProgress("");
    }
  };

  const restartServer = async () => {
    if (actionInProgress || !socket) return;

    setActionInProgress("restarting");
    try {
      socket.send(JSON.stringify({ action: "restart" }));
    } catch (err) {
      setError("Failed to restart server");
      console.error(err);
      setActionInProgress("");
    }
  };

  const sendWebSocketCommand = (cmd: string) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ action: "command", data: cmd }));
      setCommand("");
    }
  };
  const readFile = async (path: string) => {
    const response = await api.get<string>(
      `/servers/${serverName}/files/get/${path}`
    );
    return response.data;
  };
  const writeFile = async (path: string, content: string) => {
    await api.post(`/servers/${serverName}/files/write/${path}`, content);
  };

  //   uploadFile?: (targetPath: string, file: File) => Promise<void>;
  // downloadFile?: (path: string) => Promise<File>;
  // zipFiles?: (paths: string[]) => Promise<void>;
  // unzipFile?: (path: string) => Promise<void>;
  // deleteFile?: (path: string) => Promise<void>;
  // copyFile?: (from: string, to: string) => Promise<void>;
  // moveFile?: (from: string, to: string) => Promise<void>;

  const uploadFile = async (targetPath: string, file: File) => {
    const formData = new FormData();
    if (!targetPath || targetPath === "") {
      targetPath = "current_directory_super_long_because_empty_string_is_bad_and_also_if_there_were_someone_stupid_enough_to_name_a_folder_like_this_we_need_to_handle_it_properly";
    }
    console.log("Uploading file:", file.name, "to", targetPath);
    formData.append("file", file);
    await api.post(
      `/servers/${serverName}/files/upload/${targetPath}`,
      formData
    );
  };

  const downloadFile = async (path: string) => {
    try {
      const response = await api.get(
        `/servers/${serverName}/files/download/${encodeURIComponent(path)}`,
        { responseType: "blob" } // important
      ) as Blob;

      const fileName = path.split("/").pop() || "file";
      console.log("Downloading file:", response);

      // Use the modern way
      const blobUrl = URL.createObjectURL(response);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = fileName;
      a.click();
      URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error("File download failed", err);
    }
  };
  const zipFiles = async (paths: string[]) => {
    await api.post(`/servers/${serverName}/files/zip`, { paths, name: paths[0] });
  };
  const unzipFile = async (path: string) => {
    await api.post(`/servers/${serverName}/files/unzip`, { path });
  };
  const deleteFile = async (path: string) => {
    await api.delete(`/servers/${serverName}/files/delete/${path}`);
  };

  const copyFile = async (from: string, to: string) => {
    await api.post(`/servers/${serverName}/files/copy`, {
      source: from,
      destination: to,
    });
  };
  const moveFile = async (from: string, to: string) => {
    await api.post(`/servers/${serverName}/files/move`, {
      source: from,
      destination: to,
    });
  };

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
            <p className="text-red-300">
              {error || "Failed to load server details"}
            </p>
            <button
              onClick={() => router.back()}
              className="btn btn-primary mt-4"
            >
              Go Back
            </button>
          </div>
        </div>
      </AuthMiddleware>
    );
  }

  const isOnline = serverDetails.status === "online";
  const isStarting = serverDetails.status === "starting";
  const isStopping = serverDetails.status === "stopping";

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
              isOnline={isOnline}
              isStarting={isStarting}
              isStopping={isStopping}
              // isRestarting={isRestarting}
              onStart={startServer}
              onStop={stopServer}
              onRestart={restartServer}
              onBack={() => router.back()}
            />

            <TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />
          </motion.div>

          <AnimatePresence mode="wait">
            {activeTab === "overview" && (
              <motion.div
                key="overview"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="grid grid-cols-1 lg:grid-cols-3 gap-6"
              >
                <div className="lg:col-span-2 space-y-6">
                  {serverDetails && (
                    <ServerStats metrics={serverDetails.metrics} />
                  )}
                  <ConsoleOutput
                    consoleOutput={consoleOutput}
                    isOnline={isOnline}
                    compact={true}
                  />
                </div>
                <div className="space-y-6">
                  {serverDetails && (
                    <ConnectionInfo
                      ip={serverDetails.ip}
                      port={serverDetails.port}
                    />
                  )}
                  <PlayerList
                    players={serverDetails?.players || []}
                    maxPlayers={serverDetails?.maxPlayers || 0}
                  />
                </div>
              </motion.div>
            )}

            {activeTab === "console" && (
              <ConsoleOutput
                consoleOutput={consoleOutput}
                command={command}
                setCommand={setCommand}
                sendCommand={(cmd) => sendWebSocketCommand(cmd)}
                isOnline={isOnline}
              />
            )}

            {activeTab === "files" && (
              <FilesExplorer
                files={files}
                readFile={readFile}
                writeFile={writeFile}
                copyFile={copyFile}
                deleteFile={deleteFile}
                downloadFile={downloadFile}
                moveFile={moveFile}
                uploadFile={uploadFile}
                zipFiles={zipFiles}
                unzipFile={unzipFile}
              />
            )}
            {activeTab === "plugins/Mods" && <PluginsTab />}
            {activeTab === "config" && <PluginsTab />}
            {activeTab === "players" && <PluginsTab />}
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
                  The Minecraft EULA is an agreement between you and Mojang AB
                  which governs your use of the Minecraft software. By
                  accepting, you are agreeing to the terms and conditions set
                  forth by Mojang.
                </p>
              </div>

              <div className="flex justify-center gap-4">
                <button
                  onClick={() => setShowEulaModal(false)}
                  className="btn btn-secondary"
                  disabled={actionInProgress === "accepting_eula"}
                >
                  <Timer className="mr-2" />
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
                      <Check className="mr-2" />
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
