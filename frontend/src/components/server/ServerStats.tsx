import { Microchip, MemoryStick, Users, Clock } from "lucide-react";
import { motion } from "framer-motion";

interface ServerStatsProps {
  metrics: {
    cpu_usage: string;
    memory_usage: string;
    player_count: string;
    uptime: string;
  };
}

export const ServerStats = ({ metrics }: ServerStatsProps) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
      className="glass-card"
    >
      <h2 className="text-xl font-semibold text-white mb-4">Server Stats</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white/5 p-4 rounded-lg flex items-center">
          <Microchip className="text-blue-400 text-2xl mr-3" />
          <div>
            <p className="text-white/60 text-sm">CPU Usage</p>
            <p className="text-white text-lg font-semibold">{metrics.cpu_usage}</p>
          </div>
        </div>

        <div className="bg-white/5 p-4 rounded-lg flex items-center">
          <MemoryStick className="text-purple-400 text-2xl mr-3" />
          <div>
            <p className="text-white/60 text-sm">Memory Usage</p>
            <p className="text-white text-lg font-semibold">{metrics.memory_usage}</p>
          </div>
        </div>

        <div className="bg-white/5 p-4 rounded-lg flex items-center">
          <Users className="text-green-400 text-2xl mr-3" />
          <div>
            <p className="text-white/60 text-sm">Players</p>
            <p className="text-white text-lg font-semibold">{metrics.player_count}</p>
          </div>
        </div>

        <div className="bg-white/5 p-4 rounded-lg flex items-center">
          <Clock className="text-pink-400 text-2xl mr-3" />
          <div>
            <p className="text-white/60 text-sm">Uptime</p>
            <p className="text-white text-lg font-semibold">{metrics.uptime}</p>
          </div>
        </div>
      </div>
    </motion.div>
  );
};