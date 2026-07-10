<script lang="ts">
  import { onMount } from 'svelte';
  import { _ } from 'svelte-i18n';
  import { api } from '$lib/api';

  type AssignmentCard = {
    id: number;
    role: string;
    target_type?: 'class_section' | 'subject_group';
    school: { id: number; name: string; name_ar?: string | null };
    class_section?: { id: number; name?: string | null; code?: string | null } | null;
    subject_group?: { id: number; name?: string | null; code?: string | null } | null;
    branch?: { name?: string | null } | null;
    academic_year?: { name?: string | null } | null;
    grade_level?: { name?: string | null } | null;
    subject?: { name?: string | null } | null;
    valid_from: string;
  };
  type AnnouncementAttachment = {
    id: number;
    original_filename: string;
    content_type: string;
    size_bytes: number;
  };
  type Announcement = {
    id: number;
    school_id: number;
    title: string;
    body: string;
    audience_type: 'school' | 'class_section' | 'subject_group';
    class_section_name?: string | null;
    subject_group_name?: string | null;
    created_at?: string | null;
    attachment_count: number;
    attachments: AnnouncementAttachment[];
    status: string;
  };

  let loading = $state(true);
  let allowed = $state(false);
  let error = $state<string | null>(null);
  let assignments = $state<AssignmentCard[]>([]);
  let announcements = $state<Announcement[]>([]);
  let announcementTitle = $state('');
  let announcementBody = $state('');
  let announcementAudience = $state('');
  let announcementFiles = $state<FileList | null>(null);
  let announcementSaving = $state(false);
  let announcementSuccess = $state(false);
  let viewingAnnouncement = $state<Announcement | null>(null);
  let announcementModal = $state<'closed' | 'create' | 'manage' | 'detail'>('closed');

  function titleFor(card: AssignmentCard) {
    if (card.role === 'homeroom') return card.class_section?.name || card.class_section?.code || $_('teach.homeroom');
    return card.subject_group?.name || card.subject_group?.code || $_('teach.subject');
  }

  function detailsFor(card: AssignmentCard) {
    return [card.subject?.name, card.grade_level?.name, card.branch?.name, card.academic_year?.name].filter(Boolean).join(' · ');
  }

  function audienceOptions() {
    return assignments
      .map((card) => {
        const targetId = card.target_type === 'subject_group' ? card.subject_group?.id : card.class_section?.id;
        if (!targetId) return null;
        return {
          id: String(card.id),
          label: `${card.school.name} · ${titleFor(card)}`,
          school_id: card.school.id,
          audience_type: card.target_type === 'subject_group' ? 'subject_group' : 'class_section',
          class_section_id: card.target_type === 'class_section' ? targetId : null,
          subject_group_id: card.target_type === 'subject_group' ? targetId : null
        };
      })
      .filter(Boolean) as {
        id: string;
        label: string;
        school_id: number;
        audience_type: 'class_section' | 'subject_group';
        class_section_id: number | null;
        subject_group_id: number | null;
      }[];
  }

  function selectedAudience() {
    return audienceOptions().find((option) => option.id === announcementAudience) || null;
  }

  function schoolOptions(schoolId: number): RequestInit {
    return { headers: { 'X-School-Id': String(schoolId) } };
  }

  async function loadAnnouncements() {
    const audience = selectedAudience() || audienceOptions()[0];
    if (!audience) {
      announcements = [];
      return;
    }
    const data = await api.get('/teach/announcements', schoolOptions(audience.school_id));
    announcements = (data?.announcements || []).filter((announcement: Announcement) => announcement.audience_type !== 'school');
  }

  function announcementContext(announcement: Announcement) {
    if (announcement.audience_type === 'subject_group') return announcement.subject_group_name || $_('teach.announcements.subjectAudience');
    if (announcement.audience_type === 'class_section') return announcement.class_section_name || $_('teach.announcements.classAudience');
    return $_('teach.announcements.schoolAudience');
  }

  function formatDate(value?: string | null) {
    if (!value) return '';
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value));
  }

  function handleAnnouncementFiles(event: Event) {
    announcementFiles = (event.target as HTMLInputElement).files;
  }

  function openManageMode() {
    announcementModal = 'manage';
    viewingAnnouncement = null;
  }

  function closeAnnouncementModal() {
    announcementModal = 'closed';
    viewingAnnouncement = null;
  }

  function openCreateMode() {
    announcementSuccess = false;
    announcementModal = 'create';
    viewingAnnouncement = null;
  }

  function backToList() {
    announcementModal = 'manage';
    viewingAnnouncement = null;
  }

  function viewAnnouncement(announcement: Announcement) {
    viewingAnnouncement = announcement;
    announcementModal = 'detail';
  }

  function attachmentLabel(attachment: AnnouncementAttachment) {
    const sizeKb = Math.max(1, Math.round((attachment.size_bytes || 0) / 1024));
    return `${attachment.original_filename} · ${sizeKb} KB`;
  }

  async function downloadAttachment(announcement: Announcement, attachment: AnnouncementAttachment) {
    try {
      const blob = await api.download(
        `/teach/announcements/${announcement.id}/attachments/${attachment.id}/download`,
        schoolOptions(announcement.school_id)
      );
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = attachment.original_filename;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      error = err?.message || $_('teach.announcements.downloadError');
    }
  }

  async function publishAnnouncement() {
    const audience = selectedAudience();
    if (!audience) return;
    announcementSaving = true;
    error = null;
    try {
      const created = await api.post(
        '/school/announcements',
        {
          title: announcementTitle,
          body: announcementBody,
          audience_type: audience.audience_type,
          class_section_id: audience.class_section_id,
          subject_group_id: audience.subject_group_id
        },
        schoolOptions(audience.school_id)
      );
      for (const file of Array.from(announcementFiles || [])) {
        const formData = new FormData();
        formData.append('file', file);
        await api.upload(`/teach/announcements/${created.id}/attachments`, formData, schoolOptions(audience.school_id));
      }
      announcementTitle = '';
      announcementBody = '';
      announcementFiles = null;
      announcementSuccess = true;
      await loadAnnouncements();
      closeAnnouncementModal();
    } catch (err: any) {
      error = err?.message || $_('teach.announcements.saveError');
    } finally {
      announcementSaving = false;
    }
  }

  async function archiveAnnouncement(announcement: Announcement) {
    const audience = selectedAudience();
    if (!audience) return;
    announcementSaving = true;
    error = null;
    try {
      await api.delete(`/teach/announcements/${announcement.id}`, schoolOptions(audience.school_id));
      await loadAnnouncements();
    } catch (err: any) {
      error = err?.message || $_('teach.announcements.archiveError');
    } finally {
      announcementSaving = false;
    }
  }

  onMount(async () => {
    try {
      const me = await api.get('/me/v2');
      allowed = Boolean((me?.memberships || []).some((membership: any) => membership.role === 'teacher'));
      if (!allowed) {
        error = $_('teach.accessDenied');
        return;
      }
      const data = await api.get('/teach/dashboard');
      assignments = data.assignments || [];
      if (audienceOptions().length) {
        announcementAudience = audienceOptions()[0].id;
        await loadAnnouncements();
      }
    } catch (err: any) {
      if (err?.status === 401) {
        window.location.href = `/login?returnTo=${encodeURIComponent('/teach')}`;
        return;
      }
      error = err?.message || $_('teach.loadError');
    } finally {
      loading = false;
    }
  });
