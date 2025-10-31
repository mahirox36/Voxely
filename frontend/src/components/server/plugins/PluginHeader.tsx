import { AnimatePresence, motion } from "framer-motion";
import { ArrowLeft, Plus } from "lucide-react";

interface PluginsHeaderProps {
  download_page: boolean;
  setDownloadPage: (value: boolean) => void;
  query: string;
  setQuery: (value: string) => void;
}

export function PluginsHeader({
  download_page,
  setDownloadPage,
  query,
  setQuery,
}: PluginsHeaderProps) {
  return (
    <motion.div
      // layout
      // transition={{ type: "spring", stiffness: 300, damping: 25 }}
      className="glass-panel p-3 flex items-center gap-3"
    >
      {/* Back button (only visible when download_page = true) */}
      <AnimatePresence initial={false} mode="wait">
        {download_page && (
          <motion.button
            key="back"
            // layout
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ type: "spring", stiffness: 250, damping: 20 }}
            onClick={() => setDownloadPage(false)}
            className="flex items-center justify-center px-4 py-2 bg-gradient-to-r from-slate-600/30 to-slate-800/30 rounded-lg transition-colors duration-300"
          >
            <ArrowLeft className="text-white" />
            <p className="ml-2 text-white font-medium">Back</p>
          </motion.button>
        )}
      </AnimatePresence>

      {/* Search input expands/contracts depending on button visibility */}
      <motion.input
        // layout
        transition={{ type: "spring", stiffness: 300, damping: 25 }}
        type="text"
        placeholder={
          download_page
            ? "Search for new addons..."
            : "Search installed addons..."
        }
        className="flex-1 glass-panel rounded-lg px-4 py-2.5 text-sm text-white placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-color"
        onChange={(e) => setQuery(e.target.value)}
        value={query}
      />

      {/* Add button (only visible when download_page = false) */}
      <AnimatePresence initial={false} mode="wait">
        {!download_page && (
          <motion.button
            key="add"
            // layout
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            transition={{ type: "spring", stiffness: 250, damping: 20 }}
            onClick={() => setDownloadPage(true)}
            className="flex items-center justify-center px-4 py-2 bg-gradient-to-r from-emerald-400 to-emerald-500 rounded-lg transition-colors duration-300"
          >
            <Plus className="text-white" />
            <p className="ml-2 text-white font-medium">Add</p>
          </motion.button>
        )}
      </AnimatePresence>
    </motion.div>
  );
}