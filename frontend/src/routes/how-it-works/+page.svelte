<script lang="ts">
  import { locale } from 'svelte-i18n';
  import PublicInfoPage from '$lib/components/public/PublicInfoPage.svelte';
  import { getPublicSiteCopy } from '$lib/publicSite';

  let copy = $derived(getPublicSiteCopy($locale).pages.howItWorks);
</script>

<PublicInfoPage page={copy} />
