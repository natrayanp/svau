import { BaseApi } from '$lib/BaseApi';
import type {
  PermissionStructure,
  UserPermissionsResponse,
  PermissionValidationResponse,
  AllowedPermissionsResponse,
  PowerAnalysis,
  RoleTemplate,
  RolePermissionsResponse,
  SuccessResponse,
  SystemRole,
  QuickAction,
  AuditLog,
  HealthCheck,
  UserWithDetails,
  RoleStatistics,
  PermissionStructureResponse,
  UserPermissionsApiResponse,
  PermissionValidationRequest,
  AllowedPermissionsResponse as AllowedPermissionsResponseType,
  RolePermissionsApiResponse,
  SystemRolesApiResponse,
  RoleTemplatesResponse,
  QuickActionsApiResponse,
  SystemPowerAnalysisApiResponse,
  HealthCheckApiResponse,
  AuditLogsApiResponse,
  UsersByRoleResponse,
  UserPermissionsDetailsResponse,
  BulkRolePermissionsApiResponse,
  BulkUserRolesApiResponse,
  RolePermissionsUpdateRequest,
  CreateRoleRequest,
  PermissionConflictResponse,
  PermissionConflictCheckRequest,
  ApiError
} from './types_permission';
import MOCK_DATA from './Mockdata/permissions_mockdata.json';

const PERMISSION_BASE_URL = '/auth-api/permissions';

class PermissionApi extends BaseApi {
  constructor(useMock: boolean = false) {
    super(PERMISSION_BASE_URL, useMock);
    
    if (useMock) {
      this.setMockResponses({
        '/structure': MOCK_DATA.permissionStructure,
        '/user/{id}': (params: any) => {
          const userPerms = MOCK_DATA.userPermissions[params.id] || { user_id: params.id, permission_ids: [] };
          // Convert mock number IDs to string for frontend
          return {
            ...userPerms,
            permission_ids: userPerms.permission_ids.map((id: number) => id.toString())
          };
        },
        '/user/{id}/effective': (params: any) => {
          const userPerms = MOCK_DATA.userPermissions[params.id] || { user_id: params.id, permission_ids: [] };
          return {
            ...userPerms,
            permission_ids: userPerms.permission_ids.map((id: number) => id.toString())
          };
        },
        '/user/{id}/details': (params: any) => {
          const userPerms = MOCK_DATA.userPermissions[params.id] || { user_id: params.id, permission_ids: [] };
          const permissions = userPerms.permission_ids.map((id: number) => ({
            permission_id: id.toString(),
            display_name: `Permission ${id}`,
            description: `Description for permission ${id}`,
            permission_action: `action_${id}`,
            power_level: Math.min(id % 100, 100)
          }));
          return {
            user_id: params.id,
            permissions,
            total_permissions: permissions.length
          };
        },
        '/templates': () => {
          // Convert template permission IDs to string
          console.log('🔧 Mock /templates called');

          const templatesWithStringIds: { [key: string]: any } = {};
          for (const [key, template] of Object.entries(MOCK_DATA.roleTemplates)) {
            templatesWithStringIds[key] = {
              ...template,
              permission_ids: template.permission_ids.map((id: number) => id.toString())
            };
          }
          console.log('🔧 Returning templates:', templatesWithStringIds);
          return templatesWithStringIds;
        },
        '/roles': MOCK_DATA.systemRoles,
        '/roles/{role}': (params: any) => {
          const rolePerms = MOCK_DATA.rolePermissions[params.role] || MOCK_DATA.rolePermissions.basic;
          // Convert permission IDs to string
          return {
            ...rolePerms,
            permission_ids: rolePerms.permission_ids.map((id: number) => id.toString())
          };
        },
        '/roles/{role}/analysis': (params: any) => {
          const rolePerms = MOCK_DATA.rolePermissions[params.role] || MOCK_DATA.rolePermissions.basic;
          return {
            permission_count: rolePerms.permission_ids.length,
            max_power: 85,
            average_power: 45.5,
            power_distribution: { low: 2, medium: 3, high: 1, critical: 1 },
            most_powerful_permissions: []
          };
        },
        '/roles/{role}/validate': { success: true, message: "Permissions validated", data: { valid: true, conflicts: [] } },
        '/quick-actions': MOCK_DATA.quickActions,
        '/analysis/system': MOCK_DATA.systemPowerAnalysis,
        '/audit/logs': MOCK_DATA.auditLogs,
        '/health': MOCK_DATA.healthCheck,
        '/check/{permission}': { success: true, message: "Permission check passed" },
        '/check-power/{power}': { success: true, message: "Power level sufficient" },
        '/allowed-child-permissions': { 
          allowed_permissions: [],
          max_parent_power: 0 
        },
        '/validate-child-permissions': {
          max_parent_power: 0,
          validation_results: [],
          all_allowed: true
        },
        '/conflicts': {
          conflicts: [],
          has_conflicts: false,
          recommendations: []
        }
      });
    }
  }

