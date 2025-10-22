"use client";
import { ConsoleMessage } from "@/utils/types";
import { useRef, useEffect, useState } from "react";
import { Terminal, Download, Search } from "lucide-react";

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
      <div className="glass-card">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-white flex items-center gap-2">
            <Terminal className="text-white/70" />
            Console
          </h2>
          <button
            onClick={downloadLogs}
            className="p-2 hover:bg-white/10 rounded-lg transition-colors"
            title="Download logs"
          >
            <Download className="text-white/70 hover:text-white" />
          </button>
        </div>
        <div
          ref={scrollContainerRef}
          onScroll={handleScroll}
          className="bg-black/50 rounded-lg p-3 h-64 overflow-auto font-mono text-sm"
        >
          <div className="space-y-1">
            {consoleOutput.length > 0 ? (
              <>
                {consoleOutput.map((message, index) => {
                  const displayText = message.text || message.data || "";
                  const timestamp = message.timestamp || "";
                  const messageType = message.type || "default";

                  return (
                    <div
                      key={index}
                      className={getConsoleLineClass(messageType)}
                    >
                      <span className="text-gray-500 mr-2">[{timestamp}]</span>
                      {displayText}
                    </div>
                  );
                })}
                <div ref={consoleEndRef} />
              </>
            ) : (
              <div className="text-white/40 italic">
                No console output available
              </div>
            )}
          </div>
        </div>
        {!autoScroll && (
          <button
            onClick={() => {
              setAutoScroll(true);
              consoleEndRef.current?.scrollIntoView({ behavior: "smooth" });
            }}
            className="mt-3 w-full py-2 bg-white/5 hover:bg-white/10 text-white/70 text-sm rounded-lg transition-colors"
          >
            ↓ Auto-scroll disabled. Click to scroll to bottom
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="glass-card">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold text-white flex items-center gap-2">
          <Terminal className="text-white/70" />
          Console
        </h2>
        <button
          onClick={downloadLogs}
          className="p-2 hover:bg-white/10 rounded-lg transition-colors"
          title="Download logs"
        >
          <Download className="text-white/70 hover:text-white" />
        </button>
      </div>

      {/* Filter */}
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" />
        <input
          type="text"
          placeholder="Filter console output..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="w-full bg-white/10 border border-white/20 rounded-lg pl-10 pr-4 py-2 text-sm text-white placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-pink-500"
        />
      </div>

      {/* Console Output */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="bg-black/50 rounded-lg p-3 h-96 overflow-auto font-mono text-sm mb-3"
      >
        <div className="space-y-1">
          {filteredOutput.length > 0 ? (
            <>
              {filteredOutput.map((message, index) => {
                const displayText = message.text || message.data || "";
                const timestamp = message.timestamp || "";
                const messageType = message.type || "default";

                return (
                  <div key={index} className={getConsoleLineClass(messageType)}>
                    <span className="text-gray-500 mr-2">[{timestamp}]</span>
                    {displayText}
                  </div>
                );
              })}
              <div ref={consoleEndRef} />
            </>
          ) : filter ? (
            <div className="text-white/40 italic">
              No messages match your filter
            </div>
          ) : (
            <div className="text-white/40 italic">
              No console output available
            </div>
          )}
        </div>
      </div>

      {/* Command Input */}
      {setCommand && sendCommand && (
        <div className="space-y-3">
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
              className="flex-1 bg-white/10 border border-white/20 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-pink-500 disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <button
              onClick={() => handleSubmit()}
              disabled={!isOnline || !command.trim()}
              className="btn btn-primary"
            >
              Send
            </button>
          </div>

          {!autoScroll && (
            <button
              onClick={() => {
                setAutoScroll(true);
                consoleEndRef.current?.scrollIntoView({ behavior: "smooth" });
              }}
              className="w-full py-2 bg-white/5 hover:bg-white/10 text-white/70 text-sm rounded-lg transition-colors"
            >
              ↓ Auto-scroll disabled. Click to scroll to bottom
            </button>
          )}
        </div>
      )}
    </div>
  );
};
