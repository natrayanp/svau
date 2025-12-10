// permissionStores.ts
import { createEntityStore } from '../../common/entityStoreFactory';
import type { User, Role } from './types_permission';
import { permissionApi } from './api_permission';

// ------------------------------
// Users Store (full CRUD)
// ------------------------------
export const usersStore = createEntityStore<User>(
  'users',
  async (params) => permissionApi.getUsers(params),
  (user) => user.user_id,
  100,
  5000,
   {
    searchable: ['display_name', 'email', 'username'],
    sortable: ['display_name', 'email', 'created_at'],
    arrayFields: ['roles', 'permissions']
    },
  //permissionApi.createUser,
  undefined,
  //permissionApi.updateUsers,
  async (params) => permissionApi.updateUsersRole(params),
  async (params) => permissionApi.deleteUserRole(params)
  //permissionApi.deleteUser
);

// ------------------------------
// Roles Store (no delete)
// ------------------------------
export const rolesStore = createEntityStore<Role>(
  'roles',
  async (params) => permissionApi.getRoles(params),
  (role) => role.role_id,
  100,
  5000,
  {
    searchable: ['role_id', 'description'],
    sortable: ['power_level', 'permission_count'],
    arrayFields: ['permissions', 'category_access'] 
  },
  undefined, //permissionApi.createRole,
  async (params) => permissionApi.updateRole(params),  //permissionApi.updateRole  
  // deleteFn omitted → deleteItem won’t exist
);
