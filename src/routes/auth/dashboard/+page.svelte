<script>
  export let data;
</script>

<div class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
  <div class="px-4 py-6 sm:px-0">
    <h1 class="text-3xl font-bold text-gray-900 mb-6">Dashboard</h1>
    
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
      <div class="bg-white overflow-hidden shadow rounded-lg">
        <div class="px-4 py-5 sm:p-6">
          <dt class="text-sm font-medium text-gray-500 truncate">Total Users</dt>
          <dd class="mt-1 text-3xl font-semibold text-gray-900">{data.stats?.totalUsers || 0}</dd>
        </div>
      </div>
      
      <div class="bg-white overflow-hidden shadow rounded-lg">
        <div class="px-4 py-5 sm:p-6">
          <dt class="text-sm font-medium text-gray-500 truncate">Active Sessions</dt>
          <dd class="mt-1 text-3xl font-semibold text-gray-900">{data.stats?.activeSessions || 0}</dd>
        </div>
      </div>
      
      <div class="bg-white overflow-hidden shadow rounded-lg">
        <div class="px-4 py-5 sm:p-6">
          <dt class="text-sm font-medium text-gray-500 truncate">Your Role</dt>
          <dd class="mt-1 text-3xl font-semibold text-gray-900 capitalize">{data.userData?.role || 'user'}</dd>
        </div>
      </div>
    </div>
  </div>
</div>