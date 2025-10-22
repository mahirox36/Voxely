'use client';

import { useState, memo } from 'react';
import { motion } from 'framer-motion';
import { Server, Users } from 'lucide-react';

interface ServerCardProps {
  name: string;
  status: 'online' | 'offline' | 'starting' | 'stopping';
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

// Memoize the component to prevent unnecessary re-renders
const ServerCard = memo(function ServerCard({
  name,
  status,
  type,
  version,
  metrics,
  port,
  maxPlayers = 20,
  onClick
}: ServerCardProps) {
  const [isHovered, setIsHovered] = useState(false);

  // Status indicator colors
  const statusColors = {
    online: 'bg-green-500',
    offline: 'bg-red-500',
    starting: 'bg-yellow-500',
    stopping: 'bg-orange-500'
  };

  const statusText = {
    online: 'Online',
    offline: 'Offline',
    starting: 'Starting',
    stopping: 'Stopping'
  };

  return (
    <motion.div
      className={`glass-card p-6 rounded-lg cursor-pointer transition-all duration-300 ${isHovered ? 'scale-[1.02]' : ''}`}
      whileHover={{ scale: 1.02 }}
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-xl font-bold text-white truncate max-w-[200px]">{name}</h3>
          <div className="flex items-center mt-1">
            <div className={`w-3 h-3 rounded-full ${statusColors[status]} mr-2`}></div>
            <span className="text-white/70">{statusText[status]}</span>
          </div>
        </div>
        <div className="py-1 px-3 rounded bg-white/10 text-white/80">
          {type} {version}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mt-6">
        {status === 'online' && metrics ? (
          <>
            <div className="bg-white/5 p-3 rounded">
              <p className="text-white/50 text-xs mb-1">CPU</p>
              <p className="text-white font-medium">{metrics.cpu_usage}</p>
            </div>
            <div className="bg-white/5 p-3 rounded">
              <p className="text-white/50 text-xs mb-1">Memory</p>
              <p className="text-white font-medium">{metrics.memory_usage}</p>
            </div>
            <div className="bg-white/5 p-3 rounded flex items-center">
              <div className="mr-2">
                <Users className="text-white/70" />
              </div>
              <div>
                <p className="text-white/50 text-xs">Players</p>
                <p className="text-white font-medium">{metrics.player_count} / {maxPlayers}</p>
              </div>
            </div>
            <div className="bg-white/5 p-3 rounded flex items-center">
              <div className="mr-2">
                <Server className="text-white/70" />
              </div>
              <div>
                <p className="text-white/50 text-xs">Port</p>
                <p className="text-white font-medium">{port || 'N/A'}</p>
              </div>
            </div>
          </>
        ) : (
          <div className="col-span-2 text-center py-4 px-2 bg-white/5 rounded">
            <Server className="text-white/30 text-2xl mx-auto mb-2" />
            <p className="text-white/50">
              {status === 'starting' 
                ? 'Server is starting...' 
                : status === 'stopping' 
                  ? 'Server is stopping...' 
                  : 'Server is offline'}
            </p>
          </div>
        )}
      </div>
    </motion.div>
  );
});

export default ServerCard;