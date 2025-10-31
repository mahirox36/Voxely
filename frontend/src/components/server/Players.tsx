import React, { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Users,
  Heart,
  Drumstick,
  Star,
  MapPin,
  Package,
  Box,
  Code,
  RefreshCw,
  Save,
  X,
  ChevronDown,
  ChevronUp,
  Search,
} from "lucide-react";
import api from "@/utils/api";
import { useModal } from "@/components/ModalProvider";
import Image from "next/image";

// Types
interface NBTValue {
  type: string;
  value: number | string | number[];
}

interface NBTCompound {
  [key: string]: NBTValue | NBTCompound | NBTList;
}

type NBTList = Array<NBTValue | NBTCompound>;

interface PlayerStatus {
  online: number;
  players: number;
  online_players: string[];
}

interface InventoryItem {
  id: NBTValue;
  count: NBTValue;
  Slot?: NBTValue;
  tag?: NBTCompound;
}

interface PlayerData {
  name: string;
  uuid: string;
  Health: NBTValue;
  foodLevel: NBTValue;
  XpLevel: NBTValue;
  Pos: NBTList;
  Inventory: NBTList;
  EnderItems: NBTList;
  UUID: NBTValue;
  [key: string]: NBTValue | NBTCompound | NBTList | string;
}

interface ModalOptions {
  type: "inventory" | "enderchest" | "nbt";
  player: string;
  uuid: string;
  data: PlayerData;
}

// Helper functions
function getNBTValue(
  value: NBTValue | NBTCompound | NBTList | string
): number | string {
  if (typeof value === "string") return value;
  if (typeof value === "object" && "value" in value) {
    return value.value as number | string;
  }
  return 0;
}

function getListValues(list: NBTList): number[] {
  return list.map((item) => {
    if (typeof item === "object" && "value" in item) {
      return item.value as number;
    }
    return 0;
  });
}

