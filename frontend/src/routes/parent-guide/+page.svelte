<svelte:head>
  <title>Parent Guide | Family Hero Hub</title>
</svelte:head>

<div class="max-w-4xl mx-auto px-4 py-16">
  <div class="card p-8 md:p-12">
    <p class="text-xs font-black uppercase tracking-[0.2em] text-hero">Support</p>
    <h1 class="mt-3 text-4xl font-black text-slate-900">Parent Guide</h1>
    <p class="mt-5 text-lg leading-relaxed text-slate-600">
      A quick overview for parents and caregivers who want to use Family Hero Hub to manage family points, rewards, routines, school prep, and linked child devices.
    </p>

    <div class="mt-10 grid gap-4 md:grid-cols-2">
      {#each [
        'Sign in with Google using the approved parent account.',
        'Set up children, points, rewards, and family routines.',
        'Approve or reject reward requests.',
        'Invite trusted caregivers and remove access when needed.',
        'Link a child device and unlink it later if needed.',
        'Use the FAQ if you want deeper answers about privacy or allowance.'
      ] as item}
        <div class="rounded-3xl border border-slate-200 bg-slate-50/80 p-5 text-slate-700 leading-relaxed">
          {item}
        </div>
      {/each}
    </div>

    <div class="mt-10 flex flex-wrap gap-3">
      <a href="/faq" class="btn-secondary inline-flex items-center justify-center rounded-2xl px-5 py-4">Read the FAQ</a>
      <a href="/contact" class="btn-hero inline-flex items-center justify-center rounded-2xl px-5 py-4">Contact support</a>
    </div>
  </div>
</div>
