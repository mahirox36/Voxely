"use client";
import { memo } from "react";
import { motion } from "framer-motion";
import { Server, Users, Cpu, HardDrive, Clock, Activity } from "lucide-react";

interface ServerCardProps {
  name: string;
  status: "online" | "offline" | "starting" | "stopping";
  type: string;
  version: string;
  metrics?: {
    cpu_usage: string;
    memory_usage: string;
    player_count: string;
    uptime: string;
  };
  port?: number;
  maxPlayers?: number;
  onClick?: () => void;
}

const ServerCard = memo(function ServerCard({
  name,
  status,
  type,
  version,
  metrics,
  port,
  maxPlayers = 20,
  onClick,
}: ServerCardProps) {
  const statusConfig = {
    online: {
      color: "bg-emerald-500",
      text: "Online",
      glow: "shadow-emerald-500/50",
      gradient: "from-emerald-500/20 to-transparent",
    },
    offline: {
      color: "bg-slate-200",
      text: "Offline",
      glow: "shadow-slate-200/30",
      gradient: "from-slate-200/10 to-transparent",
    },
    starting: {
      color: "bg-amber-500",
      text: "Starting",
      glow: "shadow-amber-500/50",
      gradient: "from-amber-500/20 to-transparent",
    },
    stopping: {
      color: "bg-orange-500",
      text: "Stopping",
      glow: "shadow-orange-500/50",
      gradient: "from-orange-500/20 to-transparent",
    },
  };

  const config = statusConfig[status];
  const playerCount = metrics?.player_count || "0";
  const playerPercentage = (parseInt(playerCount) / maxPlayers) * 100;

  return (
    <motion.div
      className="group relative overflow-hidden glass-panel rounded-2xl cursor-pointer"
      whileHover={{ scale: 1.02, y: -4 }}
      whileTap={{ scale: 0.98 }}
      transition={{ type: "spring", stiffness: 300, damping: 20 }}
      onClick={onClick}
    >
      {/* Animated gradient overlay */}
      <div
        className={`absolute inset-0 bg-gradient-to-br ${config.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-500`}
      />

      {/* Status glow effect */}
      <div
        className={`absolute -top-24 -right-24 w-48 h-48 ${config.color} rounded-full blur-3xl opacity-20 group-hover:opacity-30 transition-opacity duration-500`}
      />

      <div className="relative p-6">
        {/* Header */}
        <div className="flex justify-between items-start mb-6">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-2">
              <div
                className={`w-2.5 h-2.5 rounded-full ${config.color} ${config.glow} shadow-lg animate-pulse`}
              />
              <h3 className="text-xl font-bold text-white truncate">{name}</h3>
            </div>
            <span className="text-sm text-slate-400">{config.text}</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg glass-container backdrop-blur-sm">
            <Server className="w-4 h-4 text-slate-400" />
            <span className="text-sm font-medium text-slate-300">
              {type} {version}
            </span>
          </div>
        </div>

        {/* Metrics Grid */}
        {status === "online" && metrics ? (
          <div className="space-y-3">
            {/* Players Bar */}
            <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-700/30 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Users className="w-4 h-4 text-blue-400" />
                  <span className="text-sm font-medium text-slate-300">
                    Players
                  </span>
                </div>
                <span className="text-lg font-bold text-white">
                  {playerCount}
                  <span className="text-slate-500">/{maxPlayers}</span>
                </span>
              </div>
              <div className="h-2 bg-slate-700/50 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full"
                  initial={{ width: 0 }}
                  animate={{ width: `${playerPercentage}%` }}
                  transition={{ duration: 1, ease: "easeOut" }}
                />
              </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 gap-3">
              <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-700/30 backdrop-blur-sm hover:border-slate-600/50 transition-colors">
                <div className="flex items-center gap-2 mb-1">
                  <Cpu className="w-4 h-4 text-purple-400" />
                  <span className="text-xs text-slate-400">CPU</span>
                </div>
                <p className="text-xl font-bold text-white">
                  {metrics.cpu_usage}
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-700/30 backdrop-blur-sm hover:border-slate-600/50 transition-colors">
                <div className="flex items-center gap-2 mb-1">
                  <HardDrive className="w-4 h-4 text-pink-400" />
                  <span className="text-xs text-slate-400">Memory</span>
                </div>
                <p className="text-xl font-bold text-white">
                  {metrics.memory_usage}
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-700/30 backdrop-blur-sm hover:border-slate-600/50 transition-colors">
                <div className="flex items-center gap-2 mb-1">
                  <Clock className="w-4 h-4 text-green-400" />
                  <span className="text-xs text-slate-400">Uptime</span>
                </div>
                <p className="text-xl font-bold text-white">{metrics.uptime}</p>
              </div>

              <div className="p-4 rounded-xl bg-slate-800/50 border border-slate-700/30 backdrop-blur-sm hover:border-slate-600/50 transition-colors">
                <div className="flex items-center gap-2 mb-1">
                  <Activity className="w-4 h-4 text-orange-400" />
                  <span className="text-xs text-slate-400">Port</span>
                </div>
                <p className="text-xl font-bold text-white">{port || "N/A"}</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-8 rounded-xl bg-slate-800/30 border border-slate-700/30 backdrop-blur-sm text-center">
            <Server className="w-12 h-12 text-slate-600 mx-auto mb-3" />
            <p className="text-slate-400 font-medium">
              {status === "starting"
                ? "Server is starting..."
                : status === "stopping"
                ? "Server is stopping..."
                : "Server is offline"}
            </p>
          </div>
        )}
      </div>

      {/* Hover shine effect */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500">
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
      </div>
    </motion.div>
  );
});

export default ServerCard;
