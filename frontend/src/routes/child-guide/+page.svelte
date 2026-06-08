<svelte:head>
  <title>Child Guide | Family Hero Hub</title>
</svelte:head>

<div class="max-w-5xl mx-auto px-4 py-16">
  <div class="mb-12">
    <p class="text-xs font-black uppercase tracking-[0.2em] text-savings">Support</p>
    <h1 class="mt-3 text-4xl md:text-5xl font-black text-slate-900">Child Guide</h1>
    <p class="mt-5 max-w-3xl text-lg leading-relaxed text-slate-600">
      A simple guide for children who use a linked Child Dashboard on their own device.
    </p>
    <p class="mt-5 max-w-3xl text-base leading-relaxed text-slate-600">
      Points show progress. You can earn them by following routines, helping out, trying hard, and completing tasks your parent has set. Some families use points for rewards or allowance values, but your parent decides how it works.
    </p>
  </div>

  <div class="grid gap-5 md:grid-cols-2">
    {#each [
      ['See your points', 'Your dashboard shows the points you have available and, when your parent uses savings, points set aside for later.'],
      ['Check tasks and School Bag', 'Use the dashboard to see what is coming up, what needs doing today, and what to remember for school.'],
      ['Request rewards', 'You can ask for rewards from your dashboard. Your parent approves or rejects each request.'],
      ['Save points', 'Saved points help you practise waiting and working toward bigger goals.'],
      ['Ask a parent if something looks wrong', 'If points, tasks, rewards, or School Bag items do not look right, ask a parent or caregiver.'],
      ['Parents approve rewards', 'Children do not get parent settings or admin access. Parents manage the family space.']
    ] as item}
      <section class="card p-6">
        <h2 class="text-xl font-black text-slate-900">{item[0]}</h2>
        <p class="mt-3 leading-relaxed text-slate-600">{item[1]}</p>
      </section>
    {/each}
  </div>

  <div class="mt-10 rounded-3xl border border-slate-200 bg-slate-50 p-5 text-slate-600">
    Family Hero Hub does not have public child profiles, a social feed, or child-to-child messaging.
  </div>

  <div class="mt-10 flex flex-wrap gap-3">
    <a href="/faq" class="btn-secondary inline-flex items-center justify-center rounded-2xl px-5 py-4">Read the FAQ</a>
    <a href="/safety-privacy" class="btn-secondary inline-flex items-center justify-center rounded-2xl px-5 py-4">Safety & Privacy</a>
    <a href="/contact" class="btn-hero inline-flex items-center justify-center rounded-2xl px-5 py-4">Contact support</a>
  </div>
</div>
