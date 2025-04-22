import { motion } from "framer-motion";

export const FileManagerTab = () => (
  <motion.div
    key="files"
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -10 }}
    className="glass-card"
  >
    <h2 className="text-xl font-semibold text-white mb-4">File Manager</h2>
    <p className="text-white/60">Coming soon - File management interface</p>
  </motion.div>
);

export const PluginsTab = () => (
  <motion.div
    key="plugins"
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -10 }}
    className="glass-card"
  >
    <h2 className="text-xl font-semibold text-white mb-4">Plugin Manager</h2>
    <p className="text-white/60">Coming soon - Plugin management interface</p>
  </motion.div>
);

export const BackupsTab = () => (
  <motion.div
    key="backups"
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -10 }}
    className="glass-card"
  >
    <h2 className="text-xl font-semibold text-white mb-4">Backup Manager</h2>
    <p className="text-white/60">Coming soon - Backup management interface</p>
  </motion.div>
);

export const LogsTab = () => (
  <motion.div
    key="logs"
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -10 }}
    className="glass-card"
  >
    <h2 className="text-xl font-semibold text-white mb-4">Log Viewer</h2>
    <p className="text-white/60">Coming soon - Server logs viewer</p>
  </motion.div>
);

export const SettingsTab = () => (
  <motion.div
    key="settings"
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -10 }}
    className="glass-card"
  >
    <h2 className="text-xl font-semibold text-white mb-4">Server Settings</h2>
    <p className="text-white/60">Coming soon - Server configuration interface</p>
  </motion.div>
);