'use client';

import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

interface Particle {
  x: number;
  y: number;
  size: number;
  color: string;
}

export default function BackgroundElements() {
  const containerRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (!containerRef.current) return;
    
    const container = containerRef.current;
    const particles: Particle[] = [];
    const particleCount = 50;
    
    // Create particles
    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * 100,
        y: Math.random() * 100,
        size: Math.random() * 4 + 2,
        color: `rgba(255, 255, 255, ${Math.random() * 0.1})`
      });
    }
    
    // Add particles to DOM
    particles.forEach(particle => {
      const element = document.createElement('div');
      element.className = 'particle';
      element.style.left = `${particle.x}%`;
      element.style.top = `${particle.y}%`;
      element.style.width = `${particle.size}px`;
      element.style.height = `${particle.size}px`;
      element.style.background = particle.color;
      element.style.animation = `float ${8 + Math.random() * 4}s infinite ease-in-out ${Math.random() * 2}s`;
      container.appendChild(element);
    });
    
    return () => {
      container.innerHTML = '';
    };
  }, []);

  return (
    <>
      <div ref={containerRef} className="particles" />
      <motion.div
        className="fixed inset-0 z-[-1]"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1 }}
      >
        <div className="absolute inset-0 bg-gradient-to-br from-purple-900/20 via-transparent to-pink-900/20" />
      </motion.div>
    </>
  );
}