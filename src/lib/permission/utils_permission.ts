import type { 
  PermissionDetail, 
  CardDetail, 
  MenuDetail, 
  ModuleDetail,
  PermissionStructure,
  PowerLevel,
  POWER_LEVELS
} from './types_permission';

export class PermissionUtils {
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

  // Permission Access Checking
  static canAccess(
    userPermissions: Set<number>,
    permissionStructure: PermissionStructure,
    moduleKey: string,
    menuKey: string,
    cardKey: string,
    action: string
  ): boolean {
    for (const module of permissionStructure.modules) {
      if (module.key === moduleKey) {
        for (const menu of module.menus) {
          if (menu.key === menuKey) {
            for (const card of menu.cards) {
              if (card.key === cardKey) {
                for (const permission of card.permissions) {
                  if (permission.action === action) {
                    return userPermissions.has(permission.id);
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
  static getMaxPower(permissionIds: number[], permissionStructure: PermissionStructure): number {
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
    parentPermissionIds: number[],
    availablePermissions: PermissionDetail[],
    permissionStructure: PermissionStructure
  ): PermissionDetail[] {
    const maxParentPower = this.getMaxPower(parentPermissionIds, permissionStructure);
    
    return availablePermissions.filter(permission => 
      permission.power_level <= maxParentPower
    );
  }

  static findPermissionById(permissionId: number, permissionStructure: PermissionStructure): PermissionDetail | null {
    for (const module of permissionStructure.modules) {
      for (const menu of module.menus) {
        for (const card of menu.cards) {
          for (const permission of card.permissions) {
            if (permission.id === permissionId) {
              return permission;
            }
          }
        }
      }
    }
    return null;
  }

  // Selection Helpers
  static getSelectedPermissionIds(selectedPermissions: Map<number, Set<number>>): number[] {
    const allIds: number[] = [];
    for (const permissionSet of selectedPermissions.values()) {
      allIds.push(...permissionSet);
    }
    return allIds;
  }

  static getCardPermissions(cardId: number, selectedPermissions: Map<number, Set<number>>): Set<number> {
    return selectedPermissions.get(cardId) || new Set();
  }

  // Power Analysis
  static analyzePower(permissionIds: number[], permissionStructure: PermissionStructure) {
  const permissions = permissionIds.map(id => 
    this.findPermissionById(id, permissionStructure)
  ).filter(Boolean) as PermissionDetail[];

  // Safe defaults
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
  const maxPower = Math.max(...permissions.map(p => p.power_level), 0);
  const avgPower = permissions.length > 0 ? totalPower / permissions.length : 0;

  const distribution = {
    low: permissions.filter(p => p.power_level <= 30).length,
    medium: permissions.filter(p => p.power_level > 30 && p.power_level <= 60).length,
    high: permissions.filter(p => p.power_level > 60 && p.power_level <= 80).length,
    critical: permissions.filter(p => p.power_level > 80).length
  };

  const mostPowerful = permissions
    .filter(p => p.power_level === maxPower)
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
    return '📋';
  }

  static getCardIcon(card: CardDetail): string {
    return '🃏';
  }

  static getPermissionIcon(permission: PermissionDetail): string {
    const icons: Record<string, string> = {
      view: '👁️',
      create: '➕',
      edit: '✏️',
      delete: '🗑️',
      manage: '⚙️',
      admin: '👑',
      analytics: '📊',
      export: '📤',
      import: '📥'
    };
    return icons[permission.action] || '🔹';
  }
}