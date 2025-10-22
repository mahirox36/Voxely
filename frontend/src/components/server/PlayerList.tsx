import { motion } from "framer-motion";
import Image from "next/image";

interface PlayerListProps {
  players: string[];
  maxPlayers: number;
}

export const PlayerList = ({ players = [], maxPlayers }: PlayerListProps) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      className="glass-card"
    >
      <h2 className="text-xl font-semibold text-white mb-4">
        Players ({players?.length || 0}/{maxPlayers})
      </h2>
      {players && players.length > 0 ? (
        <div className="space-y-2">
          {players.map((player, index) => (
            <div
              key={index}
              className="bg-white/5 p-3 rounded-lg flex items-center"
            >
              <div className="w-8 h-8 bg-green-500/20 rounded-full flex items-center justify-center mr-3">
                {/* <FaUsers className="text-green-400" /> */}
                <Image
                  width={256}
                  height={256}
                  src={`https://minotar.net/avatar/${player}/256`}
                  alt={player}
                />
              </div>
              <p className="text-white">{player}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-white/40 italic">No players online</p>
      )}
    </motion.div>
  );
};
