import { motion } from "framer-motion";
import { useRef, useEffect } from "react";

interface ConsoleOutputProps {
  consoleOutput: string[];
  consoleConnected: boolean;
  command: string;
  setCommand: (command: string) => void;
  sendCommand: (command: string) => void;
  isOnline: boolean;
}

export const ConsoleOutput = ({
  consoleOutput,
  consoleConnected,
  command,
  setCommand,
  sendCommand,
  isOnline,
}: ConsoleOutputProps) => {
  const consoleEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [consoleOutput]);

  const getConsoleLineClass = (type: string) => {
    switch (type) {
      case "info":
        return "text-blue-400";
      case "warning":
        return "text-yellow-400";
      case "error":
        return "text-red-400";
      default:
        return "text-white/80";
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      className="glass-card"
    >
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold text-white">Console</h2>
        <div
          className={`px-2 py-1 text-xs rounded-full ${
            consoleConnected
              ? "bg-green-500/20 text-green-300"
              : "bg-red-500/20 text-red-300"
          }`}
        >
          {consoleConnected ? "Connected" : "Disconnected"}
        </div>
      </div>

      <div className="bg-black/50 rounded-lg p-3 h-96 overflow-auto font-mono text-sm">
        <div className="space-y-1">
          {consoleOutput.length > 0 ? (
            <>
              {consoleOutput.map((line, index) => {
                // Try to parse the JSON message
                let messageObj;
                try {
                  messageObj = JSON.parse(line);
                } catch {
                  // If not valid JSON, just display as plain text
                  return (
                    <div key={index} className="text-white/80">
                      {line}
                    </div>
                  );
                }

                // Return colored text based on message type
                return (
                  <div
                    key={index}
                    className={getConsoleLineClass(messageObj.type)}
                  >
                    <span className="text-gray-500 mr-2">
                      [{messageObj.timestamp}]
                    </span>
                    {messageObj.text}
                  </div>
                );
              })}
              <div ref={consoleEndRef} /> {/* Scroll anchor */}
            </>
          ) : (
            <div className="text-white/40 italic">
              No console output available
            </div>
          )}
        </div>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (command.trim()) {
            sendCommand(command);
          }
        }}
        className="mt-3 flex gap-2"
      >
        <input
          type="text"
          placeholder={isOnline ? "Type a command..." : "Server is offline"}
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          disabled={!isOnline}
          className="flex-1 bg-white/10 border border-white/20 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-pink-500"
        />
        <button
          type="submit"
          disabled={!isOnline || !command.trim()}
          className="btn btn-primary"
        >
          Send
        </button>
      </form>
    </motion.div>
  );
};