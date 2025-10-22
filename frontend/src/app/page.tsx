"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import Image from "next/image";
import { Server, Rocket, Shield, Settings } from "lucide-react";

const features = [
  {
    icon: <Server className="text-4xl text-pink-500" />,
    title: "Easy Server Creation",
    description:
      "Create Minecraft servers in just a few clicks. Support for Vanilla, Paper, Fabric, and more.",
  },
  {
    icon: <Rocket className="text-4xl text-blue-500" />,
    title: "Instant Deployment",
    description:
      "Your server will be up and running in seconds with optimized performance settings.",
  },
  {
    icon: <Shield className="text-4xl text-purple-500" />,
    title: "Secure Management",
    description:
      "Full control over your servers with secure authentication and user management.",
  },
  {
    icon: <Settings className="text-4xl text-green-500" />,
    title: "Advanced Controls",
    description:
      "Monitor performance, manage players, and control your server through an intuitive interface.",
  },
];

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.2,
    },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

export default function Home() {
  return (
    <div className="min-h-screen">
      <section className="py-20 px-4">
        <div className="container mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <h1 className="text-5xl md:text-6xl font-bold text-white mb-6">
              Minecraft Server Management
              <br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-pink-500 to-purple-600">
                Made Simple
              </span>
            </h1>
            <p className="text-xl text-white/60 mb-12 max-w-2xl mx-auto">
              Create, manage, and monitor your Minecraft servers with ease. Get
              started in minutes with our intuitive interface.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/signup" className="btn btn-primary">
                Get Started
              </Link>
              <Link href="/login" className="btn btn-secondary">
                Login
              </Link>
            </div>
          </motion.div>

          <motion.div
            variants={container}
            initial="hidden"
            animate="show"
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mt-20"
          >
            {features.map((feature, index) => (
              <motion.div
                key={index}
                variants={item}
                className="glass-card hover:bg-white/20 transition-colors"
              >
                <div className="flex flex-col items-center">
                  {feature.icon}
                  <h3 className="text-xl font-semibold text-white mt-4 mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-white/60 text-center">
                    {feature.description}
                  </p>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      <motion.section
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        transition={{ duration: 0.8 }}
        className="py-20 px-4 relative overflow-hidden"
      >
        <div className="container mx-auto">
          <div className="glass-card relative z-10">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-center">
              <div>
                <h2 className="text-3xl font-bold text-white mb-4">
                  Why Choose Voxely?
                </h2>
                <ul className="space-y-4">
                  <li className="flex items-start gap-3">
                    <div className="rounded-full bg-green-500/20 p-1">
                      <svg
                        className="w-5 h-5 text-green-500"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    </div>
                    <p className="text-white/80">
                      Easy to use interface with real-time monitoring
                    </p>
                  </li>
                  <li className="flex items-start gap-3">
                    <div className="rounded-full bg-green-500/20 p-1">
                      <svg
                        className="w-5 h-5 text-green-500"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    </div>
                    <p className="text-white/80">
                      Support for multiple server types and versions
                    </p>
                  </li>
                  <li className="flex items-start gap-3">
                    <div className="rounded-full bg-green-500/20 p-1">
                      <svg
                        className="w-5 h-5 text-green-500"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    </div>
                    <p className="text-white/80">
                      Advanced performance optimization
                    </p>
                  </li>
                </ul>
              </div>
              <div className="relative">
                <div className="aspect-video rounded-lg overflow-hidden">
                  <Image
                    src="https://images.unsplash.com/photo-1742599968125-a790a680a605?q=80&w=3464&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
                    alt="Dashboard Preview"
                    className="w-full h-full object-cover opacity-80"
                    width={1920}
                    height={1080}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.section>

      <section className="py-20 px-4">
        <div className="container mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <h2 className="text-3xl font-bold text-white mb-8">
              Ready to Start?
            </h2>
            <Link href="/signup" className="btn btn-primary">
              Create Your Server Now
            </Link>
          </motion.div>
        </div>
      </section>
    </div>
  );
}
