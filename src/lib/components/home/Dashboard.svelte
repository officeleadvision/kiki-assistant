<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { toast } from 'svelte-sonner';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import ChatPlus from '$lib/components/icons/ChatPlus.svelte';
	import Document from '$lib/components/icons/Document.svelte';
	import Note from '$lib/components/icons/Note.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import SidebarIcon from '$lib/components/icons/Sidebar.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import {
		config,
		models,
		settings,
		showSearch,
		mobile,
		showSidebar,
		showArchivedChats,
		user,
		type Model
	} from '$lib/stores';

	const i18n: Writable<i18nType> = getContext('i18n');

	const safeSplit = (value?: string) =>
		value
			? value
					.split(',')
					.map((modelId) => modelId.trim())
					.filter(Boolean)
			: [];

	const isModelHidden = (model: Model) => Boolean((model?.info?.meta as any)?.hidden);
	$: availableModels = $models.filter((model) => !isModelHidden(model));
	$: configuredModelIds = safeSplit($config?.default_models);
	$: savedModelIds = ($settings?.models?.filter(Boolean) ?? configuredModelIds).filter(Boolean);
	$: defaultModelId = savedModelIds[0] ?? configuredModelIds[0] ?? '';
	$: defaultModel = defaultModelId
		? availableModels.find((model) => model.id === defaultModelId)
		: null;
	$: defaultModelName = defaultModel?.name ?? defaultModelId ?? 'Kiki';
	$: modelLabel =
		defaultModelName === 'Kiki'
			? $i18n.t('Ask Kiki')
			: $i18n.t('Ask {{model}}', { model: defaultModelName });
	$: chatRoute = defaultModelId ? `/chat?models=${encodeURIComponent(defaultModelId)}` : '/chat';

	const startChat = () => {
		void goto(chatRoute);
	};

	const openKnowledge = () => {
		void goto('/workspace/knowledge');
	};

	const openNotes = () => {
		void goto('/notes');
	};

	const triggerSearch = () => {
		showSearch.set(true);
	};

	onMount(() => {
		if ($page.url.searchParams.get('error')) {
			toast.error($page.url.searchParams.get('error') || $i18n.t('An unknown error occurred.'));
		}
	});
</script>

<div
	class="flex h-screen max-h-dvh w-full flex-col transition-width duration-200 ease-in-out bg-slate-50 dark:bg-slate-950"