// Main Players Component
export default function Players({ serverName }: { serverName: string }) {
  const [players, setPlayers] = useState<PlayerData[]>([]);
  const [status, setStatus] = useState<PlayerStatus>({
    online: 0,
    players: 0,
    online_players: [],
  });
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [modalData, setModalData] = useState<ModalOptions | null>(null);

  const fetchPlayers = useCallback(async () => {
    try {
      const data: PlayerData[] = await api.get(
        `/servers/${serverName}/players/get`
      );
      setPlayers(data);
    } catch (error) {
      console.error("Failed to fetch players:", error);
    }
  }, [serverName]);

  const fetchStatus = useCallback(async () => {
    try {
      const data: PlayerStatus = await api.get(
        `/servers/${serverName}/players/status`
      );
      setStatus(data);
    } catch (error) {
      console.error("Failed to fetch status:", error);
    }
  }, [serverName]);

  const refreshAll = useCallback(async () => {
    setLoading(true);
    await Promise.all([fetchPlayers(), fetchStatus()]);
    setLoading(false);
  }, [fetchPlayers, fetchStatus]);

  useEffect(() => {
    refreshAll();
  }, [refreshAll]);

  const filteredPlayers = players.filter((p) =>
    p.name?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <motion.div
      className="glass-card h-[calc(100vh-16rem)] mx-auto p-6 flex flex-col"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <PlayerStatusBar
        status={status}
        onRefresh={refreshAll}
        loading={loading}
      />

      <div className="flex items-center gap-4 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
          <input
            type="text"
            placeholder="Search players..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/40 focus:outline-none focus:border-purple-400"
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <motion.div
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            >
              <RefreshCw className="w-8 h-8 text-purple-400" />
            </motion.div>
          </div>
        ) : (
          <PlayersList players={filteredPlayers} onOpenModal={setModalData} status={status} />
        )}
      </div>

      <AnimatePresence>
        {modalData && (
          <PlayerModal
            {...modalData}
            serverName={serverName}
            onClose={() => setModalData(null)}
            onSave={refreshAll}
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// Player Status Bar Component
function PlayerStatusBar({
  status,
  onRefresh,
  loading,
}: {
  status: PlayerStatus;
  onRefresh: () => void;
  loading: boolean;
}) {
  return (
    <motion.div
      className="flex justify-between items-center mb-6 pb-4 border-b border-white/20"
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
    >
      <div className="flex items-center gap-6">
        <h2 className="text-2xl font-bold text-white flex items-center gap-3">
           <motion.div
              animate={{ rotate: [0, 10, -10, 0] }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
          <Users className="text-purple-400" />
          </motion.div>
          Players
        </h2>

        <div className="flex items-center gap-4">
          <div className="px-4 py-2 bg-green-500/20 border border-green-500/30 rounded-lg">
            <span className="text-green-300 font-medium">
              {status.online} Online
            </span>
          </div>
          <div className="px-4 py-2 bg-blue-500/20 border border-blue-500/30 rounded-lg">
            <span className="text-blue-300 font-medium">
              {status.players} Total
            </span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onRefresh}
          disabled={loading}
          className="px-4 py-2 bg-white/10 text-white rounded-lg font-medium flex items-center gap-2 hover:bg-white/20 transition-color border border-white/20 disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </motion.button>
      </div>
    </motion.div>
  );
}

// Players List Component
function PlayersList({
  players,
  onOpenModal,
  status
}: {
  players: PlayerData[];
  onOpenModal: (data: ModalOptions) => void;
    status: PlayerStatus
}) {
  if (players.length === 0) {
    return (
      <div className="text-center py-16">
        <Users className="w-16 h-16 text-white/20 mx-auto mb-4" />
        <p className="text-white/40 text-lg">No players found</p>
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      {players.map((player, idx) => (
        <PlayerCard
          key={player.name || idx}
          player={player}
          onOpenModal={onOpenModal}
          status={status}
        />
      ))}
    </div>
  );
}

// Player Card Component
function PlayerCard({
  player,
  onOpenModal,
  status
}: {
  player: PlayerData;
  onOpenModal: (data: ModalOptions) => void;
  status: PlayerStatus
}) {
  const [expanded, setExpanded] = useState(false);

  const health = getNBTValue(player.Health) as number;
  const hunger = getNBTValue(player.foodLevel) as number;
  const xp = getNBTValue(player.XpLevel) as number;
  const pos = getListValues(player.Pos as NBTList);

  const uuid = player.uuid;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white/5 border border-white/10 rounded-xl overflow-hidden hover:border-white/20 transition-color"
    >
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-bold text-xl">
              <Image
                width={256}
                height={256}
                src={`https://minotar.net/avatar/${player.name}/256`}
                alt={player.name}
              />
            </div>
            <div>
              <h3 className="text-xl font-bold text-white">
                {player.name || "Unknown"}
              </h3>
              <div className="flex items-center gap-2 mt-1">
                <div className={`w-2 h-2 rounded-full ${!status.online_players.includes(player.name) ? "bg-gray-400" : "bg-emerald-400"}`} />
                <span className="text-white/60 text-sm">{status.online_players.includes(player.name) ? "Online" : "Offline"}</span>
              </div>
            </div>
          </div>

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setExpanded(!expanded)}
            className="p-2 hover:bg-white/10 rounded-lg transition-color"
          >
            {expanded ? (
              <ChevronUp className="w-5 h-5 text-white/60" />
            ) : (
              <ChevronDown className="w-5 h-5 text-white/60" />
            )}
          </motion.button>
        </div>

        <div className="grid grid-cols-4 gap-4 mb-4">
          <StatBox
            icon={Heart}
            label="Health"
            value={`${health}/20`}
            color="red"
          />
          <StatBox
            icon={Drumstick}
            label="Hunger"
            value={`${hunger}/20`}
            color="orange"
          />
          <StatBox
            icon={Star}
            label="XP Level"
            value={xp.toString()}
            color="yellow"
          />
          <StatBox
            icon={MapPin}
            label="Position"
            value={`${Math.round(pos[0] || 0)}, ${Math.round(
              pos[1] || 0
            )}, ${Math.round(pos[2] || 0)}`}
            color="blue"
          />
        </div>

        <AnimatePresence>
          {expanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="border-t border-white/10 pt-4 mt-4"
            >
              <div className="flex gap-3">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() =>
                    onOpenModal({
                      type: "inventory",
                      player: player.name,
                      uuid: uuid,
                      data: player,
                    })
                  }
                  className="flex-1 px-4 py-3 bg-purple-500/20 text-purple-300 rounded-lg font-medium flex items-center justify-center gap-2 hover:bg-purple-500/30 transition-color border border-purple-500/30"
                >
                  <Package className="w-4 h-4" />
                  View Inventory
                </motion.button>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() =>
                    onOpenModal({
                      type: "enderchest",
                      player: player.name,
                      uuid: uuid,
                      data: player,
                    })
                  }
                  className="flex-1 px-4 py-3 bg-indigo-500/20 text-indigo-300 rounded-lg font-medium flex items-center justify-center gap-2 hover:bg-indigo-500/30 transition-color border border-indigo-500/30"
                >
                  <Box className="w-4 h-4" />
                  Ender Chest
                </motion.button>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() =>
                    onOpenModal({
                      type: "nbt",
                      player: player.name,
                      uuid: uuid,
                      data: player,
                    })
                  }
                  className="flex-1 px-4 py-3 bg-pink-500/20 text-pink-300 rounded-lg font-medium flex items-center justify-center gap-2 hover:bg-pink-500/30 transition-color border border-pink-500/30"
                >
                  <Code className="w-4 h-4" />
                  Edit Raw NBT
                </motion.button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

// Stat Box Component
function StatBox({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  color: string;
}) {
  const colorClasses: { [key: string]: string } = {
    red: "bg-red-500/20 border-red-500/30 text-red-300",
    orange: "bg-orange-500/20 border-orange-500/30 text-orange-300",
    yellow: "bg-yellow-500/20 border-yellow-500/30 text-yellow-300",
    blue: "bg-blue-500/20 border-blue-500/30 text-blue-300",
  };

  return (
    <div className={`p-3 rounded-lg border ${colorClasses[color]}`}>
      <div className="flex items-center gap-2 mb-1">
        <Icon className="w-4 h-4" />
        <span className="text-xs opacity-80">{label}</span>
      </div>
      <p className="font-bold">{value}</p>
    </div>
  );
}

// Player Modal Component
function PlayerModal({
  type,
  player,
  uuid,
  data,
  serverName,
  onClose,
  onSave,
}: ModalOptions & {
  serverName: string;
  onClose: () => void;
  onSave: () => void;
}) {
  const [editedData, setEditedData] = useState(JSON.stringify(data, null, 2));
  const [saving, setSaving] = useState(false);
  const modal = useModal();

  const handleSave = async () => {
    setSaving(true);
    try {
      const parsed = JSON.parse(editedData);
      await api.post(`/servers/${serverName}/players/${uuid}`, parsed);
      await modal.showModal({
        type: "info",
        title: "Success",
        content: "Player data saved successfully!",
        confirmText: "OK",
      });
      onSave();
      onClose();
    } catch (error) {
      console.error("Failed to save:", error);
      await modal.showModal({
        type: "info",
        title: "Error",
        content: `Failed to save player data: ${
          error instanceof Error ? error.message : "Unknown error"
        }`,
        confirmText: "OK",
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <motion.div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <motion.div className="absolute inset-0 bg-black/70" onClick={onClose} />

      <motion.div
        className="glass-card w-full max-w-4xl max-h-[80vh] z-50 flex flex-col"
        initial={{ scale: 0.95, y: 20 }}
        animate={{ scale: 1, y: 0 }}
        exit={{ scale: 0.95, y: 20 }}
      >
        <div className="p-6 border-b border-white/20 flex items-center justify-between">
          <h3 className="text-xl font-bold text-white">
            {type === "inventory" && "Inventory"}
            {type === "enderchest" && "Ender Chest"}
            {type === "nbt" && "Raw NBT Data"}
            {" - "}
            {player}
          </h3>
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={onClose}
            className="p-2 hover:bg-white/10 rounded-lg transition-color"
          >
            <X className="w-5 h-5 text-white/60" />
          </motion.button>
        </div>

        <div className="flex-1 overflow-auto p-6">
          {(type === "inventory" || type === "enderchest") && (
            <InventoryGrid
              items={
                type === "inventory"
                  ? (data.Inventory as NBTList)
                  : (data.EnderItems as NBTList)
              }
              slots={type === "inventory" ? 36 : 27}
            />
          )}

          {type === "nbt" && (
            <textarea
              value={editedData}
              onChange={(e) => setEditedData(e.target.value)}
              className="w-full h-full min-h-[400px] p-4 bg-black/40 text-white font-mono text-sm rounded-lg border border-white/20 focus:outline-none focus:border-purple-400 resize-none"
              spellCheck={false}
            />
          )}
        </div>

        <div className="p-6 border-t border-white/20 flex justify-end gap-3">
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={onClose}
            className="px-6 py-2 bg-white/10 text-white rounded-lg font-medium hover:bg-white/20 transition-color border border-white/20"
          >
            Cancel
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-2 bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-lg font-medium flex items-center gap-2 hover:from-purple-600 hover:to-pink-600 transition-color shadow-lg disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? "Saving..." : "Save Changes"}
          </motion.button>
        </div>
      </motion.div>
    </motion.div>
  );
}

// Inventory Grid Component
function InventoryGrid({ items, slots }: { items: NBTList; slots: number }) {
  const grid: Array<InventoryItem | null> = Array(slots).fill(null);

  items.forEach((item) => {
    if (typeof item === "object" && !("type" in item)) {
      const invItem = item as unknown as InventoryItem;
      const slot = invItem.Slot ? (getNBTValue(invItem.Slot) as number) : -1;
      if (slot >= 0 && slot < slots) {
        grid[slot] = invItem;
      }
    }
  });

  return (
    <div className="grid grid-cols-9 gap-2">
      {grid.map((item, idx) => (
        <InventorySlot key={idx} item={item} slot={idx} />
      ))}
    </div>
  );
}

// Inventory Slot Component
function InventorySlot({
  item,
  slot,
}: {
  item: InventoryItem | null;
  slot: number;
}) {
  const getItemId = (item: InventoryItem): string => {
    const id = getNBTValue(item.id) as string;
    return id;
  };

  const getItemCount = (item: InventoryItem): number => {
    console.log(item.count)
    return getNBTValue(item.count) as number;
  };
  const [src, setSrc] = useState(
    item
      ? `https://minecraft-api.vercel.app/images/items/${
          getItemId(item).split(":")[1]
        }.png`
      : null
  );

  return (
    <motion.div
      whileHover={{ scale: 1.05 }}
      className="aspect-square bg-white/5 border border-white/20 rounded-lg flex items-center justify-center relative group cursor-pointer hover:border-purple-400 transition-color"
    >
      {item ? (
        <>
          <div className="text-white font-medium text-xs">
            {src && (
              <Image
                unoptimized
                width={50}
                height={50}
                src={src}
                alt={getItemId(item).split(":")[1]}
                style={{
                  objectFit: "contain",
                  imageRendering: "pixelated",
                }}
                onError={() => {
                  if (src.endsWith(".png")) {
                    setSrc(
                      `https://minecraft-api.vercel.app/images/items/${
                        getItemId(item).split(":")[1]
                      }.gif`
                    );
                  } else {
                    setSrc("/default-item.png"); // fallback if GIF also fails
                  }
                }}
              />
            )}
          </div>
          {getItemCount(item) > 1 && (
            <div className="absolute bottom-1 right-1 text-xs text-white/80 font-bold">
              {getItemCount(item)}
            </div>
          )}
          <div className="absolute inset-0 bg-black/80 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg flex items-center justify-center p-2">
            <div className="text-white text-xs text-center break-all">
              {getItemId(item).split(":")[1]}
              {item.tag && <div className="text-white/60 mt-1">+NBT</div>}
            </div>
          </div>
        </>
      ) : (
        <div className="text-white/20 text-xs">{slot}</div>
      )}
    </motion.div>
  );
}
