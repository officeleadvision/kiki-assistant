<script lang="ts">
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { toast } from 'svelte-sonner';
	import type { Readable } from 'svelte/store';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	const i18n = getContext<
		Readable<{
			t: (key: string, params?: Record<string, unknown>) => string;
		}>
	>('i18n');

	import { DropdownMenu } from 'bits-ui';
	import { flyAndScale } from '$lib/utils/transitions';
	import { WEBUI_NAME, user, models } from '$lib/stores';
	import { getChannels } from '$lib/apis/channels';
	import {
		getMailboxes,
		createMailbox,
		deleteMailbox,
		getWebhookInfo,
		updateMailbox,
		regenerateWebhookToken,
		type EmailMailbox,
		type EmailMailboxForm,
		type WebhookInfo
	} from '$lib/apis/emails';

	import DeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import Dropdown from '../common/Dropdown.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Switch from '../common/Switch.svelte';
	import Plus from '../icons/Plus.svelte';
	import Clipboard from '../icons/Clipboard.svelte';
	import EllipsisVertical from '../icons/EllipsisVertical.svelte';
	import Search from '../icons/Search.svelte';

	let loaded = false;
	let mailboxes: EmailMailbox[] = [];
	let availableChannels: any[] = [];

	let query = '';
	let selectedMailboxId: string | null = null;
	let selectedMailbox: EmailMailbox | null = null;
	let filteredMailboxes: EmailMailbox[] = [];
	let openMenuFor: string | null = null;

	let showDeleteConfirm = false;

	let showCreateModal = false;
	let showWebhookModal = false;
	let webhookInfo: WebhookInfo | null = null;
	let webhookMailbox: EmailMailbox | null = null;
	let requestBodyTemplate = '';
	let creating = false;
	let isSaving = false;

	let editName = '';
	let editDescription = '';
	let editMailboxType: 'personal' | 'shared' = 'personal';
	let editChannelId = '';
	let editModelId = '';

	const handleSaveMailbox = async () => {
		if (!selectedMailbox) return;

		isSaving = true;
		try {
			const update = await updateMailbox(localStorage.token, selectedMailbox.id, {
				name: editName,
				description: editDescription,
				mailbox_type: editMailboxType,
				channel_id: editChannelId,
				model_id: editModelId || undefined
			});

			if (update) {
				toast.success($i18n.t('Mailbox updated'));
				mailboxes = mailboxes.map((m) => (m.id === update.id ? update : m));
				selectedMailboxId = update.id;
			}
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			isSaving = false;
		}
	};

	// Create form state
	let newMailboxName = '';
	let newMailboxDescription = '';
	let newMailboxAddress = '';
	let newMailboxType: 'personal' | 'shared' = 'personal';
	let selectedChannelId = '';
	let selectedModelId = '';

	const loadMailboxes = async () => {
		try {
			mailboxes = (await getMailboxes(localStorage.token)) ?? [];
		} catch (e) {
			console.error('Error loading mailboxes:', e);
			mailboxes = [];
			toast.error(`${e}`);
		}
	};

	const loadChannels = async () => {
		try {
			availableChannels = (await getChannels(localStorage.token)) ?? [];
		} catch (e) {
			console.error('Error loading channels:', e);
			availableChannels = [];
			toast.error(`${e}`);
		}
	};

	const handleCreateMailbox = async () => {
		if (!selectedChannelId || !newMailboxName || !newMailboxAddress) {
			toast.error($i18n.t('Please fill in all required fields'));
			return;
		}

		creating = true;
		try {
			const result = await createMailbox(localStorage.token, {
				name: newMailboxName,
				description: newMailboxDescription || undefined,
				mailbox_address: newMailboxAddress,
				mailbox_type: newMailboxType,
				channel_id: selectedChannelId,
				model_id: selectedModelId || undefined
			});

			if (result) {
				toast.success($i18n.t('Email mailbox created successfully'));
				mailboxes = [...mailboxes, result];
				selectedMailboxId = result.id;
				resetCreateForm();
				showCreateModal = false;
			}
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			creating = false;
		}
	};

	const handleDeleteMailbox = async (mailbox: EmailMailbox) => {
		try {
			const result = await deleteMailbox(localStorage.token, mailbox.id);
			if (result) {
				mailboxes = mailboxes.filter((m) => m.id !== mailbox.id);
				toast.success($i18n.t('Email mailbox deleted successfully'));
			}
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const openWebhookModal = async (mailbox: EmailMailbox) => {
		webhookMailbox = mailbox;
		try {
			webhookInfo = await getWebhookInfo(localStorage.token, mailbox.id);
			showWebhookModal = true;
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const handleRegenerateToken = async () => {
		if (!webhookMailbox) return;
		try {
			const result = await regenerateWebhookToken(localStorage.token, webhookMailbox.id);
			if (result) {
				// Refresh webhook info
				webhookInfo = await getWebhookInfo(localStorage.token, webhookMailbox.id);
				// Update mailbox in list
				mailboxes = mailboxes.map((m) =>
					m.id === webhookMailbox!.id ? { ...m, webhook_token: result.webhook_token } : m
				);
				toast.success($i18n.t('Webhook token regenerated'));
			}
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const copyToClipboard = async (text: string) => {
		try {
			await navigator.clipboard.writeText(text);
			toast.success($i18n.t('Copied to clipboard'));
		} catch (e) {
			toast.error($i18n.t('Failed to copy'));
		}
	};

	const getModelName = (modelId?: string) => {
		if (!modelId) {
			return $i18n.t('No AI processing');
		}

		const model = $models?.find((candidate) => candidate.id === modelId);
		return model?.name ?? modelId;
	};

	const resetCreateForm = () => {
		newMailboxName = '';
		newMailboxDescription = '';
		newMailboxAddress = '';
		newMailboxType = 'personal';
		selectedChannelId = '';
		selectedModelId = '';
	};

	const goToChannel = (channelId: string) => {
		goto(`/channels/${channelId}`);
	};

	const toggleMailboxActive = async (mailbox: EmailMailbox) => {
		try {
			const result = await updateMailbox(localStorage.token, mailbox.id, {
				is_active: !mailbox.is_active
			});
			if (result) {
				mailboxes = mailboxes.map((m) => (m.id === mailbox.id ? result : m));
				toast.success(
					result.is_active ? $i18n.t('Mailbox activated') : $i18n.t('Mailbox deactivated')
				);
			}
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const closeActionMenu = () => {
		openMenuFor = null;
	};

	const toggleActionMenu = (mailboxId: string) => {
		openMenuFor = openMenuFor === mailboxId ? null : mailboxId;
	};

	onMount(async () => {
		await Promise.all([loadMailboxes(), loadChannels()]);
		loaded = true;
	});

	$: requestBodyTemplate = webhookInfo
		? (webhookInfo.instructions.body_template_text ??
			JSON.stringify(webhookInfo.instructions.body_template ?? {}, null, 2))
		: '';

	$: filteredMailboxes = query.trim()
		? mailboxes.filter((mailbox) =>
				`${mailbox.name} ${mailbox.mailbox_address} ${mailbox.description ?? ''}`
					.toLowerCase()
					.includes(query.trim().toLowerCase())
			)
		: mailboxes;

	$: if (!selectedMailboxId && mailboxes.length > 0) {
		selectedMailboxId = mailboxes[0].id;
	}

	$: if (selectedMailboxId && !mailboxes.some((mailbox) => mailbox.id === selectedMailboxId)) {
		selectedMailboxId = mailboxes[0]?.id ?? null;
	}

	$: selectedMailbox = mailboxes.find((mailbox) => mailbox.id === selectedMailboxId) ?? null;

	$: if (selectedMailbox) {
		editName = selectedMailbox.name;
		editDescription = selectedMailbox.description ?? '';
		editMailboxType = selectedMailbox.mailbox_type;
		editChannelId = selectedMailbox.channel_id;
		editModelId = selectedMailbox.model_id ?? '';
	} else {
		editName = '';
		editDescription = '';
		editMailboxType = 'personal';
		editChannelId = '';
		editModelId = '';
	}
</script>

<svelte:head>
	<title>{$i18n.t('Emails')} • {$WEBUI_NAME}</title>
</svelte:head>

<!-- Delete Confirmation Dialog -->
<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete Mailbox')}
	message={$i18n.t(
		'Are you sure you want to delete this email mailbox? This will also delete all associated email records.'
	)}
	on:confirm={() => {
		if (selectedMailbox) {
			handleDeleteMailbox(selectedMailbox);
			selectedMailboxId = null;
		}
		showDeleteConfirm = false;
	}}
/>

<!-- Create Modal -->
{#if showCreateModal}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
		on:click|self={() => (showCreateModal = false)}
		role="dialog"
		aria-modal="true"
		tabindex="-1"
		on:keydown={(event) => {
			if (event.key === 'Escape') {
				showCreateModal = false;
			}
		}}
	>
		<div class="bg-white dark:bg-gray-900 rounded-2xl shadow-xl max-w-lg w-full mx-4 p-6">
			<h2 class="text-xl font-semibold mb-4">{$i18n.t('Create Email Mailbox')}</h2>

			<div class="space-y-4">
				<div>
					<label for="new-mailbox-name" class="block text-sm font-medium mb-1"
						>{$i18n.t('Name')} *</label
					>
					<input
						id="new-mailbox-name"
						type="text"
						bind:value={newMailboxName}
						placeholder={$i18n.t('E.g., Support Inbox')}
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
					/>
				</div>

				<div>
					<label for="new-mailbox-description" class="block text-sm font-medium mb-1"
						>{$i18n.t('Description')}</label
					>
					<input
						id="new-mailbox-description"
						type="text"
						bind:value={newMailboxDescription}
						placeholder={$i18n.t('Optional description')}
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
					/>
				</div>

				<div>
					<label for="new-mailbox-address" class="block text-sm font-medium mb-1"
						>{$i18n.t('Email Address')} *</label
					>
					<input
						id="new-mailbox-address"
						type="email"
						bind:value={newMailboxAddress}
						placeholder={$i18n.t('E.g., support@company.com')}
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
					/>
				</div>

				<div>
					<label for="new-mailbox-type" class="block text-sm font-medium mb-1"
						>{$i18n.t('Mailbox Type')} *</label
					>
					<select
						id="new-mailbox-type"
						bind:value={newMailboxType}
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
					>
						<option value="personal">{$i18n.t('Personal Mailbox')}</option>
						<option value="shared">{$i18n.t('Shared Mailbox')}</option>
					</select>
				</div>

				<div>
					<label for="new-mailbox-channel" class="block text-sm font-medium mb-1"
						>{$i18n.t('Channel')} *</label
					>
					<select
						id="new-mailbox-channel"
						bind:value={selectedChannelId}
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
					>
						<option value="">{$i18n.t('Select a channel...')}</option>
						{#each availableChannels as channel}
							<option value={channel.id}>#{channel.name}</option>
						{/each}
					</select>
					<p class="text-xs text-gray-500 mt-1">
						{$i18n.t('Emails will be posted to this channel')}
					</p>
				</div>

				<div>
					<label for="new-mailbox-model" class="block text-sm font-medium mb-1"
						>{$i18n.t('AI Model')}</label
					>
					<select
						id="new-mailbox-model"
						bind:value={selectedModelId}
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
					>
						<option value="">{$i18n.t('No AI processing')}</option>
						{#each $models as model}
							<option value={model.id}>{model.name}</option>
						{/each}
					</select>
					<p class="text-xs text-gray-500 mt-1">
						{$i18n.t('AI will analyze emails and provide summaries and action items')}
					</p>
				</div>
			</div>

			<div class="flex justify-end gap-3 mt-6">
				<button
					class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
					on:click={() => {
						resetCreateForm();
						showCreateModal = false;
					}}
				>
					{$i18n.t('Cancel')}
				</button>
				<button
					class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
					disabled={creating || !selectedChannelId || !newMailboxName || !newMailboxAddress}
					on:click={handleCreateMailbox}
				>
					{#if creating}
						<Spinner className="size-4" />
					{/if}
					{$i18n.t('Create')}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Webhook Info Modal -->
{#if showWebhookModal && webhookInfo}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
		on:click|self={() => (showWebhookModal = false)}
		role="dialog"
		aria-modal="true"
		tabindex="-1"
		on:keydown={(event) => {
			if (event.key === 'Escape') {
				showWebhookModal = false;
			}
		}}
	>
		<div
			class="bg-white dark:bg-gray-900 rounded-2xl shadow-xl max-w-2xl w-full mx-4 p-6 max-h-[90vh] overflow-y-auto"
		>
			<h2 class="text-xl font-semibold mb-4">{$i18n.t('Power Automate Setup')}</h2>

			<div class="space-y-4">
				<div>
					<label for="webhook-url" class="block text-sm font-medium mb-1"
						>{$i18n.t('Webhook URL')}</label
					>
					<div class="flex gap-2">
						<input
							id="webhook-url"
							type="text"
							readonly
							value={webhookInfo.webhook_url}
							class="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-gray-50 dark:bg-gray-800 text-sm font-mono"
						/>
						<button
							class="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
							on:click={() => copyToClipboard(webhookInfo?.webhook_url || '')}
						>
							<Clipboard className="size-4" />
						</button>
					</div>
				</div>

				<div
					class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4"
				>
					<h3 class="font-medium text-amber-800 dark:text-amber-200 mb-2">
						{webhookInfo.instructions.title}
					</h3>
					<ol class="list-decimal list-inside space-y-1 text-sm text-amber-700 dark:text-amber-300">
						{#each webhookInfo.instructions.steps as step}
							<li>{step}</li>
						{/each}
					</ol>
				</div>

				<div>
					<p class="text-sm font-medium mb-1">{$i18n.t('Request Body Template')}</p>
					<div class="relative">
						<pre
							class="bg-gray-100 dark:bg-gray-800 rounded-lg p-4 text-xs overflow-x-auto">{requestBodyTemplate}</pre>
						<button
							class="absolute top-2 right-2 px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 transition"
							on:click={() => copyToClipboard(requestBodyTemplate)}
						>
							{$i18n.t('Copy')}
						</button>
					</div>
				</div>

				<div class="border-t border-gray-200 dark:border-gray-700 pt-4">
					<button
						class="text-sm text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
						on:click={handleRegenerateToken}
					>
						{$i18n.t('Regenerate Webhook Token')}
					</button>
					<p class="text-xs text-gray-500 mt-1">
						{$i18n.t('Warning: This will invalidate the current webhook URL')}
					</p>
				</div>
			</div>

			<div class="flex justify-end mt-6">
				<button
					class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
					on:click={() => (showWebhookModal = false)}
				>
					{$i18n.t('Close')}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Main Content -->
<div class="py-4">
	{#if !loaded}
		<div class="flex items-center justify-center py-12">
			<Spinner className="size-8" />
		</div>
	{:else if mailboxes.length === 0}
		<div
			class="text-center py-12 bg-gray-50 dark:bg-gray-800/50 rounded-2xl border border-gray-200 dark:border-gray-800"
		>
			<div class="text-6xl mb-4">📧</div>
			<h3 class="text-lg font-medium mb-2">{$i18n.t('No email mailboxes configured')}</h3>
			<p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
				{$i18n.t('Create a mailbox to start monitoring emails via Power Automate')}
			</p>
			<button
				class="flex items-center justify-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-blue-600 rounded-full hover:bg-blue-700 transition"
				on:click={() => (showCreateModal = true)}
			>
				<Plus className="size-4" />
				{$i18n.t('Create your first mailbox')}
			</button>
		</div>
	{:else}
		<div class="flex flex-col gap-4">
			<div class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
				<div>
					<h1 class="text-2xl font-bold">{$i18n.t('Emails')}</h1>
					<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
						{$i18n.t('Monitor email mailboxes via Power Automate integration')}
					</p>
				</div>
				<button
					class="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-black rounded-full hover:bg-gray-900 transition"
					on:click={() => (showCreateModal = true)}
				>
					<Plus className="size-4" />
					{$i18n.t('Add Mailbox')}
				</button>
			</div>

			<div class="flex flex-col gap-4 lg:flex-row">
				<div
					class="w-full lg:w-80 flex flex-col rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900"
				>
					<div
						class="flex items-center gap-2 px-4 py-3 border-b border-gray-100 dark:border-gray-850"
					>
						<Search className="size-4 text-gray-400" />
						<input
							type="text"
							bind:value={query}
							class="flex-1 text-sm bg-transparent outline-none text-gray-700 dark:text-gray-200 placeholder:text-gray-400"
							placeholder={$i18n.t('Search mailboxes')}
						/>
					</div>
					<div
						class="flex items-center justify-between px-4 py-2 border-b border-gray-100 dark:border-gray-850 text-xs font-semibold tracking-wider text-gray-500 uppercase"
					>
						<span>{$i18n.t('Mailboxes')}</span>
						<span>
							{filteredMailboxes.length}/{mailboxes.length}
						</span>
					</div>
					<div class="flex-1 overflow-y-auto px-4 py-3 space-y-2 max-h-[520px]">
						{#if filteredMailboxes.length === 0}
							<div class="text-center text-xs text-gray-500">
								{$i18n.t('No mailboxes match your search')}
							</div>
						{/if}
						{#each filteredMailboxes as mailbox}
							<button
								class={`w-full text-left rounded-2xl border px-3 py-3 transition ${
									selectedMailboxId === mailbox.id
										? 'border-blue-500 bg-blue-50/50 dark:bg-blue-900/40'
										: 'border-transparent hover:border-gray-200 dark:hover:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'
								}`}
								type="button"
								on:click={() => {
									selectedMailboxId = mailbox.id;
									closeActionMenu();
								}}
							>
								<div class="flex items-start justify-between gap-3">
									<div>
										<p class="text-sm font-semibold text-gray-900 dark:text-white">
											{mailbox.name}
										</p>
										<p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
											{mailbox.mailbox_address}
										</p>
									</div>
									<div class="flex items-center gap-2">
										<Dropdown
											show={openMenuFor === mailbox.id}
											on:change={(event) => {
												if (event.detail === false) {
													closeActionMenu();
												} else {
													openMenuFor = mailbox.id;
												}
											}}
										>
											<Tooltip content={$i18n.t('Actions')}>
												<button
													on:click={(event) => {
														event.stopPropagation();
														toggleActionMenu(mailbox.id);
													}}
													class="p-2 text-gray-500 dark:text-gray-400 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition"
													type="button"
												>
													<EllipsisVertical className="size-4" />
												</button>
											</Tooltip>
											<div slot="content">
												<DropdownMenu.Content
													class="w-48 rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-lg p-1"
													sideOffset={8}
													side="bottom"
													align="end"
													transition={flyAndScale}
												>
													<DropdownMenu.Item
														class="px-3 py-2 text-sm text-gray-700 dark:text-gray-200 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800"
														on:click={() => {
															openWebhookModal(mailbox);
															closeActionMenu();
														}}
													>
														{$i18n.t('Power Automate Setup')}
													</DropdownMenu.Item>
													<DropdownMenu.Item
														class="px-3 py-2 text-sm text-gray-700 dark:text-gray-200 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800"
														on:click={() => {
															toggleMailboxActive(mailbox);
															closeActionMenu();
														}}
													>
														{mailbox.is_active
															? $i18n.t('Deactivate mailbox')
															: $i18n.t('Activate mailbox')}
													</DropdownMenu.Item>
													{#if mailbox.channel_id}
														<DropdownMenu.Item
															class="px-3 py-2 text-sm text-gray-700 dark:text-gray-200 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800"
															on:click={() => {
																goToChannel(mailbox.channel_id);
																closeActionMenu();
															}}
														>
															{$i18n.t('Go to Channel')}
														</DropdownMenu.Item>
													{/if}
													<DropdownMenu.Item
														class="px-3 py-2 text-sm text-red-600 dark:text-red-400 rounded-xl hover:bg-red-50 dark:hover:bg-red-900/30"
														on:click={() => {
															selectedMailboxId = mailbox.id;
															showDeleteConfirm = true;
															closeActionMenu();
														}}
													>
														{$i18n.t('Delete mailbox')}
													</DropdownMenu.Item>
												</DropdownMenu.Content>
											</div>
										</Dropdown>
										<div class="scale-[0.9]">
											<Switch
												state={mailbox.is_active}
												on:change={(event) => {
													event.stopPropagation();
													toggleMailboxActive(mailbox);
												}}
											/>
										</div>
									</div>
								</div>
								<div class="flex flex-wrap gap-2 text-[11px] text-gray-500 dark:text-gray-400 mt-2">
									<span>📨 {mailbox.email_count} {$i18n.t('emails')}</span>
									{#if mailbox.last_email_at}
										<span>
											{$i18n.t('Last:')}
											{dayjs(mailbox.last_email_at / 1000000).fromNow()}
										</span>
									{/if}
									{#if mailbox.channel_name}
										<span class="text-blue-600 dark:text-blue-300">#{mailbox.channel_name}</span>
									{/if}
								</div>
								{#if mailbox.description}
									<p class="text-xs text-gray-500 dark:text-gray-400 mt-2 line-clamp-2">
										{mailbox.description}
									</p>
								{/if}
							</button>
						{/each}
					</div>
				</div>

				<div
					class="flex-1 rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900"
				>
					{#if selectedMailbox}
						<div class="flex flex-col h-full">
							<div
								class="flex flex-col gap-3 border-b border-gray-100 dark:border-gray-850 px-5 py-4"
							>
								<div class="flex justify-between items-start gap-3">
									<div class="flex-1 space-y-1">
										<div
											class="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400"
										>
											{$i18n.t('Mailbox Name')}
										</div>
										<input
											class="w-full px-3 py-2 text-sm border border-gray-200 rounded-xl bg-gray-50 dark:bg-gray-950/50 dark:border-gray-800 text-gray-900 dark:text-white"
											bind:value={editName}
										/>
									</div>

									<button
										class="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-black rounded-full hover:bg-gray-900 transition disabled:opacity-60 disabled:cursor-not-allowed"
										disabled={isSaving || !selectedMailbox}
										on:click={handleSaveMailbox}
										type="button"
									>
										{#if isSaving}
											<Spinner className="size-4" />
										{/if}
										{$i18n.t('Save')}
									</button>
								</div>

								<input
									class="w-full px-3 py-2 text-sm border border-gray-200 rounded-xl bg-gray-50 dark:bg-gray-950/50 dark:border-gray-800 text-gray-900 dark:text-white"
									value={selectedMailbox.mailbox_address}
									readonly
								/>
							</div>
							<div class="px-5 py-4 space-y-4">
								<div class="grid gap-4 md:grid-cols-2">
									<div class="space-y-1">
										<div
											class="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400"
										>
											{$i18n.t('Mailbox Type')}
										</div>
										<select
											class="w-full px-3 py-2 text-sm border border-gray-200 rounded-xl bg-gray-50 dark:bg-gray-950/50 dark:border-gray-800 text-gray-900 dark:text-white"
											bind:value={editMailboxType}
										>
											<option value="personal">{$i18n.t('Personal')}</option>
											<option value="shared">{$i18n.t('Shared')}</option>
										</select>
									</div>
									<div class="space-y-1">
										<div
											class="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400"
										>
											{$i18n.t('Status')}
										</div>
										<span
											class="inline-flex w-full items-center justify-center px-3 py-2 text-sm border border-gray-200 rounded-xl bg-gray-50 dark:bg-gray-950/50 dark:border-gray-800 text-gray-900 dark:text-white"
										>
											{selectedMailbox.is_active ? $i18n.t('Active') : $i18n.t('Inactive')}
										</span>
									</div>
									<div class="space-y-1">
										<div
											class="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400"
										>
											{$i18n.t('AI Model')}
										</div>
										<select
											class="w-full px-3 py-2 text-sm border border-gray-200 rounded-xl bg-gray-50 dark:bg-gray-950/50 dark:border-gray-800 text-gray-900 dark:text-white"
											bind:value={editModelId}
										>
											<option value="">{$i18n.t('No AI processing')}</option>
											{#each $models as modelOption}
												<option value={modelOption.id}>{modelOption.name}</option>
											{/each}
										</select>
									</div>
									<div class="space-y-1">
										<div
											class="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400"
										>
											{$i18n.t('Channel')}
										</div>
										<select
											class="w-full px-3 py-2 text-sm border border-gray-200 rounded-xl bg-gray-50 dark:bg-gray-950/50 dark:border-gray-800 text-gray-900 dark:text-white"
											bind:value={editChannelId}
										>
											<option value="">{$i18n.t('No channel assigned')}</option>
											{#each availableChannels as channelOption}
												<option value={channelOption.id}>#{channelOption.name}</option>
											{/each}
										</select>
									</div>
								</div>

								<div class="space-y-1">
									<div
										class="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400"
									>
										{$i18n.t('Description')}
									</div>
									<textarea
										rows="3"
										class="w-full px-3 py-2 text-sm border border-gray-200 rounded-xl bg-gray-50 dark:bg-gray-950/50 dark:border-gray-800 text-gray-900 dark:text-white resize-none"
										bind:value={editDescription}
									></textarea>
								</div>

								<div class="grid gap-4 md:grid-cols-2">
									<div class="space-y-1">
										<div
											class="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400"
										>
											{$i18n.t('Emails Received')}
										</div>
										<p class="text-lg font-semibold text-gray-900 dark:text-white">
											{selectedMailbox.email_count}
										</p>
									</div>
									{#if selectedMailbox.last_email_at}
										<div class="space-y-1">
											<div
												class="text-xs font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400"
											>
												{$i18n.t('Last email')}
											</div>
											<p class="text-sm text-gray-700 dark:text-gray-200">
												{dayjs(selectedMailbox.last_email_at / 1000000).format('LLL')}
											</p>
											<p class="text-xs text-gray-500 dark:text-gray-400">
												{dayjs(selectedMailbox.last_email_at / 1000000).fromNow()}
											</p>
										</div>
									{/if}
								</div>

								<div
									class="bg-gray-50 dark:bg-gray-900/60 border border-gray-100 dark:border-gray-800 rounded-xl p-4 flex flex-col gap-2 text-xs"
								>
									<div class="flex items-center justify-between gap-4">
										<div>
											<p class="font-semibold text-gray-700 dark:text-gray-200">
												{$i18n.t('Webhook token')}
											</p>
											<p class="font-mono text-[13px] text-gray-500 dark:text-gray-400 break-all">
												{selectedMailbox.webhook_token || $i18n.t('Not available')}
											</p>
										</div>
										<button
											class="flex items-center gap-1 px-3 py-1 text-[11px] font-semibold text-blue-600 rounded-full border border-blue-100 hover:bg-blue-50 dark:border-blue-900 dark:text-blue-300 dark:hover:bg-blue-900/40 transition"
											on:click={() => copyToClipboard(selectedMailbox.webhook_token ?? '')}
										>
											<Clipboard className="size-4" />
											{$i18n.t('Copy')}
										</button>
									</div>
									<p class="text-[11px] text-gray-500 dark:text-gray-400">
										{$i18n.t('Use this token to configure Power Automate or other automations')}
									</p>
								</div>
							</div>
						</div>
					{:else}
						<div
							class="flex items-center justify-center h-full p-12 text-sm text-gray-500 dark:text-gray-400"
						>
							{$i18n.t('Select a mailbox to view its details')}
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}
</div>
