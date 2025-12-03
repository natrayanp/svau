// genericPagination.ts
import { Writable, get } from 'svelte/store';
import type { PaginatedData } from '../permission/types_permission';

type GenericCache<T> = Record<number, T[]>;

type CachePaginationOptions<T> = {
  cacheStore: Writable<GenericCache<T>>;
  paginationStore: Writable<PaginatedData<T>>;
  fetchBlock: (blockNum: number, blockSize: number) => Promise<{ items: T[]; total: number }>;
  getId: (item: T) => string | number;
  blockSize?: number;
  // Awareness: function that tells whether cache is complete (client-side totals) or partial (backend totals)
  getIsFullyCached?: () => boolean;
};

export function createGenericPagination<T>({
  cacheStore,
  paginationStore,
  fetchBlock,
  getId,
  blockSize = 100,
  getIsFullyCached = () => false
}: CachePaginationOptions<T>) {
  function getItemsForPage(cache: GenericCache<T>, page: number, pageSize: number): T[] {
    const start = (page - 1) * pageSize;
    const end = start + pageSize;
    const items: T[] = [];

    const entries = Object.entries(cache) as [string, T[]][];
    for (const [blockNumStr, block] of entries.sort((a, b) => Number(a[0]) - Number(b[0]))) {
      const blockNum = Number(blockNumStr);
      const blockStart = (blockNum - 1) * blockSize;
      const blockEnd = blockStart + block.length;

      if (start < blockEnd && end > blockStart) {
        const localStart = Math.max(0, start - blockStart);
        const localEnd = Math.min(block.length, end - blockStart);
        items.push(...block.slice(localStart, localEnd));
      }
    }

    return items;
  }

  function computeTotal(cache: GenericCache<T>): number {
    // If fully cached, trust cache length; else defer to backend total already in paginationStore
    if (getIsFullyCached()) {
      return Object.values(cache as T[][]).reduce((acc, block) => acc + block.length, 0);
    }
    return get(paginationStore).total;
  }

  function updatePaginationView(page: number, pageSize: number, cache: GenericCache<T>) {
    const totalItems = computeTotal(cache);
    const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
    const items = getItemsForPage(cache, page, pageSize);

    paginationStore.set({
      items,
      total: totalItems,
      page,
      page_size: pageSize,
      total_pages: totalPages,
      has_next: page < totalPages,
      has_prev: page > 1
    });
  }

  function addOrUpdateItem(item: T) {
    const cache = get(cacheStore);
    let updated = false;

    for (const [blockNumStr, block] of Object.entries(cache) as [string, T[]][]) {
      const idx = block.findIndex((u: T) => getId(u) === getId(item));
      if (idx !== -1) {
        const newBlock = [...block];
        newBlock[idx] = item;
        cache[Number(blockNumStr)] = newBlock;
        updated = true;
        break;
      }
    }

    if (!updated) {
      const blockKeys = Object.keys(cache).map(Number).sort((a, b) => a - b);
      const lastBlockNum = blockKeys[blockKeys.length - 1] || 1;
      const lastBlock = cache[lastBlockNum] || [];

      if (lastBlock.length < blockSize) {
        cache[lastBlockNum] = [...lastBlock, item];
      } else {
        cache[lastBlockNum + 1] = [item];
      }
    }

    cacheStore.set({ ...cache });
    const { page, page_size } = get(paginationStore);
    updatePaginationView(page, page_size, cache);
  }

  function deleteItem(itemId: string | number) {
    const cache = get(cacheStore);

    for (const blockNumStr of Object.keys(cache)) {
      const blockNum = Number(blockNumStr);
      const block = cache[blockNum];
      const idx = block.findIndex((u: T) => getId(u) === itemId);
      if (idx !== -1) {
        const newBlock = [...block];
        newBlock.splice(idx, 1);
        cache[blockNum] = newBlock;
        break;
      }
    }

    cacheStore.set({ ...cache });
    const { page, page_size } = get(paginationStore);
    updatePaginationView(page, page_size, cache);
  }

  async function fetchItemBlock(blockNum: number) {
    const response = await fetchBlock(blockNum, blockSize);
    const cache = get(cacheStore);
    cache[blockNum] = [...response.items];
    cacheStore.set({ ...cache });

    const { page, page_size } = get(paginationStore);
    const startIdx = (page - 1) * page_size;
    const endIdx = startIdx + page_size;
    const blockStart = (blockNum - 1) * blockSize;
    const blockEnd = blockStart + blockSize;

    if (startIdx < blockEnd && endIdx > blockStart) {
      updatePaginationView(page, page_size, cache);
    }
  }

  function setPage(newPage: number) {
    const cache = get(cacheStore);
    const { page_size } = get(paginationStore);
    updatePaginationView(newPage, page_size, cache);
  }

  function setPageSize(newSize: number) {
    const cache = get(cacheStore);
    updatePaginationView(1, newSize, cache);
  }

  function getItemById(id: string | number): T | undefined {
    const cache = get(cacheStore);
    for (const block of Object.values(cache) as T[][]) {
      const found = block.find((item: T) => getId(item) === id);
      if (found) return found;
    }
  }

  function invalidateBlock(blockNum: number) {
    const cache = get(cacheStore);
    delete cache[blockNum];
    cacheStore.set({ ...cache });
  }

  function clearCache() {
    cacheStore.set({});
    paginationStore.set({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
      total_pages: 0,
      has_next: false,
      has_prev: false
    });
  }

  return {
    updatePaginationView,
    addOrUpdateItem,
    deleteItem,
    fetchItemBlock,
    setPage,
    setPageSize,
    getItemById,
    invalidateBlock,
    clearCache
  };
}
