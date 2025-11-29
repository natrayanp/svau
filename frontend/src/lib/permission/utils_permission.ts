import type { 
  PermissionDetail, 
  PermissionStructure,
  PowerLevel,
  POWER_LEVELS,
  ModuleDetail,
  MenuDetail,
  CardDetail,
  PermissionConflict,
  PermissionConflictResponse
} from './types_permission';

export class PermissionUtils {
  private static permissionCache: Map<string, PermissionDetail> = new Map();  // ← CHANGED TO STRING
  private static conflictCache: Map<string, PermissionConflict[]> = new Map();

  // Power Level Classification
  static getPowerLevelColor(powerLevel: number): string {
    if (powerLevel <= 30) return 'green';
    if (powerLevel <= 60) return 'yellow';
    if (powerLevel <= 80) return 'orange';
    return 'red';
  }

  static getPowerLevelLabel(powerLevel: number): string {
    if (powerLevel <= 30) return 'Low';
    if (powerLevel <= 60) return 'Medium';
    if (powerLevel <= 80) return 'High';
    return 'Critical';
  }

  static getPowerLevelIcon(powerLevel: number): string {
    if (powerLevel <= 30) return '🟢';
    if (powerLevel <= 60) return '🟡';
    if (powerLevel <= 80) return '🟠';
    return '🔴';
  }

  static getPowerLevelRange(powerLevel: number): PowerLevel {
    if (powerLevel <= 30) return 'LOW';
    if (powerLevel <= 60) return 'MEDIUM';
    if (powerLevel <= 80) return 'HIGH';
    return 'CRITICAL';
  }

  // Permission Access Checking - UPDATED for string IDs
  static canAccess(
    userPermissions: Set<string>,  // ← CHANGED TO STRING
    permissionStructure: PermissionStructure,
    moduleKey: string,
    menuKey: string,
    cardKey: string,
    action: string
  ): boolean {
    for (const module of permissionStructure.modules) {
      if (module.id === moduleKey) {
        for (const menu of module.menus) {
          if (menu.id === menuKey) {
            // Check direct menu permissions first
            if (menu.permissions) {
              for (const permission of menu.permissions) {
                if (permission.permission_action === action) {
                  return userPermissions.has(permission.id);  // String ID comparison
                }
              }
            }
            
            // Check card permissions
            for (const card of menu.cards) {
              if (card.id === cardKey) {
                for (const permission of card.permissions) {
                  if (permission.permission_action === action) {
                    return userPermissions.has(permission.id);  // String ID comparison
                  }
                }
              }
            }
          }
        }
      }
    }
    return false;
  }

  // Power Constraint Calculations
  static getMaxPower(permissionIds: string[], permissionStructure: PermissionStructure): number {  // ← CHANGED TO STRING
    let maxPower = 0;
    
    for (const permissionId of permissionIds) {
      const permission = this.findPermissionById(permissionId, permissionStructure);
      if (permission && permission.power_level > maxPower) {
        maxPower = permission.power_level;
      }
    }
    
    return maxPower;
  }

  static getAllowedPermissions(
    parentPermissionIds: string[],  // ← CHANGED TO STRING
    availablePermissions: PermissionDetail[],
    permissionStructure: PermissionStructure
  ): PermissionDetail[] {
    const maxParentPower = this.getMaxPower(parentPermissionIds, permissionStructure);
    
    return availablePermissions.filter(permission => 
      permission.power_level <= maxParentPower
    );
  }