>
	<!-- Header with user menu -->
	<nav
		class="px-2.5 pt-1.5 pb-1.5 backdrop-blur-xl w-full drag-region border-b border-gray-200/70 dark:border-gray-800/70 bg-white/80 dark:bg-gray-950/70 sticky top-0 z-40"
	>
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-1">
				{#if $mobile}
					<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center">
						<Tooltip
							content={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
							interactive={true}
						>
							<button
								id="sidebar-toggle-button"
								class="cursor-pointer flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-850 transition"
								on:click={() => {
									showSidebar.set(!$showSidebar);
								}}
								aria-label={$showSidebar ? $i18n.t('Close Sidebar') : $i18n.t('Open Sidebar')}
							>
								<div class="self-center p-1.5">
									<SidebarIcon />
								</div>
							</button>
						</Tooltip>
					</div>
				{/if}
			</div>

			<div class="flex items-center gap-1">
				{#if $user}
					<UserMenu
						className="max-w-[240px]"
						role={$user?.role}
						help={true}
						on:show={(e) => {
							if (e.detail === 'archived-chat') {
								showArchivedChats.set(true);
							}
						}}
					>
						<button
							class="select-none flex rounded-xl p-1.5 hover:bg-gray-50 dark:hover:bg-gray-850 transition"
							aria-label="User Menu"
						>
							<div class="self-center">
								<img
									src={`${WEBUI_API_BASE_URL}/users/${$user?.id}/profile/image`}
									class="size-6 object-cover rounded-full"
									alt="User profile"
									draggable="false"
								/>
							</div>
						</button>
					</UserMenu>
				{/if}
			</div>
		</div>
	</nav>

	<div class="flex-1 overflow-y-auto px-4 py-6 md:px-8">
		<div class="mx-auto flex max-w-5xl flex-col gap-6">
			<img
				src="/static/kiki-login.png"
				alt="Kiki login"
				class="mx-auto mt-8 w-3/4 rounded-xl overflow-hidden border-4 border-primary"
			/>

			<div class="flex flex-col items-center gap-3 text-primary">
				<h2 class="text-3xl font-semibold">
					{$i18n.t('Welcome to {{model}}', { model: defaultModelName })}
				</h2>
				<p class="mt-2 text-center text-sm leading-tight text-primary/80">
					{$i18n.t(
						'Your personal AI assistant for Lead Me with analytics, recommendations and communication'
					)}
				</p>
			</div>

			<div
				class="rounded-3xl border border-gray-200/70 bg-white/80 px-6 py-6 shadow-lg shadow-gray-900/5 backdrop-blur dark:border-gray-800/70 dark:bg-gray-900/60"
			>
				<div class="space-y-1">
					<p
						class="text-xs font-semibold uppercase tracking-[0.3em] text-gray-500 dark:text-gray-400"
					>
						{$i18n.t('Quick Actions')}
					</p>
					<h1 class="text-3xl font-semibold text-gray-900 dark:text-white">
						{$i18n.t('Dashboard')}
					</h1>
					<p class="text-sm text-gray-500 dark:text-gray-400">
						{$i18n.t('Jump straight into what matters most.')}
					</p>
				</div>

				<div class="grid gap-4 sm:grid-cols-2">
					<button
						type="button"
						class="group flex flex-col gap-3 rounded-2xl border border-gray-200 bg-white px-5 py-6 text-left transition hover:border-primary dark:border-gray-800 dark:bg-gray-900"
						on:click={startChat}
					>
						<div class="flex items-center gap-3">
							<div
								class="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 text-primary transition group-hover:bg-primary/20"
							>
								<ChatPlus className="size-5" strokeWidth="2" />
							</div>
							<span class="text-lg font-semibold text-gray-900 dark:text-white">{modelLabel}</span>
						</div>
						<span class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('New Chat')}</span>
					</button>

					<button
						type="button"
						class="group flex flex-col gap-3 rounded-2xl border border-gray-200 bg-white px-5 py-6 text-left transition hover:border-primary dark:border-gray-800 dark:bg-gray-900"
						on:click={openKnowledge}
					>
						<div class="flex items-center gap-3">
							<div
								class="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 text-primary transition group-hover:bg-primary/20"
							>
								<Document className="size-5" strokeWidth="2" />
							</div>
							<span class="text-lg font-semibold text-gray-900 dark:text-white"
								>{$i18n.t('Documents')}</span
							>
						</div>
						<span class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Knowledge')}</span>
					</button>

					<button
						type="button"
						class="group flex flex-col gap-3 rounded-2xl border border-gray-200 bg-white px-5 py-6 text-left transition hover:border-primary dark:border-gray-800 dark:bg-gray-900"
						on:click={openNotes}
					>
						<div class="flex items-center gap-3">
							<div
								class="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 text-primary transition group-hover:bg-primary/20"
							>
								<Note className="size-5" strokeWidth="2" />
							</div>
							<span class="text-lg font-semibold text-gray-900 dark:text-white"
								>{$i18n.t('Notes')}</span
							>
						</div>
						<span class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Notes')}</span>
					</button>

					<button
						type="button"
						class="group flex flex-col gap-3 rounded-2xl border border-gray-200 bg-white px-5 py-6 text-left transition hover:border-primary dark:border-gray-800 dark:bg-gray-900"
						on:click={triggerSearch}
					>
						<div class="flex items-center gap-3">
							<div
								class="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 text-primary transition group-hover:bg-primary/20"
							>
								<Search className="size-5" strokeWidth="2" />
							</div>
							<span class="text-lg font-semibold text-gray-900 dark:text-white"
								>{$i18n.t('Search')}</span
							>
						</div>
						<span class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Search')}</span>
					</button>
				</div>
			</div>
		</div>
	</div>
</div>
