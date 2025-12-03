// readonlyStoreFactory.ts
import { writable } from 'svelte/store';

/**
 * Generic factory for read-only stores.
 * Use this for global data that doesn't need CRUD or pagination.
 *
 * @param entityName - name of the entity (for debugging/logging)
 * @param apiFetch - async function that fetches the entity from backend
 */
export function createReadonlyStore<T>(
  entityName: string,
  apiFetch: () => Promise<T>
) {
  const data = writable<T | null>(null);
  const loading = writable(false);

  async function load() {
    loading.set(true);
    try {
      const response = await apiFetch();
      data.set(response);
    } catch (err) {
      console.error(`${entityName} store load error:`, err);
      data.set(null);
    } finally {
      loading.set(false);
    }
  }

  async function refresh() {
    // semantic alias for load()
    return load();
  }

  async function sync(extraCall: () => Promise<void>) {
    // optional hook for side-effects (e.g. update last login)
    try {
      await extraCall();
    } catch (err) {
      console.error(`${entityName} store sync error:`, err);
    }
  }

  return {
    data,       // store holding the entity
    loading,    // store for loading state
    load,       // initial fetch
    refresh,    // re-fetch when needed
    sync        // optional backend side-effect
  };
}
