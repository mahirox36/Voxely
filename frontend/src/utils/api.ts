import axios from "axios";


export const isDev = process.env.NODE_ENV === "development";

export const api = axios.create({
  baseURL: isDev ? "http://localhost:25401/api/v1": "/api/v1", // all requests start here
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
