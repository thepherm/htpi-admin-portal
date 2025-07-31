// Admin types
export interface AdminUser {
  id?: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'super_admin' | 'org_admin' | 'billing_admin' | 'clinical_admin' | 'support_admin' | 'read_only';
  permissions: string[];
  org_ids: string[];
  is_active: boolean;
  is_super_admin: boolean;
  last_login?: string;
  created_at?: string;
  updated_at?: string;
}

// Organization types
export interface Organization {
  id?: string;
  name: string;
  type: 'hospital' | 'clinic' | 'private_practice' | 'urgent_care' | 'specialty_center' | 'billing_company' | 'other';
  tax_id?: string;
  npi?: string;
  
  // Contact
  primary_contact_name: string;
  primary_contact_email: string;
  primary_contact_phone: string;
  
  // Address
  address_line1: string;
  address_line2?: string;
  city: string;
  state: string;
  zip_code: string;
  country?: string;
  
  // Billing
  billing_plan: 'free_trial' | 'basic' | 'professional' | 'enterprise' | 'custom';
  billing_contact_email?: string;
  stripe_customer_id?: string;
  trial_ends_at?: string;
  
  // Status
  status: 'active' | 'suspended' | 'inactive' | 'pending_approval' | 'trial';
  suspended_reason?: string;
  suspended_at?: string;
  
  // Settings
  settings?: Record<string, any>;
  features?: string[];
  
  // Limits
  max_users?: number;
  max_patients?: number;
  max_claims_per_month?: number;
  
  // Usage
  current_users?: number;
  current_patients?: number;
  claims_this_month?: number;
  
  created_at?: string;
  updated_at?: string;
}

// User types
export interface User {
  id?: string;
  org_id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: 'owner' | 'admin' | 'biller' | 'provider' | 'staff' | 'read_only';
  permissions: string[];
  status: 'active' | 'inactive' | 'suspended' | 'pending_verification';
  email_verified?: boolean;
  
  // Professional info
  npi?: string;
  license_number?: string;
  license_state?: string;
  specialty?: string;
  
  // Activity
  last_login?: string;
  last_activity?: string;
  login_count?: number;
  
  created_at?: string;
  updated_at?: string;
}

// Statistics types
export interface OrganizationStats {
  org_id: string;
  period_start: string;
  period_end: string;
  
  // User stats
  total_users: number;
  active_users: number;
  new_users: number;
  
  // Patient stats
  total_patients: number;
  new_patients: number;
  active_patients: number;
  
  // Claim stats
  total_claims: number;
  submitted_claims: number;
  accepted_claims: number;
  rejected_claims: number;
  pending_claims: number;
  
  // Financial stats
  total_billed: number;
  total_collected: number;
  outstanding_amount: number;
  
  // Performance
  avg_claim_processing_time: number;
  eligibility_check_count: number;
  era_received_count: number;
}

// Audit log types
export interface AuditLog {
  id?: string;
  admin_id: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  org_id?: string;
  
  // Details
  ip_address: string;
  user_agent: string;
  request_method: string;
  request_path: string;
  
  // Change tracking
  old_values?: Record<string, any>;
  new_values?: Record<string, any>;
  
  // Result
  success: boolean;
  error_message?: string;
  
  created_at: string;
}

// Auth types
export interface LoginCredentials {
  email: string;
  password: string;
}

export interface AuthResponse {
  token: string;
  admin: AdminUser;
}

// API response types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
  };
}

// Pagination
export interface PaginationParams {
  page?: number;
  limit?: number;
  sort?: string;
  order?: 'asc' | 'desc';
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  totalPages: number;
}

// Dashboard stats
export interface SystemStats {
  total_organizations: number;
  active_organizations: number;
  trial_organizations: number;
  suspended_organizations: number;
  
  total_users: number;
  active_users: number;
  
  total_claims_today: number;
  total_claims_month: number;
  
  system_health: 'healthy' | 'degraded' | 'down';
  active_services: number;
  total_services: number;
}