</script>

<svelte:head>
  <title>{$_('teach.title')}</title>
</svelte:head>

{#if loading}
  <section class="mx-auto max-w-5xl px-4 py-12">
    <div class="card p-8 text-center">
      <p class="text-sm font-semibold uppercase tracking-wide text-slate-500">{$_('common.loading')}</p>
    </div>
  </section>
{:else if !allowed}
  <section class="mx-auto max-w-3xl px-4 py-12">
    <div class="card p-8 text-center">
      <h1 class="text-2xl font-black text-slate-900">{$_('teach.accessDeniedTitle')}</h1>
      <p class="mt-3 text-slate-600">{error}</p>
    </div>
  </section>
{:else}
  <section class="mx-auto max-w-5xl px-4 py-8">
    <div class="border-b border-slate-200 pb-5">
      <p class="eyebrow">{$_('teach.eyebrow')}</p>
      <h1 class="mt-2 text-3xl font-black text-slate-900">{$_('teach.heading')}</h1>
    </div>

    <div class="mt-4 flex flex-wrap items-center gap-3">
      <button type="button" class="btn-hero rounded-lg px-4 py-2 text-sm" onclick={openCreateMode}>{$_('teach.announcements.create')}</button>
      <button type="button" class="btn-secondary rounded-lg px-4 py-2 text-sm" onclick={openManageMode}>{$_('teach.announcements.manage')}</button>
    </div>

    {#if announcementSuccess}
      <div class="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-700">{$_('teach.announcements.created')}</div>
    {/if}

    {#if error}
      <div class="mt-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</div>
    {/if}

    {#if assignments.length === 0}
      <div class="mt-6 rounded-lg border border-slate-200 bg-white p-8 text-center">
        <h2 class="text-xl font-black text-slate-900">{$_('teach.emptyTitle')}</h2>
        <p class="mt-2 text-slate-600">{$_('teach.emptyText')}</p>
      </div>
    {:else}
      <div class="mt-6 grid gap-4 md:grid-cols-2">
        {#each assignments as card}
          <article class="rounded-lg border border-slate-200 bg-white p-5">
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="text-xs font-semibold uppercase tracking-wide text-slate-400">{card.school.name}</p>
                <h2 class="mt-2 text-xl font-black text-slate-900">{titleFor(card)}</h2>
              </div>
              <span class="rounded-lg bg-slate-100 px-3 py-1 text-xs font-bold uppercase text-slate-600">{$_(`teach.roles.${card.role}`)}</span>
            </div>
            {#if detailsFor(card)}
              <p class="mt-3 text-sm font-medium text-slate-600">{detailsFor(card)}</p>
            {/if}
            <p class="mt-4 text-xs font-semibold uppercase tracking-wide text-slate-400">{$_('teach.activeFrom')} {card.valid_from}</p>
            <a class="btn-hero mt-5 inline-flex rounded-lg px-4 py-2 text-sm" href={`/teach/assignments/${card.id}`}>
              {$_('teach.openClass')}
            </a>
          </article>
        {/each}
      </div>
    {/if}

  </section>
{/if}

{#if announcementModal !== 'closed'}
  <div class="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/50 p-0 sm:items-center sm:p-4" role="dialog" aria-modal="true" aria-labelledby="teach-announcements-title">
    <div class="max-h-[92vh] w-full max-w-2xl overflow-y-auto rounded-t-lg bg-white p-5 shadow-xl sm:rounded-lg sm:p-6">
      {#if announcementModal === 'detail' && viewingAnnouncement}
        <div class="flex items-start justify-between gap-4">
          <div class="min-w-0">
            <button type="button" class="text-sm font-bold text-hero" onclick={backToList}>{$_('teach.announcements.back')}</button>
            <p class="mt-2 text-xs font-bold uppercase tracking-wide text-slate-500">{announcementContext(viewingAnnouncement)}</p>
            <h2 id="teach-announcements-title" class="mt-2 text-2xl font-black text-slate-900">{viewingAnnouncement.title}</h2>
            <p class="mt-2 text-sm text-slate-500">{formatDate(viewingAnnouncement.created_at)}</p>
          </div>
          <button type="button" class="rounded-lg border border-slate-200 px-3 py-2 text-sm font-bold text-slate-600" onclick={closeAnnouncementModal}>{$_('teach.announcements.close')}</button>
        </div>

        <div class="mt-6 whitespace-pre-wrap text-base leading-relaxed text-slate-700">{viewingAnnouncement.body}</div>

        {#if viewingAnnouncement.attachments?.length}
          <div class="mt-6">
            <h3 class="text-sm font-black uppercase tracking-wide text-slate-500">{$_('teach.announcements.attachmentList')}</h3>
            <div class="mt-3 divide-y divide-slate-100 rounded-lg border border-slate-100">
              {#each viewingAnnouncement.attachments as attachment}
                <div class="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between">
                  <p class="break-all text-sm font-semibold text-slate-800">{attachmentLabel(attachment)}</p>
                  <button type="button" class="btn-secondary rounded-lg px-3 py-2 text-center text-sm" onclick={() => viewingAnnouncement && downloadAttachment(viewingAnnouncement, attachment)}>
                    {$_('teach.announcements.download')}
                  </button>
                </div>
              {/each}
            </div>
          </div>
        {/if}
      {:else if announcementModal === 'create'}
        <div class="flex items-start justify-between gap-4">
          <h2 id="teach-announcements-title" class="text-xl font-black text-slate-900">{$_('teach.announcements.title')}</h2>
          <button type="button" class="rounded-lg border border-slate-200 px-3 py-2 text-sm font-bold text-slate-600" onclick={closeAnnouncementModal}>{$_('teach.announcements.close')}</button>
        </div>

        {#if error}
          <div class="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">{error}</div>
        {/if}

        <form class="mt-4 grid gap-3" onsubmit={(event) => { event.preventDefault(); publishAnnouncement(); }}>
          <label class="block text-sm font-semibold text-slate-700">
            {$_('teach.announcements.audience')}
            <select class="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-normal" bind:value={announcementAudience} onchange={loadAnnouncements}>
              {#each audienceOptions() as option}
                <option value={option.id}>{option.label}</option>
              {/each}
            </select>
          </label>
          <input class="rounded-lg border border-slate-200 px-3 py-2" required maxlength="160" bind:value={announcementTitle} placeholder={$_('teach.announcements.titlePlaceholder')} />
          <textarea class="min-h-32 rounded-lg border border-slate-200 px-3 py-2" required maxlength="10000" bind:value={announcementBody} placeholder={$_('teach.announcements.bodyPlaceholder')}></textarea>
          <input class="rounded-lg border border-slate-200 px-3 py-2 text-sm" type="file" multiple accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,.webp,.txt,application/pdf,image/jpeg,image/png,image/webp,text/plain" onchange={handleAnnouncementFiles} />
          <div class="flex items-center gap-3">
            <button type="submit" class="btn-hero rounded-lg px-4 py-2" disabled={announcementSaving}>{announcementSaving ? $_('teach.announcements.publishing') : $_('teach.announcements.publish')}</button>
            <button type="button" class="btn-secondary rounded-lg px-4 py-2" disabled={announcementSaving} onclick={closeAnnouncementModal}>{$_('teach.announcements.cancel')}</button>
          </div>
        </form>
      {:else if announcementModal === 'manage'}
        <div class="flex items-start justify-between gap-4">
          <h2 id="teach-announcements-title" class="text-2xl font-black text-slate-900">{$_('teach.announcements.manageTitle')}</h2>
          <button type="button" class="rounded-lg border border-slate-200 px-3 py-2 text-sm font-bold text-slate-600" onclick={closeAnnouncementModal}>{$_('teach.announcements.close')}</button>
        </div>

        {#if audienceOptions().length > 0}
          <button type="button" class="btn-hero mt-4 rounded-lg px-4 py-2" onclick={openCreateMode}>{$_('teach.announcements.create')}</button>
        {:else}
          <p class="mt-4 text-sm text-slate-500">{$_('teach.announcements.noAudience')}</p>
        {/if}

        <div class="mt-4 max-h-[60vh] divide-y divide-slate-100 overflow-y-auto rounded-lg border border-slate-100">
          {#each announcements as announcement}
            <div class="flex flex-col gap-2 p-3 sm:flex-row sm:items-center sm:justify-between">
              <button type="button" class="min-w-0 flex-1 text-left" onclick={() => viewAnnouncement(announcement)}>
                <p class="truncate font-bold text-slate-900">{announcement.title}</p>
                <p class="mt-1 text-sm text-slate-500">{announcementContext(announcement)} · {formatDate(announcement.created_at)} · {$_('teach.announcements.attachments', { values: { count: announcement.attachment_count } })}</p>
              </button>
              {#if announcement.status === 'published'}
                <button type="button" class="btn-secondary shrink-0 rounded-lg px-3 py-2 text-sm" disabled={announcementSaving} onclick={() => archiveAnnouncement(announcement)}>{$_('teach.announcements.archive')}</button>
              {/if}
            </div>
          {:else}
            <p class="p-3 text-sm text-slate-500">{$_('teach.announcements.empty')}</p>
          {/each}
        </div>
      {/if}
    </div>
  </div>
{/if}
