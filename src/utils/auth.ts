const TOKEN_KEY = 'htpi_admin_token';
const ADMIN_KEY = 'htpi_admin';

export const setToken = (token: string): void => {
  localStorage.setItem(TOKEN_KEY, token);
};

export const getToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};

export const removeToken = (): void => {
  localStorage.removeItem(TOKEN_KEY);
};

export const setAdmin = (admin: any): void => {
  localStorage.setItem(ADMIN_KEY, JSON.stringify(admin));
};

export const getAdmin = (): any | null => {
  const adminStr = localStorage.getItem(ADMIN_KEY);
  if (adminStr) {
    try {
      return JSON.parse(adminStr);
    } catch {
      return null;
    }
  }
  return null;
};

export const removeAdmin = (): void => {
  localStorage.removeItem(ADMIN_KEY);
};

export const clearAuth = (): void => {
  removeToken();
  removeAdmin();
};

export const isAuthenticated = (): boolean => {
  return !!getToken();
};

export const isSuperAdmin = (): boolean => {
  const admin = getAdmin();
  return admin?.is_super_admin || false;
};