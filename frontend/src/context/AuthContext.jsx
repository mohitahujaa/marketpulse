import { createContext, useContext, useEffect, useState } from "react";
import { authApi, getErrorMessage } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Rehydrate user on page load (cookies are sent automatically)
  useEffect(() => {
    // Skip auth check on login/register pages
    const currentPath = window.location.pathname;
    if (currentPath.includes('/login') || currentPath.includes('/register')) {
      setLoading(false);
      return;
    }
    
    authApi
      .me()
      .then((res) => setUser(res.data.data))
      .catch(() => setUser(null)) // No valid session
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    // Login sets httpOnly cookies automatically on the server
    await authApi.login({ email, password });
    // Fetch user profile after successful login
    const me = await authApi.me();
    setUser(me.data.data);
  };

  const logout = async () => {
    try {
      // Call logout endpoint to clear cookies on server
      await authApi.logout();
    } catch (error) {
      // Ignore errors, clear user state anyway
    } finally {
      setUser(null);
    }
  };

  const refreshUser = async () => {
    // Fetch current user (useful after registration)
    const me = await authApi.me();
    setUser(me.data.data);
  };

  return (
    <AuthContext.Provider value={{ user, setUser, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
