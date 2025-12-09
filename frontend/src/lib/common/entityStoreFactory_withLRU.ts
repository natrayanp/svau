// entityStoreFactory.ts
import { writable, get, type Writable } from 'svelte/store';
import type { PaginatedData, ApiFetch, TableVersion } from '../permission/stores/types_permission';
import { createGenericPagination } from './genericPagination';

export function createEntityStore<T>(
  entityName: string,
  apiFetch: (data: ApiFetch) => Promise<PaginatedData<T>>,
  getId: (item: T) => string | number,
  blockSize = 100,
  maxCacheableTotal = 5000,
  fieldConfig: {
    searchable?: string[];
    sortable?: string[];
    arrayFields?: string[];
  } = {},
  createFn?: (data: Partial<T> | Partial<T>[]) => Promise<T | T[]>,
  updateFn?: (data: Partial<T>[]) => Promise<T[]>,
  deleteFn?: (id: (string | number)[]) => Promise<void>
) {
  const cache = writable<Record<number, (T & { id: string | number })[]>>({});
  const pagination = writable<PaginatedData<T & { id: string | number }>>({
    items: [],
    total: 0,
    page: 1,
    page_size: 20,
    total_pages: 0,
    has_next: false,
    has_prev: false
  });

  const loading = writable(false);
  const mutating = writable(false);

  const searchableFields = fieldConfig.searchable ?? [];
  const sortableFields = fieldConfig.sortable ?? [];
  const arrayFields = new Set(fieldConfig.arrayFields ?? []);

  let isFullyCached = false;
  let lastQueryFilter: Record<string, any> | undefined = undefined;
  let lastQuerySort: any | undefined = undefined;

  // NEW: Global fingerprint storage
  let currentOrgId = 0;
  let currentTableVersions = new Map<string, number>(); // table_name → version
  let currentQueryHash = ''; // Hash of current query (filter+sort)

  // NEW: LRU eviction (always enabled)
  const maxBlocks = Math.max(1, Math.floor(maxCacheableTotal / blockSize));
  let cacheBlocks: number[] = []; // keeps track of cached blocks in LRU order (oldest first)

  function normalizeItem(item: T): T & { id: string | number } {
    const id = getId(item);
    return { ...item, id };
  }

  function transformFilterForBackend(filter: any, arrayFields: Set<string>): any {
    if (!filter) return filter;

    const result = { ...filter };

    for (const [key, value] of Object.entries(filter)) {
      if (key === 'q' || key === 'field' || key === 'fields') continue;
      if (value === undefined || value === null || value === 'all') continue;

      if (arrayFields.has(key)) {
        result[`${key}_contains`] = [value];
        delete result[key];
      }
    }

    return result;
  }

  // NEW: Generate query hash for filter/sort changes
  function generateQueryHash(filter?: any, sort?: any): string {
    const queryObject = {
      filter: filter || null,
      sort: sort || null
    };

    // Simple hash - in production use a proper hashing function
    return JSON.stringify(queryObject);
  }

  // NEW: Check if fingerprint changed (org_id or table versions)
  function hasFingerprintChanged(newOrgId: number, newTableVersions: TableVersion[]): {
    changed: boolean;
    reason?: string;
    changedTables?: string[];
  } {
    // Case 1: First request ever
    if (currentOrgId === 0 && currentTableVersions.size === 0) {
      return { changed: false };
    }

    // Case 2: Organization changed
    if (currentOrgId !== newOrgId) {
      return { 
        changed: true, 
        reason: `Organization changed: ${currentOrgId} → ${newOrgId}`,
        changedTables: ['*ALL*'] // Special marker for org change
      };
    }

    // Case 3: Check table versions
    const changedTables: string[] = [];

    // Check for version changes in existing tables
    for (const newVersion of newTableVersions) {
      const currentVersion = currentTableVersions.get(newVersion.table_name);
      if (currentVersion !== undefined && currentVersion !== newVersion.table_version) {
        changedTables.push(newVersion.table_name);
      }
    }

    // Check for tables added/removed
    const currentTableNames = Array.from(currentTableVersions.keys());
    const newTableNames = newTableVersions.map(v => v.table_name);

    // Find tables that disappeared
    const removedTables = currentTableNames.filter(name => !newTableNames.includes(name));
    if (removedTables.length > 0) {
      changedTables.push(...removedTables.map(name => `${name} (removed)`));
    }

    // Find tables that appeared
    const addedTables = newTableNames.filter(name => !currentTableNames.includes(name));
    if (addedTables.length > 0) {
      changedTables.push(...addedTables.map(name => `${name} (added)`));
    }

    if (changedTables.length > 0) {
      return { 
        changed: true, 
        reason: `Table versions changed`,
        changedTables 
      };
    }

    return { changed: false };
  }

  // NEW: Update fingerprint
  function updateFingerprint(newOrgId: number, newTableVersions: TableVersion[], queryHash: string) {
    currentOrgId = newOrgId;
    currentTableVersions.clear();
    currentQueryHash = queryHash;

    newTableVersions.forEach(v => {
      currentTableVersions.set(v.table_name, v.table_version);
    });

    console.log(`📝 Updated fingerprint: org_id=${newOrgId}, query_hash=${queryHash.substring(0, 20)}..., versions=`, 
      Array.from(currentTableVersions.entries()));
  }

  // NEW: Clear entire cache
  function clearCache() {
    cache.set({});
    cacheBlocks = [];
    console.log('🗑️ Cleared entire cache');
  }

  // NEW: LRU helpers
  function addBlockToCache(blockNum: number, items: (T & { id: string | number })[]) {
    const cacheVal = get(cache);
    cacheVal[blockNum] = items;
    cache.set({ ...cacheVal });

    // If block already present in tracking, remove it (we will push as most-recent)
    const existingIndex = cacheBlocks.indexOf(blockNum);
    if (existingIndex !== -1) cacheBlocks.splice(existingIndex, 1);

    cacheBlocks.push(blockNum); // newest at end

    // Evict if exceed maxBlocks
    while (cacheBlocks.length > maxBlocks) {
      const evictBlock = cacheBlocks.shift(); // remove oldest
      if (evictBlock !== undefined) {
        const cv = get(cache);
        delete cv[evictBlock];
        cache.set({ ...cv });
        console.log(`🗑️ Evicted block ${evictBlock}`);
      }
    }
  }

  function touchBlockInCache(blockNum: number) {
    const cacheVal = get(cache);
    if (!cacheVal[blockNum]) return;
    const idx = cacheBlocks.indexOf(blockNum);
    if (idx !== -1) {
      cacheBlocks.splice(idx, 1);
    }
    cacheBlocks.push(blockNum); // mark as most recently used
  }

  async function fetchBlock(blockNum: number, blockSizeArg: number, opts?: { queryFilter?: any; querySort?: any }) {
    const offset = (blockNum - 1) * blockSizeArg;
    const limit = blockSizeArg;

    loading.set(true);
    try {
      // Transform filters for backend
      let backendFilter = opts?.queryFilter;
      if (backendFilter && arrayFields.size > 0) {
        backendFilter = transformFilterForBackend(backendFilter, arrayFields);
      }

      // Generate query hash for current request
      const currentQueryHash = generateQueryHash(opts?.queryFilter, opts?.querySort);

      const response = await apiFetch({ 
        offset, 
        limit, 
        filter: backendFilter, 
        sort: opts?.querySort 
      });

      const newOrgId = response.org_id || 0;
      const newTableVersions = response.version || [];
      const items = (response.items ?? []).map(normalizeItem);

      // Check if fingerprint changed
      //const fingerprintCheck = hasFingerprintChanged(newOrgId, newTableVersions);

      // Check if query changed (filter/sort)
      //const queryChanged = currentQueryHash !== this.currentQueryHash;

      let shouldClearCache = false;


      if (currentOrgId === 0) {
        // 🟢 CASE: First request - initialize fingerprint
        updateFingerprint(newOrgId, newTableVersions, currentQueryHash);
      }else {
      // Check for changes
      const fingerprintCheck = hasFingerprintChanged(newOrgId, newTableVersions);
      const queryChanged = currentQueryHash !== this.currentQueryHash;

      if (fingerprintCheck.changed) {
        // 🔴 CASE: Fingerprint changed (org_id or table versions)
        console.log(`🔄 ${fingerprintCheck.reason}`);
        if (fingerprintCheck.changedTables) {
          console.log(`   Changed tables: ${fingerprintCheck.changedTables.join(', ')}`);
        }
        shouldClearCache = true;
      } else if (queryChanged) {
        // 🟡 CASE: Same data, different query (filter/sort changed)
        console.log(`🔄 Query changed (filter/sort)`);
        shouldClearCache = true;
      }

      if (shouldClearCache) {
        clearCache();
        updateFingerprint(newOrgId, newTableVersions, currentQueryHash);
      }
    }

      // Store in cache using LRU-aware helper
      addBlockToCache(blockNum, items);

      // Update pagination total
      pagination.update(p => ({ 
        ...p, 
        total: response.total || items.length
      }));

      return { items, total: response.total || items.length };

    } finally {
      loading.set(false);
    }
  }

  // Use existing fetchEntityBlock reference
  const fetchEntityBlock = (blockNum: number) => 
    fetchBlock(blockNum, blockSize, { queryFilter: lastQueryFilter, querySort: lastQuerySort });

  const paginationApi = createGenericPagination<T & { id: string | number }>({
    cacheStore: cache as Writable<Record<number, (T & { id: string | number })[]>>,
    paginationStore: pagination as Writable<PaginatedData<T & { id: string | number }>>,
    fetchBlock: (blockNum, bs) => fetchBlock(blockNum, bs, { queryFilter: lastQueryFilter, querySort: lastQuerySort }),
    getId: (item) => item.id,
    blockSize,
    getIsFullyCached: () => isFullyCached
  });

  // ------------------------------
  // Lazy Prefetch Helpers (unchanged)
  // ------------------------------
  async function ensureAllBlocksCached() {
    const cacheVal = get(cache);
    const backendTotal = get(pagination).total;
    const totalBlocks = Math.max(1, Math.ceil(backendTotal / blockSize));

    for (let b = 1; b <= totalBlocks; b++) {
      if (!cacheVal[b]) {
        const { items } = await fetchBlock(b, blockSize, { queryFilter: lastQueryFilter, querySort: lastQuerySort });
        cacheVal[b] = items;
      } else {
        // mark as recently used
        touchBlockInCache(b);
      }
    }
    cache.set({ ...cacheVal });
  }

  function invalidateBlocks(startingBlockNum: number) {
    const currentCache = get(cache);
    const newCache: Record<number, (T & { id: string | number })[]> = {};

    for (const blockNumStr in currentCache) {
      const blockNum = Number(blockNumStr);
      if (blockNum < startingBlockNum) {
        newCache[blockNum] = currentCache[blockNum];
      }
    }

    cache.set(newCache);
    // Rebuild cacheBlocks to reflect new cache state (preserve order of remaining)
    cacheBlocks = Object.keys(newCache).map(k => Number(k)).sort((a, b) => a - b);
    console.log(`Cache invalidated from block ${startingBlockNum} onwards.`);
  }

  // ------------------------------
  // Refactored setView (Pagination)
  // ------------------------------
  async function setView(page: number, pageSize: number, opts?: { queryFilter?: any; querySort?: any }) {
    const safePage = Math.max(1, Math.floor(page));
    const safeSize = Math.max(1, Math.floor(pageSize));

    lastQueryFilter = opts?.queryFilter;
    lastQuerySort = opts?.querySort;

    let backendTotal = get(pagination).total;
    if (backendTotal === 0) {
      const { items, total } = await fetchBlock(1, blockSize, { queryFilter: lastQueryFilter, querySort: lastQuerySort });
      const cacheVal = get(cache);
      cacheVal[1] = items;
      // mark block 1 as used
      touchBlockInCache(1);
      cache.set({ ...cacheVal });
      backendTotal = total;
      pagination.update(p => ({ ...p, total }));
    }

    isFullyCached = backendTotal <= maxCacheableTotal;

    // Lazy: only fetch the block needed for this page
    const targetBlockNum = Math.floor((safePage - 1) * safeSize / blockSize) + 1;
    const cacheVal = get(cache);
    if (!cacheVal[targetBlockNum]) {
      const { items } = await fetchBlock(targetBlockNum, blockSize, { queryFilter: lastQueryFilter, querySort: lastQuerySort });
      cacheVal[targetBlockNum] = items;
      cache.set({ ...cacheVal });
    } else {
      touchBlockInCache(targetBlockNum);
    }

    // If filter/sort requested and fully cached → load all blocks
    if (isFullyCached && (lastQueryFilter || lastQuerySort)) {
      await ensureAllBlocksCached();
    }

    let allItems = Object.entries(get(cache))
      .sort((a, b) => Number(a[0]) - Number(b[0]))
      .flatMap(([, block]) => block);

    if (isFullyCached) {
      allItems = applyLocalFilter(allItems, lastQueryFilter);
      allItems = applyLocalSort(allItems, lastQuerySort);
    }

    const totalItems = allItems.length;
    const totalPages = Math.max(1, Math.ceil(totalItems / safeSize));
    const start = (safePage - 1) * safeSize;
    const items = allItems.slice(start, start + safeSize);

    pagination.set({
      items,
      total: totalItems,
      page: safePage,
      page_size: safeSize,
      total_pages: totalPages,
      has_next: safePage < totalPages,
      has_prev: safePage > 1
    });

    // Optional adjacent prefetch
    maybePrefetchAdjacent(safePage, safeSize);
  }

  // ------------------------------
  // Local Filter / Sort Helpers (unchanged)
  // ------------------------------
  function applyLocalFilter(items: (T & { id: string | number })[], filter?: any) {
    if (!filter) return items;
    let result = items;

    if (filter.q) {
      const q = String(filter.q).toLowerCase();

      if (filter.fields && Array.isArray(filter.fields)) {
        result = result.filter(item =>
          filter.fields.some(field =>
            searchableFields.includes(field) &&
            String((item as any)[field] ?? '').toLowerCase().includes(q)
          )
        );
      } else {
        result = result.filter(item =>
          searchableFields.some(field =>
            String((item as any)[field] ?? '').toLowerCase().includes(q)
          )
        );
      }
    }

    for (const [key, value] of Object.entries(filter)) {
      if (key === 'q' || key === 'field' || key === 'fields' || value === 'all') continue;
      if (value === undefined || value === null) continue;

      const isArrayField = arrayFields.has(key);

      result = result.filter(item => {
        const itemValue = (item as any)[key];

        if (isArrayField) {
          return Array.isArray(itemValue) && itemValue.some(v => 
            String(v).toLowerCase() === String(value).toLowerCase()
          );
        } else {
          return String(itemValue).toLowerCase() === String(value).toLowerCase();
        }
      });
    }

    return result;
  }

  function applyLocalSort(items: (T & { id: string | number })[], sort?: any) {
    if (!sort) return items;

    const sortEntries = Object.entries(sort).filter(([field]) =>
      sortableFields.includes(field)
    );

    return [...items].sort((a, b) => {
      for (const [field, direction] of sortEntries) {
        const av = (a as any)[field];
        const bv = (b as any)[field];

        if (av === bv) continue;
        if (av == null) return direction === 'asc' ? -1 : 1;
        if (bv == null) return direction === 'asc' ? 1 : -1;

        if (direction === 'asc') return av > bv ? 1 : -1;
        return av < bv ? 1 : -1;
      }
      return 0;
    });
  }

  // ------------------------------
  // Direct Lookup (unchanged)
  // ------------------------------
  async function getById(id: string | number) {
    if (isFullyCached) {
      await ensureAllBlocksCached();
      const allItems = Object.values(get(cache)).flat();
      return allItems.find(item => item.id === id) || null;
    } else {
      await setView(1, get(pagination).page_size, { queryFilter: { ids: [id] } });
      const allItems = Object.values(get(cache)).flat();
      return allItems.find(item => item.id === id) || null;
    }
  }

  async function getManyByIds(ids: (string | number)[]) {
    if (isFullyCached) {
      await ensureAllBlocksCached();
      const allItems = Object.values(get(cache)).flat();
      return allItems.filter(item => ids.includes(item.id));
    } else {
      await setView(1, get(pagination).page_size, { queryFilter: { ids } });
      const allItems = Object.values(get(cache)).flat();
      return allItems.filter(item => ids.includes(item.id));
    }
  }

  // ------------------------------
  // Mutations (updated to clear fingerprint)
  // ------------------------------
  async function addItem(data: Partial<T> | Partial<T>[]) {
    if (!createFn) throw new Error(`${entityName} store has no createFn`);
    mutating.set(true);
    try {
      const created = await createFn(data);
      const entities = Array.isArray(created) ? created : [created];
      const normalized = entities.map(normalizeItem);

      if (isFullyCached) {
        await ensureAllBlocksCached();
        for (const entity of normalized) paginationApi.addOrUpdateItem(entity);
      } else {
        const { page, page_size } = get(pagination);
        const currentBlock = Math.floor((page - 1) * page_size / blockSize) + 1;
        invalidateBlocks(currentBlock);
        await fetchEntityBlock(currentBlock);
        pagination.update(p => ({ ...p, total: p.total + normalized.length }));
      }

      // Clear fingerprint on mutation (tables changed)
      currentTableVersions.clear();
      currentOrgId = 0;

      return normalized;
    } finally {
      mutating.set(false);
    }
  }

  async function updateItem(id: (string | number)[], data: Partial<T>[]) {
    if (!updateFn) throw new Error(`${entityName} store has no updateFn`);
    mutating.set(true);
    try {
      const updated = await updateFn(data);
      const entities = Array.isArray(updated) ? updated : [updated];
      const normalized = entities.map(normalizeItem);

      if (isFullyCached) {
        await ensureAllBlocksCached();
        for (const entity of normalized) {
          paginationApi.addOrUpdateItem(entity);
        }
      } else {
        const { page, page_size } = get(pagination);
        const currentBlock = Math.floor((page - 1) * page_size / blockSize) + 1;
        await fetchEntityBlock(currentBlock);
      }

      // Clear fingerprint on mutation (tables changed)
      currentTableVersions.clear();
      currentOrgId = 0;

      return normalized;
    } finally {
      mutating.set(false);
    }
  }

  async function deleteItem(id: (string | number)[]) {
    if (!deleteFn) throw new Error(`${entityName} store has no deleteFn`);
    mutating.set(true);
    try {
      await deleteFn(id);
      const { page, page_size, total } = get(pagination);
      const currentBlock = Math.floor((page - 1) * page_size / blockSize) + 1;

      const startingBlockToInvalidate = currentBlock;
      invalidateBlocks(startingBlockToInvalidate);
      paginationApi.deleteItem(id);
      pagination.update(p => ({ 
        ...p, 
        total: Math.max(0, total - id.length) 
      }));

      if (isFullyCached) {
        await setView(page, page_size, { queryFilter: lastQueryFilter, querySort: lastQuerySort });
      } else {
        await fetchBlock(currentBlock, blockSize, { queryFilter: lastQueryFilter, querySort: lastQuerySort });
      }

      // Clear fingerprint on mutation (tables changed)
      currentTableVersions.clear();
      currentOrgId = 0;

    } catch (error) {
      console.error('Delete failed in store:', error);
      throw error;
    } finally {
      mutating.set(false);
    }
  }

  // ------------------------------
  // Bulk Actions / Export (unchanged)
  // ------------------------------
  async function ensureFullCacheForBulk() {
    if (isFullyCached) {
      await ensureAllBlocksCached();
    }
  }

  async function maybePrefetchAdjacent(page: number, pageSize: number) {
    if (!isFullyCached) return;

    const totalPages = get(pagination).total_pages;
    const cacheVal = get(cache);

    const nextPage = page + 1;
    if (nextPage <= totalPages) {
      const nextBlockNum = Math.floor((nextPage - 1) * pageSize / blockSize) + 1;
      if (!cacheVal[nextBlockNum]) {
        const { items } = await fetchBlock(nextBlockNum, blockSize, {
          queryFilter: lastQueryFilter,
          querySort: lastQuerySort
        });
        cacheVal[nextBlockNum] = items;
        cache.set({ ...cacheVal });
      } else {
        touchBlockInCache(nextBlockNum);
      }
    }

    const prevPage = page - 1;
    if (prevPage >= 1) {
      const prevBlockNum = Math.floor((prevPage - 1) * pageSize / blockSize) + 1;
      if (!cacheVal[prevBlockNum]) {
        const { items } = await fetchBlock(prevBlockNum, blockSize, {
          queryFilter: lastQueryFilter,
          querySort: lastQuerySort
        });
        cacheVal[prevBlockNum] = items;
        cache.set({ ...cacheVal });
      } else {
        touchBlockInCache(prevBlockNum);
      }
    }
  }

  // NEW: Get current fingerprint
  function getFingerprint() {
    return {
      org_id: currentOrgId,
      table_versions: Array.from(currentTableVersions.entries()).map(([table, version]) => 
        ({ table_name: table, table_version: version, org_id: currentOrgId })),
      query_hash: currentQueryHash
    };
  }

  // NEW: Force refresh fingerprint
  async function refreshFingerprint() {
    currentTableVersions.clear();
    currentOrgId = 0;
    // Fetch a single item to get latest fingerprint
    await fetchBlock(1, 1, { 
      queryFilter: lastQueryFilter, 
      querySort: lastQuerySort 
    });
  }

  // ------------------------------
  // Return API
  // ------------------------------
  return {
    entityName,
    cache,
    pagination,
    loading,
    mutating,
    ...paginationApi,
    fetchEntityBlock: (blockNum: number) => fetchBlock(blockNum, blockSize, { 
      queryFilter: lastQueryFilter, 
      querySort: lastQuerySort 
    }),
    setView,
    getById,
    getManyByIds,
    ensureFullCacheForBulk,
    // NEW methods
    getFingerprint,
    refreshFingerprint,
    clearCache,
    ...(createFn ? { addItem } : {}),
    ...(updateFn ? { updateItem } : {}),
    ...(deleteFn ? { deleteItem } : {})
  };
}