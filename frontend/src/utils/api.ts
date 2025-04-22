import { RequestOptions } from './types';

// Cache for API requests
const apiCache: Record<string, {data: unknown, timestamp: number}> = {};
const CACHE_DURATION = 30000; // 30 seconds instead of 5 seconds

// Track ongoing requests to prevent duplicates
const pendingRequests: Record<string, Promise<unknown>> = {};

/**
 * Centralized API request function with caching and authentication handling
 */
export async function apiRequest(
  endpoint: string,
  options: RequestOptions = {}
) {
  // For debugging: log the endpoint being requested
  console.log(`API Request initiated for: ${endpoint}`);
  
  const cacheKey = `${endpoint}-${JSON.stringify(options)}`;
  const now = Date.now();

  // Check if we have a valid cached response for GET requests
  if (
    (!options.method || options.method === 'GET') &&
    apiCache[cacheKey] &&
    now - apiCache[cacheKey].timestamp < CACHE_DURATION
  ) {
    console.log(`Using cached response for: ${endpoint}`);
    return apiCache[cacheKey].data;
  }

  // If there's already a pending request for this exact endpoint+options, return that promise
  // instead of making a duplicate request
  if (pendingRequests[cacheKey] !== undefined) {
    console.log(`Reusing pending request for: ${endpoint}`);
    return pendingRequests[cacheKey];
  }

  const { requiresAuth = true, ...fetchOptions } = options;
  const headers = new Headers(fetchOptions.headers);

  // Set content type if not already set and it's not a form submission
  if (
    !headers.has("Content-Type") &&
    fetchOptions.body && 
    typeof fetchOptions.body === 'string' &&
    !fetchOptions.body.includes("Content-Disposition: form-data")
  ) {
    headers.set("Content-Type", "application/json");
  }

  // Handle authentication
  if (requiresAuth) {
    const token = localStorage.getItem("token");
    if (!token) {
      console.error("Authentication required but no token found");
      window.location.href = "/login"; // Redirect to login
      throw new Error("Authentication required");
    }

    // Ensure token has the "Bearer " prefix
    const formattedToken = token.startsWith("Bearer ") ? token : `Bearer ${token}`;
    headers.set("Authorization", formattedToken);
    console.log("Added auth token to request");
  }

  // Ensure endpoint always starts with /api/v1 and proper path handling
  let apiUrl = endpoint;
  
  // Remove leading slash if present
  if (apiUrl.startsWith('/')) {
    apiUrl = apiUrl.substring(1);
  }
  
  // Ensure we have the correct api/v1 prefix
  if (!apiUrl.startsWith('api/v1/') && !apiUrl.startsWith('api/v1')) {
    if (!apiUrl.startsWith('v1/') && !apiUrl.startsWith('v1')) {
      apiUrl = `api/v1/${apiUrl}`;
    } else {
      apiUrl = `api/${apiUrl}`;
    }
  }
  
  // Ensure leading slash
  if (!apiUrl.startsWith('/')) {
    apiUrl = `/${apiUrl}`;
  }
  
  // Create an AbortController to handle timeouts
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000); // 15 second timeout

  console.log(`Making API request to: ${apiUrl}`);

  // Create the promise for this request and store it
  const requestPromise = (async () => {
    try {
      const response = await fetch(apiUrl, {
        ...fetchOptions,
        headers,
        signal: controller.signal,
        mode: "cors",
        credentials: "same-origin",
        cache: "no-cache",
      });

      console.log(`Received response for ${apiUrl}: status ${response.status}`);

      if (response.status === 401 || response.status === 403) {
        const errorText = await response.text();
        console.error("Authentication failed:", errorText);
        localStorage.removeItem("token");
        window.location.href = "/login";
        throw new Error("Authentication failed - please log in again");
      }

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ detail: "Request failed" }));
        throw new Error(errorData.detail || "Request failed");
      }

      // For empty responses (like 204 No Content)
      if (response.status === 204) {
        return {};
      }

      const data = await response.json();
      console.log(`API response from ${apiUrl}:`, data);

      // Cache the response for GET requests
      if (!options.method || options.method === 'GET') {
        apiCache[cacheKey] = {
          data,
          timestamp: now
        };
      }

      return data;
    } catch (error) {
      // Check if this is an abort error from our timeout
      if (error instanceof Error && error.name === "AbortError") {
        console.error("Request timed out");
        throw new Error("Request timed out. Please try again.");
      }

      console.error("API request error:", error);
      throw error;
    } finally {
      clearTimeout(timeout);
      // Remove this request from pending requests when it's done
      delete pendingRequests[cacheKey];
    }
  })();

  // Store the promise
  pendingRequests[cacheKey] = requestPromise;
  
  return requestPromise;
}
