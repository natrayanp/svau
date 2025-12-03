// entityStoreFactory.ts
import { writable, get, type Writable } from 'svelte/store';
import type { PaginatedData } from '../permission/types_permission';
import { createGenericPagination } from './genericPagination';

type ApiFetch<T> = (params: {
  offset: number;
  limit: number;
  filter?: any;
  sort?: any;
}) => Promise<PaginatedData<T>>;

type MutationCreate<T> = (data: Partial<T> | Partial<T>[]) => Promise<T | T[]>;
type MutationUpdate<T> = (id: string | number | (string | number)[], data: Partial<T> | Partial<T>[]) => Promise<T | T[]>;
type MutationDelete = (id: string | number | (string | number)[]) => Promise<void>;

// ------------------------------
// Helper: apply local filter/sort
// ------------------------------
function applyLocalFilter<T>(items: (T & { id: string | number })[], filter?: Record<string, any>): (T & { id: string | number })[] {
  if (!filter) return items;
  return items.filter((item: any) => {
    let ok = true;
    if (filter.q) {
      const q = String(filter.q).toLowerCase();
      ok = ok && (
        (item.display_name?.toLowerCase().includes(q)) ||
        (item.email?.toLowerCase().includes(q))
      );
    }
    if (filter.role || filter.role_key) {
      const roleVal = filter.role ?? filter.role_key;
      ok = ok && (item.roles ?? []).includes(roleVal);
    }
    return ok;
  });
}

function applyLocalSort<T>(items: (T & { id: string | number })[], sort?: any): (T & { id: string | number })[] {
  if (!sort) return items;
  if (typeof sort === 'string') {
    return [...items].sort((a: any, b: any) => String(a[sort]).localeCompare(String(b[sort])));
  }
  if (typeof sort === 'object') {
    const [[field, dir]] = Object.entries(sort);
    return [...items].sort((a: any, b: any) => {
      const cmp = String(a[field]).localeCompare(String(b[field]));
      return dir === 'desc' ? -cmp : cmp;
    });
  }
  return items;
}

