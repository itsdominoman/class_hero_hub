<svelte:head>
  <title>Child Guide | Family Hero Hub</title>
</svelte:head>

<div class="max-w-4xl mx-auto px-4 py-16">
  <div class="card p-8 md:p-12">
    <p class="text-xs font-black uppercase tracking-[0.2em] text-savings">Support</p>
    <h1 class="mt-3 text-4xl font-black text-slate-900">Child Guide</h1>
    <p class="mt-5 text-lg leading-relaxed text-slate-600">
      A simple guide for children who use a linked dashboard on their own device.
    </p>

    <div class="mt-10 grid gap-4 md:grid-cols-2">
      {#each [
        'See your own points, rewards, tasks, School Bag items, and progress.',
        'Ask for rewards and wait for a parent to approve them.',
        'Use the dashboard to check what is next and what you can work toward.',
        'Remember that parents manage the family space and all device links.',
        'If something is confusing, ask a parent or caregiver for help.',
        'There is no child-to-child messaging or public profile space.'
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
