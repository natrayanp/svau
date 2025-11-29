import { BaseApi } from '$lib/BaseApi';
import type {
  UserRoleAssignment,
  UserWithDetails,
  RoleStatistics,
  SuccessResponse,
  UsersByRoleResponse,
  UserRolesApiResponse,
  UsersByRoleApiResponse,
  RoleStatisticsApiResponse,
  BulkUserRolesApiResponse
} from './types_permission';
import MOCK_DATA from './Mockdata/permissions_mockdata.json';

const ROLE_BASE_URL = '/auth-api/roles';

class RoleApi extends BaseApi {
  constructor() {
    super(ROLE_BASE_URL);
    
    if (this.useMock) {
      this.setMockResponses({
        '/user/{id}': (params: any) => MOCK_DATA.userRoles?.[params.id] || { 
          user_id: params.id, 
          roles: ['basic'], 
          primary_role: 'basic' 
        },
        '/users/with-role/{role}': (params: any) => {
          const users = MOCK_DATA.usersByRole?.[params.role] || [];
          return {
            role: params.role,
            users: users,
            user_count: users.length
          };
        },
        '/stats': MOCK_DATA.roleStats || {
          total_users: 156,
          role_distribution: [
            { role: 'basic', user_count: 120, percentage: 76.92 },
            { role: 'creator', user_count: 25, percentage: 16.03 },
            { role: 'moderator', user_count: 8, percentage: 5.13 },
            { role: 'admin', user_count: 3, percentage: 1.92 }
          ],
          most_common_role: 'basic'
        },
        '/users/bulk-update': { 
          success: true, 
          message: "Bulk update completed",
          data: {
            updated: 2,
            failed: 0,
            results: []
          }
        },
        '/users/{id}/roles': { success: true, message: "Role assigned successfully" },
        '/users/{id}/roles/{role}': { success: true, message: "Role removed successfully" }
      });
    }
  }

  private handleResponse<T>(response: { success: boolean; message: string; data?: T }): T {
    if (!response.success) {
      throw new Error(response.message || 'API request failed');
    }
    if (!response.data) {
      throw new Error('No data received from server');
    }
    return response.data;
  }

  // User Role Assignment
  async getUserRoles(userId: number): Promise<UserRoleAssignment> {
    const response = await this.request<UserRolesApiResponse>(`/user/${userId}`);
    return this.handleResponse(response);
  }

  async updateUserRole(userId: number, role: string): Promise<SuccessResponse> {
    const response = await this.request<SuccessResponse>(`/user/${userId}`, {
      method: 'PUT',
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({ role })
    });
    return this.handleResponse(response);
  }

  // User Management by Role
  async getUsersByRole(roleName: string): Promise<UsersByRoleResponse> {
    const response = await this.request<UsersByRoleApiResponse>(`/users/with-role/${roleName}`);
    return this.handleResponse(response);
  }

  async assignUserToRole(userId: number, roleName: string): Promise<SuccessResponse> {
    const response = await this.request<SuccessResponse>(`/users/${userId}/roles`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({ role: roleName })
    });
    return this.handleResponse(response);
  }

  async removeUserFromRole(userId: number, roleName: string): Promise<SuccessResponse> {
    const response = await this.request<SuccessResponse>(`/users/${userId}/roles/${roleName}`, {
      method: 'DELETE'
    });
    return this.handleResponse(response);
  }

  // Statistics
async getSystemStats(): Promise<RoleStatistics> {
  const response = await this.request<{ success: boolean; message: string; data: RoleStatistics }>('/stats');
  return this.handleResponse(response);
}

  // Bulk Operations
  async bulkUpdateUserRoles(updates: Array<{
    user_id: number;
    role_name: string;
    action: 'add' | 'remove';
  }>): Promise<any> {
    const response = await this.request<BulkUserRolesApiResponse>('/users/bulk-update', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({ updates })
    });
    return this.handleResponse(response);
  }

  // Role Statistics
  async getRoleStatistics(): Promise<RoleStatistics> {
    const response = await this.request<RoleStatisticsApiResponse>('/stats');
    return this.handleResponse(response);
  }
}

export const roleApi = new RoleApi();