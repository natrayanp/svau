<script>
  export let distribution = {
    low: 0,
    medium: 0,
    high: 0,
    critical: 0
  };
  
  export let totalPermissions = 0;
  export let showLabels = true;
  export let height = 'h-3'; // h-2, h-3, h-4

  function getPercentage(count) {
    return totalPermissions > 0 ? (count / totalPermissions) * 100 : 0;
  }

  function getDistributionArray() {
    return [
      { level: 'Low', count: distribution.low, color: 'green', width: getPercentage(distribution.low) },
      { level: 'Medium', count: distribution.medium, color: 'yellow', width: getPercentage(distribution.medium) },
      { level: 'High', count: distribution.high, color: 'orange', width: getPercentage(distribution.high) },
      { level: 'Critical', count: distribution.critical, color: 'red', width: getPercentage(distribution.critical) }
    ];
  }
</script>

<div class="power-chart">
  {#if showLabels}
    <div class="flex justify-between text-xs text-gray-500 mb-2">
      {#each getDistributionArray() as dist}
        <div class="text-center flex-1">
          <div>{dist.level}</div>
          <div class="font-medium">{dist.count}</div>
        </div>
      {/each}
    </div>
  {/if}

  <!-- Chart Bars -->
  <div class="flex w-full rounded-full overflow-hidden {height}">
    {#each getDistributionArray() as dist}
      {#if dist.width > 0}
        <div
          class="bg-{dist.color}-500 transition-all duration-500 ease-out"
          style={`width: ${dist.width}%`}
          title="{dist.level}: {dist.count} permissions ({dist.width.toFixed(1)}%)"
        ></div>
      {/if}
    {/each}
  </div>

  <!-- Total -->
  {#if showLabels}
    <div class="text-xs text-gray-500 text-center mt-2">
      Total: {totalPermissions} permissions
    </div>
  {/if}
</div>

<style>
  .power-chart {
    min-width: 200px;
  }
</style>