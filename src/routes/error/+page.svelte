<script>
	import { goto } from '$app/navigation';
	import { WEBUI_NAME, config } from '$lib/stores';
	import { onMount, getContext } from 'svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		if ($config) {
			await goto('/');
		}

		loaded = true;
	});
</script>

{#if loaded}
	<div class="absolute w-full h-full flex z-50 bg-white">
		<div class="absolute rounded-xl w-full h-full backdrop-blur-sm flex justify-center">
			<div class="m-auto pb-44 flex flex-col justify-center">
				<div class="max-w-md">
					<div class="text-center text-2xl font-medium z-50 text-primary">
						{$i18n.t('{{webUIName}} Backend Required', { webUIName: $WEBUI_NAME })}
					</div>

					<div class=" mt-4 text-center text-sm w-full text-primary/70">
						{$i18n.t(
							"Oops! You're using an unsupported method (frontend only). Please serve the from the backend."
						)}
					</div>

					<div class=" mt-6 mx-auto relative group w-fit">
						<button
							class="relative z-20 flex px-5 py-2 rounded-full bg-primary hover:bg-primary-700 transition font-medium text-sm text-white"
							on:click={() => {
								location.href = '/';
							}}
						>
							{$i18n.t('Check Again')}
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}
