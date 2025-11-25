<script>
  import { PermissionUtils } from '../utils_permission';
  
  export let templates = [];
  export let selectedTemplate = null;
  export let onSelect = () => {};

  function handleSelect(template) {
    selectedTemplate = template;
    onSelect(template);
  }
</script>

<div class="role-template-selector">
  <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
    {#each templates as template}
      <div
        class="border-2 rounded-lg p-4 cursor-pointer transition-all duration-200 {{
          selectedTemplate?.id === template.id
            ? 'border-indigo-500 bg-indigo-50'
            : 'border-gray-200 hover:border-gray-300'
        }}"
        on:click={() => handleSelect(template)}
      >
        <div class="flex items-start space-x-3">
          <div class="flex-shrink-0">
            <span class="text-2xl">{template.icon}</span>
          </div>
          <div class="flex-1">
            <h3 class="font-semibold text-gray-900">{template.name}</h3>
            <p class="text-sm text-gray-600 mt-1">{template.description}</p>
            <div class="flex items-center space-x-4 mt-2 text-xs text-gray-500">
              <span>🔐 {template.permissions} permissions</span>
              <span>{PermissionUtils.getPowerLevelIcon(template.power_level)} Power {template.power_level}</span>
            </div>
          </div>
          <div class="flex-shrink-0">
            {#if selectedTemplate?.id === template.id}
              <div class="w-5 h-5 bg-indigo-600 rounded-full flex items-center justify-center">
                <svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
                </svg>
              </div>
            {:else}
              <div class="w-5 h-5 border-2 border-gray-300 rounded-full"></div>
            {/if}
          </div>
        </div>
      </div>
    {/each}
  </div>

  <!-- Selected Template Summary -->
  {#if selectedTemplate}
    <div class="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
      <div class="flex items-start space-x-2">
        <span class="text-blue-600">💡</span>
        <div class="text-sm text-blue-700">
          <strong>Based on:</strong> {selectedTemplate.name} template
          {#if selectedTemplate.permissions > 0}
            <br>+{selectedTemplate.permissions} permissions included
          {/if}
          <br>Estimated Power Level: {PermissionUtils.getPowerLevelLabel(selectedTemplate.power_level)}
        </div>
      </div>
    </div>
  {/if}
</div>