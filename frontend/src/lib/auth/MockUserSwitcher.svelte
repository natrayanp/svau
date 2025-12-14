<script>
  import { mockAuthEnabled, mockRole } from "$lib/auth/mockAuth";

  const roles = ["admin", "moderator", "user"];
</script>

<div class="fixed bottom-4 right-4 bg-gray-900 text-white p-4 rounded shadow-lg z-50">
  <label class="flex items-center space-x-2">
    <input type="checkbox" bind:checked={$mockAuthEnabled} />
    <span>Mock Auth</span>
  </label>

  {#if $mockAuthEnabled}
    <div class="mt-2">
      <label for="mock-role" class="block text-sm mb-1">Mock Role</label>
        <select id="mock-role" bind:value={$mockRole} class="text-black p-1 rounded">
        {#each roles as r}
          <option value={r}>{r}</option>
        {/each}
      </select>
    </div>
  {/if}
</div>
