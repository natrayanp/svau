<script>
  import { isAuthenticated, authUser } from '$lib/auth/authStore';
  import '../app.css';
  import MockUserSwitcher from '$lib/auth/MockUserSwitcher.svelte';
</script>

<div class="min-h-screen bg-gray-50">
  <slot />

<MockUserSwitcher />
{#if import.meta.env.PUBLIC_GLOBAL_MOCK_OVERRIDE === 'true' || import.meta.env.PUBLIC_SHOW_MOCK_SWITCHER === 'true'}
<div>ddsds</div>    

{/if}


</div>