  // UPDATED: Find permission with string ID
  static findPermissionById(permissionId: string, permissionStructure: PermissionStructure): PermissionDetail | null {  // ← CHANGED TO STRING
    // Check cache first
    if (this.permissionCache.has(permissionId)) {
      return this.permissionCache.get(permissionId) || null;
    }

    for (const module of permissionStructure.modules) {
      for (const menu of module.menus) {
        // Check direct menu permissions
        if (menu.permissions) {
          for (const permission of menu.permissions) {
            if (permission.id === permissionId) {
              this.permissionCache.set(permissionId, permission);
              return permission;
            }
          }
        }
        
        // Check card permissions
        for (const card of menu.cards) {
          for (const permission of card.permissions) {
            if (permission.id === permissionId) {
              this.permissionCache.set(permissionId, permission);
              return permission;
            }
          }
        }
      }
    }
    return null;
  }

  // Permission Conflict Detection with string IDs
  static detectPermissionConflicts(permissionIds: string[], permissionStructure: PermissionStructure): PermissionConflictResponse {  // ← CHANGED TO STRING
    const cacheKey = permissionIds.sort().join('-');
    
    // Check conflict cache
    if (this.conflictCache.has(cacheKey)) {
      const conflicts = this.conflictCache.get(cacheKey) || [];
      return {
        conflicts,
        has_conflicts: conflicts.length > 0,
        recommendations: this.generateConflictRecommendations(conflicts)
      };
    }

    const conflicts: PermissionConflict[] = [];
    const permissions = permissionIds.map(id => 
      this.findPermissionById(id, permissionStructure)
    ).filter(Boolean) as PermissionDetail[];

    // Check for duplicate actions in same context
    const actionContexts = new Map<string, string[]>();
    
    for (const perm of permissions) {
      const context = `${perm.module_name}-${perm.menu_name}-${perm.card_name}`;
      const key = `${context}-${perm.permission_action}`;
      
      if (actionContexts.has(key)) {
        const existing = actionContexts.get(key)!;
        conflicts.push({
          permission_id: perm.id,
          conflicting_with: existing,
          severity: 'high',
          description: `Duplicate action '${perm.permission_action}' in same context`
        });
      } else {
        actionContexts.set(key, [perm.id]);
      }
    }

    // Check for power level inconsistencies
    const powerGroups = new Map<number, string[]>();  // ← CHANGED TO STRING
    for (const perm of permissions) {
      if (powerGroups.has(perm.power_level)) {
        powerGroups.get(perm.power_level)!.push(perm.id);
      } else {
        powerGroups.set(perm.power_level, [perm.id]);
      }
    }

    // Check for conflicting power levels (high power with low power actions)
    const powerLevels = Array.from(powerGroups.keys()).sort((a, b) => b - a);
    if (powerLevels.length > 1 && powerLevels[0] - powerLevels[powerLevels.length - 1] > 50) {
      conflicts.push({
        permission_id: powerGroups.get(powerLevels[0])![0],
        conflicting_with: powerGroups.get(powerLevels[powerLevels.length - 1])!,
        severity: 'medium',
        description: 'Large power level gap may indicate permission misuse'
      });
    }

    this.conflictCache.set(cacheKey, conflicts);
    
    return {
      conflicts,
      has_conflicts: conflicts.length > 0,
      recommendations: this.generateConflictRecommendations(conflicts)
    };
  }

  private static generateConflictRecommendations(conflicts: PermissionConflict[]): string[] {
    const recommendations: string[] = [];
    
    if (conflicts.some(c => c.severity === 'high')) {
      recommendations.push('Resolve duplicate permission actions in the same context');
    }
    
    if (conflicts.some(c => c.severity === 'medium')) {
      recommendations.push('Review large power level gaps between permissions');
    }
    
    if (conflicts.length > 0) {
      recommendations.push('Consider using role templates for consistent permission sets');
    }
    
    return recommendations;
  }

  // Selection Helpers - UPDATED for string IDs
  static getSelectedPermissionIds(selectedPermissions: Map<string, Set<string>>): string[] {  // ← CHANGED TO STRING
    const allIds: string[] = [];
    for (const permissionSet of selectedPermissions.values()) {
      allIds.push(...permissionSet);
    }
    return [...new Set(allIds)]; // Remove duplicates
  }

