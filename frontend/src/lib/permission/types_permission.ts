import type { ApiUser } from '$lib/types';

// ==================== CORE DATABASE TYPES ====================

// Add ActionDetail interface
export interface ActionDetail {
  action_key: string;
  display_name: string;
  power_level: number;
  category?: string;
}

// Update existing interfaces to include allowed_actions
export interface PermissionDetail {
  id: string;
  permission_action: string;
  display_name: string;
  description: string;
  power_level: number;
  default_roles?: string[]; // Fixed in next step
  icon?: string;
  card_id?: string;
  card_name?: string;
  menu_name?: string;
  module_name?: string;
}

export interface CardDetail {
  id: string;
  key: string;
  name: string;
  description: string;
  display_order: number;
  menu_id: string;
  permissions: PermissionDetail[];
  allowed_actions?: ActionDetail[]; // ← ADD THIS
}

export interface MenuDetail {
  id: string;
  key: string;
  name: string;
  description: string;
  display_order: number;
  module_id: string;
  permissions: PermissionDetail[];
  cards: CardDetail[];
  allowed_actions?: ActionDetail[]; // ← ADD THIS
}

export interface ModuleDetail {
  id: string;
  key: string;
  name: string;
  icon: string;
  color: string;
  description: string;
  display_order: number;
  menus: MenuDetail[];
  allowed_actions?: ActionDetail[]; // ← ADD THIS
}

export interface PermissionStructure {
  modules: ModuleDetail[];
  metadata: {
    total_modules: number;
    total_menus: number;
    total_cards: number;
    total_permissions: number;
    last_updated: string;
  };
}

// ==================== ERROR TYPES ====================

export interface ApiError {
  code: string;
  message: string;
  details?: any;
  timestamp: string;
}

export interface PermissionConflict {
  permission_id: string;  // ← CHANGED TO STRING
  conflicting_with: string[];  // ← CHANGED TO STRING
  severity: 'low' | 'medium' | 'high';
  description: string;
}

// ==================== API RESPONSE WRAPPERS ====================

export interface ApiResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
  error?: ApiError;
}

export interface SuccessResponse {
  success: boolean;
  message: string;
  data?: any;
}

export interface BulkOperationResponse {
  success: boolean;
  message: string;
  data?: {
    results: Array<{
      user_id: number;
      success: boolean;
      message: string;
    }>;
    summary?: {
      total_roles?: number;
      successful?: number;
      failed?: number;
    };
  };
}

// ==================== REQUEST TYPES ====================

export interface PermissionValidationRequest {
  parent_permission_ids: string[];  // ← CHANGED TO STRING
  child_permission_ids: string[];   // ← CHANGED TO STRING
}

export interface RolePermissionsUpdateRequest {
  permission_ids: string[];  // ← CHANGED TO STRING
}

export interface UpdateUserRoleRequest {
  role: string;
}

export interface AssignUserToRoleRequest {
  role: string;
}

export interface BulkRoleUpdateRequest {
  updates: Array<{
    user_id: number;
    role_name: string;
    action: 'add' | 'remove';
  }>;
}

export interface CreateRoleRequest {
  name: string;
  description: string;
  permission_ids: string[];  // ← CHANGED TO STRING
}

export interface UserPermissionsRequest {
  permission_ids: string[];  // ← CHANGED TO STRING
}

export interface PermissionConflictCheckRequest {
  permission_ids: string[];  // ← CHANGED TO STRING
}

// ==================== RESPONSE TYPES ====================

export interface UserPermissionsResponse {
  user_id: number;
  permission_ids: string[];  // ← CHANGED TO STRING
}

export interface PermissionValidationResponse {
  max_parent_power: number;
  validation_results: Array<{
    permission_id: string;  // ← CHANGED TO STRING
    permission_name: string;
    power_level: number;
    is_allowed: boolean;
    reason: string;
  }>;
  all_allowed: boolean;
}

export interface AllowedPermissionsResponse {
  allowed_permissions: PermissionDetail[];
  max_parent_power: number;
}

export interface RoleTemplate {
  template_key: string;
  template_name: string;
  description: string;
  permission_ids: string[];
  power_level: number;
  is_system_template: boolean;
  permission_details?: Record<string, any>[];
  roles_using_count: number;
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
}


