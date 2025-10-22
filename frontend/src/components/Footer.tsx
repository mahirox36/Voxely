'use client';

import { motion } from 'framer-motion';
import { Heart } from 'lucide-react';
import { useEffect, useState } from 'react';
import { FaGithub, FaDiscord } from 'react-icons/fa';


export default function Footer() {
  // Check if we are in page / dashboard/server/[name] and if yes hid the footer
  const [isServerPage, setIsServerPage] = useState(false);
  
  useEffect(() => {
    if (typeof window !== 'undefined') {
      setIsServerPage(window.location.pathname.startsWith('/dashboard/server/'));
    }
  }, []);

  if (isServerPage) return null;
  return (
    <motion.footer
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.5 }}
      className="glass-footer mt-auto"
    >
      <div className="container mx-auto px-4 py-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="text-center md:text-left">
            <h3 className="text-lg font-semibold text-white mb-2">
              Voxely
            </h3>
            <p className="text-white/60">
              Easy Minecraft server management
            </p>
          </div>

          <div className="flex items-center gap-6">
            <a
              href="https://github.com/mahirox36/Voxely"
              target="_blank"
              rel="noopener noreferrer"
              className="text-white/60 hover:text-white transition-colors"
            >
              <FaGithub size={24} />
            </a>
            <a
              href="https://discord.gg/a85rPNbGhn"
              target="_blank"
              rel="noopener noreferrer"
              className="text-white/60 hover:text-white transition-colors"
            >
              <FaDiscord size={24} />
            </a>
          </div>
        </div>

        <div className="mt-8 pt-4 border-t border-white/10">
          <p className="text-center text-white/60 flex items-center justify-center gap-2">
            Made with <Heart className="text-pink-500" /> by MahiroX36
          </p>
        </div>
      </div>
    </motion.footer>
  );
}