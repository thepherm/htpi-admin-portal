import axios, { AxiosInstance, AxiosError } from 'axios';
import { getToken, removeToken } from '../utils/auth';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

class ApiService {
  private axios: AxiosInstance;
  
  constructor() {
    this.axios = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    // Request interceptor to add auth token
    this.axios.interceptors.request.use(
      (config) => {
        const token = getToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );
    
    // Response interceptor to handle auth errors
    this.axios.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          removeToken();
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }
  
  // Auth endpoints
  async login(email: string, password: string) {
    const response = await this.axios.post('/auth/login', { email, password });
    return response.data;
  }
  
  async logout() {
    const response = await this.axios.post('/auth/logout');
    return response.data;
  }
  
  async getProfile() {
    const response = await this.axios.get('/auth/profile');
    return response.data;
  }
  
  // Admin endpoints
  async getAdmins(params?: any) {
    const response = await this.axios.get('/admins', { params });
    return response.data;
  }
  
  async getAdmin(id: string) {
    const response = await this.axios.get(`/admins/${id}`);
    return response.data;
  }
  
  async createAdmin(data: any) {
    const response = await this.axios.post('/admins', data);
    return response.data;
  }
  
  async updateAdmin(id: string, data: any) {
    const response = await this.axios.put(`/admins/${id}`, data);
    return response.data;
  }
  
  async deleteAdmin(id: string) {
    const response = await this.axios.delete(`/admins/${id}`);
    return response.data;
  }
  
  // Organization endpoints
  async getOrganizations(params?: any) {
    const response = await this.axios.get('/organizations', { params });
    return response.data;
  }
  
  async getOrganization(id: string) {
    const response = await this.axios.get(`/organizations/${id}`);
    return response.data;
  }
  
  async createOrganization(data: any) {
    const response = await this.axios.post('/organizations', data);
    return response.data;
  }
  
  async updateOrganization(id: string, data: any) {
    const response = await this.axios.put(`/organizations/${id}`, data);
    return response.data;
  }
  
  async suspendOrganization(id: string, reason: string) {
    const response = await this.axios.post(`/organizations/${id}/suspend`, { reason });
    return response.data;
  }
  
  async getOrganizationStats(id: string, periodDays: number = 30) {
    const response = await this.axios.get(`/organizations/${id}/stats`, {
      params: { period_days: periodDays }
    });
    return response.data;
  }
  
  // User endpoints
  async getUsers(orgId: string, params?: any) {
    const response = await this.axios.get(`/organizations/${orgId}/users`, { params });
    return response.data;
  }
  
  async getUser(orgId: string, userId: string) {
    const response = await this.axios.get(`/organizations/${orgId}/users/${userId}`);
    return response.data;
  }
  
  async createUser(orgId: string, data: any) {
    const response = await this.axios.post(`/organizations/${orgId}/users`, data);
    return response.data;
  }
  
  async updateUser(orgId: string, userId: string, data: any) {
    const response = await this.axios.put(`/organizations/${orgId}/users/${userId}`, data);
    return response.data;
  }
  
  async suspendUser(orgId: string, userId: string, reason: string) {
    const response = await this.axios.post(`/organizations/${orgId}/users/${userId}/suspend`, { reason });
    return response.data;
  }
  
  async inviteUser(orgId: string, data: any) {
    const response = await this.axios.post(`/organizations/${orgId}/users/invite`, data);
    return response.data;
  }
  
  // Audit logs
  async getAuditLogs(params?: any) {
    const response = await this.axios.get('/audit-logs', { params });
    return response.data;
  }
  
  // System stats
  async getSystemStats() {
    const response = await this.axios.get('/system/stats');
    return response.data;
  }
  
  async getSystemHealth() {
    const response = await this.axios.get('/system/health');
    return response.data;
  }
  
  // Generic request method
  async request(method: string, url: string, data?: any, config?: any) {
    const response = await this.axios.request({
      method,
      url,
      data,
      ...config
    });
    return response.data;
  }
}

export default new ApiService();