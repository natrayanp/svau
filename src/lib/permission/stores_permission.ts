import { writable, derived, get } from 'svelte/store';
import { permissionApi } from './api_permission';
import { PermissionUtils } from './utils_permission';
import type {
  PermissionStructure,
  TreeSelectionState,
  PowerAnalysis,
  RoleTemplate,
  UserPermissionsResponse,
  PermissionDetail
} from './types_permission';

// Mock permission structure for immediate testing
const mockPermissionStructure: PermissionStructure = {
  modules: [
    {
      id: 1,
      key: 'flashcards',
      name: 'Flashcards',
      icon: '📚',
      color: 'blue',
      description: 'Flashcard management system',
      display_order: 1,
      menus: [
        {
          id: 101,
          key: 'dashboard',
          name: 'Dashboard',
          description: 'Overview and analytics',
          display_order: 1,
          module_id: 1,
          cards: [
            {
              id: 1001,
              key: 'overview',
              name: 'Overview',
              description: 'Main dashboard overview',
              display_order: 1,
              menu_id: 101,
              permissions: [
                {
                  id: 5001,
                  action: 'view',
                  display_name: 'View',
                  description: 'View overview dashboard',
                  power_level: 10,
                  default_roles: ['basic', 'creator', 'moderator', 'admin']
                },
                {
                  id: 5002,
                  action: 'analytics',
                  display_name: 'Analytics',
                  description: 'Access analytics data',
                  power_level: 15,
                  default_roles: ['creator', 'moderator', 'admin']
                },
                {
                  id: 5003,
                  action: 'export',
                  display_name: 'Export',
                  description: 'Export dashboard data',
                  power_level: 20,
                  default_roles: ['creator', 'moderator', 'admin']
                }
              ]
            },
            {
              id: 1002,
              key: 'statistics',
              name: 'Statistics',
              description: 'Usage statistics and reports',
              display_order: 2,
              menu_id: 101,
              permissions: [
                {
                  id: 5004,
                  action: 'view',
                  display_name: 'View',
                  description: 'View statistics',
                  power_level: 10,
                  default_roles: ['basic', 'creator', 'moderator', 'admin']
                },
                {
                  id: 5005,
                  action: 'export',
                  display_name: 'Export',
                  description: 'Export statistics data',
                  power_level: 20,
                  default_roles: ['creator', 'moderator', 'admin']
                }
              ]
            }
          ]
        },
        {
          id: 102,
          key: 'cards',
          name: 'Cards',
          description: 'Card management',
          display_order: 2,
          module_id: 1,
          cards: [
            {
              id: 1003,
              key: 'card_list',
              name: 'Card List',
              description: 'List and manage all cards',
              display_order: 1,
              menu_id: 102,
              permissions: [
                {
                  id: 5006,
                  action: 'view',
                  display_name: 'View',
                  description: 'View card list',
                  power_level: 10,
                  default_roles: ['basic', 'creator', 'moderator', 'admin']
                },
                {
                  id: 5007,
                  action: 'create',
                  display_name: 'Create',
                  description: 'Create new cards',
                  power_level: 25,
                  default_roles: ['creator', 'moderator', 'admin']
                },
                {
                  id: 5008,
                  action: 'edit',
                  display_name: 'Edit',
                  description: 'Edit existing cards',
                  power_level: 30,
                  default_roles: ['creator', 'moderator', 'admin']
                },
                {
                  id: 5009,
                  action: 'delete',
                  display_name: 'Delete',
                  description: 'Delete cards',
                  power_level: 60,
                  default_roles: ['moderator', 'admin']
                },
                {
                  id: 5010,
                  action: 'import',
                  display_name: 'Import',
                  description: 'Import cards',
                  power_level: 35,
                  default_roles: ['moderator', 'admin']
                },
                {
                  id: 5011,
                  action: 'export',
                  display_name: 'Export',
                  description: 'Export cards',
                  power_level: 20,
                  default_roles: ['creator', 'moderator', 'admin']
                }
              ]
            }
          ]
        }
      ]
    },
    {
      id: 2,
      key: 'portfolio',
      name: 'Portfolio',
      icon: '💼',
      color: 'green',
      description: 'Project portfolio management',
      display_order: 2,
      menus: [
        {
          id: 201,
          key: 'projects',
          name: 'Projects',
          description: 'Project management',
          display_order: 1,
          module_id: 2,
          cards: [
            {
              id: 2001,
              key: 'project_list',
              name: 'Project List',
              description: 'List and manage projects',
              display_order: 1,
              menu_id: 201,
              permissions: [
                {
                  id: 6001,
                  action: 'view',
                  display_name: 'View',
                  description: 'View project list',
                  power_level: 10,
                  default_roles: ['basic', 'creator', 'moderator', 'admin']
                },
                {
                  id: 6002,
                  action: 'create',
                  display_name: 'Create',
                  description: 'Create new projects',
                  power_level: 25,
                  default_roles: ['creator', 'moderator', 'admin']
                },
                {
                  id: 6003,
                  action: 'edit',
                  display_name: 'Edit',
                  description: 'Edit projects',
                  power_level: 30,
                  default_roles: ['creator', 'moderator', 'admin']
                },
                {
                  id: 6004,
                  action: 'delete',
                  display_name: 'Delete',
                  description: 'Delete projects',
                  power_level: 60,
                  default_roles: ['moderator', 'admin']
                },
                {
                  id: 6005,
                  action: 'publish',
                  display_name: 'Publish',
                  description: 'Publish projects',
                  power_level: 40,
                  default_roles: ['creator', 'moderator', 'admin']
                }
              ]
            }
          ]
        }
      ]
    },
    {
      id: 3,
      key: 'users',
      name: 'Users',
      icon: '👥',
      color: 'purple',
      description: 'User management system',
      display_order: 3,
      menus: [
        {
          id: 301,
          key: 'user_management',
          name: 'User Management',
          description: 'Manage users and permissions',
          display_order: 1,
          module_id: 3,
          cards: [
            {
              id: 3001,
              key: 'user_list',
              name: 'User List',
              description: 'List and manage users',
              display_order: 1,
              menu_id: 301,
              permissions: [
                {
                  id: 8001,
                  action: 'view',
                  display_name: 'View Users',
                  description: 'View user list and profiles',
                  power_level: 70,
                  default_roles: ['moderator', 'admin']
                },
                {
                  id: 8002,
                  action: 'manage',
                  display_name: 'Manage Users',
                  description: 'Manage user roles and permissions',
                  power_level: 80,
                  default_roles: ['admin']
                },
                {
                  id: 8003,
                  action: 'admin',
                  display_name: 'Admin Access',
                  description: 'Full administrative access',
                  power_level: 90,
                  default_roles: ['admin']
                }
              ]
            }
          ]
        }
      ]
    },
    {
      id: 4,
      key: 'admin',
      name: 'Admin',
      icon: '⚙️',
      color: 'orange',
      description: 'Administration panel',
      display_order: 4,
      menus: [
        {
          id: 401,
          key: 'system',
          name: 'System',
          description: 'System administration',
          display_order: 1,
          module_id: 4,
          cards: [
            {
              id: 4001,
              key: 'system_settings',
              name: 'System Settings',
              description: 'Manage system settings',
              display_order: 1,
              menu_id: 401,
              permissions: [
                {
                  id: 9001,
                  action: 'access',
                  display_name: 'Admin Access',
                  description: 'Access administration panel',
                  power_level: 100,
                  default_roles: ['admin']
                }
              ]
            }
          ]
        }
      ]
    }
  ],
  metadata: {
    total_modules: 4,
    total_menus: 6,
    total_cards: 7,
    total_permissions: 23,
    last_updated: new Date().toISOString()
  }
};

