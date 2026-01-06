<script lang="ts">
	import { getContext } from 'svelte';
	import Dashboard from '$lib/components/home/Dashboard.svelte';
	import { WEBUI_NAME } from '$lib/stores';

	const i18n = getContext('i18n');
</script>

<svelte:head>
	<title>{$i18n.t('Dashboard')} • {$WEBUI_NAME}</title>
</svelte:head>

<Dashboard />
