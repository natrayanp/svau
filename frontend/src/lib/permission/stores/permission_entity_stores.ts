// permissionStores.ts
import { createEntityStore } from '../../common/entityStoreFactory';
import type { User, Role } from '../types_permission';
import { permissionApi } from './api_permission';

// ------------------------------
// Users Store (full CRUD)
// ------------------------------
export const usersStore = createEntityStore<User>(
  'users',
  async ({ offset, limit, filter, sort }) => {
    // backend fetch expects offset/limit (+ optional filter/sort)
    const response = await permissionApi.getUsers(offset, limit, filter, sort);
    return response; // PaginatedData<User>
  },
  (user) => user.user_id,
  100,
  5000,
  //permissionApi.createUser,
  //permissionApi.updateUser,
  //permissionApi.deleteUser
);

// ------------------------------
// Roles Store (no delete)
// ------------------------------
export const rolesStore = createEntityStore<Role>(
  'roles',
  async ({ offset, limit, filter, sort }) => {
    const response = await permissionApi.getSystemRoles(offset, limit, filter, sort);
    return response; // PaginatedData<Role>
  },
  (role) => role.role_key,
  100,
  5000,
  //permissionApi.createRole,
  //permissionApi.updateRole
  // deleteFn omitted → deleteItem won’t exist
);
