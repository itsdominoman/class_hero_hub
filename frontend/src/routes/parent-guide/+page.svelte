<svelte:head>
  <title>Parent Guide | Family Hero Hub</title>
</svelte:head>

<div class="max-w-5xl mx-auto px-4 py-16">
  <div class="mb-12">
    <p class="text-xs font-black uppercase tracking-[0.2em] text-hero">Support</p>
    <h1 class="mt-3 text-4xl md:text-5xl font-black text-slate-900">Parent Guide</h1>
    <p class="mt-5 max-w-3xl text-lg leading-relaxed text-slate-600">
      A practical starting point for parents and caregivers using Family Hero Hub to manage points, rewards, routines, school prep, and linked child devices.
    </p>
  </div>

  <div class="grid gap-5 md:grid-cols-2">
    {#each [
      ['Start with one child', 'Create one child profile first. You can add more children when the basic rhythm feels clear.'],
      ['Add simple points', 'Begin with a few everyday reasons: helpful choices, school prep, routines, effort, or kindness.'],
      ['Create a few rewards', 'Keep rewards easy to understand and age-appropriate. Children can request them, but parents approve them.'],
      ['Add School Bag and Calendar later', 'Use School Bag and Calendar when your family is ready to make school prep and routines more visible.'],
      ['Link a child device if useful', 'A linked child device opens the Child Dashboard without sharing the parent account, parent login, or parent device.'],
      ['Invite caregivers only when needed', 'Parents & Caregivers is for trusted grownups who help manage routines, points, rewards, or family setup.'],
      ['Keep points fair and age-appropriate', 'Use points as a clear family tool, not a replacement for parenting judgment or real conversations.'],
      ['Use savings and allowance carefully', 'Saved points and allowance values are optional family tools. Family Hero Hub does not hold or move money.']
    ] as item}
      <section class="card p-6">
        <h2 class="text-xl font-black text-slate-900">{item[0]}</h2>
        <p class="mt-3 leading-relaxed text-slate-600">{item[1]}</p>
      </section>
    {/each}
  </div>

  <div class="mt-8 rounded-3xl border border-slate-200 bg-slate-50 p-5 text-slate-600 leading-relaxed">
    Use points to encourage effort and follow-through, not just payment for chores. Some families connect points to allowance values, while others use points only for rewards, privileges, or progress.
  </div>

  <div class="mt-10 flex flex-wrap gap-3">
    <a href="/faq" class="btn-secondary inline-flex items-center justify-center rounded-2xl px-5 py-4">Read the FAQ</a>
    <a href="/safety-privacy" class="btn-secondary inline-flex items-center justify-center rounded-2xl px-5 py-4">Safety & Privacy</a>
    <a href="/contact" class="btn-hero inline-flex items-center justify-center rounded-2xl px-5 py-4">Contact support</a>
  </div>
</div>
