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
  ApiError
} from './types_permission';

// Enhanced stores with string IDs
export const permissionStructure = writable<PermissionStructure | null>(null);
export const userPermissions = writable<Set<string>>(new Set());  // ← CHANGED TO STRING
export const treeSelection = writable<TreeSelectionState>({
  expandedNodes: new Set<string>(),  // ← CHANGED TO STRING ONLY
  selectedPermissions: new Map<string, Set<string>>(),  // ← CHANGED TO STRING
  selectedModules: new Set<string>(),  // ← CHANGED TO STRING ONLY
  selectedMenus: new Set<string>(),  // ← CHANGED TO STRING ONLY
  loading: false,
  searchTerm: ''
});
export const roleTemplates = writable<Map<string, RoleTemplate>>(new Map());
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

// Enhanced loading states with cache tracking
export const loading = writable({
  structure: false,
  userPermissions: false,
  validation: false,
  saving: false,
  roles: false,
  stats: false,
  quickActions: false,
  auditLogs: false,
  health: false,
  conflictCheck: false
});

// Enhanced error states with recovery
export const error = writable({
  structure: null as string | null,
  userPermissions: null as string | null,
  saving: null as string | null,
  roles: null as string | null,
  stats: null as string | null,
  quickActions: null as string | null,
  auditLogs: null as string | null,
  health: null as string | null,
  conflictCheck: null as string | null
});

// Cache management
const cache = {
  permissionStructure: {
    data: null as PermissionStructure | null,
    timestamp: 0,
    ttl: 5 * 60 * 1000 // 5 minutes
  }
};

