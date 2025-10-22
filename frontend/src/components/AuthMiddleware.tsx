'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { api } from '@/utils/api';

export default function AuthMiddleware({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [isAuthorized, setIsAuthorized] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const verifyAuth = async () => {
      try {
        setIsLoading(true);
        const token = localStorage.getItem('token');
        
        if (!token) {
          throw new Error('No authentication token found');
        }

        // Use the apiRequest utility to verify the token
        await api.get('/auth/verify');
        setIsAuthorized(true);
      } catch (error) {
        console.error('Auth verification failed:', error);
        let errorMessage = 'Authentication failed. Please login again.';
        
        if (error instanceof Error) {
          errorMessage = error.message;
        }
        
        setError(errorMessage);
        
        // Redirect to login after a short delay to show the error
        setTimeout(() => {
          router.push('/login');
        }, 1500);
      } finally {
        setIsLoading(false);
      }
    };

    verifyAuth();
  }, [router]);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="loader"></div>
      </div>
    );
  }

  if (!isAuthorized) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-red-400 text-center p-6 bg-red-500/20 rounded-lg glass-card"
        >
          <p>{error || 'Authentication failed. Redirecting to login...'}</p>
        </motion.div>
      </div>
    );
  }

  return <>{children}</>;
}