"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import {
  Server,
  MemoryStick,
  Users,
  Network,
  ChevronDown,
  Check,
} from "lucide-react";
import AuthMiddleware from "@/components/AuthMiddleware";
import { api } from "@/utils/api";

// Server type options
const serverTypes = [
  { id: "vanilla", name: "Vanilla", description: "Pure Minecraft experience" },
  {
    id: "paper",
    name: "Paper",
    description: "Optimized server with plugin support",
  },
  { id: "fabric", name: "Fabric", description: "Lightweight mod loader" },
  {
    id: "purpur",
    name: "Purpur",
    description: "Paper fork with additional features",
  },
  {
    id: "custom",
    name: "Custom",
    description: "upload your own Jar file",
  },
];

// Custom dropdown component for animated version selector
function AnimatedDropdown({
  options,
  value,
  onChange,
  className = "",
}: {
  options: string[];
  value: string;
  onChange: (value: string) => void;
  className?: string;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      <button
        type="button"
        className="w-full flex items-center justify-between bg-white/10 border border-white/20 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-pink-500 transition-all"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span>{value}</span>
        <motion.span
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <ChevronDown className="text-white/70" />
        </motion.span>
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10, scaleY: 0.8 }}
            animate={{ opacity: 1, y: 0, scaleY: 1 }}
            exit={{ opacity: 0, y: -10, scaleY: 0.8 }}
            transition={{ duration: 0.2 }}
            className="absolute z-10 mt-1 w-full max-h-60 overflow-auto rounded-md bg-black/70 border border-white/20 p-1 backdrop-blur-xl"
            style={{ transformOrigin: "top" }}
          >
            <div className="py-1">
              {options.map((option) => (
                <motion.button
                  key={option}
                  type="button"
                  whileHover={{ backgroundColor: "rgba(255, 255, 255, 0.1)" }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => {
                    onChange(option);
                    setIsOpen(false);
                  }}
                  className="w-full text-left px-3 py-2 text-white rounded flex items-center justify-between"
                >
                  <span>{option}</span>
                  {option === value && <Check className="text-pink-400" />}
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function CreateServer() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [versions, setVersions] = useState<Record<string, string[]>>({});
  const [systemRam, setSystemRam] = useState(16384);
  const [formData, setFormData] = useState({
    name: "",
    type: "paper",
    version: "1.21.10",
    minRam: 1024,
    maxRam: 2048,
    port: 25565,
    maxPlayers: 20,
  });
  const [jarFile, setJarFile] = useState<File | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setJarFile(e.target.files[0]);
    }
  };

  useEffect(() => {
    const fetchVersions = async () => {
      try {
        const data: Record<string, string[]> = await api("/servers/versions");
        setVersions(data);
      } catch (err) {
        console.error("Failed to fetch versions:", err);
      }
    };

    // Fetch system RAM information
    const fetchSystemInfo = async () => {
      try {
        // This would ideally come from a backend endpoint
        // For now we'll estimate based on navigator.deviceMemory if available
        const memory = (navigator as Navigator & { deviceMemory?: number })
          .deviceMemory;
        if (memory) {
          setSystemRam(memory * 1024); // Convert GB to MB
        }
      } catch (err) {
        console.error("Failed to get system RAM:", err);
      }
    };

    fetchVersions();
    fetchSystemInfo();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    try {
      const data = new FormData();
      data.append("name", formData.name);
      data.append("type", formData.type);
      data.append("version", formData.version);
      data.append("minRam", formData.minRam.toString());
      data.append("maxRam", formData.maxRam.toString());
      data.append("port", formData.port.toString());
      data.append("maxPlayers", formData.maxPlayers.toString());

      if (jarFile) {
        data.append("jar_file", jarFile);
      }

      await api.post("/servers/create", data);

      router.push("/dashboard");
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("An unknown error occurred");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]:
        name === "minRam" ||
        name === "maxRam" ||
        name === "port" ||
        name === "maxPlayers"
          ? parseInt(value)
          : value,
    }));
  };

  const handleVersionChange = (version: string) => {
    setFormData((prev) => ({ ...prev, version }));
  };

  // Get available versions for the selected server type
  const availableVersions = versions[formData.type] || [];

  return (
    <AuthMiddleware>
      <div className="min-h-screen">
        <div className="container mx-auto px-4 py-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="max-w-2xl mx-auto"
          >
            <h1 className="text-4xl font-bold text-white mb-8">
              Create New Server
            </h1>

            <form onSubmit={handleSubmit} className="space-y-8">
              {error && (
                <motion.div
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="text-red-300 text-sm bg-red-500/20 py-2 px-4 rounded-lg"
                >
                  {error}
                </motion.div>
              )}

              <div className="glass-card space-y-6">
                <div>
                  <label className="block text-sm font-medium text-white mb-2">
                    Server Name
                  </label>
                  <div className="flex items-center gap-2">
                    <Server className="text-pink-400" />
                    <input
                      type="text"
                      name="name"
                      required
                      value={formData.name}
                      onChange={handleChange}
                      className="flex-1 bg-white/10 border border-white/20 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-pink-500"
                      placeholder="My Awesome Server"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-white mb-2">
                    Server Type
                  </label>
                  <div className="grid grid-cols-2 gap-4">
                    {serverTypes.map((type) => (
                      <motion.div
                        key={type.id}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        className={`cursor-pointer p-4 rounded-lg border-2 transition-colors ${
                          formData.type === type.id
                            ? "border-pink-500 bg-pink-500/20"
                            : "border-white/20 hover:border-white/40"
                        }`}
                        onClick={() =>
                          setFormData((prev) => ({ ...prev, type: type.id }))
                        }
                      >
                        <h3 className="text-white font-medium">{type.name}</h3>
                        <p className="text-white/60 text-sm">
                          {type.description}
                        </p>
                      </motion.div>
                    ))}
                    <AnimatePresence>
                      {formData.type === "custom" && (
                        <motion.div
                          key="customJar"
                          initial={{ opacity: 0, y: -10 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -10 }}
                          transition={{ duration: 0.2 }}
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          className="p-4 rounded-lg border-2 col-span-2 border-pink-500 bg-pink-500/20"
                        >
                          <label className="block text-sm font-medium text-white mb-2">
                            Upload Custom Jar
                          </label>

                          <div className="flex items-center gap-2">
                            <input
                              type="file"
                              name="jar_file"
                              accept=".jar,.zip"
                              onChange={handleFileChange}
                              disabled={formData.type !== "custom"}
                              className="w-full bg-white/10 border border-white/20 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-pink-500 disabled:opacity-50 disabled:cursor-not-allowed"
                            />
                            <motion.span
                              className="text-white/70 text-sm"
                              animate={{
                                opacity: formData.type === "custom" ? 1 : 0.6,
                              }}
                            >
                              {formData.type === "custom"
                                ? "Ready to upload"
                                : "Enable Custom to upload"}
                            </motion.span>
                          </div>

                          <p className="text-white/60 text-xs mt-2">
                            Choose a .jar (or .zip) file to upload. When
                            submitting the form the file should be included as
                            the form field &quot;jar_file&quot; in a
                            multipart/form-data request.
                          </p>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-white mb-2">
                      Minecraft Version
                    </label>
                    <AnimatedDropdown
                      options={availableVersions}
                      value={formData.version}
                      onChange={handleVersionChange}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-white mb-2">
                      Maximum Players
                    </label>
                    <div className="flex items-center gap-2">
                      <Users className="text-blue-400" />
                      <input
                        type="number"
                        name="maxPlayers"
                        min="1"
                        max="100"
                        value={formData.maxPlayers}
                        onChange={handleChange}
                        className="w-full bg-white/10 border border-white/20 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-pink-500"
                      />
                    </div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-white mb-2">
                      RAM (Min-Max) - Max Available:{" "}
                      {Math.floor(systemRam / 1024)}GB
                    </label>
                    <div className="flex items-center gap-2">
                      <MemoryStick className="text-purple-400" />
                      <input
                        type="number"
                        name="minRam"
                        min="512"
                        max={systemRam}
                        step="512"
                        value={formData.minRam}
                        onChange={handleChange}
                        className="w-full bg-white/10 border border-white/20 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-pink-500"
                      />
                      <span className="text-white">-</span>
                      <input
                        type="number"
                        name="maxRam"
                        min="512"
                        max={systemRam}
                        step="512"
                        value={formData.maxRam}
                        onChange={handleChange}
                        className="w-full bg-white/10 border border-white/20 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-pink-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-white mb-2">
                      Server Port
                    </label>
                    <div className="flex items-center gap-2">
                      <Network className="text-green-400" />
                      <input
                        type="number"
                        name="port"
                        min="1024"
                        max="65535"
                        value={formData.port}
                        onChange={handleChange}
                        className="w-full bg-white/10 border border-white/20 rounded-lg px-4 py-2 text-white focus:outline-none focus:ring-2 focus:ring-pink-500"
                      />
                    </div>
                  </div>
                </div>
              </div>

              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.2 }}
                className="flex justify-end gap-4"
              >
                <button
                  type="button"
                  onClick={() => router.back()}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isLoading}
                  className="btn btn-primary"
                >
                  {isLoading ? (
                    <div className="loader w-5 h-5"></div>
                  ) : (
                    "Create Server"
                  )}
                </button>
              </motion.div>
            </form>
          </motion.div>
        </div>
      </div>
    </AuthMiddleware>
  );
}
