<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "$lib/api";
  import { AVATAR_OPTIONS, getAvatarAsset, normaliseAvatarKey } from "$lib/avatars";
  import {
    ArrowRight,
    CalendarDays,
    Check,
    Gift,
    PiggyBank,
    QrCode,
    Settings,
    Trophy,
    Pencil,
    UserPlus,
    Users,
    X,
  } from "lucide-svelte";

  type ChildSummary = {
    child: {
      id: number;
      display_name: string;
      avatar_name: string | null;
      active: boolean;
    };
    spending_balance: number;
    savings_balance: number;
    locked_savings: number;
    available_savings: number;
    available_spending: number;
    pending_redemptions: number;
  };

  type ChildEditForm = {
    display_name: string;
    avatar_name: string;
  };

  const quickLaunchers = [
    {
      href: "/allowance",
      label: "Allowance setup",
      description: "Configure allowance-linked points for each child.",
      icon: PiggyBank,
    },
    {
      href: "/calendar",
      label: "Calendar",
      description: "Manage family tasks, events, and rewardable jobs.",
      icon: CalendarDays,
    },
    {
      href: "/redemptions",
      label: "Pending requests",
      description: "Review reward requests and approve or reject them.",
      icon: Check,
    },
  ];

  const launcherTools = [
    {
      href: "/parent?tool=rewards",
      label: "Manage rewards",
      description: "Open the reward modal from the parent dashboard.",
      icon: Gift,
    },
    {
      href: "/parent?tool=family",
      label: "Family settings",
      description: "Invite co-parents and review the family member list.",
      icon: Users,
    },
    {
      href: "/parent?tool=presets",
      label: "Behaviour presets",
      description: "Edit quick point actions and reusable behaviour presets.",
      icon: Settings,
    },
    {
      href: "/parent?tool=add-child",
      label: "Add child",
      description: "Launch the add-child flow from the parent dashboard.",
      icon: UserPlus,
    },
    {
      href: "/parent?tool=child-links",
      label: "Child device links",
      description: "Generate or revoke child dashboard QR links.",
      icon: QrCode,
    },
    {
      href: "/parent",
      label: "Back to launcher",
      description: "Return to the child-first parent dashboard.",
      icon: ArrowRight,
    },
  ];

  let children = $state<ChildSummary[]>([]);
  let loadingChildren = $state(true);
  let childLoadError = $state<string | null>(null);
  let childEditOpen = $state(false);
  let savingChild = $state(false);
  let childEditError = $state<string | null>(null);
  let editingChild = $state<ChildSummary | null>(null);
  let childForm = $state<ChildEditForm>({
    display_name: "",
    avatar_name: "1",
  });

  const selectedAvatar = $derived(getAvatarAsset(childForm.avatar_name));

  function openChildEditor(childSummary: ChildSummary) {
    editingChild = childSummary;
    childEditError = null;
    childForm = {
      display_name: childSummary.child.display_name,
      avatar_name:
        normaliseAvatarKey(childSummary.child.avatar_name) ?? "1",
    };
    childEditOpen = true;
  }

  function closeChildEditor() {
    childEditOpen = false;
    savingChild = false;
    childEditError = null;
    editingChild = null;
    childForm = {
      display_name: "",
      avatar_name: "1",
    };
  }

  async function loadChildren() {
    try {
      loadingChildren = true;
      childLoadError = null;
      const response = await api.get("/children/");
      children = Array.isArray(response) ? response : [];
    } catch (error) {
      childLoadError =
        error instanceof Error ? error.message : "Unable to load children";
      children = [];
    } finally {
      loadingChildren = false;
    }
  }

  async function saveChild() {
    if (!editingChild) return;
    const displayName = childForm.display_name.trim();
    const avatarName = normaliseAvatarKey(childForm.avatar_name) ?? "1";
    if (!displayName) {
      childEditError = "Child name is required.";
      return;
    }

    try {
      savingChild = true;
      childEditError = null;
      await api.patch(`/children/${editingChild.child.id}`, {
        display_name: displayName,
        avatar_name: avatarName,
      });
      await loadChildren();
      closeChildEditor();
    } catch (error) {
      childEditError =
        error instanceof Error ? error.message : "Unable to save child";
    } finally {
      savingChild = false;
    }
  }

  onMount(() => {
    void loadChildren();
  });
</script>

<svelte:head>
  <title>Parent Settings - Family Hero Hub</title>
</svelte:head>

