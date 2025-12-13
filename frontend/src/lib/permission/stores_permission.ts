import { writable, derived, get } from 'svelte/store';
import { permissionApi } from './api_permission';
import { roleApi } from './api_role';
import { PermissionUtils } from './utils_permission';
import type {
  PermissionStructure,
  TreeSelectionState,
  PowerAnalysis,
  RoleTemplate,
  UserPermissionsResponse,
  SystemRole,
  QuickAction,
  AuditLog,
  HealthCheck,
  UserRoleAssignment,
  UsersByRoleResponse,
  RoleStatistics,
  UserPermissionsDetailsResponse,
  PermissionConflictResponse,
  ApiError,
  User
} from './types_permission';

// --------------------
// Core Stores
// --------------------
export const permissionStructure = writable<PermissionStructure | null>(null);
export const userPermissions = writable<Set<string>>(new Set());
export const treeSelection = writable<TreeSelectionState>({
  expandedNodes: new Set<string>(),
  selectedPermissions: new Map<string, Set<string>>(),
  selectedModules: new Set<string>(),
  selectedMenus: new Set<string>(),
  loading: false,
  searchTerm: ''
});
export const roleTemplates = writable<Map<string, RoleTemplate>>(new Map());

// ENHANCED: Users store with role synchronization
export const users = writable<User[]>([]);

// ENHANCED: SystemRoles with permissions data
export const systemRoles = writable<SystemRole[]>([]);

export const systemStats = writable<RoleStatistics | null>(null);
export const quickActions = writable<QuickAction[]>([]);
export const auditLogs = writable<AuditLog[]>([]);
export const healthStatus = writable<HealthCheck | null>(null);
export const permissionConflicts = writable<PermissionConflictResponse>({
  conflicts: [],
  has_conflicts: false,
  recommendations: []
});

// --------------------
// Loading & Error States
// --------------------
export const loading = writable({
  structure: false,
  userPermissions: false,
  validation: false,
  saving: false,
  roles: false,
  stats: false,
  quickActions: false,
  systemRoles: false,
  auditLogs: false,
  health: false,
  conflictCheck: false,
  users: false
});

export const error = writable({
  structure: null as string | null,
  userPermissions: null as string | null,
  saving: null as string | null,
  roles: null as string | null,
  stats: null as string | null,
  quickActions: null as string | null,
  auditLogs: null as string | null,
  health: null as string | null,
  conflictCheck: null as string | null,
  users: null as string | null
});

// --------------------
// Cache & TTL Configuration
// --------------------
const TTL = 60000; // 1 minute
export const lastFetched = writable({
  structure: 0,
  roles: 0,
  stats: 0,
  quickActions: 0,
  userPermissions: 0,
  roleTemplates: 0
});

// Enhanced cache for permission structure with fallback
const permissionStructureCache = {
  data: null as PermissionStructure | null,
  timestamp: 0,
  ttl: 5 * 60 * 1000 // 5 minutes for structure (longer TTL)
};

// --------------------
// Derived Stores
// --------------------
export const userMaxPower = derived(
  [permissionStructure, userPermissions],
  ([$permissionStructure, $userPermissions]) =>
    $permissionStructure
      ? PermissionUtils.getMaxPower(
        Array.from($userPermissions),
        $permissionStructure
      )
      : 0
);

export const userPowerLevel = derived(
  userMaxPower,
  $userMaxPower => PermissionUtils.getPowerLevelLabel($userMaxPower)
);

export const selectedPermissionIds = derived(
  treeSelection,
  $treeSelection => PermissionUtils.getSelectedPermissionIds($treeSelection.selectedPermissions)
);

export const selectedPermissionsAnalysis = derived(
  [permissionStructure, selectedPermissionIds],
  ([$permissionStructure, $selectedPermissionIds]) =>
    $permissionStructure
      ? PermissionUtils.analyzePower($selectedPermissionIds, $permissionStructure)
      : null
);

// Real-time conflict detection
export const currentConflicts = derived(
  [permissionStructure, selectedPermissionIds],
  ([$permissionStructure, $selectedPermissionIds]) => {
    if (!$permissionStructure || $selectedPermissionIds.length === 0) {
      return { conflicts: [], has_conflicts: false, recommendations: [] };
    }
    return PermissionUtils.detectPermissionConflicts($selectedPermissionIds, $permissionStructure);
  }
);

