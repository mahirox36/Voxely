import { Network } from "lucide-react";
import { motion } from "framer-motion";

interface ConnectionInfoProps {
  ip: {
    private: string;
    public: string;
  };
  port: number;
}

export const ConnectionInfo = ({ ip, port }: ConnectionInfoProps) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="glass-card"
    >
      <h2 className="text-xl font-semibold text-white mb-4">Connection Info</h2>
      <div className="space-y-4">
        <div>
          <p className="text-white/60 text-sm mb-1">Local Address</p>
          <div className="flex items-center bg-white/5 p-3 rounded-lg">
            <Network className="text-blue-400 mr-3" />
            <p className="text-white font-mono">{ip?.private || `localhost:${port}`}</p>
          </div>
        </div>

        <div>
          <p className="text-white/60 text-sm mb-1">External Address (Public)</p>
          <div className="flex items-center bg-white/5 p-3 rounded-lg">
            <Network className="text-green-400 mr-3" />
            <p className="text-white font-mono">{ip?.public || "Not available"}</p>
          </div>
        </div>

        <div>
          <p className="text-white/60 text-sm mb-1">Port</p>
          <div className="flex items-center bg-white/5 p-3 rounded-lg">
            <Network className="text-purple-400 mr-3" />
            <p className="text-white font-mono">{port}</p>
          </div>
        </div>
      </div>
    </motion.div>
  );
};