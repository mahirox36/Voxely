import axios from "axios";

// Get API URL from environment variable, with fallback for development
const getApiBaseUrl = () => {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  
  // Fallback for development
  if (process.env.NODE_ENV === "development") {
    return "http://localhost:25401/api/v1";
  }
  
  // Default for production
  return "/api/v1";
};

export const api = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 15000, // 15 seconds
});

// Automatically attach token if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = token
  }
  return config;
});

// Handle auth errors globally
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response && [401, 403].includes(error.response.status)) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default api;
