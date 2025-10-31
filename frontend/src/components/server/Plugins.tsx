"use client";
import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
// import { toast } from "sonner";
import usePlugins from "@/hooks/usePlugins";
import {
  AlertTriangle,
  Download,
  ExternalLink,
  HelpCircle,
  ImageIcon,
  Puzzle,
  Trash,
} from "lucide-react";
import { PluginsHeader } from "./plugins/PluginHeader";
import { Addon, Project } from "@/utils/types";
import Image from "next/image";
import { useModal } from "@/components/ModalProvider";
import api from "@/utils/api";
import { toast } from "sonner";
// Component props: parent should pass serverName (string)

export default function Plugins({ serverName }: { serverName: string }) {
  const {
    setQuery,
    installed,
    removeInstalled,
    query,
    doSearch,
    searchResults,
    downloadProjectVersion,
    downloadingMods,
    removeDownloadingMods,
    addDownloadingMods,
  } = usePlugins(serverName);
  const { showModal } = useModal();

  const ImportModal: React.FC<{ serverName: string }> = ({ serverName }) => {
    const { hideModal } = useModal();
    const [file, setFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const onChange = (e: React.ChangeEvent<HTMLInputElement>) => {
      const f = e.target.files && e.target.files[0];
      if (f && f.name.endsWith(".mrpack")) setFile(f);
      else setFile(null);
    };

    const handleUpload = async () => {
      if (!file) return;
      setUploading(true);
      try {
        const formData = new FormData();
        formData.append("file", file);
        try {
          await api.post(`/servers/${serverName}/plugins/import`, formData);
          toast.success("Imported Modpack!");
        } catch {}
        // handle response as needed

        hideModal(); // close top-most modal
      } catch (err) {
        console.error(err);
        hideModal();
      } finally {
        setUploading(false);
      }
    };

    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 8 }}
        className="space-y-4"
      >
        <p className="text-sm text-white/80">
          Select a .mrpack file to import to the server.
        </p>
        <input
          type="file"
          accept=".mrpack"
          onChange={onChange}
          className="w-full text-sm"
        />
        <div className="flex justify-end gap-3">
          <button
            className="btn btn-secondary"
            onClick={() => hideModal()}
            disabled={uploading}
          >
            Cancel
          </button>
          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.98 }}
            className="btn btn-primary flex items-center gap-2"
            onClick={handleUpload}
            disabled={!file || uploading}
          >
            <Download className="w-4 h-4" />
            {uploading ? "Uploading..." : "Import"}
          </motion.button>
        </div>
      </motion.div>
    );
  };
  const [download_page, setDownloadPage] = useState<boolean>(false);
  const [page, setPage] = useState<number>(0);
  const [filteredInstalled, setFilteredInstalled] = useState<Addon[]>([]);
  const divRef = useRef<HTMLDivElement>(null);

  // useEffect(() => {
  //   if (installed) {
  //     setFilteredInstalled(installed);
  //   }
  // }, [installed]);

  const getServerSideWarning = (serverSide: string) => {
    if (serverSide === "unsupported") {
      return (
        <div className="flex items-center gap-2 text-red-400 text-sm mt-2">
          <AlertTriangle className="w-4 h-4" />
          <span>Server-side unsupported - Client only</span>
        </div>
      );
    }
    if (serverSide === "unknown") {
      return (
        <div className="flex items-center gap-2 text-yellow-400 text-sm mt-2">
          <HelpCircle className="w-4 h-4" />
          <span>Server compatibility unknown</span>
        </div>
      );
    }
    return null;
  };

  useEffect(() => {
    if (download_page) {
      // add a delay only for remote searches
      const handler = setTimeout(() => {
        doSearch(page);
      }, 400);
      return () => clearTimeout(handler);
    } else {
      // instant filtering for installed mods
      setFilteredInstalled(
        installed.filter((item) =>
          item.project.title.toLowerCase().includes(query.toLowerCase())
        )
      );
    }
  }, [query, page, download_page, doSearch, installed]);

  return (
    <motion.div
      className="glass-card h-[calc(100vh-16rem)] mx-auto p-6 flex flex-col justify-center"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      // onClick={() => {
      //   if (contextMenu.visible) closeContextMenu();
      // }}
    >
      {/* Header */}
      <motion.div
        className="flex justify-between items-center mb-6"
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.1 }}
      >
        <div className="flex flex-row items-center justify-between gap-4">
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <motion.div
              animate={{ rotate: [0, 10, -10, 0] }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              <Puzzle className="text-emerald-300" />
            </motion.div>
            Addons
          </h2>
        </div>

        <motion.div className="flex items-center gap-3">
          <motion.button
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.98 }}
            onClick={() =>
              showModal({
                type: "custom",
                title: "Import .mrpack",
                custom: <ImportModal serverName={serverName} />,
              })
            }
            className="px-4 py-2 bg-white/10 text-white rounded-lg font-medium flex items-center gap-2 hover:bg-white/20 transition-color border border-white/20"
          >
            <Download className="w-4 h-4" />
            Import
          </motion.button>
        </motion.div>
      </motion.div>
      <PluginsHeader
        download_page={download_page}
        query={query}
        setDownloadPage={setDownloadPage}
        setQuery={setQuery}
      />
      <motion.div className="h-full overflow-y-auto mt-4 custom-scrollbar">
        <AnimatePresence mode="wait">
          {download_page ? (
            <motion.div
              key="download"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="bg-white/10 backdrop-blur-xl rounded-2xl p-6 border border-white/20"
            >
              <div ref={divRef} />
              {searchResults.length !== 0 ? (
                <div className="grid gap-6">
                  {searchResults.map((project: Project) => (
                    <motion.div
                      key={project.id}
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      whileHover={{ scale: 1.01 }}
                      className="bg-white/5 rounded-xl p-6 border border-white/10 hover:border-white/20 transition-color"
                    >
                      <div className="flex gap-6">
                        {/* Icon */}
                        <div className="flex-shrink-0">
                          {project.icon_url ? (
                            <Image
                              height={96}
                              width={96}
                              src={project.icon_url}
                              alt={project.title}
                              className="w-24 h-24 rounded-xl border-2 border-white/20 object-cover"
                            />
                          ) : (
                            <div className="w-24 h-24 rounded-xl border-2 border-white/20 bg-white/5 flex items-center justify-center">
                              <ImageIcon className="w-10 h-10 text-white/30" />
                            </div>
                          )}
                        </div>

                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <h3 className="text-2xl font-bold text-white mb-2">
                            {project.title}
                          </h3>
                          <p className="text-white/70 mb-3 line-clamp-2">
                            {project.description}
                          </p>

                          {/* Stats */}
                          <div className="flex gap-6 text-sm text-white/50 mb-3">
                            <span>
                              ↓ {project.downloads.toLocaleString()} downloads
                            </span>
                            <span>
                              ♥ {project.followers.toLocaleString()} followers
                            </span>
                          </div>

                          {/* Tags */}
                          <div className="flex flex-wrap gap-2 mb-3">
                            {project.categories.slice(0, 3).map((cat) => (
                              <span
                                key={cat}
                                className="px-3 py-1 bg-purple-500/20 text-purple-200 rounded-full text-xs font-medium"
                              >
                                {cat}
                              </span>
                            ))}
                            {project.loaders.map((loader) => (
                              <span
                                key={loader}
                                className="px-3 py-1 bg-indigo-500/20 text-indigo-200 rounded-full text-xs font-medium"
                              >
                                {loader}
                              </span>
                            ))}
                          </div>

                          {/* Warning */}
                          {getServerSideWarning(project.server_side)}

                          {/* Actions */}
                          <div className="flex gap-3 mt-4">
                            <motion.button
                              whileHover={{ scale: 1.05 }}
                              whileTap={{ scale: 0.95 }}
                              onClick={() => {
                                addDownloadingMods(project);
                                downloadProjectVersion(project.id);
                                removeDownloadingMods(project);
                              }}
                              disabled={
                                downloadingMods.includes(project) ||
                                project.server_side === "unsupported"
                              }
                              className="px-6 py-2.5 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg font-medium flex items-center gap-2 hover:from-purple-600 hover:to-pink-600 transition-color shadow-lg disable:bg-gray-500 disable:cursor-not-allowed"
                            >
                              <Download className="w-4 h-4" />
                              {downloadingMods.includes(project)
                                ? "Installing.."
                                : "Install"}
                            </motion.button>
                            <motion.button
                              whileHover={{ scale: 1.05 }}
                              whileTap={{ scale: 0.95 }}
                              onClick={() =>
                                window.open(
                                  `https://modrinth.com/mod/${project.slug}`,
                                  "_blank"
                                )
                              }
                              className="px-6 py-2.5 bg-white/10 text-white rounded-lg font-medium flex items-center gap-2 hover:bg-white/20 transition-color border border-white/20"
                            >
                              <ExternalLink className="w-4 h-4" />
                              View on Modrinth
                            </motion.button>
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                  <div className="flex justify-center items-center mt-6 gap-4">
                    <motion.button
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.9 }}
                      onClick={() => {
                        setPage((prev) => Math.max(prev - 1, 0));
                        divRef.current?.scrollIntoView({ behavior: "smooth" });
                      }}
                      disabled={page === 0}
                      className={`px-4 py-2 rounded-lg font-medium ${
                        page === 0
                          ? "bg-gray-500/20 text-gray-300 cursor-not-allowed"
                          : "bg-blue-500/20 text-blue-300 hover:bg-blue-500/30"
                      } transition-color`}
                    >
                      Previous
                    </motion.button>
                    <span className="text-white/70 text-sm">
                      Page {page + 1}
                    </span>
                    <motion.button
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.9 }}
                      onClick={() => {
                        setPage((prev) => prev + 1);
                        divRef.current?.scrollIntoView({ behavior: "smooth" });
                      }}
                      className="px-4 py-2 bg-blue-500/20 text-blue-300 rounded-lg font-medium hover:bg-blue-500/30 transition-color"
                    >
                      Next
                    </motion.button>
                  </div>
                </div>
              ) : (
                <div className="text-center py-16">
                  <p className="text-white/40 text-lg italic">
                    No addons found
                  </p>
                </div>
              )}
            </motion.div>
          ) : (
            <motion.div
              key="installed"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="bg-white/10 backdrop-blur-xl rounded-2xl p-6 border border-white/20"
            >
              {filteredInstalled.length !== 0 ? (
                <div className="space-y-3">
                  {filteredInstalled.map((plugin: Addon) => (
                    <motion.div
                      key={plugin.project.id}
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      whileHover={{
                        backgroundColor: "rgba(255, 255, 255, 0.08)",
                      }}
                      className="flex items-center justify-between p-4 rounded-lg bg-white/5 border border-white/10 transition-color"
                    >
                      <div className="flex items-center gap-4 flex-1 min-w-0">
                        {plugin.project.icon_url ? (
                          <Image
                            width={48}
                            height={48}
                            src={plugin.project.icon_url}
                            alt={plugin.project.title}
                            className="w-12 h-12 rounded-lg border border-white/20 object-cover flex-shrink-0"
                          />
                        ) : (
                          <div className="w-12 h-12 rounded-lg border border-white/20 bg-white/5 flex items-center justify-center flex-shrink-0">
                            <ImageIcon className="w-6 h-6 text-white/30" />
                          </div>
                        )}
                        <div className="min-w-0 flex-1">
                          <p className="text-white font-medium truncate">
                            {plugin.project.title}
                          </p>
                          <p className="text-white/50 text-sm">
                            v{plugin.version.version_number}
                          </p>
                        </div>
                      </div>
                      <motion.button
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => removeInstalled(plugin.project.id)}
                        className="px-4 py-2 bg-red-500/20 text-red-300 rounded-lg font-medium flex items-center gap-2 hover:bg-red-500/30 transition-color border border-red-500/30 flex-shrink-0"
                      >
                        <Trash className="w-4 h-4" />
                        Remove
                      </motion.button>
                    </motion.div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-16">
                  <p className="text-white/40 text-lg italic">
                    No installed addons
                  </p>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </motion.div>
  );
}
