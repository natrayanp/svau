export interface User {
  user_id: string;                // Primary key
  uid: string;               // Unique external identifier
  email: string;             // User email
  display_name?: string;     // Optional display name
  org_id: string;   // Organization foreign key
  email_verified: boolean;   // Whether email is verified
  created_at: string;        // ISO timestamp
  updated_at: string;        // ISO timestamp
  roles: string[];           // List of role keys assigned to the user
  department?: string;    // Optional department
  location?: string;      // Optional location
  status?: 'AC' | 'IA' | 'SU' | 'EX' | 'CA' | 'DE';
  statusEffectiveFrom?: string; // ISO timestamp for status effective date
  statusEffectiveTo?: string;   // ISO timestamp for status end date
}

export type UserPaginationData = PaginatedData<User>;



// Derive from User, but allow extra fields
export type UserUpdatePayload = {
  user_id: string;                // Primary key
  uid: string;               // Unique external identifier
  email: string;             // User email
  display_name?: string;     // Optional display name
  org_id: string;            // Organization foreign key
  email_verified: boolean;   // Whether email is verified
  roles: string[];           // List of role keys assigned to the user
  department?: string;    // Optional department
  location?: string;      // Optional location
  status: string;        // status (e.g., active, inactive)
  statusEffectiveFrom?: string; // ISO timestamp for status effective date
  statusEffectiveTo?: string;   // ISO timestamp for status end date
};

export type ApiFetch = {
  offset: number;
  limit: number;
  filter?: any;
  sort?: any;
};

export type RolePermissions = {
  permissstruct_id: string;
  granted_action_key: string[];
};

export interface Role {
  role_id: string;
  display_name: string;
  description: string;
  is_system_role: boolean;
  is_template: boolean;
  template_id: string[];
  template_name: string[];
  permission_count: number;
  user_count: number;
  status: 'AC' | 'IA';  // Active or Inactive

  // ADD THESE FOR LOCAL OPERATIONS:
  permissions?: RolePermissions[]; // permission IDs for this role
  power_level?: number;   // calculated power level
  created_at?: string;    // ISO timestamp
  updated_at?: string;    // ISO timestamp
}



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


// ==================== API RESPONSE WRAPPERS ====================

export interface ApiResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
  operation_metadata?: {
    success: boolean;
    entity: string;
    operation: string;
    message: string;
    count: number;
    ids: string[];
  };
  error?: ApiError;
}

export interface ApiError {
  code: string;
  message: string;
  details?: any;
  timestamp: string;
}


export interface TableVersion {
  table_name: string;        // Name of the table
  table_version: number;     // Global version number for the table
  org_id: number;            // Organization identifier that owns the table
}

export interface PaginatedData<T> {
  items: T[];
  total: number;
  offset: number;
  limit: number;
  org_id: number;
  version: TableVersion[];
}


// ==================== SPECIFIC API RESPONSE TYPES ====================
export interface PermissionStructureResponse extends ApiResponse<PermissionStructure> { }
export interface RoleApiResponse extends ApiResponse<PaginatedData<Role>> { }
export interface UsersGetApiResponse extends ApiResponse<PaginatedData<User>> { }
export interface UsersDelApiResponse extends ApiResponse<String> { }
