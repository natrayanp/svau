import type { ApiUser } from '$lib/types';

// Permission Structure Types
export interface PermissionDetail {
  id: number;
  action: string;
  display_name: string;
  description: string;
  power_level: number;
  default_roles: string[];
}

export interface CardDetail {
  id: number;
  key: string;
  name: string;
  description: string;
  display_order: number;
  menu_id: number;
  permissions: PermissionDetail[];
}

export interface MenuDetail {
  id: number;
  key: string;
  name: string;
  description: string;
  display_order: number;
  module_id: number;
  cards: CardDetail[];
}

export interface ModuleDetail {
  id: number;
  key: string;
  name: string;
  icon: string;
  color: string;
  description: string;
  display_order: number;
  menus: MenuDetail[];
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

// Selection State Types
export interface TreeSelectionState {
  expandedNodes: Set<number>;
  selectedPermissions: Map<number, Set<number>>;
  loading: boolean;
  searchTerm: string;
}

export interface PowerAnalysis {
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
}

// API Response Types
export interface UserPermissionsResponse {
  user_id: number;
  permission_ids: number[];
}

export interface PermissionValidationResponse {
  max_parent_power: number;
  validation_results: Array<{
    permission_id: number;
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
  name: string;
  description: string;
  permission_ids: number[];
  power_level: number;
}

export interface RolePermissionsResponse {
  role: string;
  permission_ids: number[];
  permission_count: number;
}

// UI State Types
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

// Role Management Types
export interface Role {
  name: string;
  description: string;
  user_count: number;
  permission_count: number;
  power_level: number;
  is_system_role: boolean;
}

export interface UserRoleAssignment {
  user_id: number;
  roles: string[];
  effective_permissions: number;
  combined_power_level: number;
}

// Power Level Constants
export const POWER_LEVELS = {
  LOW: { max: 30, color: 'green', label: 'Low', icon: '🟢' },
  MEDIUM: { max: 60, color: 'yellow', label: 'Medium', icon: '🟡' },
  HIGH: { max: 80, color: 'orange', label: 'High', icon: '🟠' },
  CRITICAL: { max: 100, color: 'red', label: 'Critical', icon: '🔴' }
} as const;

export type PowerLevel = keyof typeof POWER_LEVELS;