<script>
  import { onMount } from 'svelte';
  import { PermissionUtils } from '$lib/permission/utils_permission';

  let selectedRole = 'all';
  let analysisData = null;

  const roles = [
    { id: 'all', name: 'All Roles' },
    { id: 'basic', name: 'Basic' },
    { id: 'creator', name: 'Creator' },
    { id: 'moderator', name: 'Moderator' },
    { id: 'admin', name: 'Admin' }
  ];

  // Mock analysis data
  const analysisMap = {
    all: {
      role: 'System Overview',
      permission_count: 35,
      max_power: 100,
      average_power: 45,
      power_distribution: {
        low: 8,
        medium: 7,
        high: 12,
        critical: 8
      },
      most_powerful_permissions: [
        { display_name: 'Admin Access', power_level: 100, action: 'admin' },
        { display_name: 'User Management', power_level: 80, action: 'manage' },
        { display_name: 'System Settings', power_level: 90, action: 'admin' }
      ]
    },
    basic: {
      role: 'Basic',
      permission_count: 8,
      max_power: 10,
      average_power: 10,
      power_distribution: {
        low: 8,
        medium: 0,
        high: 0,
        critical: 0
      },
      most_powerful_permissions: [
        { display_name: 'View Dashboard', power_level: 10, action: 'view' }
      ]
    },
    creator: {
      role: 'Creator',
      permission_count: 15,
      max_power: 30,
      average_power: 22,
      power_distribution: {
        low: 8,
        medium: 7,
        high: 0,
        critical: 0
      },
      most_powerful_permissions: [
        { display_name: 'Edit Content', power_level: 30, action: 'edit' }
      ]
    }
  };

  onMount(() => {
    analysisData = analysisMap.all;
  });

  function updateAnalysis() {
    analysisData = analysisMap[selectedRole] || analysisMap.all;
  }

  $: if (selectedRole) {
    updateAnalysis();
  }

  function getDistributionPercentage(count) {
    return (count / analysisData.permission_count) * 100;
  }
</script>