export interface RolePermissionsResponse {
  role: string;
  permission_ids: string[];  // ← CHANGED TO STRING
  permission_count: number;
}



export interface SystemRole {
  role_key: string;
  display_name: string;
  description: string;
  is_system_role: boolean;
  is_template: boolean;
  template_id: string[];
  template_name: string[];
  permission_count: number;
  user_count: number;

  // ADD THESE FOR LOCAL OPERATIONS:
  permissions?: string[]; // permission IDs for this role
  power_level?: number;   // calculated power level
  created_at?: string;    // ISO timestamp
  updated_at?: string;    // ISO timestamp
}

export interface SystemRolesResponse {
  roles: SystemRole[];
  summary: Record<string, any>;
}

export interface User {
  id: number;                // Primary key
  uid: string;               // Unique external identifier
  email: string;             // User email
  display_name?: string;     // Optional display name
  organization_id: number;   // Organization foreign key
  email_verified: boolean;   // Whether email is verified
  created_at: string;        // ISO timestamp
  updated_at: string;        // ISO timestamp
  roles: string[];           // List of role keys assigned to the user
}

export interface QuickAction {
  icon: string;
  label: string;
  href: string;
  description: string;
}

export interface QuickActionsResponse {
  actions: QuickAction[];
  total_actions: number;
}

export interface AuditLog {
  id: number;
  timestamp: string;
  user_id: number;
  username: string;
  action: string;
  target_type: string;
  target_id: number;
  target_name: string;
  details: {
    performed_by: string;
    performed_by_id: number;
  };
  ip_address: string;
}

export interface AuditLogsResponse {
  logs: AuditLog[];
  total_logs: number;
  filters_applied: {
    start_date?: string;
    end_date?: string;
    user_id?: number;
    role_name?: string;
    action_type?: string;
  };
}

export interface HealthCheck {
  status: 'healthy' | 'degraded' | 'unhealthy';
  services: {
    database: boolean;
    cache: boolean;
    messaging: boolean;
  };
  tables: {
    [key: string]: boolean;
  };
  metrics: {
    total_roles: number;
    total_users: number;
    total_permissions: number;
    active_sessions: number;
  };
  last_updated: string;
}

export interface UserWithDetails {
  user_id: number;
  username: string;
  email: string;
  joined_date: string;
  display_name?: string;
  role?: string;
}

export interface UsersByRoleResponse {
  role: string;
  users: UserWithDetails[];
  user_count: number;
}

export interface UserRoleAssignment {
  user_id: number;
  roles: string[];
  primary_role: string;
}

export interface RoleStatistics {
  total_users: number;
  role_distribution: Array<{
    role: string;
    user_count: number;
    percentage: number;
  }>;
  most_common_role: string;
  last_updated: string;
}

// ==================== POWER ANALYSIS TYPES ====================

export interface PowerAnalysis {
  role?: string;
  user_id?: number;
  permission_count: number;
  max_power: number;
  average_power: number;
  power_distribution: {
    low: number;
    medium: number;
    high: number;
    critical: number;
  };
  most_powerful_permissions: PermissionDetail[];
  analyzed_at?: string;
}

export interface SystemPowerAnalysis {
  overall_power_distribution: {
    low: number;
    medium: number;
    high: number;
    critical: number;
  };
  role_analysis: PowerAnalysis[];
  risk_assessment: {
    high_risk_roles: string[];
    potential_conflicts: string[];
    recommendations: string[];
  };
  system_metrics: {
    total_roles: number;
    total_users: number;
    avg_account_age_days?: number;
  };
}

// ==================== PERMISSION CONFLICT TYPES ====================

export interface PermissionConflictResponse {
  conflicts: PermissionConflict[];
  has_conflicts: boolean;
  recommendations: string[];
}

// ==================== BULK OPERATION TYPES ====================

export interface BulkPermissionResult {
  permission_id: string;  // ← CHANGED TO STRING
  success: boolean;
  message: string;
}

export interface BulkRolePermissionResult {
  role_name: string;
  success: boolean;
  message: string;
  permission_count?: number;
}

export interface BulkRoleUpdateResult {
  user_id: number;
  success: boolean;
  message: string;
}

export interface BulkPermissionsResponse {
  results: BulkPermissionResult[];
}

