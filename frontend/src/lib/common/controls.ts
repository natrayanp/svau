import { writable, derived, get, type Writable } from 'svelte/store';
import type { PaginatedData } from '$lib/permission/types_permission';

// ------------------------------
// Selection controls
// ------------------------------
export function useSelection() {
  const selectedIds: Writable<string[]> = writable([]);

  function toggleSelection(id: string | number | undefined | null) {
    if (id === undefined || id === null) return;
    const safeId = String(id);
    selectedIds.update(ids =>
      ids.includes(safeId) ? ids.filter(x => x !== safeId) : [...ids, safeId]
    );
  }

  function clearSelection() {
    selectedIds.set([]);
  }

  return { selectedIds, toggleSelection, clearSelection };
}

// ------------------------------
// Page-aware selection
// ------------------------------
export function usePageSelection<T>(
  paginationStore: Writable<PaginatedData<T>>,
  idKey: keyof T = 'id'
) {
  const { selectedIds, toggleSelection, clearSelection } = useSelection();

  function toggleAllPageItems(pagedItems: T[]) {
    const pageIds = pagedItems
      .map(item => item[idKey])
      .filter(id => id !== undefined && id !== null)
      .map(String);

    if (pageIds.length === 0) return;

    selectedIds.update(current => {
      const allSelected = pageIds.every(id => current.includes(id));
      return allSelected
        ? current.filter(id => !pageIds.includes(id))
        : [...new Set([...current, ...pageIds])];
    });
  }

  // ✅ Derived stores
  const allPageItemsSelected = derived(
    [selectedIds, paginationStore],
    ([$ids, $pagination]) => {
      const pagedItems = $pagination.items ?? [];
      return pagedItems.length > 0 &&
             pagedItems.every(item => $ids.includes(String(item[idKey])));
    }
  );

  const somePageItemsSelected = derived(
    [selectedIds, paginationStore, allPageItemsSelected],
    ([$ids, $pagination, $all]) => {
      const pagedItems = $pagination.items ?? [];
      return pagedItems.some(item => $ids.includes(String(item[idKey]))) && !$all;
    }
  );

  const hasSelectedItems = derived(selectedIds, $ids => $ids.length > 0);

  // Select all filtered items across all pages
  async function selectAllFilteredItems(fetchAllFn: () => Promise<T[]>) {
    const allItems = await fetchAllFn();
    const allIds = allItems
      .map(item => item[idKey])
      .filter(id => id !== undefined && id !== null)
      .map(String);

    selectedIds.set([...new Set([...get(selectedIds), ...allIds])]);
  }

  return {
    selectedIds,
    toggleSelection,
    clearSelection,
    toggleAllPageItems,
    allPageItemsSelected,
    somePageItemsSelected,
    hasSelectedItems,
    selectAllFilteredItems
  };
}

// ------------------------------
// Pagination controls
// ------------------------------
export function usePaginationControls<T>(store: {
  pagination: Writable<PaginatedData<T>>;
  setView: (page: number, size: number, opts?: any) => Promise<void>;
}) {
  const currentPage = derived(store.pagination, $p => $p.page);
  const pageSize = derived(store.pagination, $p => $p.page_size);
  const totalPages = derived(store.pagination, $p => $p.total_pages);
  const totalItems = derived(store.pagination, $p => $p.total);

  function goToPage(page: number) {
    const { page_size } = get(store.pagination);
    store.setView(page, page_size);
  }

  function nextPage() {
    const { page, page_size, total_pages } = get(store.pagination);
    if (page < total_pages) store.setView(page + 1, page_size);
  }

  function prevPage() {
    const { page, page_size } = get(store.pagination);
    if (page > 1) store.setView(page - 1, page_size);
  }

  function setPageSize(size: number) {
    const { page } = get(store.pagination);
    store.setView(page, size);
  }

  return {
    currentPage,
    pageSize,
    totalPages,
    totalItems,
    goToPage,
    nextPage,
    prevPage,
    setPageSize
  };
}

// ------------------------------
// Generic filter type
// ------------------------------
export type QueryFilter<T> = Partial<Record<keyof T, any>> & {
  q?: string;
};

// ------------------------------
// Generic filter builder
// ------------------------------
export function buildFilter<T>(
  values: Record<string, any>,
  allowedKeys: (keyof T | 'q')[]
): QueryFilter<T> {
  const filter: QueryFilter<T> = {};
  for (const key of allowedKeys) {
    const val = values[key as string];
    if (val !== undefined && val !== 'all' && val !== '') {
      filter[key] = val;
    }
  }
  return filter;
}

// ------------------------------
// Generic sort builder
// ------------------------------
export type QuerySort<T> = Partial<Record<keyof T, 'asc' | 'desc'>> | string;

export function buildSort<T>(
  field: keyof T,
  direction: 'asc' | 'desc'
): QuerySort<T> {
  return { [field]: direction };
}

// ------------------------------
// Mutation helpers
// ------------------------------
export function useMutations<T>(store: {
  addItem?: (data: Partial<T> | Partial<T>[]) => Promise<T | T[]>;
  updateItem?: (
    id: string | number | (string | number)[],
    changes: Partial<T> | Partial<T>[]
  ) => Promise<T | T[]>;
  deleteItem?: (id: string | number | (string | number)[]) => Promise<void>;
}) {
  async function add(data: Partial<T> | Partial<T>[]) {
    return store.addItem?.(data);
  }
  async function update(
    id: string | number | (string | number)[],
    changes: Partial<T> | Partial<T>[]
  ) {
    return store.updateItem?.(id, changes);
  }
  async function remove(id: string | number | (string | number)[]) {
    return store.deleteItem?.(id);
  }
  return { add, update, remove };
}
