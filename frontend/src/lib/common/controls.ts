//controls.ts
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
  deleteItem?: (id: string | number | (string | number)[]) => Promise<T | T[]>;
}) {
  // Add new entity or entities
  async function addItem(data: Partial<T> | Partial<T>[]) {
    if (!store.addItem) {
      throw new Error("addItem not implemented on store");
    }
    return store.addItem(data);
  }

// Update one or many entities (always bulk format)
/**
 * Generic update function.
 * Accepts either a single entity or an array of entities.
 * Caller decides the payload type via generics.
 */
async function updateItem<U>(
  id: string | number | (string | number)[],
  changes: U | U[]
) {
  if (!store.updateItem) {
    throw new Error("updateItem not implemented on store");
  }
  return store.updateItem(id, changes);
}


// Delete one or many entities
async function deleteItem<U>(
    id: (string | number)[]
) {
    if (!store.deleteItem) {
      throw new Error("deleteItem not implemented on store");
    }
    return store.deleteItem(id);
  }

  return { addItem, updateItem, deleteItem };
}

// ------------------------------
// Unified lookup helper with filter/sort
// ------------------------------
/* Example
        import { useLookup } from './controls';
        import { usersStore } from './entityStoreFactory';

        const { getEntities } = useLookup(usersStore);

        // Single ID lookup
        const user = await getEntities(123);

        // Multiple IDs lookup
        const users = await getEntities([101, 102, 103]);

        // Lookup with filter/sort
        const filteredUsers = await getEntities([101, 102, 103], {
        queryFilter: { role: 'admin' },
        querySort: { display_name: 'asc' }
        });
*/
export function useLookup<T>(store: {
  getById: (id: string | number, opts?: { queryFilter?: any; querySort?: any }) => Promise<T | null>;
  getManyByIds: (ids: (string | number)[], opts?: { queryFilter?: any; querySort?: any }) => Promise<T[]>;
}) {
  async function getEntities(
    ids: string | number | (string | number)[],
    opts?: { queryFilter?: any; querySort?: any }
  ) {
    console.log(ids);
    if (Array.isArray(ids)) {
      return store.getManyByIds(ids, opts);
    } else {
      return store.getById(ids, opts);
    }
  }

  return { getEntities };
}
        
