'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { motion } from 'framer-motion';

export default function Signup() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [isRedirecting, setIsRedirecting] = useState(false);
  const router = useRouter();

  // Check for existing authentication on component mount
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      setIsRedirecting(true);
      // Add a small delay to show the redirecting message
      const redirectTimer = setTimeout(() => {
        router.push('/dashboard');
      }, 1000);
      
      return () => clearTimeout(redirectTimer);
    }
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    try {
      // First create the user
      const signupRes = await fetch('/api/v1/auth/signup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username,
          password,
          email
        }),
      });

      const signupData = await signupRes.json();

      if (!signupRes.ok) {
        setError(signupData.detail || 'Signup failed');
        return;
      }

      // Then login to get the token
      const loginRes = await fetch('/api/v1/auth/token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`,
      });

      const loginData = await loginRes.json();

      if (loginRes.ok) {
        localStorage.setItem('token', `${loginData.token_type} ${loginData.access_token}`);
        setIsRedirecting(true);
        router.push('/dashboard');
      } else {
        setError(loginData.detail || 'Login after signup failed');
      }
    } catch (err) {
      setError('An error occurred. Please try again.');
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
              Create Account
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
              <label htmlFor="username" className="block text-sm font-medium text-white mb-1">
                Username
              </label>
              <input
                id="username"
                name="username"
                type="text"
                required
                className="w-full px-4 py-2 rounded-lg border border-white/30 bg-white/10 backdrop-blur-sm text-white placeholder:text-white/50 focus:outline-none focus:ring-2 focus:ring-white/50 focus:border-transparent"
                placeholder="Choose a username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
            >
              <label htmlFor="email" className="block text-sm font-medium text-white mb-1">
                Email (Optional)
              </label>
              <input
                id="email"
                name="email"
                type="email"
                className="w-full px-4 py-2 rounded-lg border border-white/30 bg-white/10 backdrop-blur-sm text-white placeholder:text-white/50 focus:outline-none focus:ring-2 focus:ring-white/50 focus:border-transparent"
                placeholder="Enter your email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
            >
              <label htmlFor="password" className="block text-sm font-medium text-white mb-1">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                className="w-full px-4 py-2 rounded-lg border border-white/30 bg-white/10 backdrop-blur-sm text-white placeholder:text-white/50 focus:outline-none focus:ring-2 focus:ring-white/50 focus:border-transparent"
                placeholder="Create a password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 }}
            >
              <button
                type="submit"
                className="btn btn-primary w-full"
              >
                Sign up
              </button>
            </motion.div>
          </form>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.7 }}
            className="text-center mt-6"
          >
            <p className="text-sm text-on-glass-muted">
              Already have an account?{' '}
              <Link
                href="/login"
                className="text-white hover:text-pink-200 transition-colors font-medium"
              >
                Sign in
              </Link>
            </p>
          </motion.div>
        </div>
      </motion.div>
    </div>
  );
}