'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { Server, User, LogOut } from 'lucide-react';

export default function Navbar() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const router = useRouter();
  const [isServerPage, setIsServerPage] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      setIsServerPage(window.location.pathname.startsWith('/dashboard/server/'));
    }
  }, []);

  useEffect(() => {
    const token = localStorage.getItem('token');
    setIsAuthenticated(!!token);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    router.push('/login');
  };

  if (isServerPage) return null;

  return (
    <motion.nav 
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      className="glass-navbar"
    >
      <div className="container mx-auto px-4">
        <div className="h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <Server className="text-pink-500 text-2xl" />
            <span className="text-xl font-bold text-white">Voxely</span>
          </Link>

          <div className="flex items-center gap-6">
            {isAuthenticated ? (
              <>
                <Link 
                  href="/dashboard"
                  className="text-white/80 hover:text-white transition-colors"
                >
                  Dashboard
                </Link>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 text-white/80 hover:text-white transition-colors"
                >
                  <LogOut />
                  Logout
                </button>
              </>
            ) : (
              <Link 
                href="/login"
                className="flex items-center gap-2 text-white/80 hover:text-white transition-colors"
              >
                <User />
                Login
              </Link>
            )}
          </div>
        </div>
      </div>
    </motion.nav>
  );
}