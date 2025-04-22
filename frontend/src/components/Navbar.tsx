'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { FaServer, FaUser, FaSignOutAlt } from 'react-icons/fa';

export default function Navbar() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem('token');
    setIsAuthenticated(!!token);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    router.push('/login');
  };

  return (
    <motion.nav 
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      className="glass-navbar"
    >
      <div className="container mx-auto px-4">
        <div className="h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <FaServer className="text-pink-500 text-2xl" />
            <span className="text-xl font-bold text-white">MineGimmeThat</span>
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
                  <FaSignOutAlt />
                  Logout
                </button>
              </>
            ) : (
              <Link 
                href="/login"
                className="flex items-center gap-2 text-white/80 hover:text-white transition-colors"
              >
                <FaUser />
                Login
              </Link>
            )}
          </div>
        </div>
      </div>
    </motion.nav>
  );
}