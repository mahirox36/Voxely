"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import api from "@/utils/api";

export default function Login() {
  const username = "root";
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isRedirecting, setIsRedirecting] = useState(false);
  const [first, setFirst] = useState<boolean>(true);
  const router = useRouter();

  // Check for existing authentication on component mount
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      setIsRedirecting(true);
      // Add a small delay to show the redirecting message
      const redirectTimer = setTimeout(() => {
        router.push("/dashboard");
      }, 1000);

      return () => clearTimeout(redirectTimer);
    }
  }, [router]);

  useEffect(() => {
    (async () => {
      try {
        const res: boolean = await api.get("/auth/first_time");
        setFirst(res)

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } catch (err: any) {
        setError(err.response?.data?.detail || "Login failed");
        console.error(err);
      }
    })();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    try {
      const data: {token_type: string, access_token:string} = await api.post("/auth/token", {
        username: username,
        password: password,
      });


      // Store the complete token with type
      localStorage.setItem("token", `${data.token_type} ${data.access_token}`);
      setIsRedirecting(true);
      router.push("/dashboard");
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      setError(err.response?.data?.detail || "Login failed");
      console.error(err);
    }
  };

  // If already authenticated and redirecting, show a message
  if (isRedirecting) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-card p-8 text-center"
        >
          <h2 className="text-xl text-white mb-4">Already logged in!</h2>
          <p className="text-white/70 mb-4">Redirecting to dashboard...</p>
          <div className="loader mx-auto"></div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-md w-full"
      >
        <div className="glass-card">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
          >
            <h2 className="text-3xl font-bold text-center mb-8 text-white">
              {first ? "Create a password" : "Welcome Back"}
            </h2>
          </motion.div>

          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="text-red-300 text-sm text-center bg-red-500/20 py-2 px-4 rounded-lg"
              >
                {error}
              </motion.div>
            )}

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <label
                htmlFor="username"
                className="block text-sm font-medium text-white mb-1"
              >
                Username
              </label>
              <input
                id="username"
                name="username"
                type="text"
                required
                className="w-full px-4 py-2 rounded-lg border border-white/30 bg-white/10 backdrop-blur-sm text-white placeholder:text-white/50 focus:outline-none focus:ring-2 focus:ring-white/50 focus:border-transparent"
                placeholder="Enter your username"
                value={username}
                disabled
                // onChange={(e) => setUsername(e.target.value)}
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              <label
                htmlFor="password"
                className="block text-sm font-medium text-white mb-1"
              >
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                className="w-full px-4 py-2 rounded-lg border border-white/30 bg-white/10 backdrop-blur-sm text-white placeholder:text-white/50 focus:outline-none focus:ring-2 focus:ring-white/50 focus:border-transparent"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
            >
              <button type="submit" className="btn btn-primary w-full">
                Sign in
              </button>
            </motion.div>
          </form>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="text-center mt-6"
          ></motion.div>
        </div>
      </motion.div>
    </div>
  );
}