// Global permission state using traditional Svelte stores
export const permissionStructure = writable<PermissionStructure | null>(mockPermissionStructure);
export const userPermissions = writable<Set<number>>(new Set());
export const treeSelection = writable<TreeSelectionState>({
  expandedNodes: new Set<number>(),
  selectedPermissions: new Map<number, Set<number>>(),
  loading: false,
  searchTerm: ''
});
export const roleTemplates = writable<Map<string, RoleTemplate>>(new Map());

// Loading states - set structure to false since we're using mock data
export const loading = writable({
  structure: false,
  userPermissions: false,
  validation: false
});

// Error states
export const error = writable({
  structure: null as string | null,
  userPermissions: null as string | null
});

// Derived state
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

// Actions
export const permissionActions = {
  async loadPermissionStructure() {
    // Use mock data immediately, no API call needed for testing
    permissionStructure.set(mockPermissionStructure);
  },

  async loadUserPermissions(userId: number) {
    loading.update(l => ({ ...l, userPermissions: true }));
    error.update(e => ({ ...e, userPermissions: null }));
    
    try {
      const response = await permissionApi.getUserPermissions(userId);
      userPermissions.set(new Set(response.permission_ids));
    } catch (err) {
      error.update(e => ({ ...e, userPermissions: err instanceof Error ? err.message : 'Failed to load user permissions' }));
    } finally {
      loading.update(l => ({ ...l, userPermissions: false }));
    }
  },

  async loadRoleTemplates() {
    try {
      const templates = await permissionApi.getRoleTemplates();
      roleTemplates.set(new Map(Object.entries(templates)));
    } catch (err) {
      console.error('Failed to load role templates:', err);
    }
  },

  // Tree selection actions
  toggleNodeExpansion(nodeId: number) {
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
    
    const allNodeIds = new Set<number>();
    
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
  togglePermissionSelection(cardId: number, permissionId: number) {
    treeSelection.update(ts => {
      const newSelectedPermissions = new Map(ts.selectedPermissions);
      const cardPermissions = newSelectedPermissions.get(cardId) || new Set();
      
      if (cardPermissions.has(permissionId)) {
        cardPermissions.delete(permissionId);
      } else {
        cardPermissions.add(permissionId);
      }
      
      newSelectedPermissions.set(cardId, cardPermissions);
      return { ...ts, selectedPermissions: newSelectedPermissions };
    });
  },

  selectAllCardPermissions(cardId: number, permissionIds: number[]) {
    treeSelection.update(ts => {
      const newSelectedPermissions = new Map(ts.selectedPermissions);
      newSelectedPermissions.set(cardId, new Set(permissionIds));
      return { ...ts, selectedPermissions: newSelectedPermissions };
    });
  },

  clearCardPermissions(cardId: number) {
    treeSelection.update(ts => {
      const newSelectedPermissions = new Map(ts.selectedPermissions);
      newSelectedPermissions.delete(cardId);
      return { ...ts, selectedPermissions: newSelectedPermissions };
    });
  },

  selectAllPermissions() {
    const $permissionStructure = get(permissionStructure);
    if (!$permissionStructure) return;
    
    const newSelectedPermissions = new Map<number, Set<number>>();
    
    $permissionStructure.modules.forEach(module => {
      module.menus.forEach(menu => {
        menu.cards.forEach(card => {
          const permissionIds = card.permissions.map(p => p.id);
          newSelectedPermissions.set(card.id, new Set(permissionIds));
        });
      });
    });
    
    treeSelection.update(ts => ({ ...ts, selectedPermissions: newSelectedPermissions }));
  },

  clearAllPermissions() {
    treeSelection.update(ts => ({ ...ts, selectedPermissions: new Map() }));
  },

  // Search
  setSearchTerm(term: string) {
    treeSelection.update(ts => ({ ...ts, searchTerm: term }));
  },

  // Validation
  async validatePermissions(parentPermissionIds: number[], childPermissionIds: number[]) {
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
      loading: false,
      searchTerm: ''
    });
  }
};

// Initialize with mock data immediately
permissionActions.loadPermissionStructure();
permissionActions.loadRoleTemplates();