// ENHANCED: Get role by key from store
export const getRoleByKey = (roleKey: string) => {
  const $systemRoles = get(systemRoles);
  return $systemRoles.find(role => role.role_id === roleKey);
};

// ENHANCED: Get role by ID from store
export const getRoleById = (roleId: string) => {
  const $systemRoles = get(systemRoles);
  return $systemRoles.find(role => role.role_id === roleId);
};

// ENHANCED: Get role permissions from store
export const getRolePermissions = (roleKey: string): string[] => {
  const role = getRoleByKey(roleKey);
  return role?.permissions || [];
};

// ENHANCED: Get role permissions as Set
export const getRolePermissionsSet = (roleKey: string): Set<string> => {
  const role = getRoleByKey(roleKey);
  return new Set(role?.permissions || []);
};

// --------------------
// Helper Functions
// --------------------
function getAllPermissionsInModule(module: any) {
  const permissions: any[] = [];
  module.menus.forEach((menu: any) => {
    if (menu.permissions) {
      permissions.push(...menu.permissions);
    }
    menu.cards.forEach((card: any) => {
      permissions.push(...card.permissions);
    });
  });
  return permissions;
}

function getAllPermissionsInMenu(menu: any) {
  const permissions: any[] = [];
  if (menu.permissions) {
    permissions.push(...menu.permissions);
  }
  menu.cards.forEach((card: any) => {
    permissions.push(...card.permissions);
  });
  return permissions;
}

// ENHANCED: Calculate role power level from permissions
function calculateRolePowerLevel(permissionIds: string[], permissionStructure: PermissionStructure | null): number {
  if (!permissionStructure) return 0;
  return PermissionUtils.getMaxPower(permissionIds, permissionStructure);
}

// ENHANCED: Update systemRoles store with new permissions
function updateSystemRolePermissions(roleKey: string, newPermissions: string[]): void {
  systemRoles.update(roles =>
    roles.map(role => {
      if (role.role_id === roleKey) {
        const $permissionStructure = get(permissionStructure);
        return {
          ...role,
          permissions: newPermissions,
          permission_count: newPermissions.length,
          power_level: calculateRolePowerLevel(newPermissions, $permissionStructure),
          updated_at: new Date().toISOString()
        };
      }
      return role;
    })
  );
}

// ENHANCED: Update user count for a role
function updateRoleUserCount(roleKey: string, change: number): void {
  systemRoles.update(roles =>
    roles.map(role => {
      if (role.role_id === roleKey) {
        return {
          ...role,
          user_count: Math.max(0, (role.user_count || 0) + change)
        };
      }
      return role;
    })
  );
}

