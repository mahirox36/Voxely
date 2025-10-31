import { useState, useRef, useEffect, ReactNode } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Folder,
  File,
  Edit,
  Save,
  Search,
  ChevronRight,
  FolderOpen,
  Home,
  UploadCloud,
  Archive,
  Clipboard,
  Columns,
  Grid as GridIcon,
  PlusCircle,
  Trash2,
  FolderPlus,
  FilePlus2,
  X,
} from "lucide-react";
import { toast } from "sonner";

interface ServerFile {
  path: string;
  name: string;
  type: "directory" | "file";
  size?: number | null;
  modified: string;
}

type TooltipProps = {
  content: string;
  children: ReactNode;
};

export function Tooltip({ content, children }: TooltipProps) {
  const [show, setShow] = useState(false);

  return (
    <div
      className="relative inline-block"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      {children}
      {show && (
        <div className="absolute bottom-full mb-2 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-sm px-2 py-1 rounded shadow-lg whitespace-nowrap z-50">
          {content}
        </div>
      )}
    </div>
  );
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
  createFile?: (path: string) => Promise<void>;
  createFolder?: (path: string) => Promise<void>;
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
  createFile,
  createFolder,
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

  const pathParts = currentPath.split("/").filter(Boolean);

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
  const handleCreation = async (file: boolean) => {
    if (file) {
      const name = prompt("Enter new file name");
      if (name && createFile) {
        await createFile(currentPath ? `${currentPath}/${name}` : name);
      }
    } else {
      const name = prompt("Enter new folder name");
      if (name && createFolder) {
        await createFolder(currentPath ? `${currentPath}/${name}` : name);
      }
    }
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
    toast.success("File Copied successfully");
  };

  const handleCut = (target: ServerFile) => {
    setClipboard({ action: "cut", path: target.path });
    closeContextMenu();
    toast.success("File Cut successfully");
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
    toast.success("File Pasted successfully");
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
    toast.success("File Renamed successfully");
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

  // Add these types and helper functions near the other helpers / state definitions
  type ConfigType = "string" | "number" | "boolean" | "list" | "dict";
  interface ConfigEntry {
    key: string;
    value: unknown; // typed value: number, boolean, string, array, object
    type: ConfigType;
    description?: string; // from comments above the key
    raw?: string; // original raw value (for fallback)
  }

  // New state: custom editor
  const [openCustomEditor, setOpenCustomEditor] = useState(false);
  const [customEntries, setCustomEntries] = useState<ConfigEntry[] | null>(
    null
  );

  const inferType = (raw: string): ConfigType => {
    const s = raw.trim();
    if (/^(true|false)$/i.test(s)) return "boolean";
    if (/^-?\d+(\.\d+)?$/.test(s)) return "number";
    if (
      (s.startsWith("{") && s.endsWith("}")) ||
      (s.startsWith("[") && s.endsWith("]"))
    ) {
      try {
        const parsed = JSON.parse(s);
        return Array.isArray(parsed) ? "list" : "dict";
      } catch {
        // fallthrough
      }
    }
    if (s.includes(",")) return "list";
    return "string";
  };

  // Helper: convert raw string to typed value for the UI
  const convertRawToValue = (raw: string, type: ConfigType) => {
    const s = raw.trim();
    try {
      if (type === "boolean") return /^(true)$/i.test(s);
      if (type === "number") return Number(s);
      if (type === "list") {
        if (s.startsWith("[") && s.endsWith("]")) return JSON.parse(s);
        return s
          .split(",")
          .map((p) => p.trim())
          .filter(Boolean);
      }
      if (type === "dict") {
        if (s.startsWith("{") && s.endsWith("}")) return JSON.parse(s);
        const obj: Record<string, string> = {};
        s.split(",").forEach((pair) => {
          const [k, ...rest] = pair.split(":");
          if (!k) return;
          obj[k.trim()] = rest.join(":").trim();
        });
        return obj;
      }
    } catch {
      // parsing error -> keep as string
    }
    return raw;
  };

  // Helper: convert typed value back to string representation
  const convertValueToString = (val: unknown, type: ConfigType) => {
    if (type === "boolean") return val ? "true" : "false";
    if (type === "number") return String(val);
    if (type === "list" || type === "dict") return JSON.stringify(val);
    return String(val);
  };

  // Parse different config formats
  const parseConfig = (content: string, format: string): ConfigEntry[] => {
    if (format === "json") return parseJSON(content);
    if (format === "yaml" || format === "yml") return parseYAML(content);
    if (format === "toml") return parseTOML(content);
    if (format === "xml") return parseXML(content);
    if (format === "env") return parseENV(content);
    return parseProperties(content);
  };

  // Parse JSON
  const parseJSON = (content: string): ConfigEntry[] => {
    try {
      const obj = JSON.parse(content);
      return flattenObject(obj);
    } catch {
      return [];
    }
  };

  // Flatten nested object into entries with dot notation keys
  const flattenObject = (
    obj: Record<string, unknown>,
    prefix = "",
    description?: string
  ): ConfigEntry[] => {
    const entries: ConfigEntry[] = [];
    for (const [key, val] of Object.entries(obj)) {
      const fullKey = prefix ? `${prefix}.${key}` : key;
      if (val && typeof val === "object" && !Array.isArray(val)) {
        entries.push(...flattenObject(val as Record<string, unknown>, fullKey));
      } else {
        const type = Array.isArray(val)
          ? "list"
          : typeof val === "boolean"
          ? "boolean"
          : typeof val === "number"
          ? "number"
          : "string";
        entries.push({ key: fullKey, value: val, type, description });
      }
    }
    return entries;
  };

  // Parse YAML (basic support)
  const parseYAML = (content: string): ConfigEntry[] => {
    const entries: ConfigEntry[] = [];
    const lines = content.split(/\r?\n/);
    let commentBuffer: string[] = [];

    for (const rawLine of lines) {
      const line = rawLine.trimEnd();
      if (line === "") {
        commentBuffer = [];
        continue;
      }
      if (/^\s*#/.test(line)) {
        const desc = line.replace(/^\s*#\s?/, "");
        commentBuffer.push(desc);
        continue;
      }

      const match = line.match(/^\s*([^:]+):\s*(.*)$/);
      if (match) {
        const key = match[1].trim();
        const rawVal = match[2].trim();
        const inferred = inferType(rawVal);
        entries.push({
          key,
          value: convertRawToValue(rawVal, inferred),
          type: inferred,
          description: commentBuffer.length
            ? commentBuffer.join("\n")
            : undefined,
          raw: rawVal,
        });
        commentBuffer = [];
      }
    }
    return entries;
  };

  // Parse TOML (basic support)
  const parseTOML = (content: string): ConfigEntry[] => {
    const entries: ConfigEntry[] = [];
    const lines = content.split(/\r?\n/);
    let commentBuffer: string[] = [];
    let section = "";

    for (const rawLine of lines) {
      const line = rawLine.trimEnd();
      if (line === "") {
        commentBuffer = [];
        continue;
      }
      if (/^\s*#/.test(line)) {
        const desc = line.replace(/^\s*#\s?/, "");
        commentBuffer.push(desc);
        continue;
      }

      const sectionMatch = line.match(/^\[([^\]]+)\]$/);
      if (sectionMatch) {
        section = sectionMatch[1];
        commentBuffer = [];
        continue;
      }

      const match = line.match(/^([^=]+)=(.*)$/);
      if (match) {
        const key = match[1].trim();
        const rawVal = match[2].trim();
        const fullKey = section ? `${section}.${key}` : key;
        const inferred = inferType(rawVal);
        entries.push({
          key: fullKey,
          value: convertRawToValue(rawVal, inferred),
          type: inferred,
          description: commentBuffer.length
            ? commentBuffer.join("\n")
            : undefined,
          raw: rawVal,
        });
        commentBuffer = [];
      }
    }
    return entries;
  };

  // Parse XML (basic support)
  const parseXML = (content: string): ConfigEntry[] => {
    const entries: ConfigEntry[] = [];
    const parser = new DOMParser();
    try {
      const doc = parser.parseFromString(content, "text/xml");
      const extractFromNode = (node: Element, prefix = "") => {
        for (const attr of Array.from(node.attributes)) {
          const key = prefix ? `${prefix}.${attr.name}` : attr.name;
          const inferred = inferType(attr.value);
          entries.push({
            key,
            value: convertRawToValue(attr.value, inferred),
            type: inferred,
            raw: attr.value,
          });
        }
        for (const child of Array.from(node.children)) {
          const key = prefix ? `${prefix}.${child.tagName}` : child.tagName;
          if (child.children.length === 0) {
            const text = child.textContent?.trim() || "";
            const inferred = inferType(text);
            entries.push({
              key,
              value: convertRawToValue(text, inferred),
              type: inferred,
              raw: text,
            });
          } else {
            extractFromNode(child, key);
          }
        }
      };
      if (doc.documentElement) extractFromNode(doc.documentElement);
    } catch {
      // parsing failed
    }
    return entries;
  };

  // Parse .env files
  const parseENV = (content: string): ConfigEntry[] => {
    const entries: ConfigEntry[] = [];
    const lines = content.split(/\r?\n/);
    let commentBuffer: string[] = [];

    for (const rawLine of lines) {
      const line = rawLine.trimEnd();
      if (line === "") {
        commentBuffer = [];
        continue;
      }
      if (/^\s*#/.test(line)) {
        const desc = line.replace(/^\s*#\s?/, "");
        commentBuffer.push(desc);
        continue;
      }

      const match = line.match(/^([^=]+)=(.*)$/);
      if (match) {
        const key = match[1].trim();
        let rawVal = match[2].trim();
        if (
          (rawVal.startsWith('"') && rawVal.endsWith('"')) ||
          (rawVal.startsWith("'") && rawVal.endsWith("'"))
        ) {
          rawVal = rawVal.slice(1, -1);
        }
        const inferred = inferType(rawVal);
        entries.push({
          key,
          value: convertRawToValue(rawVal, inferred),
          type: inferred,
          description: commentBuffer.length
            ? commentBuffer.join("\n")
            : undefined,
          raw: rawVal,
        });
        commentBuffer = [];
      }
    }
    return entries;
  };

  // Parse .properties/.cfg/.ini/.conf style files
  const parseProperties = (content: string): ConfigEntry[] => {
    const lines = content.split(/\r?\n/);
    const entries: ConfigEntry[] = [];
    let commentBuffer: string[] = [];
    let section = "";

    for (const rawLine of lines) {
      const line = rawLine.trimEnd();
      if (line === "") {
        commentBuffer = [];
        continue;
      }
      if (/^\s*[#;!]/.test(line)) {
        const desc = line.replace(/^\s*[#;!]\s?/, "");
        commentBuffer.push(desc);
        continue;
      }

      const sectionMatch = line.match(/^\[([^\]]+)\]$/);
      if (sectionMatch) {
        section = sectionMatch[1];
        commentBuffer = [];
        continue;
      }

      const idxEq = line.indexOf("=");
      const idxColon = line.indexOf(":");
      let sepIdx = -1;
      if (idxEq >= 0 && (idxColon === -1 || idxEq < idxColon)) sepIdx = idxEq;
      else if (idxColon >= 0) sepIdx = idxColon;

      let key = line;
      let rawVal = "";
      if (sepIdx >= 0) {
        key = line.slice(0, sepIdx).trim();
        rawVal = line.slice(sepIdx + 1).trim();
      } else {
        key = line.trim();
        rawVal = "";
      }

      const fullKey = section ? `${section}.${key}` : key;
      const inferred = inferType(rawVal);
      entries.push({
        key: fullKey,
        value: convertRawToValue(rawVal, inferred),
        type: inferred,
        description: commentBuffer.length
          ? commentBuffer.join("\n")
          : undefined,
        raw: rawVal,
      });

      commentBuffer = [];
    }

    return entries;
  };

  // Serialize back to appropriate format
  const serializeConfig = (entries: ConfigEntry[], format: string) => {
    if (format === "json") return serializeJSON(entries);
    if (format === "yaml" || format === "yml") return serializeYAML(entries);
    if (format === "toml") return serializeTOML(entries);
    if (format === "xml") return serializeXML(entries);
    if (format === "env") return serializeENV(entries);
    return serializeProperties(entries, format);
  };

  // Serialize to JSON
  const serializeJSON = (entries: ConfigEntry[]) => {
    const obj: Record<string, unknown> = {};
    for (const e of entries) {
      const keys = e.key.split(".");
      let current = obj;
      for (let i = 0; i < keys.length - 1; i++) {
        if (!current[keys[i]]) current[keys[i]] = {};
        current = current[keys[i]] as Record<string, unknown>;
      }
      current[keys[keys.length - 1]] = e.value;
    }
    return JSON.stringify(obj, null, 2);
  };

  // Serialize to YAML
  const serializeYAML = (entries: ConfigEntry[]) => {
    const out: string[] = [];
    for (const e of entries) {
      if (e.description) {
        e.description.split("\n").forEach((ln) => out.push(`# ${ln}`));
      }
      const valStr = convertValueToString(e.value, e.type);
      out.push(`${e.key}: ${valStr}`);
    }
    return out.join("\n");
  };

  // Serialize to TOML
  const serializeTOML = (entries: ConfigEntry[]) => {
    const sections: Record<string, ConfigEntry[]> = { "": [] };
    for (const e of entries) {
      const dotIdx = e.key.indexOf(".");
      if (dotIdx > 0) {
        const section = e.key.slice(0, dotIdx);
        if (!sections[section]) sections[section] = [];
        sections[section].push({
          ...e,
          key: e.key.slice(dotIdx + 1),
        });
      } else {
        sections[""].push(e);
      }
    }

    const out: string[] = [];
    for (const [section, sectionEntries] of Object.entries(sections)) {
      if (section) out.push(`\n[${section}]`);
      for (const e of sectionEntries) {
        if (e.description) {
          e.description.split("\n").forEach((ln) => out.push(`# ${ln}`));
        }
        const valStr = convertValueToString(e.value, e.type);
        out.push(`${e.key} = ${valStr}`);
      }
    }
    return out.join("\n").trim();
  };

  // Serialize to XML
  const serializeXML = (entries: ConfigEntry[]) => {
    const out: string[] = [
      '<?xml version="1.0" encoding="UTF-8"?>',
      "<config>",
    ];
    for (const e of entries) {
      const valStr = convertValueToString(e.value, e.type);
      const xmlSafe = valStr
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
      if (e.description) {
        out.push(`  <!-- ${e.description} -->`);
      }
      out.push(`  <${e.key}>${xmlSafe}</${e.key}>`);
    }
    out.push("</config>");
    return out.join("\n");
  };

  // Serialize to ENV
  const serializeENV = (entries: ConfigEntry[]) => {
    const out: string[] = [];
    for (const e of entries) {
      if (e.description) {
        e.description.split("\n").forEach((ln) => out.push(`# ${ln}`));
      }
      let valStr = convertValueToString(e.value, e.type);
      if (e.type === "string" && valStr.includes(" ")) {
        valStr = `"${valStr}"`;
      }
      out.push(`${e.key}=${valStr}`);
    }
    return out.join("\n");
  };

  // Serialize to properties format
  const serializeProperties = (entries: ConfigEntry[], format: string) => {
    const isProperties = format === "properties";
    const sections: Record<string, ConfigEntry[]> = { "": [] };

    for (const e of entries) {
      const dotIdx = e.key.indexOf(".");
      if (!isProperties && dotIdx > 0) {
        const section = e.key.slice(0, dotIdx);
        if (!sections[section]) sections[section] = [];
        sections[section].push({
          ...e,
          key: e.key.slice(dotIdx + 1),
        });
      } else {
        sections[""].push(e);
      }
    }

    const out = [];

    for (const [section, sectionEntries] of Object.entries(sections)) {
      // skip category headers if format is .properties
      if (!isProperties && section) out.push(`\n[${section}]`);

      for (const e of sectionEntries) {
        if (e.description) {
          e.description.split("\n").forEach((ln) => out.push(`# ${ln}`));
        }

        const valStr = convertValueToString(e.value, e.type);

        // in .properties, keep the full key (with section prefix)
        const key = isProperties && section ? `${section}.${e.key}` : e.key;
        out.push(`${key}=${valStr}`);
      }
    }

    return out.join("\n").trim();
  };

  // Detect config format from filename
  const detectConfigFormat = (filename: string): string => {
    const lower = filename.toLowerCase();
    if (lower.endsWith(".json")) return "json";
    if (lower.endsWith(".yaml") || lower.endsWith(".yml")) return "yaml";
    if (lower.endsWith(".toml")) return "toml";
    if (lower.endsWith(".xml")) return "xml";
    if (lower.endsWith(".env") || lower === ".env") return "env";
    if (
      lower.endsWith(".properties") ||
      lower.endsWith(".cfg") ||
      lower.endsWith(".ini") ||
      lower.endsWith(".conf")
    )
      return "properties";
    return "txt";
  };

  const handleFileClick = async (file: ServerFile) => {
    if (file.type === "directory") {
      setCurrentPath(file.path);
      setFilter("");
    } else {
      const format = detectConfigFormat(file.name);
      const isConfigFile =
        format === "json" ||
        format === "yaml" ||
        format === "toml" ||
        format === "xml" ||
        format === "env" ||
        format === "properties";

      if (isConfigFile) {
        setEditingFile(file.path);
        setOpenCustomEditor(true);
        setEditorReadOnly(false);
        try {
          const content = await readFile(file.path);
          const parsed = parseConfig(content, format);
          setCustomEntries(parsed);
          setFileContent(content);
        } catch {
          setCustomEntries([]);
        }
        return;
      }

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

  const handleSave = async () => {
    if (openCustomEditor && editingFile && writeFile && customEntries) {
      const format = detectConfigFormat(editingFile.split("/").pop() || "");
      const serialized = serializeConfig(customEntries, format);
      await writeFile(editingFile, serialized);
      setOpenCustomEditor(false);
      setCustomEntries(null);
      setEditingFile(null);
      setFileContent("");
      // await writeFile(editingFile, fileContent);
      toast.success("File saved successfully");
      return;
    }

    if (editingFile && writeFile && !editorReadOnly) {
      await writeFile(editingFile, fileContent);
      // loadFiles(currentPath);
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
                    <Tooltip content="Create File">
                      <button
                        onClick={() => handleCreation(true)}
                        className="p-2 bg-white/5 rounded-md"
                      >
                        <FilePlus2 className="text-white/90" />
                      </button>
                    </Tooltip>
                    <Tooltip content="Create Folder">
                      <button
                        onClick={() => handleCreation(false)}
                        className="p-2 bg-white/5 rounded-md"
                      >
                        <FolderPlus className="text-white/90" />
                      </button>
                    </Tooltip>
                    <Tooltip content="Upload">
                      <button
                        onClick={() => handleUpload()}
                        className="p-2 bg-white/5 rounded-md"
                      >
                        <UploadCloud className="text-white/90" />
                      </button>
                    </Tooltip>
                    <Tooltip content="Zip">
                      <button
                        onClick={() => handleZip()}
                        className="p-2 bg-white/5 rounded-md"
                      >
                        <Archive className="text-white/90" />
                      </button>
                    </Tooltip>
                    <Tooltip content="Paste">
                      <button
                        onClick={() => handlePaste()}
                        className="p-2 bg-white/5 rounded-md"
                      >
                        <Clipboard className="text-white/90" />
                      </button>
                    </Tooltip>
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
                  className="px-3 py-1.5 bg-white/10 hover:bg-white/15 rounded-lg transition-color flex items-center gap-2 text-white/90"
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
                        className="px-3 py-1.5 bg-white/10 hover:bg-white/15 rounded-lg transition-color text-white/90 text-sm font-medium"
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
                  className="w-full bg-white/10 border border-white/20 rounded-xl pl-12 pr-4 py-3 text-sm text-white placeholder:text-white/40 focus:outline-none focus:ring-2 focus:ring-pink-500 focus:border-transparent transition-color"
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
                                ? "flex items-center gap-3 p-2 mb-1 cursor-pointer transition-color rounded-md group hover:bg-white/5"
                                : viewMode === "grid"
                                ? "p-4 bg-white/2 rounded-lg cursor-pointer"
                                : "flex items-center gap-4 p-4 mb-2 hover:bg-gradient-to-r hover:from-white/10 hover:to-transparent cursor-pointer transition-color rounded-xl group border border-transparent hover:border-white/20 group"
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
          ) : openCustomEditor ? (
            <motion.div
              key="custom-editor"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              className="h-full flex flex-col"
            >
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold text-white flex items-center gap-3">
                  <Edit className="text-pink-400" />
                  <span className="truncate">
                    {editingFile?.split("/").pop()}
                  </span>
                  <span className="text-sm text-white/60 ml-2">
                    Config Editor
                  </span>
                </h2>
                <div className="flex gap-2">
                  <Tooltip content="Save">
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    className="p-3 bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded-xl border border-green-500/30"
                    onClick={handleSave}
                  >
                    <Save />
                  </motion.button>
                  </Tooltip>
                  <Tooltip content="Close editor">
                  <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={() => {
                      setOpenCustomEditor(false);
                      setCustomEntries(null);
                      setEditingFile(null);
                      setFileContent("");
                    }}
                    className="p-3 bg-red-500/20 hover:bg-red-500/30 text-red-400 hover:text-red-300 rounded-xl transition-colors border border-red-500/30"
                  >
                    <X />
                  </motion.button>
                  </Tooltip>
                </div>
              </div>

              <div className="mb-4 bg-white/6 border border-white/10 rounded-xl p-4">
                <p className="text-sm text-white/70">
                  Edit configuration keys. Types are inferred but can be
                  changed. Comments above keys are preserved as descriptions.
                </p>
              </div>

              <div className="flex-1 overflow-auto custom-scrollbar -mb-6">
                <div className="space-y-3">
                  {customEntries && customEntries.length === 0 && (
                    <div className="text-white/50 italic p-4">
                      No keys found — add new keys with the button below.
                    </div>
                  )}
                  {customEntries?.map((entry, idx) => (
                    <motion.div
                      key={entry.key + idx}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="bg-black/40 border border-white/6 rounded-xl p-4 flex gap-3 items-start"
                    >
                      <div className="w-48 min-w-[12rem]">
                        <div className="text-white font-medium truncate">
                          {entry.key}
                        </div>
                        {entry.description && (
                          <div className="text-white/50 text-xs mt-1 whitespace-pre-wrap">
                            {entry.description}
                          </div>
                        )}
                        <input
                          value={entry.key}
                          onChange={(e) => {
                            const newKey = e.target.value;
                            setCustomEntries((prev) => {
                              if (!prev) return prev;
                              const copy = [...prev];
                              copy[idx] = { ...copy[idx], key: newKey };
                              return copy;
                            });
                          }}
                          className="mt-2 w-full bg-white/5 text-white px-2 py-1 rounded text-sm"
                          placeholder="key.name"
                        />
                      </div>

                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <motion.select
                            initial={{ opacity: 0, y: -5 }}
                            animate={{ opacity: 1, y: 0 }}
                            // whileHover={{ scale: 1.05 }}
                            // whileFocus={{ scale: 1.03 }}
                            className=" appearance-none bg-white/10 text-white border border-white/20 px-3 py-1.5 rounded-md focus:outline-none focus:ring-2 focus:ring-white/40 hover:bg-white/20 transition-colors duration-150"
                            transition={{ duration: 0.2, ease: "easeOut" }}
                            value={entry.type}
                            onChange={(e) => {
                              const newType = e.target.value as ConfigType;
                              setCustomEntries((prev) => {
                                if (!prev) return prev;
                                const copy = [...prev];
                                // attempt conversion
                                const current = copy[idx];
                                let newValue = current.value;
                                try {
                                  if (newType === "string")
                                    newValue = String(current.value);
                                  else if (newType === "number")
                                    newValue = Number(current.value) || 0;
                                  else if (newType === "boolean")
                                    newValue = !!current.value;
                                  else if (newType === "list")
                                    newValue = Array.isArray(current.value)
                                      ? current.value
                                      : String(current.value)
                                          .split(",")
                                          .map((s) => s.trim());
                                  else if (newType === "dict")
                                    newValue =
                                      typeof current.value === "object" &&
                                      !Array.isArray(current.value)
                                        ? current.value
                                        : {};
                                } catch {
                                  /* ignore conversion errors */
                                }
                                copy[idx] = {
                                  ...current,
                                  type: newType,
                                  value: newValue,
                                };
                                return copy;
                              });
                            }}
                            // className="bg-white/5 text-white px-2 py-1 rounded"
                          >
                            <option className="text-black" value="string">
                              String
                            </option>
                            <option className="text-black" value="number">
                              Number
                            </option>
                            <option className="text-black" value="boolean">
                              Boolean
                            </option>
                            <option className="text-black" value="list">
                              List
                            </option>
                            <option className="text-black" value="dict">
                              Dict
                            </option>
                          </motion.select>

                          <div className="flex-1">
                            {/* type-aware input */}
                            {entry.type === "string" && (
                              <input
                                className="w-full bg-white/5 text-white px-3 py-2 rounded"
                                value={String(entry.value ?? "")}
                                onChange={(e) => {
                                  const v = e.target.value;
                                  setCustomEntries((prev) => {
                                    if (!prev) return prev;
                                    const copy = [...prev];
                                    copy[idx] = { ...copy[idx], value: v };
                                    return copy;
                                  });
                                }}
                              />
                            )}
                            {entry.type === "number" && (
                              <input
                                type="number"
                                className="w-full bg-white/5 text-white px-3 py-2 rounded"
                                value={String(entry.value ?? 0)}
                                onChange={(e) => {
                                  const v = Number(e.target.value);
                                  setCustomEntries((prev) => {
                                    if (!prev) return prev;
                                    const copy = [...prev];
                                    copy[idx] = { ...copy[idx], value: v };
                                    return copy;
                                  });
                                }}
                              />
                            )}
                            {entry.type === "boolean" && (
                              <label className="inline-flex items-center gap-2">
                                <motion.input
                                  type="checkbox"
                                  checked={!!entry.value}
                                  onChange={(e) => {
                                    const v = e.target.checked;
                                    setCustomEntries((prev) => {
                                      if (!prev) return prev;
                                      const copy = [...prev];
                                      copy[idx] = { ...copy[idx], value: v };
                                      return copy;
                                    });
                                  }}
                                />
                                <span className="text-white/80">Enabled</span>
                              </label>
                            )}
                            {entry.type === "list" && (
                              <textarea
                                rows={2}
                                className="w-full bg-white/5 text-white px-3 py-2 rounded"
                                value={
                                  Array.isArray(entry.value)
                                    ? entry.value.join(", ")
                                    : String(entry.value)
                                }
                                onChange={(e) => {
                                  const arr = e.target.value
                                    .split(",")
                                    .map((s) => s.trim())
                                    .filter(Boolean);
                                  setCustomEntries((prev) => {
                                    if (!prev) return prev;
                                    const copy = [...prev];
                                    copy[idx] = { ...copy[idx], value: arr };
                                    return copy;
                                  });
                                }}
                              />
                            )}
                            {entry.type === "dict" && (
                              <textarea
                                rows={3}
                                className="w-full bg-white/5 text-white px-3 py-2 rounded font-mono text-sm"
                                value={
                                  typeof entry.value === "object"
                                    ? JSON.stringify(entry.value, null, 2)
                                    : String(entry.value)
                                }
                                onChange={(e) => {
                                  try {
                                    const parsed = JSON.parse(e.target.value);
                                    setCustomEntries((prev) => {
                                      if (!prev) return prev;
                                      const copy = [...prev];
                                      copy[idx] = {
                                        ...copy[idx],
                                        value: parsed,
                                      };
                                      return copy;
                                    });
                                  } catch {
                                    // ignore parse errors for now
                                    setCustomEntries((prev) => {
                                      if (!prev) return prev;
                                      const copy = [...prev];
                                      copy[idx] = {
                                        ...copy[idx],
                                        value: e.target.value,
                                      };
                                      return copy;
                                    });
                                  }
                                }}
                              />
                            )}
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => {
                                // open small prompt to edit description
                                const newDesc = prompt(
                                  "Description (comment) for this key",
                                  entry.description || ""
                                );
                                setCustomEntries((prev) => {
                                  if (!prev) return prev;
                                  const copy = [...prev];
                                  copy[idx] = {
                                    ...copy[idx],
                                    description: newDesc || undefined,
                                  };
                                  return copy;
                                });
                              }}
                              className="p-2 bg-white/5 rounded"
                            >
                              ✎
                            </button>
                            <button
                              onClick={() => {
                                setCustomEntries((prev) =>
                                  prev ? prev.filter((_, i) => i !== idx) : prev
                                );
                              }}
                              className="p-2 bg-red-600/20 hover:bg-red-600/30 rounded"
                            >
                              <Trash2 />
                            </button>
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  ))}

                  <div className="pt-4">
                    <button
                      onClick={() => {
                        const base = customEntries ?? [];
                        // ensure unique key suggestion
                        let i = 1;
                        let candidate = `new.key`;
                        while (base.find((e) => e.key === candidate)) {
                          candidate = `new.key${i++}`;
                        }
                        setCustomEntries([
                          ...base,
                          {
                            key: candidate,
                            value: "",
                            type: "string",
                            description: "",
                          },
                        ]);
                      }}
                      className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-pink-500 to-purple-600 text-white rounded-xl mb-6"
                    >
                      <PlusCircle /> Add Key
                    </button>
                  </div>
                </div>
              </div>

              {/* <div className="mt-6 flex gap-3">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleSave}
                  className="flex-1 bg-gradient-to-r from-pink-500 to-purple-600 text-white font-bold py-4 px-6 rounded-xl"
                >
                  💾 Save Config
                </motion.button>
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => {
                    setOpenCustomEditor(false);
                    setCustomEntries(null);
                    setEditingFile(null);
                  }}
                  className="px-8 bg-white/10 hover:bg-white/20 text-white font-bold py-4 rounded-xl"
                >
                  Cancel
                </motion.button>
              </div> */}
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
                  <Tooltip content="Save">
                  <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={handleSave}
                    className="p-3 bg-green-500/20 hover:bg-green-500/30 text-green-400 hover:text-green-300 rounded-xl transition-colors border border-green-500/30"
                    title="Save file"
                  >
                    <Save />
                  </motion.button>
                  </Tooltip>
                  <Tooltip content="Close editor">
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
                    <X />
                  </motion.button></Tooltip>
                </div>
              </div>

              {/* Editor */}
              <motion.textarea
                initial={{ y: 20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.1 }}
                value={fileContent}
                onChange={(e) => setFileContent(e.target.value)}
                readOnly={editorReadOnly}
                className="flex-1 bg-black/50 backdrop-blur-sm border border-white/20 rounded-xl p-6 text-white font-mono text-sm focus:outline-none focus:ring-0 resize-none custom-scrollbar"
                placeholder="File content..."
              />
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
