import { BaseApi } from '$lib/BaseApi';
import type {
  PermissionStructure,
  UserPermissionsResponse,
  PermissionValidationResponse,
  AllowedPermissionsResponse,
  PowerAnalysis,
  RoleTemplate,
  RolePermissionsResponse,
  UserRoleAssignment
} from './types_permission';

const PERMISSION_BASE_URL = '/auth-api/permissions';

class PermissionApi extends BaseApi {
  constructor(useMock: boolean = true) {
    super(PERMISSION_BASE_URL, useMock);
    
    if (useMock) {
      this.setMockResponses({
        '/structure': {
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
                        }
                      ]
                    }
                  ]
                }
              ]
            }
          ],
          metadata: {
            total_modules: 1,
            total_menus: 1,
            total_cards: 1,
            total_permissions: 2,
            last_updated: new Date().toISOString()
          }
        },
        '/user/1': {
          user_id: 1,
          permission_ids: [5001, 5002]
        },
        '/templates': {
          content_viewer: {
            name: 'Content Viewer',
            description: 'Can view all content but cannot modify',
            permission_ids: [5001],
            power_level: 10
          },
          content_creator: {
            name: 'Content Creator', 
            description: 'Can create and edit content',
            permission_ids: [5001, 5002],
            power_level: 30
          }
        }
      });
    }
  }

  // Permission Structure
  async getPermissionStructure() {
    return this.request<{ success: boolean; data: PermissionStructure }>('/structure');
  }

  // User Permissions
  async getUserPermissions(userId: number) {
    return this.request<UserPermissionsResponse>(`/user/${userId}`);
  }

  async getEffectivePermissions(userId: number) {
    return this.request<UserPermissionsResponse>(`/user/${userId}/effective`);
  }

  // Power Validation
  async validateChildPermissions(parentPermissionIds: number[], childPermissionIds: number[]) {
    return this.request<PermissionValidationResponse>('/validate-child-permissions', {
      method: 'POST',
      body: JSON.stringify({
        parent_permission_ids: parentPermissionIds,
        child_permission_ids: childPermissionIds
      })
    });
  }

  async getAllowedChildPermissions(parentPermissionIds: number[]) {
    const ids = parentPermissionIds.join(',');
    return this.request<AllowedPermissionsResponse>(`/allowed-child-permissions?parent_permission_ids=${ids}`);
  }

  // Role Management
  async getRolePermissions(roleName: string) {
    return this.request<RolePermissionsResponse>(`/roles/${roleName}`);
  }

  async getRolePowerAnalysis(roleName: string) {
    return this.request<PowerAnalysis>(`/roles/${roleName}/power-analysis`);
  }

  async updateRolePermissions(roleName: string, permissionIds: number[]) {
    return this.request<{ success: boolean; message: string }>(`/roles/${roleName}`, {
      method: 'POST',
      body: JSON.stringify({ permission_ids: permissionIds })
    });
  }

  // Role Templates
  async getRoleTemplates() {
    return this.request<{ [key: string]: RoleTemplate }>('/templates');
  }

  // User Role Assignment
  async getUserRoles(userId: number) {
    return this.request<{
      user_id: number;
      roles: string[];
      primary_role: string;
    }>(`/auth-api/roles/user/${userId}`);
  }

  async updateUserRole(userId: number, role: string) {
    return this.request<{ success: boolean; message: string }>(`/auth-api/roles/user/${userId}`, {
      method: 'PUT',
      body: JSON.stringify({ role })
    });
  }

  // Permission Checking
  async checkPermission(permissionId: number) {
    return this.request<{ success: boolean; message: string }>(`/check/${permissionId}`, {
      method: 'POST'
    });
  }
}

export const permissionApi = new PermissionApi(true);