// --------------------
// Enhanced Permission Actions with Store-First Approach
// --------------------
export const permissionActions = {
  // ✅ Load Permission Structure with TTL & Force Refresh
  async loadPermissionStructure(forceRefresh = false) {
    const now = Date.now();
    const stale = now - get(lastFetched).structure > TTL;

    // Check if already loading or data is fresh
    if (!forceRefresh && (get(loading).structure || (get(permissionStructure) && !stale))) {
      return;
    }

    // Check cache first (with longer TTL)
    if (!forceRefresh &&
      permissionStructureCache.data &&
      now - permissionStructureCache.timestamp < permissionStructureCache.ttl) {
      permissionStructure.set(permissionStructureCache.data);
      lastFetched.update(lf => ({ ...lf, structure: now }));
      return;
    }

    loading.update(l => ({ ...l, structure: true }));
    error.update(e => ({ ...e, structure: null }));

    try {
      const structure = await permissionApi.getPermissionStructure();
      permissionStructure.set(structure);

      // Update cache and timestamps
      permissionStructureCache.data = structure;
      permissionStructureCache.timestamp = now;
      lastFetched.update(lf => ({ ...lf, structure: now }));

      // Clear utility cache when structure changes
      PermissionUtils.clearCache();
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to load permission structure');
      error.update(e => ({ ...e, structure: errorMsg }));

      // Try to use cached data if available
      if (permissionStructureCache.data) {
        permissionStructure.set(permissionStructureCache.data);
        console.warn('Using cached permission structure due to API failure');
      }
    } finally {
      loading.update(l => ({ ...l, structure: false }));
    }
  },

  // ✅ Load System Roles with Enhanced Data
  async loadSystemRoles(force = false) {
    const now = Date.now();
    const stale = now - get(lastFetched).roles > TTL;

    if (!force && (get(loading).roles || (get(systemRoles).length > 0 && !stale))) {
      return;
    }

    loading.update(l => ({ ...l, roles: true }));
    error.update(e => ({ ...e, roles: null }));

    try {
      const roles = await permissionApi.getSystemRoles();

      // ENHANCED: Calculate power levels and enhance role data
      const $permissionStructure = get(permissionStructure);
      const enhancedRoles = roles.map(role => ({
        ...role,
        power_level: calculateRolePowerLevel(role.permissions || [], $permissionStructure),
        permissions: role.permissions || [] // Ensure permissions array exists
      }));

      systemRoles.set(enhancedRoles);
      lastFetched.update(lf => ({ ...lf, roles: now }));
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to load system roles');
      error.update(e => ({ ...e, roles: errorMsg }));
    } finally {
      loading.update(l => ({ ...l, roles: false }));
    }
  },

  // ✅ Load users with role synchronization
  async loadUsers(force = false) {
    const now = Date.now();
    const stale = now - get(lastFetched).users > TTL;

    if (!force && (get(loading).users || (get(users).length > 0 && !stale))) {
      return;
    }

    loading.update(l => ({ ...l, users: true }));
    error.update(e => ({ ...e, users: null }));

    try {
      const data = await permissionApi.getUsers();
      users.set(data);
      lastFetched.update(lf => ({ ...lf, users: now }));
    } catch (err: any) {
      error.update(e => ({ ...e, users: err.message }));
    } finally {
      loading.update(l => ({ ...l, users: false }));
    }
  },

  // ✅ Load Role Data from Store (No API Call Needed)
  async loadRoleData(roleKey: string) {
    let role = getRoleByKey(roleKey);

    // If role not found, ensure system roles are loaded
    if (!role) {
      await this.loadSystemRoles();
      role = getRoleByKey(roleKey);
    }

    if (!role) {
      throw new Error(`Role ${roleKey} not found in store`);
    }

    // Clear existing selections
    this.clearAllPermissions();

    // Select permissions from store data
    if (role.permissions && role.permissions.length > 0) {
      role.permissions.forEach(permId => {
        this.selectPermissionGlobally(permId);
      });
    }

    // Check for conflicts
    await this.checkPermissionConflicts();

    return role;
  },

  // ✅ Enhanced Role Permissions Update (Update Store + API)
  async updateRolePermissions(roleKey: string, permissionIds: string[]): Promise<{ success: boolean; message: string; conflicts?: PermissionConflictResponse }> {
    loading.update(l => ({ ...l, saving: true }));
    error.update(e => ({ ...e, saving: null }));

    try {
      // Check for conflicts before saving
      const conflicts = get(currentConflicts);
      if (conflicts.has_conflicts) {
        return {
          success: false,
          message: 'Cannot save due to permission conflicts',
          conflicts
        };
      }

      // Update local store FIRST for immediate UI update
      updateSystemRolePermissions(roleKey, permissionIds);

      // Then call API for persistence
      const result = await permissionApi.updateRolePermissions(roleKey, permissionIds);

      // Invalidate relevant caches after update
      this.invalidateStatsCache();

      return {
        success: true,
        message: result.message || 'Permissions saved successfully'
      };
    } catch (err) {
      // Rollback store update on error
      this.rollbackRoleUpdate(roleKey);
      const errorMsg = this.handleError(err, 'Failed to save permissions');
      error.update(e => ({ ...e, saving: errorMsg }));

      return {
        success: false,
        message: errorMsg
      };
    } finally {
      loading.update(l => ({ ...l, saving: false }));
    }
  },

  // ✅ NEW: Update role permissions in store only (for PermissionTree component)
  updateRolePermissionsInStore(roleId: string, permissions: string[]): void {
    updateSystemRolePermissions(roleId, permissions);
  },

  // ✅ NEW: Get current role permissions from store
  getCurrentRolePermissions(roleId: string): Set<string> {
    return getRolePermissionsSet(roleId);
  },

  // ✅ Create New Role (Store + API)
  async createRole(roleData: { name: string; description: string; permissions: string[] }): Promise<{ success: boolean; message: string; role?: SystemRole }> {
    loading.update(l => ({ ...l, saving: true }));

    try {
      // Call API to create role
      const result = await permissionApi.createRole({
        name: roleData.name,
        description: roleData.description,
        permission_ids: roleData.permissions
      });

      if (result.success) {
        // Add new role to store
        const newRole: SystemRole = {
          role_id: roleData.name.toLowerCase().replace(/\s+/g, '_'),
          display_name: roleData.name,
          description: roleData.description,
          is_system_role: false,
          permission_count: roleData.permissions.length,
          user_count: 0,
          organization_name: 'Custom',
          permissions: roleData.permissions,
          power_level: calculateRolePowerLevel(roleData.permissions, get(permissionStructure)),
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        };

        systemRoles.update(roles => [...roles, newRole]);
        this.invalidateStatsCache();

        return {
          success: true,
          message: result.message || 'Role created successfully',
          role: newRole
        };
      } else {
        return {
          success: false,
          message: result.message || 'Failed to create role'
        };
      }
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to create role');
      return {
        success: false,
        message: errorMsg
      };
    } finally {
      loading.update(l => ({ ...l, saving: false }));
    }
  },

  // ✅ Update user role (Store + API)
  async updateUserRole(userId: number, roles: string[]): Promise<{ success: boolean; message: string }> {
    loading.update(l => ({ ...l, saving: true }));

    try {
      // Update local store FIRST
      this.updateUserRolesInStore(userId, roles);

      // Update role user counts
      roles.forEach(roleKey => {
        updateRoleUserCount(roleKey, 1);
      });

      // Then call API (using first role for now)
      const result = await roleApi.updateUserRole(userId, roles[0]);

      // Invalidate caches after update
      this.invalidateStatsCache();

      return {
        success: true,
        message: result.message || 'User role updated successfully'
      };
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to update user role');
      return {
        success: false,
        message: errorMsg
      };
    } finally {
      loading.update(l => ({ ...l, saving: false }));
    }
  },

  // ✅ Load System Stats with TTL & Deduplication
  async loadSystemStats(force = false) {
    const now = Date.now();
    const stale = now - get(lastFetched).stats > TTL;

    if (!force && (get(loading).stats || (get(systemStats) && !stale))) {
      return;
    }

    loading.update(l => ({ ...l, stats: true }));
    error.update(e => ({ ...e, stats: null }));

    try {
      const stats = await roleApi.getSystemStats();
      systemStats.set(stats);
      lastFetched.update(lf => ({ ...lf, stats: now }));
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to load system stats');
      error.update(e => ({ ...e, stats: errorMsg }));
    } finally {
      loading.update(l => ({ ...l, stats: false }));
    }
  },

  // ✅ Load Quick Actions with TTL & Deduplication
  async loadQuickActions(force = false) {
    const now = Date.now();
    const stale = now - get(lastFetched).quickActions > TTL;

    if (!force && (get(loading).quickActions || (get(quickActions).length > 0 && !stale))) {
      return;
    }

    loading.update(l => ({ ...l, quickActions: true }));
    error.update(e => ({ ...e, quickActions: null }));

    try {
      const actions = await permissionApi.getQuickActions();
      quickActions.set(actions);
      lastFetched.update(lf => ({ ...lf, quickActions: now }));
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to load quick actions');
      error.update(e => ({ ...e, quickActions: errorMsg }));
    } finally {
      loading.update(l => ({ ...l, quickActions: false }));
    }
  },

  // ✅ Load Role Templates with TTL & Deduplication
  async loadRoleTemplates(force = false) {
    const now = Date.now();
    const stale = now - get(lastFetched).roleTemplates > TTL;

    if (!force && (get(roleTemplates).size > 0 && !stale)) {
      return;
    }

    try {
      const templates = await permissionApi.getRoleTemplates();
      roleTemplates.set(new Map(Object.entries(templates)));
      lastFetched.update(lf => ({ ...lf, roleTemplates: now }));
    } catch (err) {
      console.error('Failed to load role templates:', this.handleError(err));
    }
  },

  // ✅ Load User Permissions with TTL & Deduplication
  async loadUserPermissions(userId: number, force = false) {
    const now = Date.now();
    const stale = now - get(lastFetched).userPermissions > TTL;

    if (!force && (get(loading).userPermissions || (!stale && get(userPermissions).size > 0))) {
      return;
    }

    loading.update(l => ({ ...l, userPermissions: true }));
    error.update(e => ({ ...e, userPermissions: null }));

    try {
      const response = await permissionApi.getUserPermissions(userId);
      userPermissions.set(new Set(response.permission_ids));
      lastFetched.update(lf => ({ ...lf, userPermissions: now }));
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to load user permissions');
      error.update(e => ({ ...e, userPermissions: errorMsg }));
    } finally {
      loading.update(l => ({ ...l, userPermissions: false }));
    }
  },

  // ✅ Combined Dashboard Loader
  async loadDashboard(force = false) {
    await Promise.all([
      this.loadPermissionStructure(force),
      this.loadSystemRoles(force),
      this.loadSystemStats(force),
      this.loadQuickActions(force),
      this.loadRoleTemplates(force)
    ]);
  },

  // ✅ Helper: Update role in store
  updateRoleInStore(roleKey: string, updates: Partial<SystemRole>) {
    systemRoles.update(roles =>
      roles.map(role =>
        role.role_id === roleKey
          ? { ...role, ...updates }
          : role
      )
    );
  },

  // ✅ Helper: Update user roles in store
  updateUserRolesInStore(userId: number, roles: string[]) {
    users.update(userList =>
      userList.map(user =>
        user.id === userId
          ? { ...user, roles }
          : user
      )
    );
  },

  // ✅ Helper: Rollback role update on error
  rollbackRoleUpdate(roleKey: string) {
    // In a real app, you might want to reload the role data
    // For now, we'll just invalidate the cache to force reload
    this.invalidateRolesCache();
  },

  // ✅ Cache Invalidation Methods
  invalidateStructureCache() {
    permissionStructure.set(null);
    permissionStructureCache.data = null;
    permissionStructureCache.timestamp = 0;
    lastFetched.update(lf => ({ ...lf, structure: 0 }));
  },

  invalidateRolesCache() {
    systemRoles.set([]);
    lastFetched.update(lf => ({ ...lf, roles: 0 }));
  },

  invalidateUsersCache() {
    users.set([]);
    lastFetched.update(lf => ({ ...lf, users: 0 }));
  },

  invalidateStatsCache() {
    systemStats.set(null);
    lastFetched.update(lf => ({ ...lf, stats: 0 }));
  },

  invalidateQuickActionsCache() {
    quickActions.set([]);
    lastFetched.update(lf => ({ ...lf, quickActions: 0 }));
  },

  invalidateUserPermissionsCache() {
    userPermissions.set(new Set());
    lastFetched.update(lf => ({ ...lf, userPermissions: 0 }));
  },

  invalidateAllCache() {
    this.invalidateStructureCache();
    this.invalidateRolesCache();
    this.invalidateStatsCache();
    this.invalidateQuickActionsCache();
    this.invalidateUserPermissionsCache();
    roleTemplates.set(new Map());
    lastFetched.update(lf => ({ ...lf, roleTemplates: 0 }));
  },
  // ✅ Existing methods for role operations
  async loadRolePermissions(roleId: string) {
    try {
      // Use store-first approach instead of API call
      return await this.loadRoleData(roleId);
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to load role permissions');
      throw new Error(errorMsg);
    }
  },

  async loadUserRoles(userId: number): Promise<UserRoleAssignment> {
    try {
      return await roleApi.getUserRoles(userId);
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to load user roles');
      throw new Error(errorMsg);
    }
  },

  async loadUsersByRole(roleName: string): Promise<UsersByRoleResponse> {
    try {
      return await roleApi.getUsersByRole(roleName);
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to load users by role');
      throw new Error(errorMsg);
    }
  },

  async assignUserToRole(userId: number, roleName: string): Promise<{ success: boolean; message: string }> {
    try {
      const result = await roleApi.assignUserToRole(userId, roleName);

      // Invalidate caches after assignment
      this.invalidateStatsCache();

      return {
        success: true,
        message: result.message || 'User assigned to role successfully'
      };
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to assign user to role');
      return {
        success: false,
        message: errorMsg
      };
    }
  },

  async removeUserFromRole(userId: number, roleName: string): Promise<{ success: boolean; message: string }> {
    try {
      const result = await roleApi.removeUserFromRole(userId, roleName);

      // Invalidate caches after removal
      this.invalidateStatsCache();

      return {
        success: true,
        message: result.message || 'User removed from role successfully'
      };
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to remove user from role');
      return {
        success: false,
        message: errorMsg
      };
    }
  },

  async bulkUpdateUserRoles(updates: Array<{
    user_id: number;
    role_name: string;
    action: 'add' | 'remove';
  }>): Promise<{ success: boolean; message: string; results?: any }> {
    loading.update(l => ({ ...l, saving: true }));

    try {
      const result = await roleApi.bulkUpdateUserRoles(updates);

      // Invalidate caches after bulk update
      this.invalidateStatsCache();

      return {
        success: true,
        message: result.message || 'Bulk update completed successfully',
        results: result.results
      };
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to perform bulk update');
      return {
        success: false,
        message: errorMsg
      };
    } finally {
      loading.update(l => ({ ...l, saving: false }));
    }
  },

  async loadRoleStatistics(): Promise<RoleStatistics> {
    try {
      return await roleApi.getRoleStatistics();
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to load role statistics');
      throw new Error(errorMsg);
    }
  },

  async loadAuditLogs(filters?: any) {
    loading.update(l => ({ ...l, auditLogs: true }));
    error.update(e => ({ ...e, auditLogs: null }));

    try {
      const logs = await permissionApi.getPermissionAuditLogs(filters);
      auditLogs.set(logs);
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to load audit logs');
      error.update(e => ({ ...e, auditLogs: errorMsg }));
    } finally {
      loading.update(l => ({ ...l, auditLogs: false }));
    }
  },

  async loadHealthStatus() {
    loading.update(l => ({ ...l, health: true }));
    error.update(e => ({ ...e, health: null }));

    try {
      const health = await permissionApi.healthCheck();
      healthStatus.set(health);
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to load health status');
      error.update(e => ({ ...e, health: errorMsg }));
    } finally {
      loading.update(l => ({ ...l, health: false }));
    }
  },

  // Permission conflict checking
  async checkPermissionConflicts(): Promise<PermissionConflictResponse> {
    loading.update(l => ({ ...l, conflictCheck: true }));
    error.update(e => ({ ...e, conflictCheck: null }));

    try {
      const $permissionStructure = get(permissionStructure);
      const $selectedPermissionIds = get(selectedPermissionIds);

      if (!$permissionStructure) {
        return { conflicts: [], has_conflicts: false, recommendations: [] };
      }

      const conflicts = PermissionUtils.detectPermissionConflicts(
        $selectedPermissionIds,
        $permissionStructure
      );

      permissionConflicts.set(conflicts);
      return conflicts;
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to check permission conflicts');
      error.update(e => ({ ...e, conflictCheck: errorMsg }));
      return { conflicts: [], has_conflicts: false, recommendations: [] };
    } finally {
      loading.update(l => ({ ...l, conflictCheck: false }));
    }
  },

  // Tree selection actions
  toggleNodeExpansion(nodeId: string) {
    treeSelection.update(ts => {
      const newExpandedNodes = new Set(ts.expandedNodes);
      if (newExpandedNodes.has(nodeId)) {
        newExpandedNodes.delete(nodeId);
      } else {
        newExpandedNodes.add(nodeId);
      }
      return { ...ts, expandedNodes: newExpandedNodes };
    });
  },

  expandAllNodes() {
    const $permissionStructure = get(permissionStructure);
    if (!$permissionStructure) return;

    const allNodeIds = new Set<string>();

    $permissionStructure.modules.forEach(module => {
      allNodeIds.add(module.id);
      module.menus.forEach(menu => {
        allNodeIds.add(menu.id);
        menu.cards.forEach(card => {
          allNodeIds.add(card.id);
        });
      });
    });

    treeSelection.update(ts => ({ ...ts, expandedNodes: allNodeIds }));
  },

  collapseAllNodes() {
    treeSelection.update(ts => ({ ...ts, expandedNodes: new Set() }));
  },

  // Permission selection actions
  togglePermissionSelection(cardId: string, permissionId: string) {
    treeSelection.update(ts => {
      const newSelectedPermissions = new Map(ts.selectedPermissions);
      const cardPermissions = newSelectedPermissions.get(cardId) || new Set<string>();

      if (cardPermissions.has(permissionId)) {
        cardPermissions.delete(permissionId);
      } else {
        cardPermissions.add(permissionId);
      }

      newSelectedPermissions.set(cardId, cardPermissions);
      return { ...ts, selectedPermissions: newSelectedPermissions };
    });

    // Auto-check for conflicts
    this.checkPermissionConflicts();
  },

  selectAllCardPermissions(cardId: string, permissionIds: string[]) {
    treeSelection.update(ts => {
      const newSelectedPermissions = new Map(ts.selectedPermissions);
      newSelectedPermissions.set(cardId, new Set(permissionIds));
      return { ...ts, selectedPermissions: newSelectedPermissions };
    });

    this.checkPermissionConflicts();
  },

  clearCardPermissions(cardId: string) {
    treeSelection.update(ts => {
      const newSelectedPermissions = new Map(ts.selectedPermissions);
      newSelectedPermissions.delete(cardId);
      return { ...ts, selectedPermissions: newSelectedPermissions };
    });

    this.checkPermissionConflicts();
  },

  selectAllPermissions() {
    const $permissionStructure = get(permissionStructure);
    if (!$permissionStructure) return;

    const newSelectedPermissions = new Map<string, Set<string>>();

    $permissionStructure.modules.forEach(module => {
      module.menus.forEach(menu => {
        menu.cards.forEach(card => {
          const permissionIds = card.permissions.map(p => p.id);
          newSelectedPermissions.set(card.id, new Set(permissionIds));
        });
      });
    });

    treeSelection.update(ts => ({ ...ts, selectedPermissions: newSelectedPermissions }));
    this.checkPermissionConflicts();
  },

  clearAllPermissions() {
    treeSelection.update(ts => ({ ...ts, selectedPermissions: new Map() }));
    permissionConflicts.set({ conflicts: [], has_conflicts: false, recommendations: [] });
  },

  // Search
  setSearchTerm(term: string) {
    treeSelection.update(ts => ({ ...ts, searchTerm: term }));
  },

  // Validation
  async validatePermissions(parentPermissionIds: string[], childPermissionIds: string[]) {
    loading.update(l => ({ ...l, validation: true }));

    try {
      return await permissionApi.validateChildPermissions(parentPermissionIds, childPermissionIds);
    } finally {
      loading.update(l => ({ ...l, validation: false }));
    }
  },

  // Reset
  resetSelection() {
    treeSelection.set({
      expandedNodes: new Set(),
      selectedPermissions: new Map(),
      selectedModules: new Set(),
      selectedMenus: new Set(),
      loading: false,
      searchTerm: ''
    });
    permissionConflicts.set({ conflicts: [], has_conflicts: false, recommendations: [] });
  },

  // Global permission synchronization actions
  togglePermissionGlobally(permissionId: string) {
    const $selectedPermissionIds = get(selectedPermissionIds);
    const isSelected = $selectedPermissionIds.includes(permissionId);

    if (isSelected) {
      permissionActions.deselectPermissionEverywhere(permissionId);
    } else {
      permissionActions.selectPermissionEverywhere(permissionId);
    }
  },

  selectPermissionGlobally(permissionId: string) {
    permissionActions.selectPermissionEverywhere(permissionId);
  },

  selectPermissionEverywhere(permissionId: string) {
    const $permissionStructure = get(permissionStructure);
    if (!$permissionStructure) return;

    treeSelection.update(ts => {
      const newSelectedPermissions = new Map(ts.selectedPermissions);

      // Find and select the permission in all modules/menus/cards
      $permissionStructure.modules.forEach(module => {
        module.menus.forEach(menu => {
          // Check direct menu permissions
          if (menu.permissions) {
            menu.permissions.forEach(perm => {
              if (perm.id === permissionId) {
                const menuPermissionKey = `menu-${menu.id}`;
                const currentPermissions = newSelectedPermissions.get(menuPermissionKey) || new Set<string>();
                currentPermissions.add(permissionId);
                newSelectedPermissions.set(menuPermissionKey, currentPermissions);
              }
            });
          }

          // Check card permissions
          menu.cards.forEach(card => {
            card.permissions.forEach(perm => {
              if (perm.id === permissionId) {
                const currentCardPermissions = newSelectedPermissions.get(card.id) || new Set<string>();
                currentCardPermissions.add(permissionId);
                newSelectedPermissions.set(card.id, currentCardPermissions);
              }
            });
          });
        });
      });

      return { ...ts, selectedPermissions: newSelectedPermissions };
    });

    this.checkPermissionConflicts();
  },

  deselectPermissionEverywhere(permissionId: string) {
    const $permissionStructure = get(permissionStructure);
    if (!$permissionStructure) return;

    treeSelection.update(ts => {
      const newSelectedPermissions = new Map(ts.selectedPermissions);

      // Find and deselect the permission in all modules/menus/cards
      $permissionStructure.modules.forEach(module => {
        module.menus.forEach(menu => {
          // Check direct menu permissions
          if (menu.permissions) {
            const menuPermissionKey = `menu-${menu.id}`;
            const currentMenuPermissions = newSelectedPermissions.get(menuPermissionKey);
            if (currentMenuPermissions) {
              currentMenuPermissions.delete(permissionId);
              if (currentMenuPermissions.size === 0) {
                newSelectedPermissions.delete(menuPermissionKey);
              } else {
                newSelectedPermissions.set(menuPermissionKey, currentMenuPermissions);
              }
            }
          }

          // Check card permissions
          menu.cards.forEach(card => {
            const currentCardPermissions = newSelectedPermissions.get(card.id);
            if (currentCardPermissions) {
              currentCardPermissions.delete(permissionId);
              if (currentCardPermissions.size === 0) {
                newSelectedPermissions.delete(card.id);
              } else {
                newSelectedPermissions.set(card.id, currentCardPermissions);
              }
            }
          });
        });
      });

      return { ...ts, selectedPermissions: newSelectedPermissions };
    });

    this.checkPermissionConflicts();
  },

  // Enhanced selection actions
  toggleModuleSelectionEnhanced(module: any) {
    const $permissionStructure = get(permissionStructure);
    if (!$permissionStructure) return;

    const allPermissions = getAllPermissionsInModule(module);
    const isFullySelected = allPermissions.every(perm =>
      get(selectedPermissionIds).includes(perm.id)
    );

    if (isFullySelected) {
      allPermissions.forEach(perm => {
        permissionActions.deselectPermissionEverywhere(perm.id);
      });
    } else {
      allPermissions.forEach(perm => {
        permissionActions.selectPermissionEverywhere(perm.id);
      });
    }
  },

  toggleMenuSelectionEnhanced(menu: any) {
    const allPermissions = getAllPermissionsInMenu(menu);
    const isFullySelected = allPermissions.every(perm =>
      get(selectedPermissionIds).includes(perm.id)
    );

    if (isFullySelected) {
      allPermissions.forEach(perm => {
        permissionActions.deselectPermissionEverywhere(perm.id);
      });
    } else {
      allPermissions.forEach(perm => {
        permissionActions.selectPermissionEverywhere(perm.id);
      });
    }
  },

  toggleCardSelectionEnhanced(card: any) {
    const isFullySelected = card.permissions.every(perm =>
      get(selectedPermissionIds).includes(perm.id)
    );

    if (isFullySelected) {
      card.permissions.forEach((perm: any) => {
        permissionActions.deselectPermissionEverywhere(perm.id);
      });
    } else {
      card.permissions.forEach((perm: any) => {
        permissionActions.selectPermissionEverywhere(perm.id);
      });
    }
  },

  // Cache management
  clearCache() {
    permissionStructureCache.data = null;
    permissionStructureCache.timestamp = 0;
    PermissionUtils.clearCache();
  },

  getCacheStats() {
    const $lastFetched = get(lastFetched);
    const now = Date.now();

    return {
      structure: $lastFetched.structure > 0 ? now - $lastFetched.structure : 'never',
      roles: $lastFetched.roles > 0 ? now - $lastFetched.roles : 'never',
      stats: $lastFetched.stats > 0 ? now - $lastFetched.stats : 'never',
      quickActions: $lastFetched.quickActions > 0 ? now - $lastFetched.quickActions : 'never',
      userPermissions: $lastFetched.userPermissions > 0 ? now - $lastFetched.userPermissions : 'never',
      structureCache: permissionStructureCache.data ? 'valid' : 'empty',
      ...PermissionUtils.getCacheStats()
    };
  },

  // Enhanced error handling
  handleError(err: unknown, defaultMessage: string): string {
    if (err instanceof Error) {
      return err.message;
    }

    if (typeof err === 'object' && err !== null && 'message' in err) {
      return (err as any).message;
    }

    return defaultMessage;
  },

  // Clear errors
  clearErrors() {
    error.set({
      structure: null,
      userPermissions: null,
      saving: null,
      roles: null,
      stats: null,
      quickActions: null,
      auditLogs: null,
      health: null,
      conflictCheck: null,
      users: null
    });
  }
};

// ✅ Initialize with single dashboard call (instead of multiple separate calls)
permissionActions.loadDashboard();