import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Folder,
  File,
  Edit,
  Save,
  Timer,
  Search,
  ChevronRight,
  FolderOpen,
  Home,
  UploadCloud,
  Archive,
  Clipboard,
  Columns,
  Grid as GridIcon,
  MoreHorizontal,
} from "lucide-react";

interface ServerFile {
  path: string;
  name: string;
  type: "directory" | "file";
  size?: number | null;
  modified: string;
}

interface FilesExplorerProps {
  files: ServerFile[];
  readFile: (path: string) => Promise<string>;
  writeFile: (path: string, content: string) => Promise<void>;
  // optional backend actions
  uploadFile?: (targetPath: string, file: File) => Promise<void>;
  downloadFile?: (path: string) => Promise<void>;
  zipFiles?: (paths: string[]) => Promise<void>;
  unzipFile?: (path: string) => Promise<void>;
  deleteFile?: (path: string) => Promise<void>;
  copyFile?: (from: string, to: string) => Promise<void>;
  moveFile?: (from: string, to: string) => Promise<void>;
}

export const FilesExplorer = ({
  files,
  readFile,
  writeFile,
  uploadFile,
  downloadFile,
  zipFiles,
  unzipFile,
  deleteFile,
  copyFile,
  moveFile,
}: FilesExplorerProps) => {
  const [filter, setFilter] = useState("");
  const [currentPath, setCurrentPath] = useState("");
  // view mode: compact (default), list, grid
  const [viewMode, setViewMode] = useState<"compact" | "list" | "grid">(
    "compact"
  );
  const [editingFile, setEditingFile] = useState<string | null>(null);
  const [fileContent, setFileContent] = useState("");
  const [editorReadOnly, setEditorReadOnly] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // clipboard for copy/cut/paste
  const [clipboard, setClipboard] = useState<{
    action: "copy" | "cut" | null;
    path: string | null;
  }>({ action: null, path: null });

  // context menu
  const [contextMenu, setContextMenu] = useState<{
    visible: boolean;
    x: number;
    y: number;
    file: ServerFile | null;
  }>({ visible: false, x: 0, y: 0, file: null });
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Build file tree structure
  const buildFileTree = () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const tree: any = {};

    files.forEach((file) => {
      const parts = file.path.split("/").filter(Boolean);
      let current = tree;

      parts.forEach((part, index) => {
        if (!current[part]) {
          current[part] = {
            name: part,
            path: parts.slice(0, index + 1).join("/"),
            type: index === parts.length - 1 ? file.type : "directory",
            size: index === parts.length - 1 ? file.size : null,
            modified: file.modified,
            children: {},
          };
        }
        current = current[part].children;
      });
    });

    return tree;
  };

  const fileTree = buildFileTree();

  // helper: determine whether a file is readable in the text editor
  const textReadableExts = [
    "txt",
    "log",
    "cfg",
    "conf",
    "config",
    "ini",
    "json",
    "yml",
    "yaml",
    "properties",
    "csv",
    "md",
    "xml",
    "plugin",
    "skript",
    "lang",
  ];

  const isTextReadable = (filename: string): boolean => {
    const ext = filename.split(".").pop()?.toLowerCase();
    return !!ext && textReadableExts.includes(ext);
  };

  // unreadable for binary or very large files
  const isReadable = (file: ServerFile): boolean => {
    if (file.type !== "file") return false;
    if (!isTextReadable(file.name)) return false;
    if (file.size && file.size > 5 * 1024 * 1024) return false; // >5MB treat as unreadable to avoid heavy loads
    return true;
  };

  // Get files at current path
  const getCurrentFiles = (): ServerFile[] => {
    if (!currentPath) return Object.values(fileTree) as ServerFile[];

    const parts = currentPath.split("/").filter(Boolean);
    let current = fileTree;

    for (const part of parts) {
      if (current[part]) {
        current = current[part].children;
      } else {
        return [];
      }
    }

    return Object.values(current) as ServerFile[];
  };

  const currentFiles = getCurrentFiles()
    .filter((file: ServerFile) => {
      if (!filter) return true;
      return file.name.toLowerCase().includes(filter.toLowerCase());
    })
    .sort((a: ServerFile, b: ServerFile) => {
      if (a.type !== b.type) return a.type === "directory" ? -1 : 1;
      return a.name.localeCompare(b.name);
    });

  // Action handlers (call props if provided otherwise noop)
  const handleUpload = () => {
    if (fileInputRef.current) fileInputRef.current.click();
  };

  const onFileInputChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    try {
      if (uploadFile) {
        await uploadFile(currentPath, f);
      } else {
        console.warn("uploadFile handler not provided");
      }
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleZip = async (target?: ServerFile) => {
    const paths = target ? [target.path] : currentFiles.map((f) => f.path);
    if (zipFiles) await zipFiles(paths);
    else console.warn("zipFiles not provided");
    closeContextMenu();
  };

  const handleUnzip = async (target: ServerFile) => {
    if (unzipFile) await unzipFile(target.path);
    else console.warn("unzipFile not provided");
    closeContextMenu();
  };

  const handleDelete = async (target: ServerFile) => {
    if (confirm(`Delete ${target.name}?`)) {
      if (deleteFile) await deleteFile(target.path);
      else console.warn("deleteFile not provided");
    }
    closeContextMenu();
  };

  const handleCopy = (target: ServerFile) => {
    setClipboard({ action: "copy", path: target.path });
    closeContextMenu();
  };

  const handleCut = (target: ServerFile) => {
    setClipboard({ action: "cut", path: target.path });
    closeContextMenu();
  };

  const handlePaste = async (destinationPath = currentPath) => {
    if (!clipboard.path || !clipboard.action) return;
    const name = clipboard.path.split("/").pop() || "";
    const target = destinationPath ? `${destinationPath}/${name}` : name;
    if (clipboard.action === "copy") {
      if (copyFile) await copyFile(clipboard.path, target);
      else console.warn("copyFile not provided");
    } else if (clipboard.action === "cut") {
      if (moveFile) await moveFile(clipboard.path, target);
      else console.warn("moveFile not provided");
      setClipboard({ action: null, path: null });
    }
    closeContextMenu();
  };

  const handleRename = async (target: ServerFile) => {
    const newName = prompt("New name", target.name);
    if (!newName || newName === target.name) return;
    const newPath = target.path
      .split("/")
      .slice(0, -1)
      .concat(newName)
      .join("/");
    if (moveFile) await moveFile(target.path, newPath);
    else console.warn("moveFile not provided (used for rename)");
    closeContextMenu();
  };

  // open/download helpers
  const handleDownload = async (target: ServerFile) => {
    try {
      if (downloadFile) {
        await downloadFile(target.path);
      } else {
        console.warn("downloadFile handler not provided");
      }
    } catch (err) {
      console.error("download failed", err);
    }
    closeContextMenu();
  };

  const handleFileClick = async (file: ServerFile) => {
    if (file.type === "directory") {
      setCurrentPath(file.path);
      setFilter("");
    } else {
      const readable = isReadable(file);
      setEditingFile(file.path);
      setEditorReadOnly(!readable);
      if (readable) {
        const content = await readFile(file.path);
        setFileContent(content);
      } else {
        setFileContent("// Cannot preview this file (binary or too large)");
      }
    }
  };

  const navigateToPath = (path: string) => {
    setCurrentPath(path);
    setFilter("");
  };

  const pathParts = currentPath.split("/").filter(Boolean);

  const handleSave = () => {
    if (editingFile && writeFile && !editorReadOnly) {
      writeFile(editingFile, fileContent);
    }
    setEditingFile(null);
    setFileContent("");
    setEditorReadOnly(false);
  };

  // context menu helpers
  const openContextMenu = (e: React.MouseEvent, file: ServerFile) => {
    e.preventDefault();
    setContextMenu({
      visible: true,
      x: e.clientX,
      y: e.clientY,
      file,
    });
  };

  // Adjust menu position *after* it renders
  useEffect(() => {
    if (contextMenu.visible && menuRef.current) {
      const rect = menuRef.current.getBoundingClientRect();
      let x = contextMenu.x;
      let y = contextMenu.y;

      const { innerWidth, innerHeight } = window;
      if (x + rect.width > innerWidth) x = innerWidth - rect.width - 10;
      if (y + rect.height > innerHeight) y = innerHeight - rect.height - 10;

      if (x !== contextMenu.x || y !== contextMenu.y) {
        setContextMenu((prev) => ({ ...prev, x, y }));
      }
    }
  }, [contextMenu.visible, contextMenu.x, contextMenu.y]);
  const closeContextMenu = () =>
    setContextMenu({ visible: false, x: 0, y: 0, file: null });

  const formatSize = (bytes?: number | null) => {
    if (!bytes) return "-";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileIcon = (name: string) => {
    const ext = name.split(".").pop()?.toLowerCase();
    const iconClass = "text-lg flex-shrink-0";

    switch (ext) {
      case "json":
        return <File className={`${iconClass} text-yellow-400`} />;
      case "yml":
      case "yaml":
        return <File className={`${iconClass} text-orange-400`} />;
      case "properties":
        return <File className={`${iconClass} text-green-400`} />;
      case "txt":
      case "log":
        return <File className={`${iconClass} text-gray-400`} />;
      case "jar":
      case "zip":
        return <File className={`${iconClass} text-red-400`} />;
      default:
        return <File className={`${iconClass} text-blue-400`} />;
    }
  };

  return (
    <>
      <motion.div
        className="glass-card h-[calc(100vh-16rem)]"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        onClick={() => {
          if (contextMenu.visible) closeContextMenu();
        }}
      >
        <AnimatePresence mode="wait">
          {!editingFile ? (
            <motion.div
              key="explorer"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="h-full flex flex-col"
            >
              {/* Header */}
              <motion.div
                className="flex justify-between items-center mb-6"
                initial={{ y: -20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.1 }}
              >
                <div className="flex items-center gap-4">
                  <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                    <motion.div
                      animate={{ rotate: [0, 10, -10, 0] }}
                      transition={{ duration: 0.5, delay: 0.2 }}
                    >
                      <FolderOpen className="text-yellow-400" />
                    </motion.div>
                    File Explorer
                  </h2>

                  {/* action bar */}
                  <div className="flex items-center gap-2 ml-4">
                    <button
                      onClick={() => handleUpload()}
                      title="Upload"
                      className="p-2 bg-white/5 rounded-md"
                    >
                      <UploadCloud className="text-white/90" />
                    </button>
                    <button
                      onClick={() => handleZip()}
                      title="Zip"
                      className="p-2 bg-white/5 rounded-md"
                    >
                      <Archive className="text-white/90" />
                    </button>
                    <button
                      onClick={() => handlePaste()}
                      title="Paste"
                      className="p-2 bg-white/5 rounded-md"
                    >
                      <Clipboard className="text-white/90" />
                    </button>
                    <button
                      onClick={() => {
                        if (clipboard.action && clipboard.path)
                          setClipboard({ action: null, path: null });
                        else console.warn("No clipboard");
                      }}
                      title="Clear clipboard"
                      className="p-2 bg-white/5 rounded-md"
                    >
                      <MoreHorizontal className="text-white/90" />
                    </button>
                  </div>
                </div>

                {/* view and upload hidden input */}
                <div className="flex items-center gap-3">
                  <div className="flex gap-2 bg-white/5 p-1 rounded-lg">
                    <button
                      onClick={() => setViewMode("compact")}
                      title="Compact"
                      className={`p-2 rounded ${
                        viewMode === "compact" ? "bg-white/10" : ""
                      }`}
                    >
                      <Columns className="text-white/90" />
                    </button>
                    <button
                      onClick={() => setViewMode("list")}
                      title="List"
                      className={`p-2 rounded ${
                        viewMode === "list" ? "bg-white/10" : ""
                      }`}
                    >
                      <GridIcon className="text-white/90" />
                    </button>
                    <button
                      onClick={() => setViewMode("grid")}
                      title="Grid"
                      className={`p-2 rounded ${
                        viewMode === "grid" ? "bg-white/10" : ""
                      }`}
                    >
                      <GridIcon className="text-white/90" />
                    </button>
                  </div>
                </div>
              </motion.div>

              {/* Breadcrumb Navigation */}
              <motion.div
                className="mb-4 flex items-center gap-2 flex-wrap"
                initial={{ x: -20, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ delay: 0.2 }}
              >
                <motion.button
                  whileHover={{
                    scale: 1.05,
                    backgroundColor: "rgba(255,255,255,0.15)",
                  }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => navigateToPath("")}
                  className="px-3 py-1.5 bg-white/10 hover:bg-white/15 rounded-lg transition-all flex items-center gap-2 text-white/90"
                >
                  <Home className="text-sm" />
                  <span className="text-sm font-medium">Root</span>
                </motion.button>

                {pathParts.map((part, index) => {
                  const path = pathParts.slice(0, index + 1).join("/");
                  return (
                    <motion.div
                      key={path}
                      className="flex items-center gap-2"
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.1 * index }}
                    >
                      <ChevronRight className="text-white/40 text-xs" />
                      <motion.button
                        whileHover={{
                          scale: 1.05,
                          backgroundColor: "rgba(255,255,255,0.15)",
                        }}
                        whileTap={{ scale: 0.95 }}
                        onClick={() => navigateToPath(path)}
                        className="px-3 py-1.5 bg-white/10 hover:bg-white/15 rounded-lg transition-all text-white/90 text-sm font-medium"
                      >
                        {part}
                      </motion.button>
                    </motion.div>
                  );
                })}
              </motion.div>

              {/* Search Filter */}
              <motion.div
                className="relative mb-4"
                initial={{ y: -10, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.3 }}
              >
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-white/40" />
                <input
                  type="text"
                  placeholder="Search files and folders..."
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                  className="w-full bg-white/10 border border-white/20 rounded-xl pl-12 pr-4 py-3 text-sm text-white placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-transparent transition-all"
                />
              </motion.div>

              {/* Files List */}
              <motion.div
                className="flex-1 bg-black/50 backdrop-blur-sm rounded-xl overflow-hidden border border-white/10"
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.4 }}
              >
                <div className="h-full overflow-auto custom-scrollbar">
                  <AnimatePresence mode="popLayout">
                    {currentFiles.length > 0 ? (
                      <div
                        className={
                          viewMode === "grid"
                            ? "p-3 grid grid-cols-3 gap-3"
                            : "p-2"
                        }
                      >
                        {currentFiles.map((file: ServerFile) => (
                          <motion.div
                            key={file.path}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0, x: 20 }}
                            transition={{ duration: 0.3 }}
                            whileHover={{ scale: 1.005 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={() => handleFileClick(file)}
                            onContextMenu={(e) => openContextMenu(e, file)}
                            className={
                              viewMode === "compact"
                                ? "flex items-center gap-3 p-2 mb-1 cursor-pointer transition-all rounded-md group hover:bg-white/5"
                                : viewMode === "grid"
                                ? "p-4 bg-white/2 rounded-lg cursor-pointer"
                                : "flex items-center gap-4 p-4 mb-2 hover:bg-gradient-to-r hover:from-white/10 hover:to-transparent cursor-pointer transition-all rounded-xl group border border-transparent hover:border-white/20 group"
                            }
                          >
                            <motion.div
                              whileHover={{
                                rotate:
                                  file.type === "directory"
                                    ? [0, -10, 10, 0]
                                    : 0,
                              }}
                              transition={{ duration: 0.3 }}
                            >
                              {file.type === "directory" ? (
                                <Folder className="text-yellow-400 text-xl flex-shrink-0" />
                              ) : (
                                getFileIcon(file.name)
                              )}
                            </motion.div>

                            <div className="flex-1 min-w-0">
                              <div
                                className={`text-white font-semibold truncate ${
                                  viewMode === "compact"
                                    ? "text-sm"
                                    : "text-base"
                                }`}
                              >
                                {file.name}
                                {!isReadable(file) && file.type === "file" ? (
                                  <span className="text-red-400 ml-2 text-xs">
                                    {" "}
                                    (binary)
                                  </span>
                                ) : null}
                              </div>
                              {viewMode !== "compact" && (
                                <div className="text-white/50 text-xs mt-0.5 flex items-center gap-3">
                                  <span>{file.modified}</span>
                                  <span>•</span>
                                  <span>{formatSize(file.size)}</span>
                                </div>
                              )}
                            </div>

                            <div className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                              {file.type === "file" ? (
                                <Edit className="text-pink-400 text-sm" />
                              ) : (
                                <ChevronRight className="text-white/40 text-sm" />
                              )}
                            </div>
                          </motion.div>
                        ))}
                      </div>
                    ) : (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="h-full flex items-center justify-center p-8"
                      >
                        <div className="text-center">
                          <Folder className="text-white/20 text-6xl mx-auto mb-4" />
                          <p className="text-white/40 italic">
                            {filter
                              ? "No files match your search"
                              : "This directory is empty"}
                          </p>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </motion.div>
            </motion.div>
          ) : (
            <motion.div
              key="editor"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="h-full flex flex-col"
            >
              {/* Editor Header */}
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                  <Edit className="text-pink-400" />
                  <span className="truncate">
                    {editingFile?.split("/").pop()}
                  </span>
                  {editorReadOnly && (
                    <span className="text-red-400 text-sm ml-2">Read-only</span>
                  )}
                </h2>
                <div className="flex gap-2">
                  <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={handleSave}
                    className="p-3 bg-green-500/20 hover:bg-green-500/30 text-green-400 hover:text-green-300 rounded-xl transition-colors border border-green-500/30"
                    title="Save file"
                  >
                    <Save />
                  </motion.button>
                  <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={() => {
                      setEditingFile(null);
                      setFileContent("");
                      setEditorReadOnly(false);
                    }}
                    className="p-3 bg-red-500/20 hover:bg-red-500/30 text-red-400 hover:text-red-300 rounded-xl transition-colors border border-red-500/30"
                    title="Close editor"
                  >
                    <Timer />
                  </motion.button>
                </div>
              </div>

              {/* File Path */}
              <motion.div
                className="mb-4 bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-sm text-white/70 font-mono"
                initial={{ y: -10, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
              >
                {editingFile}
              </motion.div>

              {/* Editor */}
              <motion.textarea
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.1 }}
                value={fileContent}
                onChange={(e) => setFileContent(e.target.value)}
                readOnly={editorReadOnly}
                className="flex-1 bg-black/50 backdrop-blur-sm border border-white/20 rounded-xl p-6 text-white font-mono text-sm focus:outline-none focus:ring-2 focus:ring-pink-500 resize-none custom-scrollbar"
                placeholder="File content..."
              />

              {/* Save Button */}
              <motion.div
                className="mt-6 flex gap-3"
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.2 }}
              >
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleSave}
                  className="flex-1 bg-gradient-to-r from-pink-500 to-purple-600 hover:from-pink-600 hover:to-purple-700 text-white font-bold py-4 px-6 rounded-xl transition-all shadow-lg shadow-pink-500/30"
                >
                  💾 Save Changes
                </motion.button>
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => {
                    setEditingFile(null);
                    setFileContent("");
                    setEditorReadOnly(false);
                  }}
                  className="px-8 bg-white/10 hover:bg-white/20 text-white font-bold py-4 rounded-xl transition-all border border-white/20"
                >
                  Cancel
                </motion.button>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* hidden file input for upload */}
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          onChange={onFileInputChange}
        />

        {/* context menu */}

        <style jsx>{`
          .custom-scrollbar::-webkit-scrollbar {
            width: 8px;
            height: 8px;
          }
          .custom-scrollbar::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
          }
          .custom-scrollbar::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 10px;
          }
          .custom-scrollbar::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.3);
          }
        `}</style>
      </motion.div>
      {contextMenu.visible && contextMenu.file && (
        <div
          ref={menuRef}
          style={{
            position: "fixed",
            top: contextMenu.y,
            left: contextMenu.x,
            zIndex: 9999,
          }}
          className="bg-black/80 text-white rounded-md shadow-lg border border-white/10"
          onMouseLeave={closeContextMenu}
        >
          <div className="flex flex-col min-w-[200px]">
            <button
              className="px-4 py-2 text-left hover:bg-white/5"
              onClick={() => {
                if (isReadable(contextMenu.file!))
                  handleFileClick(contextMenu.file!);
                else handleDownload(contextMenu.file!);
              }}
                  onContextMenu={(e: React.MouseEvent) => e.preventDefault()}
            >
              {isReadable(contextMenu.file!) ? "Open" : "Download/Preview"}
            </button>
            {contextMenu.file!.type === "file" && (
              <>
                <button
                  className="px-4 py-2 text-left hover:bg-white/5"
                  onClick={() => handleCopy(contextMenu.file!)}
                  onContextMenu={(e: React.MouseEvent) => e.preventDefault()}
                >
                  Copy
                </button>
                <button
                  className="px-4 py-2 text-left hover:bg-white/5"
                  onClick={() => handleCut(contextMenu.file!)}
                  onContextMenu={(e: React.MouseEvent) => e.preventDefault()}
                >
                  Cut
                </button>
                <button
                  className="px-4 py-2 text-left hover:bg-white/5"
                  onClick={() => handleRename(contextMenu.file!)}
                  onContextMenu={(e: React.MouseEvent) => e.preventDefault()}
                >
                  Rename
                </button>
                <button
                  className="px-4 py-2 text-left hover:bg-white/5"
                  onClick={() => handleDelete(contextMenu.file!)}
                  onContextMenu={(e: React.MouseEvent) => e.preventDefault()}
                >
                  Delete
                </button>
                {contextMenu.file.name.endsWith(".zip") ? (
                  <button
                    className="px-4 py-2 text-left hover:bg-white/5"
                    onClick={() => handleUnzip(contextMenu.file!)}
                  onContextMenu={(e: React.MouseEvent) => e.preventDefault()}
                  >
                    Unzip
                  </button>
                ) : (
                  <button
                    className="px-4 py-2 text-left hover:bg-white/5"
                    onClick={() => handleZip(contextMenu.file!)}
                  onContextMenu={(e: React.MouseEvent) => e.preventDefault()}
                  >
                    Zip
                  </button>
                )}
                {isReadable(contextMenu.file!) && (
                  <button
                    className="px-4 py-2 text-left hover:bg-white/5"
                    onClick={() => handleDownload(contextMenu.file!)}
                  onContextMenu={(e: React.MouseEvent) => e.preventDefault()}
                  >
                    Download
                  </button>
                )}
              </>
            )}
            {contextMenu.file!.type === "directory" && (
              <>
                <button
                  className="px-4 py-2 text-left hover:bg-white/5"
                  onClick={() => handlePaste(contextMenu.file!.path)}
                  onContextMenu={(e: React.MouseEvent) => e.preventDefault()}
                >
                  Paste into
                </button>
                <button
                  className="px-4 py-2 text-left hover:bg-white/5"
                  onClick={() => handleZip(contextMenu.file!)}
                  onContextMenu={(e: React.MouseEvent) => e.preventDefault()}
                >
                  Zip folder
                </button>
                <button
                  className="px-4 py-2 text-left hover:bg-white/5"
                  onClick={() => handleDelete(contextMenu.file!)}
                  onContextMenu={(e: React.MouseEvent) => e.preventDefault()}
                >
                  Delete folder
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </>
  );
};