<svelte:head>
  <title>Power Analysis - AuthApp</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 py-8">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <!-- Header -->
    <div class="mb-8">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-3xl font-bold text-gray-900">Power Analysis</h1>
          <p class="mt-2 text-lg text-gray-600">
            Analyze permission power levels and security risks
          </p>
        </div>
        <div class="flex items-center space-x-4">
          <!-- Role Selector -->
          <select
            bind:value={selectedRole}
            class="border border-gray-300 rounded-lg px-4 py-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            {#each roles as role}
              <option value={role.id}>{role.name}</option>
            {/each}
          </select>
        </div>
      </div>
    </div>

    {#if analysisData}
      <!-- Overview Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <div class="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                <span class="text-2xl">🔐</span>
              </div>
            </div>
            <div class="ml-4">
              <div class="text-sm font-medium text-gray-500">Total Permissions</div>
              <div class="text-2xl font-bold text-gray-900">{analysisData.permission_count}</div>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <div class="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center">
                <span class="text-2xl">⚡</span>
              </div>
            </div>
            <div class="ml-4">
              <div class="text-sm font-medium text-gray-500">Max Power</div>
              <div class="text-2xl font-bold text-gray-900">{analysisData.max_power}/100</div>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <div class="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                <span class="text-2xl">📊</span>
              </div>
            </div>
            <div class="ml-4">
              <div class="text-sm font-medium text-gray-500">Average Power</div>
              <div class="text-2xl font-bold text-gray-900">{analysisData.average_power.toFixed(1)}</div>
            </div>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <div class="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                <span class="text-2xl">🎯</span>
              </div>
            </div>
            <div class="ml-4">
              <div class="text-sm font-medium text-gray-500">Risk Level</div>
                <div class="text-2xl font-bold text-gray-900">
                  {#if analysisData.max_power >= 80}
                    High
                  {:else if analysisData.max_power >= 60}
                    Medium
                  {:else}
                    Low
                  {/if}
                </div>
            </div>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <!-- Power Distribution -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 class="text-xl font-semibold text-gray-900 mb-4">📈 Power Distribution</h2>
          
          <div class="space-y-4">
            {#each [
              { level: 'Low', color: 'green', count: analysisData.power_distribution.low, max: 30 },
              { level: 'Medium', color: 'yellow', count: analysisData.power_distribution.medium, max: 60 },
              { level: 'High', color: 'orange', count: analysisData.power_distribution.high, max: 80 },
              { level: 'Critical', color: 'red', count: analysisData.power_distribution.critical, max: 100 }
            ] as dist}
              <div>
                <div class="flex justify-between text-sm mb-1">
                  <span class="font-medium text-gray-700">{dist.level} (0-{dist.max})</span>
                  <span class="text-gray-500">{dist.count} permissions ({getDistributionPercentage(dist.count).toFixed(1)}%)</span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-3">
                  <div
                    class="h-3 rounded-full bg-{dist.color}-500"
                    style={`width: ${getDistributionPercentage(dist.count)}%`}
                  ></div>
                </div>
              </div>
            {/each}
          </div>
        </div>

        <!-- Risk Assessment -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 class="text-xl font-semibold text-gray-900 mb-4">⚠️ Risk Assessment</h2>
          
          <div class="space-y-4">
            {#each [
              {
                level: 'Low',
                color: 'green',
                description: 'Viewing operations',
                permissions: analysisData.power_distribution.low,
                recommendation: '✅ Appropriate for basic users'
              },
              {
                level: 'Medium', 
                color: 'yellow',
                description: 'Content modification',
                permissions: analysisData.power_distribution.medium,
                recommendation: '✅ Suitable for content creators'
              },
              {
                level: 'High',
                color: 'orange',
                description: 'User management',
                permissions: analysisData.power_distribution.high,
                recommendation: '⚠️ Monitor user management activities'
              },
              {
                level: 'Critical',
                color: 'red',
                description: 'Administrative access',
                permissions: analysisData.power_distribution.critical,
                recommendation: '🔴 Regular security audits required'
              }
            ] as risk}
              <div class="flex items-start space-x-3">
                <span class="text-2xl">{PermissionUtils.getPowerLevelIcon(risk.level === 'Low' ? 10 : risk.level === 'Medium' ? 40 : risk.level === 'High' ? 70 : 90)}</span>
                <div class="flex-1">
                  <div class="font-medium text-gray-900">{risk.level} Risk</div>
                  <div class="text-sm text-gray-600">{risk.description} ({risk.permissions} permissions)</div>
                  <div class="text-xs text-gray-500 mt-1">{risk.recommendation}</div>
                </div>
              </div>
            {/each}
          </div>
        </div>

        <!-- Most Powerful Permissions -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 class="text-xl font-semibold text-gray-900 mb-4">💪 Most Powerful Permissions</h2>
          
          <div class="space-y-3">
            {#each analysisData.most_powerful_permissions as permission}
              <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div class="flex items-center space-x-3">
                  <span class="text-lg">{PermissionUtils.getPermissionIcon(permission)}</span>
                  <div>
                    <div class="font-medium text-gray-900">{permission.display_name}</div>
                    <div class="text-sm text-gray-500">{permission.action}</div>
                  </div>
                </div>
                <div class="text-right">
                  <div class="font-semibold text-gray-900">Power {permission.power_level}</div>
                  <div class="text-xs text-gray-500">{PermissionUtils.getPowerLevelLabel(permission.power_level)}</div>
                </div>
              </div>
            {/each}
          </div>
        </div>

        <!-- Security Recommendations -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 class="text-xl font-semibold text-gray-900 mb-4">💡 Security Recommendations</h2>
          
          <div class="space-y-4">
            {#each [
              {
                icon: '✅',
                title: 'Role Validation',
                description: 'All roles follow power constraints properly'
              },
              {
                icon: '⚠️',
                title: 'Monitor High-Power Users',
                description: '3 users have power level 80 or above'
              },
              {
                icon: '🔄',
                title: 'Regular Audits',
                description: 'Schedule quarterly permission reviews'
              },
              {
                icon: '📊',
                title: 'Usage Analytics',
                description: 'Track permission usage patterns'
              }
            ] as rec}
              <div class="flex items-start space-x-3">
                <span class="text-xl">{rec.icon}</span>
                <div>
                  <div class="font-medium text-gray-900">{rec.title}</div>
                  <div class="text-sm text-gray-600">{rec.description}</div>
                </div>
              </div>
            {/each}
          </div>
        </div>
      </div>

      <!-- Role Comparison -->
      <div class="mt-8 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 class="text-xl font-semibold text-gray-900 mb-4">🔄 Comparison with Other Roles</h2>
        
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {#each [
            { name: 'Basic', power: 10, permissions: 8, users: 45 },
            { name: 'Creator', power: 30, permissions: 15, users: 23 },
            { name: 'Moderator', power: 80, permissions: 22, users: 8 },
            { name: 'Admin', power: 100, permissions: 35, users: 3 }
          ] as role}
            <div class="border border-gray-200 rounded-lg p-4 {role.name === analysisData.role ? 'border-indigo-500 bg-indigo-50' : ''}">
              <div class="flex items-center justify-between mb-2">
                <span class="font-semibold text-gray-900">{role.name}</span>
                <span class="text-lg">{PermissionUtils.getPowerLevelIcon(role.power)}</span>
              </div>
              <div class="space-y-1 text-sm text-gray-600">
                <div>Power: {role.power}/100</div>
                <div>{role.permissions} permissions</div>
                <div>{role.users} users</div>
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/if}
  </div>
</div>