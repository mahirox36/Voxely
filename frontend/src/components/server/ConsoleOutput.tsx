"use client";
import { useRef, useEffect, useState } from "react";
import { Terminal, Download, Search } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { ConsoleMessage } from "@/utils/types";

interface ConsoleOutputProps {
  consoleOutput: ConsoleMessage[];
  command?: string;
  setCommand?: (command: string) => void;
  sendCommand?: (command: string) => void;
  isOnline: boolean;
  compact?: boolean;
}

export const ConsoleOutput = ({
  consoleOutput,
  command = "",
  setCommand,
  sendCommand,
  isOnline,
  compact = false,
}: ConsoleOutputProps) => {
  const consoleEndRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [filter, setFilter] = useState("");
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && scrollContainerRef.current) {
      scrollContainerRef.current.scrollTop =
        scrollContainerRef.current.scrollHeight;
    }
  }, [consoleOutput, autoScroll]);

  const handleScroll = () => {
    if (!scrollContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } =
      scrollContainerRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    setAutoScroll(isAtBottom);
  };

  const getConsoleLineClass = (type: string) => {
    switch (type) {
      case "error":
      case "critical":
        return "text-red-400";
      case "warning":
        return "text-yellow-400";
      case "success":
        return "text-green-400";
      case "info":
        return "text-blue-400";
      case "debug":
        return "text-purple-400";
      case "eula":
        return "text-orange-400";
      case "startup":
        return "text-cyan-400";
      case "shutdown":
        return "text-gray-400";
      case "system":
        return "text-gray-300";
      default:
        return "text-white/80";
    }
  };

  const downloadLogs = () => {
    const logText = consoleOutput
      .map(
        (msg) =>
          `[${msg.timestamp}] [${msg.type?.toUpperCase()}] ${
            msg.text || msg.data
          }`
      )
      .join("\n");
    const blob = new Blob([logText], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `console-${new Date().toISOString()}.log`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const filteredOutput = consoleOutput.filter((msg) => {
    if (!filter) return true;
    const text = (msg.text || msg.data || "").toLowerCase();
    const type = (msg.type || "").toLowerCase();
    const searchTerm = filter.toLowerCase();
    return text.includes(searchTerm) || type.includes(searchTerm);
  });

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (command.trim() && sendCommand) {
      sendCommand(command);
    }
  };

  if (compact) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="glass-card"
      >
        <div className="flex justify-between items-center mb-4">
          <motion.h2
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="text-xl font-semibold text-white flex items-center gap-2"
          >
            <Terminal className="text-teal-300" />
            Console
          </motion.h2>
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.95 }}
            onClick={downloadLogs}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            title="Download logs"
          >
            <Download className="text-white/70 hover:text-white" />
          </motion.button>
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4, delay: 0.2 }}
          ref={scrollContainerRef}
          onScroll={handleScroll}
          className="bg-black/50 rounded-lg p-3 h-64 overflow-auto font-mono text-sm custom-scrollbar"
        >
          <div className="space-y-1">
            <AnimatePresence mode="popLayout">
              {consoleOutput.length > 0 ? (
                <motion.div key="compact-output" layout>
                  {consoleOutput.map((message, index) => {
                    const displayText = message.text || message.data || "";
                    const timestamp = message.timestamp || "";
                    const messageType = message.type || "default";

                    return (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 10 }}
                        transition={{ duration: 0.3, ease: "easeOut" }}
                        className={getConsoleLineClass(messageType)}
                      >
                        <span className="text-gray-500 mr-2">
                          [{timestamp}]
                        </span>
                        {displayText}
                      </motion.div>
                    );
                  })}
                  <div ref={consoleEndRef} />
                </motion.div>
              ) : (
                <motion.div
                  key="compact-empty"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.4 }}
                  className="text-white/40 italic"
                >
                  No console output available
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>

        <AnimatePresence>
          {!autoScroll && (
            <motion.button
              key="compact-autoscroll"
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.3 }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => {
                setAutoScroll(true);
                consoleEndRef.current?.scrollIntoView({ behavior: "smooth" });
              }}
              className="mt-3 w-full py-2 bg-white/5 hover:bg-white/10 text-white/70 text-sm rounded-lg transition-colors"
            >
              ↓ Auto-scroll disabled. Click to scroll to bottom
            </motion.button>
          )}
        </AnimatePresence>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="glass-card"
    >
      <div className="flex justify-between items-center mb-4">
        <motion.h2
          initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.4 }}
          className="text-2xl font-semibold text-white flex items-center gap-2"
        >
          <motion.div
            animate={{ rotate: [0, 10, -10, 0] }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <Terminal className="text-teal-300" />
          </motion.div>
          Console
        </motion.h2>
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
          onClick={downloadLogs}
          className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          title="Download logs"
        >
          <Download className="text-white/70 hover:text-white" />
        </motion.button>
      </div>

      {/* Filter */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2 }}
        className="relative mb-4"
      >
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" />
        <input
          type="text"
          placeholder="Filter console output..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="w-full bg-white/10 border border-white/20 rounded-lg pl-10 pr-4 py-2 text-sm text-white placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-pink-500 transition-color"
        />
      </motion.div>

      {/* Console Output */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.3 }}
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="bg-black/50 rounded-lg p-3 h-96 overflow-auto font-mono text-sm mb-3 custom-scrollbar"
      >
        <div className="space-y-1">
          <AnimatePresence mode="popLayout">
            {filteredOutput.length > 0 ? (
              <motion.div key="output-wrapper" layout>
                {filteredOutput.map((message, index) => {
                  const displayText = message.text || message.data || "";
                  const timestamp = message.timestamp || "";
                  const messageType = message.type || "default";

                  return (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 10 }}
                      transition={{ duration: 0.3, ease: "easeOut" }}
                      className={getConsoleLineClass(messageType)}
                    >
                      <span className="text-gray-500 mr-2">[{timestamp}]</span>
                      {displayText}
                    </motion.div>
                  );
                })}
                <div ref={consoleEndRef} />
              </motion.div>
            ) : filter ? (
              <motion.div
                key="no-filter"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.4 }}
                className="text-white/40 italic"
              >
                No messages match your filter
              </motion.div>
            ) : (
              <motion.div
                key="no-output"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.4 }}
                className="text-white/40 italic"
              >
                No console output available
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>

      {/* Command Input */}
      {setCommand && sendCommand && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.4 }}
          className="space-y-3"
        >
          <div className="flex gap-2">
            <input
              type="text"
              placeholder={isOnline ? "Type a command..." : "Server is offline"}
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  handleSubmit(e);
                }
              }}
              disabled={!isOnline}
              className="flex-1 bg-white/10 border border-white/20 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-pink-500 disabled:opacity-50 disabled:cursor-not-allowed transition-color"
            />
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => handleSubmit()}
              disabled={!isOnline || !command.trim()}
              className="btn btn-primary"
            >
              Send
            </motion.button>
          </div>

          <AnimatePresence>
            {!autoScroll && (
              <motion.button
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3 }}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => {
                  setAutoScroll(true);
                  consoleEndRef.current?.scrollIntoView({ behavior: "smooth" });
                }}
                className="w-full py-2 bg-white/5 hover:bg-white/10 text-white/70 text-sm rounded-lg transition-colors"
              >
                ↓ Auto-scroll disabled. Click to scroll to bottom
              </motion.button>
            )}
          </AnimatePresence>
        </motion.div>
      )}
    </motion.div>
  );
};
