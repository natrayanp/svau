import { BaseApi } from '$lib/BaseApi';
import type {
  PermissionStructure,
  Role,
  PermissionStructureResponse,
  //AllowedPermissionsResponse as AllowedPermissionsResponseType,
  ApiResponse,
  RoleApiResponse,
  ApiError,
  ApiFetch,
  User,
  UsersGetApiResponse,
  PaginatedData,
  UserUpdatePayload,
  UsersDelApiResponse
} from './types_permission';

import MOCK_DATA from '../Mockdata/permissions_mockdata.json';

import type { } from './types_permission';
import type { ApiUser } from '$lib/auth/authtypes';


const PERMISSION_PREFIX_URL = '/auth-api/permissions';

class PermissionApi extends BaseApi {
  constructor() {
    super(PERMISSION_PREFIX_URL);
    console.log("inside permission new", this.useMock);

    if (this.useMock) {
      this.setMockResponses({
        '/structure': () => ({
          success: true,
          message: "Permission structure loaded successfully",
          data: MOCK_DATA.permissionStructure
        }),

        '/users': ({ offset = 0, limit = 20 }) => {
          offset = Number(offset);
          limit = Number(limit);

          const total = MOCK_DATA.users.length;
          const sliced = MOCK_DATA.users.slice(offset, offset + limit);

          return {
            success: true,
            message: "Users loaded",
            data: {
              items: sliced,
              total,
              page: Math.floor(offset / limit) + 1,
              page_size: limit,
              total_pages: Math.ceil(total / limit),
              has_next: offset + limit < total,
              has_prev: offset > 0
            }
          };
        },

        '/roles': ({ offset = 0, limit = 20 }) => {
          offset = Number(offset);
          limit = Number(limit);

          const total = MOCK_DATA.systemRoles.length;
          const sliced = MOCK_DATA.systemRoles.slice(offset, offset + limit);

          return {
            success: true,
            message: "System roles loaded",
            data: {
              items: sliced,
              total,
              page: Math.floor(offset / limit) + 1,
              page_size: limit,
              total_pages: Math.ceil(total / limit),
              has_next: offset + limit < total,
              has_prev: offset > 0
            }
          };
        },



        /*                  
         '/roles': () => 
           
           {
        
           console.log('🎯 Mock /roles endpoint called');
           console.log('📦 MOCK_DATA.systemRoles:', MOCK_DATA.systemRoles);
           
           if (!MOCK_DATA.systemRoles || MOCK_DATA.systemRoles.length === 0) {
             console.error('❌ MOCK_DATA.systemRoles is empty!');
             return {
               success: false,
               message: "No system roles data found",
               error: {
                 code: "MOCK_DATA_MISSING",
                 message: "System roles mock data is not defined"
               }
             };
           }
           
           /*const response = {
             success: true,
             message: "System roles loaded successfully",
             data: {
               roles: MOCK_DATA.systemRoles,
               total_roles: MOCK_DATA.systemRoles.length
             }
           };*/

        /*
                     const response =                                     {
                                                                  success: true,
                                      message: "Permission structure loaded successfully",
                                      data:{  
                                    items: MOCK_DATA.systemRoles,
                                    total: 105,
                                    page: 1,
                                    page_size: 10,
                                    total_pages: 1,
                                    has_next: true,
                                    has_prev: true
                                  }};
                
                console.log('📤 Mock response for /roles:', response);
                return response;
               
              },
                */


      });
    }
  }


  private handleResponse<T>(response: ApiResponse<T | PaginatedData<T> | T[]>): T | PaginatedData<T> | T[] {

    console.log('handleresponse');
    console.log(response);
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
    console.log(response.data);
    return response.data;
  }


  // Permission Structure
  async getPermissionStructure(): Promise<PermissionStructure> {
    console.log('getPermissionStructure1');
    const response = await this.request<ApiResponse<PermissionStructure>>('/structure');
    console.log('getPermissionStructure2');
    return (this.handleResponse<PermissionStructure>(response)) as PermissionStructure; // handleResponse returns PermissionStructure
  }


  async getUsers({ offset = 1, limit = 20 }: ApiFetch): Promise<PaginatedData<User>> {
    console.log('getUsers1');
    console.log(`/users?offset=${offset}&limit=${limit}`);
    //const response = await this.request<UsersApiResponse>(`/users`);  
    const response = await this.request<ApiResponse<PaginatedData<User>>>(
      `/users?offset=${offset}&limit=${limit}`
    );
    console.log('getUsers2');
    const data = this.handleResponse<PaginatedData<User>>(response);
    console.log('getUsers3');
    return data as PaginatedData<User>; // data is { items: User[], total, page, ... }
  }

  async updateUsersRole(updates: Partial<User>[]): Promise<PaginatedData<User>> {
    // Call backend endpoint
    console.log(updates);
    const response = await this.request<ApiResponse<PaginatedData<User>>>(
      '/users/update',
      {
        method: 'PUT',   // or POST depending on backend
        body: JSON.stringify({ action: 'update', data: updates })  // send array of payloads
      }
    );

    const data = this.handleResponse<PaginatedData<User>>(response);
    return data;
  }

  async deleteUserRole(deletes: string| number []): Promise<PaginatedData<User>> {
    console.log(deletes);
    const response = await this.request<ApiResponse<PaginatedData<User>>>(`/users/delete`, {
      method: 'DELETE',
      body: JSON.stringify({ 
          user_ids: deletes
      })
    });
    return this.handleResponse<PaginatedData<User>>(response);
  }

  // System Roles - Returns string IDs in permissions
  // In api_permission.ts
  async getRoles({ offset = 1, limit = 20 }: ApiFetch): Promise<PaginatedData<Role>> {
    console.log('getSystemRoles1');
    //const response = await this.request<SystemRolesApiResponse>(`/roles?page=${page}&page_size=${page_size}`);
    console.log('getSystemRoles2');
    const response = await this.request<RoleApiResponse>(
      `/roles?offset=${offset}&limit=${limit}`
    );

    console.log('getSystemRoles3');
    const data = this.handleResponse(response);
    // data = { roles: [...], total_roles: 4 }
    return data as PaginatedData<Role>;
  }

  async updateRole(updates: Partial<Role>[]): Promise<PaginatedData<Role>> {
    // Call backend endpoint
    console.log(updates);
    const response = await this.request<ApiResponse<PaginatedData<Role>>>(
      '/roles/update',
      {
        method: 'PUT',
        body: JSON.stringify({
          data: updates
        })
      }
    );

    const data = this.handleResponse<PaginatedData<Role>>(response);
    return data as PaginatedData<Role>;
  }


  async deleteRole(deletes: string| number []): Promise<PaginatedData<Role>> {
    console.log(deletes);
    const response = await this.request<ApiResponse<PaginatedData<Role>>>(`/roles/delete`, {
      method: 'DELETE',
      body: JSON.stringify({
          role_ids: deletes
      })
    });

    return this.handleResponse<PaginatedData<Role>>(response);
  }

}

export const permissionApi = new PermissionApi();