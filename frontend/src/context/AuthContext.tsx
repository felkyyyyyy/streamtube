import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { api, setAccessToken } from '../api/client';
import type { UserPublic } from '../types';

interface AuthContextValue {
  user: UserPublic | null;
  loading: boolean;
  isStaff: boolean;
  isAdmin: boolean;
  login: (identifier: string, password: string) => Promise<UserPublic>;
  register: (data: {
    username: string;
    email: string;
    password: string;
    channel_name?: string;
  }) => Promise<UserPublic>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserPublic | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      const me = await api.me();
      setUser(me);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (identifier: string, password: string) => {
    const res = await api.login({ identifier, password });
    setAccessToken(res.access_token);
    setUser(res.user);
    return res.user;
  };

  const register = async (data: {
    username: string;
    email: string;
    password: string;
    channel_name?: string;
  }) => {
    const res = await api.register(data);
    setAccessToken(res.access_token);
    setUser(res.user);
    return res.user;
  };

  const logout = async () => {
    try {
      await api.logout();
    } catch {
      // ignore network error on logout
    }
    setAccessToken(null);
    setUser(null);
  };

  const isStaff = user?.role === 'moderator' || user?.role === 'admin';
  const isAdmin = user?.role === 'admin';

  return (
    <AuthContext.Provider
      value={{ user, loading, isStaff, isAdmin, login, register, logout, refreshUser }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