  static getCardPermissions(cardId: string, selectedPermissions: Map<string, Set<string>>): Set<string> {  // ← CHANGED TO STRING
    return selectedPermissions.get(cardId) || new Set<string>();
  }

  // Power Analysis with string IDs
  static analyzePower(permissionIds: string[], permissionStructure: PermissionStructure) {  // ← CHANGED TO STRING
    const permissions = permissionIds.map(id => 
      this.findPermissionById(id, permissionStructure)
    ).filter(Boolean) as PermissionDetail[];

    if (permissions.length === 0) {
      return {
        permission_count: 0,
        max_power: 0,
        average_power: 0,
        power_distribution: {
          low: 0,
          medium: 0,
          high: 0,
          critical: 0
        },
        most_powerful_permissions: []
      };
    }

    const totalPower = permissions.reduce((sum, perm) => sum + perm.power_level, 0);
    const maxPower = Math.max(...permissions.map(p => p.power_level));
    const avgPower = totalPower / permissions.length;

    const distribution = {
      low: permissions.filter(p => p.power_level <= 30).length,
      medium: permissions.filter(p => p.power_level > 30 && p.power_level <= 60).length,
      high: permissions.filter(p => p.power_level > 60 && p.power_level <= 80).length,
      critical: permissions.filter(p => p.power_level > 80).length
    };

    const mostPowerful = permissions
      .sort((a, b) => b.power_level - a.power_level)
      .slice(0, 5);

    return {
      permission_count: permissions.length,
      max_power: maxPower,
      average_power: Math.round(avgPower * 100) / 100,
      power_distribution: distribution,
      most_powerful_permissions: mostPowerful
    };
  }

  // UI Helpers
  static getModuleIcon(module: ModuleDetail): string {
    return module.icon || '📁';
  }

  static getMenuIcon(menu: MenuDetail): string {
    return menu.icon || '📋';
  }

  static getCardIcon(card: CardDetail): string {
    return card.icon || '🃏';
  }

  static getPermissionIcon(permission: PermissionDetail): string {
    if (permission.icon) {
      return permission.icon;
    }
    
    const icons: Record<string, string> = {
      view: '👁️',
      create: '➕',
      edit: '✏️',
      delete: '🗑️',
      manage: '⚙️',
      admin: '👑',
      analytics: '📊',
      export: '📤',
      import: '📥',
      settings: '⚙️',
      notifications: '🔔',
      mobile: '📱',
      search: '🔍',
      tags: '🏷️',
      categories: '📁',
      browse: '🔍',
      bookmark: '🔖',
      profiles: '👤',
      access: '🔒',
      configure: '🔧',
      filter: '🔧'
    };
    return icons[permission.permission_action] || '🔹';
  }

  // Menu Selection Helpers with string IDs
  static getMenuPermissions(menuId: string, permissionStructure: PermissionStructure): string[] {  // ← CHANGED TO STRING
    const permissions: string[] = [];
    
    for (const module of permissionStructure.modules) {
      for (const menu of module.menus) {
        if (menu.id === menuId) {
          // Add direct menu permissions
          if (menu.permissions) {
            permissions.push(...menu.permissions.map(p => p.id));
          }
          
          // Add card permissions
          for (const card of menu.cards) {
            permissions.push(...card.permissions.map(p => p.id));
          }
        }
      }
    }
    
    return permissions;
  }

  static isMenuFullySelected(menuId: string, selectedPermissions: Map<string, Set<string>>, permissionStructure: PermissionStructure): boolean {  // ← CHANGED TO STRING
    const menuPermissions = this.getMenuPermissions(menuId, permissionStructure);
    const selectedPermissionIds = this.getSelectedPermissionIds(selectedPermissions);
    
    return menuPermissions.every(permissionId => 
      selectedPermissionIds.includes(permissionId)
    );
  }

