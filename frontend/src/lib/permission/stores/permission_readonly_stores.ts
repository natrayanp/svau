// permission_readonly_stores.ts
import { createReadonlyStore } from '$lib/common/readonlyStoreFactory';
import { permissionApi } from './api_permission';
import type { PermissionStructure } from './types_permission';
import type { SystemStats} from '../types_permission';

// ------------------------------
// System Stats Store
// ------------------------------
export const systemStatsStore = createReadonlyStore<SystemStats>(
  'systemStats',
  async () => {
    const response = await permissionApi.getSystemStats();
    return response; // SystemStats object
  }
);

// ------------------------------
// Permission Structure Store
// ------------------------------
export const permissionStructureStore = createReadonlyStore<PermissionStructure>(
  'permissionStructure',
  async () => {
    const response = await permissionApi.getPermissionStructure();
    return response; // PermissionStructure object
  }
);
