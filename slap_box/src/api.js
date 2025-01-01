// src/services/api.js
import axios from 'axios';

const API_URL = 'http://localhost:8001/api';

const api = axios.create({
  baseURL: API_URL,
});
export let tokenEnabled = false
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
    tokenEnabled = true
  }
  return config;
});

export const auth = {
  login: (credentials) => api.post('/auth/login', credentials),
  register: (userData) => api.post('/auth/register', userData),
};

export const servers = {
  list: () => api.get('/servers'),
  create: (serverData) => api.post('/servers', serverData),
  getInfo: (serverName) => api.get(`/servers/${serverName}`),
  start: (serverName) => api.post(`/servers/${serverName}/start`),
  stop: (serverName) => api.post(`/servers/${serverName}/stop`),
  sendCommand: (serverName, command) => 
    api.post(`/servers/${serverName}/command`, { command }),
  acceptEula: (serverName) => api.post(`/servers/${serverName}/eula`),
};

export const versions = {
  getAll: () => api.get('/versions'),
};