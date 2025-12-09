// entityStoreFactory.ts
import { writable, get, type Writable } from 'svelte/store';
import type { PaginatedData,ApiFetch } from '../permission/stores/types_permission';
import { createGenericPagination } from './genericPagination';



export function createEntityStore<T>(
  entityName: string,
  apiFetch: (data:ApiFetch) => Promise<PaginatedData<T>>,
  getId: (item: T) => string | number,
  blockSize = 100,
  maxCacheableTotal = 5000,
  fieldConfig: {
    searchable?: string[];
    sortable?: string[];
    arrayFields?: string[];
  } = {},
  createFn?: (data: Partial<T> | Partial<T>[]) => Promise<T | T[]>,
  updateFn?: (data: U[]) => Promise<T[]>,
  deleteFn?: (id: (string | number)[]) => Promise<U>
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

  const fetchEntityBlock = (blockNum: number) => 
  fetchBlock(blockNum, blockSize, { queryFilter: lastQueryFilter, querySort: lastQuerySort });


  const loading = writable(false);
  const mutating = writable(false);

  const searchableFields = fieldConfig.searchable ?? [];
  const sortableFields = fieldConfig.sortable ?? [];
  const arrayFields = new Set(fieldConfig.arrayFields ?? []);

  let isFullyCached = false;
  let lastQueryFilter: Record<string, any> | undefined = undefined;
  let lastQuerySort: any | undefined = undefined;

  function normalizeItem(item: T): T & { id: string | number } {
    const id = getId(item);
    return { ...item, id };
  }


  // Helper function to transform filters for backend
  function transformFilterForBackend(filter: any, arrayFields: Set<string>): any {
    if (!filter) return filter;
    
    const result = { ...filter };
    
    for (const [key, value] of Object.entries(filter)) {
      // Skip special fields
      if (key === 'q' || key === 'field' || key === 'fields') continue;
      
      // Skip 'all' or empty values
      if (value === undefined || value === null || value === 'all') continue;
      
      // Transform array fields for backend
      if (arrayFields.has(key)) {
        // Choose the format your backend expects:
        // Format 1: Contains filter
        result[`${key}_contains`] = [value];
        delete result[key];
        
        // Format 2: In filter
        // result[`${key}_in`] = [value];
        // delete result[key];
        
        // Format 3: Direct array (if backend accepts array = value)
        // result[key] = [value];
      }
    }
    
    return result;
  }



  async function fetchBlock(blockNum: number, blockSizeArg: number, opts?: { queryFilter?: any; querySort?: any }) {
    const offset = (blockNum - 1) * blockSizeArg;
    const limit = blockSizeArg;
    loading.set(true);
    try {
      // Transform filters for backend (array field support)
      let backendFilter = opts?.queryFilter;
      if (backendFilter && arrayFields.size > 0) {
        backendFilter = transformFilterForBackend(backendFilter, arrayFields);
      }
      
      const response = await apiFetch({ 
        offset, 
        limit, 
        filter: backendFilter, 
        sort: opts?.querySort 
      });
      
      const items = (response.items ?? []).map(normalizeItem);
      return { items, total: response.total ?? items.length };
    } finally {
      loading.set(false);
    }
  }

  const paginationApi = createGenericPagination<T & { id: string | number }>({
    cacheStore: cache as Writable<Record<number, (T & { id: string | number })[]>>,
    paginationStore: pagination as Writable<PaginatedData<T & { id: string | number }>>,
    fetchBlock: (blockNum, bs) => fetchBlock(blockNum, bs, { queryFilter: lastQueryFilter, querySort: lastQuerySort }),
    getId: (item) => item.id,
    blockSize,
    getIsFullyCached: () => isFullyCached
  });

  // ------------------------------
  // Lazy Prefetch Helpers
  // ------------------------------
  async function ensureAllBlocksCached() {
    const cacheVal = get(cache);
    const backendTotal = get(pagination).total;
    const totalBlocks = Math.max(1, Math.ceil(backendTotal / blockSize));

    for (let b = 1; b <= totalBlocks; b++) {
      if (!cacheVal[b]) {
        const { items } = await fetchBlock(b, blockSize, { queryFilter: lastQueryFilter, querySort: lastQuerySort });
        cacheVal[b] = items;
      }
    }
    cache.set({ ...cacheVal });
  }

  // --- CORE CACHE HELPERS ---
  // CRITICAL NEW HELPER FUNCTION
  /**
   * Invalidates the cache starting from the given block number (1-based) through the end.
   */
  function invalidateBlocks(startingBlockNum: number) {
      const currentCache = get(cache);
      const newCache: Record<number, (T & { id: string | number })[]> = {};

      // Keep blocks *before* the starting block as they are unaffected.
      for (const blockNumStr in currentCache) {
          const blockNum = Number(blockNumStr);
          if (blockNum < startingBlockNum) {
              newCache[blockNum] = currentCache[blockNum];
          }
      }
      // All blocks from startingBlockNum onwards are dropped (invalidated).
      cache.set(newCache);
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
  // Local Filter / Sort Helpers
  // ------------------------------
  // Apply local filter function (also needs array field support)
  function applyLocalFilter(items: (T & { id: string | number })[], filter?: any) {
    if (!filter) return items;
    let result = items;

    // Handle text search (existing logic)
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

    // Apply other filters with array field awareness
    for (const [key, value] of Object.entries(filter)) {
      if (key === 'q' || key === 'field' || key === 'fields' || value === 'all') continue;
      if (value === undefined || value === null) continue;
      
      const isArrayField = arrayFields.has(key);
      
      result = result.filter(item => {
        const itemValue = (item as any)[key];
        
        if (isArrayField) {
          // Array field: check if value exists in array
          return Array.isArray(itemValue) && itemValue.some(v => 
            String(v).toLowerCase() === String(value).toLowerCase()
          );
        } else {
          // Scalar field: direct comparison
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

        if (av === bv) continue; // move to next field
        if (av == null) return direction === 'asc' ? -1 : 1;
        if (bv == null) return direction === 'asc' ? 1 : -1;

        if (direction === 'asc') return av > bv ? 1 : -1;
        return av < bv ? 1 : -1;
      }
      return 0; // all fields equal
    });
  }


  // ------------------------------
  // Direct Lookup
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
  // Mutations (lazy load before local mutation)
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
      return normalized;
    } finally {
      mutating.set(false);
    }
  }


async function updateItem<T>(
  id: (string | number)[],          // always array of IDs
  data: Partial<T>[]                 // always array of payloads
) {
  if (!updateFn) throw new Error(`${entityName} store has no updateFn`);
  mutating.set(true);
  try {
    // Call API with parallel arrays
    const updated = await updateFn(data);

    // Normalize response
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

    return normalized;
  } finally {
    mutating.set(false);
  }
}


  async function deleteItem(
    id: (string | number)[],          // always array of IDs
  ) {
    if (!deleteFn) throw new Error(`${entityName} store has no deleteFn`);
    mutating.set(true);
    try {
      await deleteFn(id);
      const { page, page_size, total } = get(pagination);
      const currentBlock = Math.floor((page - 1) * page_size / blockSize) + 1;

      const startingBlockToInvalidate =  currentBlock;
      invalidateBlocks(startingBlockToInvalidate); // Assumes invalidateBlocks is defined outside
      paginationApi.deleteItem(id);
      pagination.update(p => ({ 
          ...p, 
          total: Math.max(0, total - id.length) 
      }));

      if (isFullyCached) {
        await setView(page, page_size, { queryFilter: lastQueryFilter, querySort: lastQuerySort });

        /*await ensureAllBlocksCached();
        paginationApi.deleteItem(id);*/
      } else {
        await fetchBlock(currentBlock, blockSize, { queryFilter: lastQueryFilter, querySort: lastQuerySort });
        
        /*
        const { page, page_size } = get(pagination);
        const currentBlock = Math.floor((page - 1) * page_size / blockSize) + 1;
        await fetchEntityBlock(currentBlock);*/
      }
    } catch (error) {
        console.error('Delete failed in store:', error);
        throw error;
    } finally {
      mutating.set(false);
    }
  }

  // ------------------------------
  // Bulk Actions / Export
  // ------------------------------
  async function ensureFullCacheForBulk() {
    if (isFullyCached) {
      await ensureAllBlocksCached();
    }
  }


  async function maybePrefetchAdjacent(page: number, pageSize: number) {
  console.log('inside maybeprefetch');
  if (!isFullyCached) return; // only prefetch when caching is enabled
  console.log('inside maybeprefetch af');

  const totalPages = get(pagination).total_pages;
  const cacheVal = get(cache);

  // Prefetch next page block if it exists
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
    }
  }

  // Prefetch previous page block if it exists
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
    }
  }
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
    fetchEntityBlock: (blockNum: number) => fetchBlock(blockNum, blockSize, { queryFilter: lastQueryFilter, querySort: lastQuerySort }),
    setView,
    getById,
    getManyByIds,
    ensureFullCacheForBulk,
    ...(createFn ? { addItem } : {}),
    ...(updateFn ? { updateItem } : {}),
    ...(deleteFn ? { deleteItem } : {})
  };
}
