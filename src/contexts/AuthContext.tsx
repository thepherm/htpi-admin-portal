import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { AdminUser, LoginCredentials } from '../types';
import { setToken, getToken, removeToken, setAdmin, getAdmin, clearAuth } from '../utils/auth';
import api from '../services/api';

interface AuthContextType {
  admin: AdminUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  isSuperAdmin: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  updateAdmin: (admin: AdminUser) => void;
  hasPermission: (permission: string) => boolean;
  canAccessOrg: (orgId: string) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [admin, setAdminState] = useState<AdminUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  useEffect(() => {
    // Check for existing auth on mount
    const initAuth = async () => {
      const token = getToken();
      const savedAdmin = getAdmin();
      
      if (token && savedAdmin) {
        setAdminState(savedAdmin);
        
        try {
          // Verify token is still valid
          const response = await api.getProfile();
          if (response.success) {
            setAdminState(response.data);
            setAdmin(response.data);
          } else {
            clearAuth();
          }
        } catch (error) {
          console.error('Auth verification failed:', error);
          clearAuth();
        }
      }
      
      setIsLoading(false);
    };
    
    initAuth();
  }, []);
  
  const login = async (credentials: LoginCredentials) => {
    try {
      const response = await api.login(credentials.email, credentials.password);
      
      if (response.success) {
        const { token, admin } = response.data;
        
        setToken(token);
        setAdmin(admin);
        setAdminState(admin);
      } else {
        throw new Error(response.error?.message || 'Login failed');
      }
    } catch (error: any) {
      console.error('Login error:', error);
      throw error;
    }
  };
  
  const logout = async () => {
    try {
      await api.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      clearAuth();
      setAdminState(null);
    }
  };
  
  const updateAdmin = (updatedAdmin: AdminUser) => {
    setAdmin(updatedAdmin);
    setAdminState(updatedAdmin);
  };
  
  const hasPermission = (permission: string): boolean => {
    if (!admin) return false;
    if (admin.is_super_admin) return true;
    return admin.permissions.includes(permission);
  };
  
  const canAccessOrg = (orgId: string): boolean => {
    if (!admin) return false;
    if (admin.is_super_admin) return true;
    return admin.org_ids.length === 0 || admin.org_ids.includes(orgId);
  };
  
  const value = {
    admin,
    isLoading,
    isAuthenticated: !!admin,
    isSuperAdmin: admin?.is_super_admin || false,
    login,
    logout,
    updateAdmin,
    hasPermission,
    canAccessOrg
  };
  
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};