export interface BulkRolePermissionsResponse {
  results: BulkRolePermissionResult[];
  summary: {
    total_roles: number;
    successful: number;
    failed: number;
  };
}

export interface BulkUserRolesResponse {
  updated: number;
  failed: number;
  results: BulkRoleUpdateResult[];
}

// ==================== USER PERMISSION DETAILS ====================

export interface UserPermissionDetail {
  permission_id: string;  // ← CHANGED TO STRING
  display_name: string;
  description: string;
  permission_action: string;
  power_level: number;
}

export interface UserPermissionsDetailsResponse {
  user_id: number;
  permissions: UserPermissionDetail[];
  total_permissions: number;
}

// ==================== UI STATE TYPES ====================

export interface TreeSelectionState {
  expandedNodes: Set<string>;  // ← CHANGED TO STRING ONLY
  selectedPermissions: Map<string, Set<string>>;  // ← CHANGED TO STRING
  selectedModules: Set<string>;  // ← CHANGED TO STRING ONLY
  selectedMenus: Set<string>;  // ← CHANGED TO STRING ONLY
  loading: boolean;
  searchTerm: string;
}

export interface PermissionAccess {
  module: string;
  menu: string;
  card: string;
  actions: string[];
}

export interface UserWithPermissions extends ApiUser {
  permissions: PermissionAccess[];
  max_power: number;
  role_permissions: string[];
}

export interface Role {
  name: string;
  description: string;
  user_count: number;
  permission_count: number;
  power_level: number;
  is_system_role: boolean;
}

// ==================== CACHE TYPES ====================

export interface PermissionCache {
  structure: PermissionStructure | null;
  lastUpdated: string;
  ttl: number;
}

// ==================== SPECIFIC API RESPONSE TYPES ====================

export interface PermissionStructureResponse extends ApiResponse<PermissionStructure> {}
export interface SystemRolesApiResponse extends ApiResponse<SystemRolesResponse> {}
export interface UsersApiResponse extends ApiResponse<User[]> {}
export interface RoleTemplatesResponse extends ApiResponse<{ [key: string]: RoleTemplate }> {}
export interface RolePermissionsApiResponse extends ApiResponse<RolePermissionsResponse> {}
export interface UserPermissionsApiResponse extends ApiResponse<UserPermissionsResponse> {}
export interface UserPermissionsDetailsApiResponse extends ApiResponse<UserPermissionsDetailsResponse> {}
export interface UserRolesApiResponse extends ApiResponse<UserRoleAssignment> {}
export interface UsersByRoleApiResponse extends ApiResponse<UsersByRoleResponse> {}
export interface RoleStatisticsApiResponse extends ApiResponse<RoleStatistics> {}
export interface SystemPowerAnalysisApiResponse extends ApiResponse<SystemPowerAnalysis> {}
export interface HealthCheckApiResponse extends ApiResponse<HealthCheck> {}
export interface QuickActionsApiResponse extends ApiResponse<QuickActionsResponse> {}
export interface AuditLogsApiResponse extends ApiResponse<AuditLogsResponse> {}
export interface GrantPermissionsResponse extends ApiResponse<BulkPermissionsResponse> {}
export interface RevokePermissionsResponse extends ApiResponse<BulkPermissionsResponse> {}
export interface BulkRolePermissionsApiResponse extends ApiResponse<BulkRolePermissionsResponse> {}
export interface BulkUserRolesApiResponse extends ApiResponse<BulkUserRolesResponse> {}
export interface PermissionConflictApiResponse extends ApiResponse<PermissionConflictResponse> {}

// ==================== CONSTANTS ====================

export const POWER_LEVELS = {
  LOW: { max: 30, color: 'green', label: 'Low', icon: '🟢' },
  MEDIUM: { max: 60, color: 'yellow', label: 'Medium', icon: '🟡' },
  HIGH: { max: 80, color: 'orange', label: 'High', icon: '🟠' },
  CRITICAL: { max: 100, color: 'red', label: 'Critical', icon: '🔴' }
} as const;

export type PowerLevel = keyof typeof POWER_LEVELS;

// ==================== HELPER TYPES ====================

export type ApiResponseData<T> = T extends ApiResponse<infer U> ? U : never;
export type ExtractApiData<T> = T extends ApiResponse<infer U> ? U : T;