  private handleResponse<T>(response: { success: boolean; message: string; data?: T; error?: ApiError }): T {
    if (!response.success) {
      const error: ApiError = response.error || {
        code: 'API_ERROR',
        message: response.message || 'API request failed',
        timestamp: new Date().toISOString()
      };
      throw new Error(error.message);
    }
    if (!response.data) {
      throw new Error('No data received from server');
    }
    return response.data;
  }

  // Permission Structure
  async getPermissionStructure(): Promise<PermissionStructure> {
    const response = await this.request<PermissionStructureResponse>('/structure');
    return this.handleResponse(response);
  }

  // User Permissions - Backend returns string IDs, no conversion needed
  async getUserPermissions(userId: number): Promise<UserPermissionsResponse> {
    const response = await this.request<UserPermissionsApiResponse>(`/user/${userId}`);
    return this.handleResponse(response);
  }

  async getEffectivePermissions(userId: number): Promise<UserPermissionsResponse> {
    const response = await this.request<UserPermissionsApiResponse>(`/user/${userId}/effective`);
    return this.handleResponse(response);
  }

  async getUserPermissionsWithDetails(userId: number): Promise<UserPermissionsDetailsResponse> {
    const response = await this.request<{ success: boolean; message: string; data: UserPermissionsDetailsResponse }>(`/user/${userId}/details`);
    return this.handleResponse(response);
  }

