"use client";
import { useEffect, useState, useCallback, useRef } from "react";
import type { Project, Category, Addon, SearchRequest } from "@/utils/types";
import {
  apiGetServerType,
  apiGetCategories,
  apiListPlugins,
  apiSearchProjects,
  apiGetProjectVersions,
  apiDownloadProject,
  apiRemoveProject,
} from "@/lib/api/plugins";

export default function usePlugins(serverName: string) {
  const [serverType, setServerType] = useState<"mod" | "plugin">("mod");
  const [serverVersion, setServerVersion] = useState<string>("1.21.0");
  const [categories, setCategories] = useState<Category[]>([]);
  const [installed, setInstalled] = useState<Addon[]>([]);
  const [downloadingMods, setDownloadingMods] = useState<Project[]>([]);

  const addDownloadingMods = (project: Project) => {
    setDownloadingMods((prev) => [...prev, project]);
  };

  const removeDownloadingMods = (project: Project) => {
    setDownloadingMods((prev) => prev.filter((p) => p.id !== project.id));
  };

  // search state
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [limit] = useState(30);
  const [total, setTotal] = useState(0);
  const [searchResults, setSearchResults] = useState<Project[]>([]);

  // simple in-memory cache (clears on reload)
  const cache = useRef<
    Record<string, { projects: Project[]; total: number; timestamp: number }>
  >({});

  const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

  const detectServerType = useCallback(async () => {
    const res = await apiGetServerType(serverName);
    setServerType(res.type);
    setServerVersion(res.version);
    setCategory(res.loader);
  }, [serverName]);

  const loadCategories = useCallback(async () => {
    try {
      const cats = await apiGetCategories(serverName);
      setCategories(cats || []);
    } catch {
      setCategories([]);
    }
  }, [serverName]);

  const refreshInstalled = useCallback(async () => {
    try {
      const list = await apiListPlugins(serverName);
      setInstalled(list || []);
    } catch {
      setInstalled([]);
    }
  }, [serverName]);

  useEffect(() => {
    detectServerType();
    loadCategories();
    refreshInstalled();
  }, [detectServerType, loadCategories, refreshInstalled]);

  const doSearch = useCallback(
    async (targetPage = 0) => {
      setPage(targetPage);
      const key = JSON.stringify({
        query,
        category,
        page: targetPage,
        limit,
        serverType,
        serverVersion,
      });

      // check cache
      const cached = cache.current[key];
      const now = Date.now();

      if (cached && now - cached.timestamp < CACHE_TTL) {
        setSearchResults(cached.projects);
        setTotal(cached.total);
        return; // no fetch needed
      }

      const body: SearchRequest = {
        query,
        limit,
        offset: targetPage * limit,
        sort: "downloads", // use consistent sorting
        project_type: serverType,
        versions: [serverVersion],
        categories: category ? [category] : undefined,
      };

      const results = await apiSearchProjects(serverName, body);
      const projects = results.hits as Project[];

      setSearchResults(projects);
      setTotal(results.total_hits);

      // store in cache
      cache.current[key] = {
        projects,
        total: results.total_hits,
        timestamp: now,
      };
    },
    [query, category, limit, serverType, serverVersion, CACHE_TTL, serverName]
  );

  const getVersionsForProject = useCallback(
    async (projectId: string) => {
      return apiGetProjectVersions(serverName, projectId);
    },
    [serverName]
  );

  const downloadProjectVersion = useCallback(
    async (projectId: string, versionId?: string) => {
      await apiDownloadProject(serverName, projectId, serverVersion, versionId);
      await refreshInstalled();
    },
    [refreshInstalled, serverName, serverVersion]
  );

  const removeInstalled = useCallback(
    async (projectId: string) => {
      await apiRemoveProject(serverName, projectId);
      await refreshInstalled();
    },
    [serverName, refreshInstalled]
  );

  return {
    serverType,
    serverVersion,
    categories,
    installed,
    query,
    downloadingMods,
    addDownloadingMods,
    removeDownloadingMods,
    setQuery,
    setCategory,
    page,
    total,
    searchResults,
    doSearch,
    getVersionsForProject,
    downloadProjectVersion,
    removeInstalled,
    refreshInstalled,
  };
}