// ------------------------------
// Factory
// ------------------------------
export function createEntityStore<T>(
  entityName: string,
  apiFetch: ApiFetch<T>,
  getId: (item: T) => string | number,
  blockSize = 100,
  maxCacheableTotal = 5000,
  createFn?: MutationCreate<T>,
  updateFn?: MutationUpdate<T>,
  deleteFn?: MutationDelete
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

  let isFullyCached = false;
  let lastQueryFilter: Record<string, any> | undefined = undefined;
  let lastQuerySort: any | undefined = undefined;

  function normalizeItem(item: T): T & { id: string | number } {
    const id = getId(item);
    return { ...item, id };
  }

  async function fetchBlock(
    blockNum: number,
    blockSizeArg: number,
    opts?: { queryFilter?: any; querySort?: any }
  ): Promise<{ items: (T & { id: string | number })[]; total: number }> {
    const offset = (blockNum - 1) * blockSizeArg;
    const limit = blockSizeArg;
    loading.set(true);
    try {
      const response = await apiFetch({
        offset,
        limit,
        filter: opts?.queryFilter,
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

  const inflight = new Map<number, Promise<void>>();
  async function fetchEntityBlock(blockNum: number) {
    if (inflight.has(blockNum)) return inflight.get(blockNum);
    const promise = (async () => {
      const { items, total } = await fetchBlock(blockNum, blockSize, {
        queryFilter: lastQueryFilter,
        querySort: lastQuerySort
      });
      const cacheVal = get(cache);
      cacheVal[blockNum] = [...items];
      cache.set({ ...cacheVal });

      if (!isFullyCached) {
        pagination.update(p => ({ ...p, total }));
      }

      const { page, page_size } = get(pagination);
      const startIdx = (page - 1) * page_size;
      const endIdx = startIdx + page_size;
      const blockStart = (blockNum - 1) * blockSize;
      const blockEnd = blockStart + blockSize;
      if (startIdx < blockEnd && endIdx > blockStart) {
        paginationApi.updatePaginationView(page, page_size, get(cache));
      }
    })().finally(() => inflight.delete(blockNum));

    inflight.set(blockNum, promise);
    return promise;
  }

  function maybePrefetchAdjacent(page: number, pageSize: number) {
    const safePage = Math.max(1, Math.floor(page));
    const safeSize = Math.max(1, Math.floor(pageSize));
    const start = (safePage - 1) * safeSize;
    const blockNum = Math.floor(start / blockSize) + 1;
    const nextBlock = blockNum + 1;
    const prevBlock = blockNum - 1;
    const cacheVal = get(cache);
    if (!cacheVal[nextBlock]) void fetchEntityBlock(nextBlock);
    if (prevBlock > 0 && !cacheVal[prevBlock]) void fetchEntityBlock(prevBlock);
  }
  // ------------------------------
  // Refactored setView
  // ------------------------------
  async function setView(page: number, pageSize: number, opts?: { queryFilter?: any; querySort?: any }) {
    const safePage = Math.max(1, Math.floor(page));
    const safeSize = Math.max(1, Math.floor(pageSize));

    lastQueryFilter = opts?.queryFilter;
    lastQuerySort = opts?.querySort;

    let cacheVal = get(cache);
    let backendTotal = get(pagination).total;

    if (backendTotal === 0) {
      const { items, total } = await fetchBlock(1, blockSize, {
        queryFilter: lastQueryFilter,
        querySort: lastQuerySort
      });
      cacheVal[1] = items;
      cache.set({ ...cacheVal });
      backendTotal = total;
      pagination.update(p => ({ ...p, total }));
    }

    isFullyCached = backendTotal <= maxCacheableTotal;

    if (isFullyCached) {
      const totalBlocks = Math.max(1, Math.ceil(backendTotal / blockSize));
      for (let b = 1; b <= totalBlocks; b++) {
        if (!cacheVal[b]) {
          const { items } = await fetchBlock(b, blockSize, {
            queryFilter: lastQueryFilter,
            querySort: lastQuerySort
          });
          cacheVal[b] = items;
        }
      }
      cache.set({ ...cacheVal });

      let allItems = Object.entries(cacheVal)
        .sort((a, b) => Number(a[0]) - Number(b[0]))
        .flatMap(([, block]) => block);

      allItems = applyLocalFilter(allItems, lastQueryFilter);
      allItems = applyLocalSort(allItems, lastQuerySort);

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

      maybePrefetchAdjacent(safePage, safeSize);
    } else {
      const targetBlockNum = Math.floor((safePage - 1) * safeSize / blockSize) + 1;
      const { items, total } = await fetchBlock(targetBlockNum, blockSize, {
        queryFilter: lastQueryFilter,
        querySort: lastQuerySort
      });

      cacheVal[targetBlockNum] = items;
      cache.set({ ...cacheVal });

      pagination.set({
        items,
        total,
        page: safePage,
        page_size: safeSize,
        total_pages: Math.max(1, Math.ceil(total / safeSize)),
        has_next: safePage * safeSize < total,
        has_prev: safePage > 1
      });
    }
  }

  // ------------------------------
  // Mutation helpers
  // ------------------------------
  function computeBlockNumForIndex(index: number) {
    return Math.floor(index / blockSize) + 1;
  }

  async function addItem(data: Partial<T> | Partial<T>[]) {
    if (!createFn) throw new Error(`${entityName} store has no createFn`);
    mutating.set(true);
    try {
      const created = await createFn(data);
      const entities = Array.isArray(created) ? created : [created];
      const normalized = entities.map(normalizeItem);

      if (isFullyCached) {
        for (const entity of normalized) paginationApi.addOrUpdateItem(entity);
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

  async function updateItem(id: string | number | (string | number)[], data: Partial<T> | Partial<T>[]) {
    if (!updateFn) throw new Error(`${entityName} store has no updateFn`);
    mutating.set(true);
    try {
      const updated = await updateFn(id, data);
      const entities = Array.isArray(updated) ? updated : [updated];
      const normalized = entities.map(normalizeItem);

      if (isFullyCached) {
        for (const entity of normalized) paginationApi.addOrUpdateItem(entity);
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

  async function deleteItem(id: string | number | (string | number)[]) {
    if (!deleteFn) throw new Error(`${entityName} store has no deleteFn`);
    mutating.set(true);
    try {
      const ids = Array.isArray(id) ? id : [id];
      await deleteFn(ids);

      if (isFullyCached) {
        for (const singleId of ids) paginationApi.deleteItem(singleId);
      } else {
        const { page, page_size } = get(pagination);
        const currentBlock = Math.floor((page - 1) * page_size / blockSize) + 1;
        await fetchEntityBlock(currentBlock);
      }
    } finally {
      mutating.set(false);
    }
  }

  return {
    entityName,
    cache,
    pagination,
    loading,
    mutating,
    ...paginationApi,
    fetchEntityBlock,
    setView,
    ...(createFn ? { addItem } : {}),
    ...(updateFn ? { updateItem } : {}),
    ...(deleteFn ? { deleteItem } : {})
  };
}