  // Power Validation - Accepts string IDs
  async validateChildPermissions(parentPermissionIds: string[], childPermissionIds: string[]): Promise<PermissionValidationResponse> {
    const response = await this.request<PermissionValidationResponse>('/validate-child-permissions', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({
        parent_permission_ids: parentPermissionIds,  // String IDs
        child_permission_ids: childPermissionIds     // String IDs
      })
    });
    return this.handleResponse(response);
  }

  async getAllowedChildPermissions(parentPermissionIds: string[]): Promise<AllowedPermissionsResponseType> {
    const ids = parentPermissionIds.join(',');
    const response = await this.request<AllowedPermissionsResponseType>(`/allowed-child-permissions?parent_permission_ids=${ids}`);
    return this.handleResponse(response);
  }

  // Permission Conflict Detection - Accepts string IDs
  async checkPermissionConflicts(permissionIds: string[]): Promise<PermissionConflictResponse> {
    const response = await this.request<PermissionConflictResponse>('/conflicts', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({ permission_ids: permissionIds })  // String IDs
    });
    return this.handleResponse(response);
  }

  // Role Management - Uses string IDs throughout
  async getRolePermissions(roleName: string): Promise<RolePermissionsResponse> {
    const response = await this.request<RolePermissionsApiResponse>(`/roles/${roleName}`);
    return this.handleResponse(response);
  }

  async getRolePowerAnalysis(roleName: string): Promise<PowerAnalysis> {
    const response = await this.request<{ success: boolean; message: string; data: PowerAnalysis }>(`/roles/${roleName}/analysis`);
    return this.handleResponse(response);
  }

  // UPDATED: Accepts string IDs
  async updateRolePermissions(roleName: string, permissionIds: string[]): Promise<SuccessResponse> {
    const response = await this.request<SuccessResponse>(`/roles/${roleName}/permissions`, {
      method: 'PUT',
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({ permission_ids: permissionIds })  // String IDs
    });
    return this.handleResponse(response);
  }

  async validateRolePermissions(roleName: string, permissionIds: string[]): Promise<{ valid: boolean; conflicts: any[] }> {
    const response = await this.request<any>(`/roles/${roleName}/validate`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({ permission_ids: permissionIds })  // String IDs
    });
    return this.handleResponse(response);
  }

  // Role Creation and Management - Uses string IDs
  async createRole(roleData: CreateRoleRequest): Promise<SuccessResponse> {
    const response = await this.request<SuccessResponse>('/roles', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(roleData)  // Contains string permission_ids
    });
    return this.handleResponse(response);
  }

  async deleteRole(roleName: string): Promise<SuccessResponse> {
    const response = await this.request<SuccessResponse>(`/roles/${roleName}`, {
      method: 'DELETE'
    });
    return this.handleResponse(response);
  }

  // Role Templates - Returns string IDs
  async getRoleTemplates(): Promise<{ [key: string]: RoleTemplate }> {
    console.log('insde get role');
    const response = await this.request<RoleTemplatesResponse>('/templates');
    return this.handleResponse(response);
  }

  // System Roles - Returns string IDs in permissions
  async getSystemRoles(): Promise<SystemRole[]> {
    const response = await this.request<SystemRolesApiResponse>('/roles');
    const data = this.handleResponse(response);
    return data.roles;
  }

  // Permission Checking - Backend uses int for dependency injection
  async checkPermission(permissionId: number): Promise<SuccessResponse> {
    const response = await this.request<SuccessResponse>(`/check/${permissionId}`, {
      method: 'POST'
    });
    return this.handleResponse(response);
  }

  async checkPowerLevel(requiredPower: number): Promise<SuccessResponse> {
    const response = await this.request<SuccessResponse>(`/check-power/${requiredPower}`, {
      method: 'POST'
    });
    return this.handleResponse(response);
  }

  // Quick Actions
  async getQuickActions(): Promise<QuickAction[]> {
    const response = await this.request<QuickActionsApiResponse>('/quick-actions');
    const data = this.handleResponse(response);
    return data.actions;
  }

  // Power analysis
  async getSystemPowerAnalysis(): Promise<any> {
    const response = await this.request<SystemPowerAnalysisApiResponse>('/analysis/system');
    return this.handleResponse(response);
  }

  // Audit logs
  async getPermissionAuditLogs(filters?: {
    start_date?: string;
    end_date?: string;
    user_id?: number;
    role_name?: string;
    action_type?: string;
  }): Promise<AuditLog[]> {
    const queryParams = new URLSearchParams();
    if (filters?.start_date) queryParams.append('start_date', filters.start_date);
    if (filters?.end_date) queryParams.append('end_date', filters.end_date);
    if (filters?.user_id) queryParams.append('user_id', filters.user_id.toString());
    if (filters?.role_name) queryParams.append('role_name', filters.role_name);
    if (filters?.action_type) queryParams.append('action_type', filters.action_type);

    const queryString = queryParams.toString();
    const url = `/audit/logs${queryString ? `?${queryString}` : ''}`;
    
    const response = await this.request<AuditLogsApiResponse>(url);
    const data = this.handleResponse(response);
    return data.logs;
  }

  // Bulk operations - Uses string IDs
  async bulkUpdateRolePermissions(updates: Array<{
    role_name: string;
    permission_ids: string[];  // String IDs
  }>): Promise<any> {
    const response = await this.request<BulkRolePermissionsApiResponse>('/roles/bulk-permissions', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({ updates })  // Contains string permission_ids
    });
    return this.handleResponse(response);
  }

  // Health check
  async healthCheck(): Promise<HealthCheck> {
    const response = await this.request<HealthCheckApiResponse>('/health');
    return this.handleResponse(response);
  }
}

export const permissionApi = new PermissionApi(true);