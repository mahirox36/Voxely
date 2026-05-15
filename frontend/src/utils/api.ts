import axios from "axios";

export const baseURL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:25401/v1";

export const api = axios.create({
  baseURL: baseURL,
  timeout: 15000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = token;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response && [401, 403].includes(error.response.status)) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  },
);

export default api;
