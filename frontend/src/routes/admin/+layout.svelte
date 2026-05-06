<script lang="ts">
  import { page } from '$app/state';
  import { ListChecks, Users } from 'lucide-svelte';

  const tabs = [
    { href: '/admin/registration-requests', label: 'Registration Requests', icon: ListChecks },
    { href: '/admin/users', label: 'Users', icon: Users }
  ];

  function isActive(href: string) {
    return page.url.pathname === href || page.url.pathname.startsWith(`${href}/`);
  }
</script>

<div class="max-w-6xl mx-auto px-4 pt-6">
  <div class="card p-2 flex flex-wrap gap-2">
    {#each tabs as tab}
      <a
        href={tab.href}
        class={`inline-flex items-center gap-2 rounded-2xl px-4 py-3 text-sm font-semibold transition-colors ${
          isActive(tab.href)
            ? 'bg-hero text-white shadow-lg shadow-hero/20'
            : 'text-slate-600 hover:bg-slate-100'
        }`}
        aria-current={isActive(tab.href) ? 'page' : undefined}
      >
        <svelte:component this={tab.icon} size={16} />
        {tab.label}
      </a>
    {/each}
  </div>
</div>

<slot />
