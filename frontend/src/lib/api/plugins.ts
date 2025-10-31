import {
  Addon,
  Category,
  Project,
  SearchRequest,
  SearchResult,
  Version,
} from "@/utils/types";
import api from "@/utils/api";

const extractErrorMessage = (err: unknown, fallback = "Request failed") => {
  const error = err as {
    response?: { data?: { detail?: string } };
    message?: string;
  };
  return String(
    error.response?.data?.detail ??
      error.response?.data ??
      error.message ??
      fallback
  );
};

export async function apiGetServerType(serverName: string) {
  try {
    return (await api.get(`/servers/${serverName}/plugins/type`)) as {
      type: "mod" | "plugin";
      version: string;
      loader: string;
    };
  } catch (err) {
    throw new Error(extractErrorMessage(err, "Failed to detect server type"));
  }
}

export async function apiGetCategories(serverName: string) {
  try {
    return (await api.get(
      `/servers/${serverName}/plugins/categories`
    )) as Category[];
  } catch (err) {
    throw new Error(extractErrorMessage(err, "Failed to load categories"));
  }
}

export async function apiListPlugins(serverName: string) {
  try {
    return (await api.get(`/servers/${serverName}/plugins/list`)) as Addon[];
  } catch (err) {
    throw new Error(extractErrorMessage(err, "Failed to list plugins"));
  }
}

export async function apiSearchProjects(
  serverName: string,
  body: SearchRequest
) {
  try {
    return (await api.post(
      `/servers/${serverName}/plugins/search`,
      body
    )) as SearchResult;
  } catch (err) {
    throw new Error(extractErrorMessage(err, "Search failed"));
  }
}

export async function apiGetProject(serverName: string, projectId: string) {
  try {
    return (await api.get(
      `/servers/${serverName}/plugins/get/${projectId}`
    )) as Project;
  } catch (err) {
    throw new Error(extractErrorMessage(err, "Failed to get versions"));
  }
}

export async function apiGetProjectVersions(
  serverName: string,
  projectId: string
) {
  try {
    return (await api.get(
      `/servers/${serverName}/plugins/get_versions/${projectId}`
    )) as Version[];
  } catch (err) {
    throw new Error(extractErrorMessage(err, "Failed to get versions"));
  }
}

export async function apiDownloadProject(
  serverName: string,
  projectId: string,
  gameVersion = "",
  projectVersion: string | undefined = undefined
) {
  try {
    return (await api.post(
      `/servers/${serverName}/plugins/download/${projectId}`,
      { version: gameVersion, project_version: projectVersion }
    )) as void;
  } catch (err) {
    throw new Error(extractErrorMessage(err, "Download failed"));
  }
}

export async function apiRemoveProject(serverName: string, projectId: string) {
  try {
    return await api.post(`/servers/${serverName}/plugins/remove/${projectId}`);
  } catch (err) {
    throw new Error(extractErrorMessage(err, "Remove failed"));
  }
}