  static isMenuPartiallySelected(menuId: string, selectedPermissions: Map<string, Set<string>>, permissionStructure: PermissionStructure): boolean {  // ← CHANGED TO STRING
    const menuPermissions = this.getMenuPermissions(menuId, permissionStructure);
    const selectedPermissionIds = this.getSelectedPermissionIds(selectedPermissions);
    
    return menuPermissions.some(permissionId => 
      selectedPermissionIds.includes(permissionId)
    ) && !this.isMenuFullySelected(menuId, selectedPermissions, permissionStructure);
  }

  // Module Selection Helpers with string IDs
  static getModulePermissions(moduleId: string, permissionStructure: PermissionStructure): string[] {  // ← CHANGED TO STRING
    const permissions: string[] = [];
    
    for (const module of permissionStructure.modules) {
      if (module.id === moduleId) {
        for (const menu of module.menus) {
          // Add direct menu permissions
          if (menu.permissions) {
            permissions.push(...menu.permissions.map(p => p.id));
          }
          
          // Add card permissions
          for (const card of menu.cards) {
            permissions.push(...card.permissions.map(p => p.id));
          }
        }
      }
    }
    
    return permissions;
  }

  static isModuleFullySelected(moduleId: string, selectedPermissions: Map<string, Set<string>>, permissionStructure: PermissionStructure): boolean {  // ← CHANGED TO STRING
    const modulePermissions = this.getModulePermissions(moduleId, permissionStructure);
    const selectedPermissionIds = this.getSelectedPermissionIds(selectedPermissions);
    
    return modulePermissions.every(permissionId => 
      selectedPermissionIds.includes(permissionId)
    );
  }

  static isModulePartiallySelected(moduleId: string, selectedPermissions: Map<string, Set<string>>, permissionStructure: PermissionStructure): boolean {  // ← CHANGED TO STRING
    const modulePermissions = this.getModulePermissions(moduleId, permissionStructure);
    const selectedPermissionIds = this.getSelectedPermissionIds(selectedPermissions);
    
    return modulePermissions.some(permissionId => 
      selectedPermissionIds.includes(permissionId)
    ) && !this.isModuleFullySelected(moduleId, selectedPermissions, permissionStructure);
  }

  // Cache Management
  static clearCache(): void {
    this.permissionCache.clear();
    this.conflictCache.clear();
  }

  static getCacheStats(): { permissionCache: number; conflictCache: number } {
    return {
      permissionCache: this.permissionCache.size,
      conflictCache: this.conflictCache.size
    };
  }

  // Add to utils_permission.ts
static isCardFullySelected(cardId: string, selectedPermissions: Map<string, Set<string>>, permissionStructure: PermissionStructure): boolean {
  const card = this.findCardById(cardId, permissionStructure);
  if (!card) return false;
  
  const cardPermissionIds = card.permissions.map(p => p.id);
  const selectedPermissionIds = this.getSelectedPermissionIds(selectedPermissions);
  
  return cardPermissionIds.every(permissionId => 
    selectedPermissionIds.includes(permissionId)
  );
}

static isCardPartiallySelected(cardId: string, selectedPermissions: Map<string, Set<string>>, permissionStructure: PermissionStructure): boolean {
  const card = this.findCardById(cardId, permissionStructure);
  if (!card) return false;
  
  const cardPermissionIds = card.permissions.map(p => p.id);
  const selectedPermissionIds = this.getSelectedPermissionIds(selectedPermissions);
  
  return cardPermissionIds.some(permissionId => 
    selectedPermissionIds.includes(permissionId)
  ) && !this.isCardFullySelected(cardId, selectedPermissions, permissionStructure);
}

static findCardById(cardId: string, permissionStructure: PermissionStructure): CardDetail | null {
  for (const module of permissionStructure.modules) {
    for (const menu of module.menus) {
      for (const card of menu.cards) {
        if (card.id === cardId) {
          return card;
        }
      }
    }
  }
  return null;
}

}