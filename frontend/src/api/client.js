/**
 * Axios instance with:
 * - Base URL configuration
 * - Cookie-based authentication (httpOnly cookies)
 * - Automatic credential inclusion
 * - Token refresh on 401
 * - Consistent error extraction
 */
import axios from "axios";

// Use relative URL to leverage Vite proxy
const BASE_URL = import.meta.env.VITE_API_URL || "/api/v1";

// Token storage (in-memory for security)
let accessToken = null;
let refreshToken = null;

export const setTokens = (access, refresh) => {
  accessToken = access;
  refreshToken = refresh;
};

export const getAccessToken = () => accessToken;
export const getRefreshToken = () => refreshToken;

export const clearTokens = () => {
  accessToken = null;
  refreshToken = null;
};

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Add Authorization header to all requests
apiClient.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

// On 401, attempt token refresh once
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const currentPath = window.location.pathname;
    const isAuthPage = currentPath.includes('/login') || currentPath.includes('/register');
    
    // Don't retry refresh endpoint or when already on auth pages
    if (error.response?.status === 401 && !original._retry && !isAuthPage && !original.url.includes('/auth/refresh') && refreshToken) {
      original._retry = true;
      try {
        const { data } = await axios.post(`${BASE_URL}/auth/refresh`, { refresh_token: refreshToken });
        setTokens(data.data.access_token, data.data.refresh_token);
        original.headers.Authorization = `Bearer ${data.data.access_token}`;
        return apiClient(original);
      } catch (refreshError) {
        clearTokens();
        window.location.href = "/login";
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);

// ---------------------------------------------------------------------------
// Auth API
// ---------------------------------------------------------------------------
export const authApi = {
  async register(data) {
    const response = await apiClient.post("/auth/register", data);
    if (response.data.data.access_token) {
      setTokens(response.data.data.access_token, response.data.data.refresh_token);
    }
    return response;
  },
  
  async login(data) {
    const response = await apiClient.post("/auth/login", data);
    if (response.data.data.access_token) {
      setTokens(response.data.data.access_token, response.data.data.refresh_token);
    }
    return response;
  },
  
  async logout() {
    clearTokens();
    return apiClient.post("/auth/logout");
  },
  
  me: () => apiClient.get("/auth/me"),
};

// ---------------------------------------------------------------------------
// Watchlist API
// ---------------------------------------------------------------------------
export const watchlistApi = {
  list: () => apiClient.get("/watchlists"),
  create: (data) => apiClient.post("/watchlists", data),
  get: (id) => apiClient.get(`/watchlists/${id}`),
  update: (id, data) => apiClient.patch(`/watchlists/${id}`, data),
  delete: (id) => apiClient.delete(`/watchlists/${id}`),
  addCoin: (id, data) => apiClient.post(`/watchlists/${id}/coins`, data),
  removeCoin: (watchlistId, itemId) =>
    apiClient.delete(`/watchlists/${watchlistId}/coins/${itemId}`),
  getPrices: (id) => apiClient.get(`/watchlists/${id}/prices`),
};

// ---------------------------------------------------------------------------
// Market API
// ---------------------------------------------------------------------------
export const marketApi = {
  search: (q) => apiClient.get("/market/search", { params: { q } }),
};

/** Extract a user-friendly error message from any axios error */
export function getErrorMessage(error) {
  return (
    error?.response?.data?.error?.message ||
    error?.message ||
    "An unexpected error occurred."
  );
}
