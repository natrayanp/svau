<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { PermissionUtils } from '$lib/permission/utils_permission';

  let roleName = $page.params.role;
  let analysisData = null;

  // Mock detailed analysis data
  const detailedAnalysis = {
    creator: {
      role: 'Creator',
      users: 23,
      permissions: 15,
      max_power: 30,
      average_power: 22,
      power_distribution: {
        low: 8,
        medium: 7,
        high: 0,
        critical: 0
      },
      most_powerful_permissions: [
        { display_name: 'Edit Content', power_level: 30, action: 'edit', module: 'Flashcards' },
        { display_name: 'Create Projects', power_level: 25, action: 'create', module: 'Portfolio' },
        { display_name: 'Export Data', power_level: 20, action: 'export', module: 'Flashcards' }
      ],
      risk_assessment: {
        level: 'low',
        concerns: [],
        recommendations: [
          'Appropriate for content creation',
          'Standard monitoring sufficient',
          'No elevated risks identified'
        ]
      }
    },
    admin: {
      role: 'Admin',
      users: 3,
      permissions: 35,
      max_power: 100,
      average_power: 68,
      power_distribution: {
        low: 8,
        medium: 7,
        high: 12,
        critical: 8
      },
      most_powerful_permissions: [
        { display_name: 'Admin Access', power_level: 100, action: 'admin', module: 'Admin' },
        { display_name: 'User Management', power_level: 80, action: 'manage', module: 'Users' },
        { display_name: 'System Settings', power_level: 90, action: 'admin', module: 'Admin' }
      ],
      risk_assessment: {
        level: 'critical',
        concerns: [
          'Full system access',
          'Can modify user permissions',
          'No access restrictions'
        ],
        recommendations: [
          'Regular security audits required',
          'Monitor all administrative activities',
          'Implement two-factor authentication'
        ]
      }
    }
  };

  onMount(() => {
    analysisData = detailedAnalysis[roleName] || detailedAnalysis.creator;
  });

  function getRiskColor(level) {
    return {
      critical: 'red',
      high: 'orange',
      medium: 'yellow',
      low: 'green'
    }[level];
  }
</script>

<svelte:head>
  <title>{analysisData?.role} - Power Analysis</title>
</svelte:head>

<div class="min-h-screen bg-gray-50 py-8">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <!-- Header -->
    <div class="mb-8">
      <div class="flex items-center justify-between">
        <div class="flex items-center space-x-4">
          <a href="/permission/analysis" class="text-indigo-600 hover:text-indigo-700">
            ← Back to Analysis
          </a>
          <div>
            <h1 class="text-3xl font-bold text-gray-900">{analysisData?.role} - Power Analysis</h1>
            <p class="mt-2 text-lg text-gray-600">
              Detailed security analysis and recommendations
            </p>
          </div>
        </div>
        <div class="text-right">
          <div class="text-sm text-gray-500">Risk Level</div>
          <div class="flex items-center space-x-2">
            <span class="text-2xl">{PermissionUtils.getPowerLevelIcon(analysisData?.max_power || 0)}</span>
            <span class="font-semibold text-gray-900 capitalize">{analysisData?.risk_assessment.level || 'low'}</span>
          </div>
        </div>
      </div>
    </div>

    {#if analysisData}
      <!-- Key Metrics -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="text-2xl font-bold text-gray-900">{analysisData.users}</div>
          <div class="text-sm text-gray-500">Users</div>
        </div>
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="text-2xl font-bold text-gray-900">{analysisData.permissions}</div>
          <div class="text-sm text-gray-500">Permissions</div>
        </div>
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="text-2xl font-bold text-gray-900">{analysisData.max_power}/100</div>
          <div class="text-sm text-gray-500">Max Power</div>
        </div>
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div class="text-2xl font-bold text-gray-900">{analysisData.average_power.toFixed(1)}</div>
          <div class="text-sm text-gray-500">Avg Power</div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <!-- Power Distribution Chart -->
        <div class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 class="text-xl font-semibold text-gray-900 mb-4">📊 Power Distribution</h2>
          <div class="space-y-4">
            {#each [
              { label: 'Low', color: 'green', count: analysisData.power_distribution.low },
              { label: 'Medium', color: 'yellow', count: analysisData.power_distribution.medium },
              { label: 'High', color: 'orange', count: analysisData.power_distribution.high },
              { label: 'Critical', color: 'red', count: analysisData.power_distribution.critical }
            ] as dist}
              <div>
                <div class="flex justify-between text-sm mb-1">
                  <span class="font-medium">{dist.label}</span>
                  <span class="text-gray-500">{dist.count} permissions</span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-3">
                  <div
                    class="h-3 rounded-full bg-{dist.color}-500"
                    style={`width: ${(dist.count / analysisData.permissions) * 100}%`}
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
            <div class="flex items-center space-x-3">
              <span class="text-2xl">{PermissionUtils.getPowerLevelIcon(analysisData.max_power)}</span>
              <div>
                <div class="font-medium text-gray-900 capitalize">{analysisData.risk_assessment.level} Risk</div>
                <div class="text-sm text-gray-600">
                  {#if analysisData.risk_assessment.level === 'critical'}
                    Full administrative access - highest security concern
                  {:else if analysisData.risk_assessment.level === 'high'}
                    Elevated permissions requiring monitoring
                  {:else if analysisData.risk_assessment.level === 'medium'}
                    Moderate risk with content modification capabilities
                  {:else}
                    Low risk - standard user permissions
                  {/if}
                </div>
              </div>
            </div>

            {#if analysisData.risk_assessment.concerns.length > 0}
              <div>
                <div class="font-medium text-gray-900 mb-2">Security Concerns:</div>
                <ul class="list-disc list-inside text-sm text-gray-600 space-y-1">
                  {#each analysisData.risk_assessment.concerns as concern}
                    <li>{concern}</li>
                  {/each}
                </ul>
              </div>
            {/if}
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
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
                    <div class="text-sm text-gray-500">{permission.module} • {permission.action}</div>
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
          <div class="space-y-3">
            {#each analysisData.risk_assessment.recommendations as recommendation}
              <div class="flex items-start space-x-3">
                <span class="text-green-600 text-lg">✅</span>
                <div class="text-sm text-gray-700">{recommendation}</div>
              </div>
            {/each}
          </div>
        </div>
      </div>

      <!-- Usage Statistics -->
      <div class="mt-8 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 class="text-xl font-semibold text-gray-900 mb-4">📈 Usage Statistics</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div class="text-center">
            <div class="text-2xl font-bold text-gray-900">{analysisData.users}</div>
            <div class="text-sm text-gray-500">Active Users</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-gray-900">94%</div>
            <div class="text-sm text-gray-500">Permission Usage</div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-gray-900">2.3</div>
            <div class="text-sm text-gray-500">Avg Sessions/Day</div>
          </div>
        </div>
      </div>
    {/if}
  </div>
</div>