// Derived state with caching
export const userMaxPower = derived(
  [permissionStructure, userPermissions],
  ([$permissionStructure, $userPermissions]) =>
    $permissionStructure 
      ? PermissionUtils.getMaxPower(
          Array.from($userPermissions),  // Already string IDs
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

// Helper functions
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

// Enhanced permission actions with caching and error recovery
export const permissionActions = {
  async loadPermissionStructure(forceRefresh = false) {
    const now = Date.now();
    
    // Check cache first
    if (!forceRefresh && 
        cache.permissionStructure.data && 
        now - cache.permissionStructure.timestamp < cache.permissionStructure.ttl) {
      permissionStructure.set(cache.permissionStructure.data);
      return;
    }

    loading.update(l => ({ ...l, structure: true }));
    error.update(e => ({ ...e, structure: null }));
    
    try {
      const structure = await permissionApi.getPermissionStructure();
      permissionStructure.set(structure);
      
      // Update cache
      cache.permissionStructure.data = structure;
      cache.permissionStructure.timestamp = now;
      
      // Clear utility cache when structure changes
      PermissionUtils.clearCache();
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to load permission structure');
      error.update(e => ({ ...e, structure: errorMsg }));
      
      // Try to use cached data if available
      if (cache.permissionStructure.data) {
        permissionStructure.set(cache.permissionStructure.data);
        console.warn('Using cached permission structure due to API failure');
      }
    } finally {
      loading.update(l => ({ ...l, structure: false }));
    }
  },

  async loadSystemRoles() {
    loading.update(l => ({ ...l, roles: true }));
    error.update(e => ({ ...e, roles: null }));
    
    try {
      const roles = await permissionApi.getSystemRoles();
      systemRoles.set(roles);
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to load system roles');
      error.update(e => ({ ...e, roles: errorMsg }));
    } finally {
      loading.update(l => ({ ...l, roles: false }));
    }
  },

  async loadSystemStats() {
    loading.update(l => ({ ...l, stats: true }));
    error.update(e => ({ ...e, stats: null }));
    
    try {
      const stats = await roleApi.getSystemStats();
      systemStats.set(stats);
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to load system stats');
      error.update(e => ({ ...e, stats: errorMsg }));
    } finally {
      loading.update(l => ({ ...l, stats: false }));
    }
  },

  async loadQuickActions() {
    loading.update(l => ({ ...l, quickActions: true }));
    error.update(e => ({ ...e, quickActions: null }));
    
    try {
      const actions = await permissionApi.getQuickActions();
      quickActions.set(actions);
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to load quick actions');
      error.update(e => ({ ...e, quickActions: errorMsg }));
    } finally {
      loading.update(l => ({ ...l, quickActions: false }));
    }
  },

  async loadRolePermissions(roleId: string) {
    try {
      const response = await permissionApi.getRolePermissions(roleId);
      
      // Clear existing selections
      permissionActions.clearAllPermissions();
      
      // Select permissions from backend (already string IDs)
      response.permission_ids.forEach(permId => {
        permissionActions.selectPermissionGlobally(permId);
      });
      
      // Check for conflicts
      await this.checkPermissionConflicts();
      
      return response.permission_ids;
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to load role permissions');
      throw new Error(errorMsg);
    }
  },

  async updateRolePermissions(roleId: string): Promise<{ success: boolean; message: string; conflicts?: PermissionConflictResponse }> {
    loading.update(l => ({ ...l, saving: true }));
    error.update(e => ({ ...e, saving: null }));
    
    try {
      const permissionIds = get(selectedPermissionIds);
      
      // Check for conflicts before saving
      const conflicts = get(currentConflicts);
      if (conflicts.has_conflicts) {
        return {
          success: false,
          message: 'Cannot save due to permission conflicts',
          conflicts
        };
      }
      
      const result = await permissionApi.updateRolePermissions(roleId, permissionIds);
      
      return {
        success: true,
        message: result.message || 'Permissions saved successfully'
      };
    } catch (err) {
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

  async loadUserPermissions(userId: number) {
    loading.update(l => ({ ...l, userPermissions: true }));
    error.update(e => ({ ...e, userPermissions: null }));
    
    try {
      const response = await permissionApi.getUserPermissions(userId);
      userPermissions.set(new Set(response.permission_ids));  // Already string IDs
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to load user permissions');
      error.update(e => ({ ...e, userPermissions: errorMsg }));
    } finally {
      loading.update(l => ({ ...l, userPermissions: false }));
    }
  },

  async loadRoleTemplates() {
    try {
      console.log('inside load role templates');
      const templates = await permissionApi.getRoleTemplates();
      
      console.log(templates);
      roleTemplates.set(new Map(Object.entries(templates)));
    } catch (err) {
      console.error('Failed to load role templates:', this.handleError(err));
    }
  },

  // Enhanced role assignment with conflict checking
  async loadUserRoles(userId: number): Promise<UserRoleAssignment> {
    try {
      return await roleApi.getUserRoles(userId);
    } catch (err) {
      const errorMsg = this.handleError(err, 'Failed to load user roles');
      throw new Error(errorMsg);
    }
  },

  async updateUserRole(userId: number, role: string): Promise<{ success: boolean; message: string }> {
    loading.update(l => ({ ...l, saving: true }));
    
    try {
      const result = await roleApi.updateUserRole(userId, role);
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
  togglePermissionSelection(cardId: string, permissionId: string) {  // ← CHANGED PARAM TYPES
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

  selectAllCardPermissions(cardId: string, permissionIds: string[]) {  // ← CHANGED PARAM TYPES
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
  async validatePermissions(parentPermissionIds: string[], childPermissionIds: string[]) {  // ← CHANGED PARAM TYPES
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
  togglePermissionGlobally(permissionId: string) {  // ← CHANGED PARAM TYPE
    const $selectedPermissionIds = get(selectedPermissionIds);
    const isSelected = $selectedPermissionIds.includes(permissionId);
    
    if (isSelected) {
      permissionActions.deselectPermissionEverywhere(permissionId);
    } else {
      permissionActions.selectPermissionEverywhere(permissionId);
    }
  },

  selectPermissionGlobally(permissionId: string) {  // ← CHANGED PARAM TYPE
    permissionActions.selectPermissionEverywhere(permissionId);
  },

  selectPermissionEverywhere(permissionId: string) {  // ← CHANGED PARAM TYPE
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

  deselectPermissionEverywhere(permissionId: string) {  // ← CHANGED PARAM TYPE
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
    cache.permissionStructure.data = null;
    cache.permissionStructure.timestamp = 0;
    PermissionUtils.clearCache();
  },

  getCacheStats() {
    return {
      ...PermissionUtils.getCacheStats(),
      structureCache: cache.permissionStructure.data ? 'valid' : 'empty'
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
      conflictCheck: null
    });
  }
};

// Initialize with API data
permissionActions.loadPermissionStructure();
permissionActions.loadRoleTemplates();
permissionActions.loadSystemRoles();
permissionActions.loadSystemStats();
permissionActions.loadQuickActions();