<div class="min-h-dvh bg-slate-50 pb-[calc(4rem+var(--safe-bottom))]">
  <div class="border-b border-slate-200/70 bg-white/90 backdrop-blur-xl pt-[var(--safe-top)]">
    <div class="mx-auto max-w-5xl px-3 py-5 sm:px-4 md:py-6">
      <div class="flex items-start justify-between gap-4">
        <div class="min-w-0">
          <p class="text-[10px] font-black uppercase tracking-[0.28em] text-hero">Settings hub</p>
          <h1 class="mt-2 text-3xl font-black tracking-tight text-slate-950 sm:text-4xl">
            Parent settings
          </h1>
          <p class="mt-2 max-w-2xl text-sm font-medium leading-relaxed text-slate-600">
            Use this page as the launcher for the management surfaces that are still split out in phase 2A.
          </p>
        </div>
        <div class="rounded-2xl bg-slate-900 px-3 py-3 text-white">
          <Settings size={22} />
        </div>
      </div>
    </div>
  </div>

  <div class="mx-auto max-w-5xl space-y-6 px-3 py-6 sm:px-4 md:py-8">
    <section class="grid gap-4 md:grid-cols-3">
      {#each quickLaunchers as item}
        <a
          href={item.href}
          class="card flex min-h-[11rem] flex-col justify-between overflow-hidden border-slate-100 bg-white p-5 shadow-xl transition hover:-translate-y-0.5 hover:shadow-2xl sm:p-6"
        >
          <div class="flex items-start justify-between gap-4">
            <div class="min-w-0">
              <p class="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">
                Primary route
              </p>
              <h2 class="mt-2 text-2xl font-black text-slate-950">{item.label}</h2>
              <p class="mt-2 text-sm font-medium leading-relaxed text-slate-600">
                {item.description}
              </p>
            </div>
            <div class="rounded-2xl bg-hero/10 px-3 py-3 text-hero">
              <item.icon size={22} />
            </div>
          </div>
          <span class="mt-5 inline-flex w-fit items-center gap-2 rounded-full bg-slate-100 px-3 py-2 text-[10px] font-black uppercase tracking-[0.16em] text-slate-600">
            Open route
          </span>
        </a>
      {/each}
    </section>

    <section id="children" class="card overflow-hidden border-slate-100 bg-white p-5 shadow-xl sm:p-6">
      <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div class="min-w-0">
          <p class="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">Children</p>
          <h2 class="mt-2 text-2xl font-black text-slate-950">Edit child names and avatars</h2>
          <p class="mt-2 max-w-2xl text-sm font-medium leading-relaxed text-slate-600">
            Each child card has a quick edit action. Parents can rename a child and switch their avatar without leaving the settings hub.
          </p>
        </div>
        <a
          href="#children"
          class="inline-flex items-center gap-2 rounded-full bg-slate-100 px-4 py-3 text-xs font-black uppercase tracking-[0.16em] text-slate-600"
        >
          <Pencil size={14} />
          Edit children
        </a>
      </div>

      {#if loadingChildren}
        <div class="mt-5 rounded-[1.75rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
          <p class="text-sm font-black uppercase tracking-[0.22em] text-slate-400">
            Loading children
          </p>
        </div>
      {:else if childLoadError}
        <div class="mt-5 rounded-[1.75rem] border border-red-100 bg-red-50 p-5 text-sm font-bold text-red-700 break-words">
          {childLoadError}
        </div>
      {:else if children.length === 0}
        <div class="mt-5 rounded-[1.75rem] border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
          <p class="text-sm font-black uppercase tracking-[0.22em] text-slate-400">No children yet</p>
          <p class="mt-2 text-sm text-slate-500">
            Add a child from the parent launcher, then come back here to edit the name and avatar.
          </p>
        </div>
      {:else}
        <div class="mt-5 grid gap-4 md:grid-cols-2">
          {#each children as childSummary}
            {@const avatar = getAvatarAsset(childSummary.child.avatar_name)}
            <article class="rounded-[1.75rem] border border-slate-100 bg-slate-50 p-4 sm:p-5">
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <h3 class="truncate text-lg font-black text-slate-950">
                    {childSummary.child.display_name}
                  </h3>
                  <p class="mt-1 text-xs font-black uppercase tracking-[0.16em] text-slate-400">
                    Avatar {avatar.key}
                  </p>
                </div>
                <div class="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-slate-100">
                  <img src={avatar.path} alt={avatar.label} class="h-full w-full object-cover" />
                </div>
              </div>

              <div class="mt-4 grid grid-cols-2 gap-3">
                <div class="rounded-2xl bg-white p-3">
                  <p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-400">Points</p>
                  <p class="mt-2 text-2xl font-black text-slate-950">
                    {childSummary.available_spending}
                  </p>
                </div>
                <div class="rounded-2xl bg-white p-3">
                  <p class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-400">Saved</p>
                  <p class="mt-2 text-2xl font-black text-slate-950">
                    {childSummary.savings_balance}
                  </p>
                </div>
              </div>

              <div class="mt-4 flex flex-wrap gap-2">
                {#if childSummary.pending_redemptions > 0}
                  <span class="inline-flex items-center gap-2 rounded-full bg-amber-100 px-3 py-2 text-[10px] font-black uppercase tracking-[0.16em] text-amber-700">
                    <Trophy size={13} />
                    {childSummary.pending_redemptions} pending
                  </span>
                {/if}
                {#if childSummary.locked_savings > 0}
                  <span class="inline-flex items-center gap-2 rounded-full bg-savings/10 px-3 py-2 text-[10px] font-black uppercase tracking-[0.16em] text-savings">
                    <PiggyBank size={13} />
                    Locked savings
                  </span>
                {/if}
                <span
                  class={`inline-flex items-center gap-2 rounded-full px-3 py-2 text-[10px] font-black uppercase tracking-[0.16em] ${
                    childSummary.child.active
                      ? "bg-slate-100 text-slate-600"
                      : "bg-red-100 text-red-700"
                  }`}
                >
                  <span class="h-2 w-2 rounded-full bg-current"></span>
                  {childSummary.child.active ? "Active" : "Inactive"}
                </span>
              </div>

              <div class="mt-5 grid gap-2 sm:grid-cols-3">
                <button
                  type="button"
                  onclick={() => openChildEditor(childSummary)}
                  class="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-slate-900 px-4 py-3 text-xs font-black uppercase tracking-[0.16em] text-white"
                >
                  <Pencil size={14} />
                  Edit
                </button>
                <a
                  href={`/child/${childSummary.child.id}`}
                  class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs font-black uppercase tracking-[0.16em] text-slate-700 transition hover:border-hero hover:text-hero"
                >
                  Dashboard
                </a>
                <a
                  href="/parent?tool=child-links"
                  class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-xs font-black uppercase tracking-[0.16em] text-slate-700 transition hover:border-hero hover:text-hero"
                >
                  <QrCode size={14} />
                  Device links
                </a>
              </div>
            </article>
          {/each}
        </div>
      {/if}
    </section>

    <section class="card overflow-hidden border-slate-100 bg-white p-5 shadow-xl sm:p-6">
      <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div class="min-w-0">
          <p class="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">Launcher links</p>
          <h2 class="mt-2 text-2xl font-black text-slate-950">Tools still opened from the parent dashboard</h2>
          <p class="mt-2 max-w-2xl text-sm font-medium leading-relaxed text-slate-600">
            These routes preserve the old modals for now, but the parent dashboard no longer has to carry the whole control panel.
          </p>
        </div>
        <a
          href="/parent"
          class="inline-flex items-center gap-2 rounded-full bg-slate-900 px-4 py-3 text-xs font-black uppercase tracking-[0.16em] text-white shadow-lg shadow-slate-900/15 transition hover:bg-slate-800"
        >
          <ArrowRight size={14} />
          Back to launcher
        </a>
      </div>

      <div class="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {#each launcherTools as item}
          <a
            href={item.href}
            class="inline-flex w-full flex-col gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4 text-left transition hover:border-hero hover:text-hero"
          >
            <span class="inline-flex items-center gap-2 text-xs font-black uppercase tracking-[0.16em] text-slate-700">
              <item.icon size={16} />
              {item.label}
            </span>
            <span class="text-sm font-medium leading-relaxed text-slate-600">
              {item.description}
            </span>
          </a>
        {/each}
      </div>
    </section>

    <section class="card overflow-hidden border-slate-100 bg-white p-5 shadow-xl sm:p-6">
      <div class="flex items-start justify-between gap-4">
        <div class="min-w-0">
          <p class="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">Notes</p>
          <h2 class="mt-2 text-2xl font-black text-slate-950">Phase 2A keeps the risk low</h2>
          <p class="mt-2 max-w-3xl text-sm font-medium leading-relaxed text-slate-600">
            Parent tools remain reachable without changing the backend flow. The child launcher stays the primary dashboard, and the old modal flows remain available until they are fully moved.
          </p>
        </div>
        <div class="rounded-2xl bg-hero/10 px-3 py-3 text-hero">
          <Trophy size={22} />
        </div>
      </div>
    </section>
  </div>

  {#if childEditOpen && editingChild}
    <div class="fixed inset-0 z-[100] flex items-end justify-center p-0 sm:items-center sm:p-4">
      <button
        type="button"
        class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
        aria-label="Close child editor"
        onclick={closeChildEditor}
      ></button>

      <div class="relative z-10 flex max-h-[calc(100dvh-var(--safe-top))] w-full max-w-2xl flex-col overflow-hidden rounded-t-[2rem] bg-white shadow-2xl sm:rounded-[2rem]">
        <div class="flex items-start justify-between gap-4 border-b border-slate-100 p-5 sm:p-6">
          <div class="min-w-0">
            <p class="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">
              Child editor
            </p>
            <h3 class="mt-2 text-2xl font-black text-slate-950">
              Edit {editingChild.child.display_name}
            </h3>
          </div>
          <button
            type="button"
            onclick={closeChildEditor}
            class="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-slate-50 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
            aria-label="Close child editor"
          >
            <X size={18} />
          </button>
        </div>

        <div class="min-h-0 flex-1 overflow-y-auto p-5 sm:p-6">
          {#if childEditError}
            <div class="mb-5 rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm font-bold text-red-700 break-words">
              {childEditError}
            </div>
          {/if}

          <div class="grid gap-5 md:grid-cols-[minmax(0,0.75fr)_minmax(0,1.25fr)]">
            <div class="rounded-[1.75rem] border border-slate-100 bg-slate-50 p-4 sm:p-5">
              <p class="text-[10px] font-black uppercase tracking-[0.22em] text-slate-400">
                Preview
              </p>
              <div class="mt-4 flex items-center gap-4">
                <div class="flex h-20 w-20 items-center justify-center overflow-hidden rounded-[1.5rem] bg-white shadow-sm ring-1 ring-slate-100">
                  <img
                    src={selectedAvatar.path}
                    alt={selectedAvatar.label}
                    class="h-full w-full object-cover"
                  />
                </div>
                <div class="min-w-0">
                  <p class="truncate text-2xl font-black text-slate-950">
                    {childForm.display_name || editingChild.child.display_name}
                  </p>
                  <p class="mt-1 text-sm font-medium text-slate-500">
                    Avatar {selectedAvatar.key}
                  </p>
                </div>
              </div>
            </div>

            <div class="space-y-4">
              <label class="block">
                <span class="mb-2 block text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">
                  Child name
                </span>
                <input
                  type="text"
                  bind:value={childForm.display_name}
                  class="w-full rounded-2xl border-2 border-slate-200 bg-slate-50 px-4 py-4 text-slate-900 font-bold focus:border-hero/30 focus:outline-none"
                  placeholder="Child display name"
                />
              </label>

              <div>
                <span class="mb-2 block text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">
                  Avatar
                </span>
                <div class="grid max-h-[22rem] grid-cols-4 gap-2 overflow-y-auto rounded-[1.5rem] border border-slate-100 bg-slate-50 p-2 sm:grid-cols-6">
                  {#each AVATAR_OPTIONS as avatar}
                    <button
                      type="button"
                      onclick={() => (childForm.avatar_name = avatar.key)}
                      class={`flex flex-col items-center gap-2 rounded-2xl border-2 p-2 text-center transition ${
                        childForm.avatar_name === avatar.key
                          ? 'border-hero bg-white shadow-sm'
                          : 'border-transparent bg-white/60 hover:border-hero/20 hover:bg-white'
                      }`}
                      aria-pressed={childForm.avatar_name === avatar.key}
                    >
                      <img
                        src={avatar.path}
                        alt={avatar.label}
                        class="h-12 w-12 rounded-xl object-cover"
                      />
                      <span class="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">
                        {avatar.key}
                      </span>
                    </button>
                  {/each}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="border-t border-slate-100 bg-white p-5 sm:p-6">
          <div class="flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onclick={saveChild}
              disabled={savingChild}
              class="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-slate-900 px-4 py-4 text-xs font-black uppercase tracking-[0.16em] text-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              {savingChild ? "Saving..." : "Save child"}
            </button>
            <button
              type="button"
              onclick={closeChildEditor}
              class="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-4 text-xs font-black uppercase tracking-[0.16em] text-slate-700"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  {/if}
</div>
