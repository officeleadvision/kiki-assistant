<script lang="ts">
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, config, user, models, channels } from '$lib/stores';
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
	import Tooltip from '../common/Tooltip.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Plus from '../icons/Plus.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import Clipboard from '../icons/Clipboard.svelte';

	let loaded = false;
	let mailboxes: EmailMailbox[] = [];
	let availableChannels: any[] = [];

	let showDeleteConfirm = false;
	let selectedMailbox: EmailMailbox | null = null;

	let showCreateModal = false;
	let showWebhookModal = false;
	let webhookInfo: WebhookInfo | null = null;
	let webhookMailbox: EmailMailbox | null = null;
	let creating = false;

	// Create form state
	let newMailboxName = '';
	let newMailboxDescription = '';
	let newMailboxAddress = '';
	let newMailboxType: 'personal' | 'shared' = 'personal';
	let selectedChannelId = '';
	let selectedModelId = '';

	const loadMailboxes = async () => {
		try {
			mailboxes = await getMailboxes(localStorage.token) ?? [];
		} catch (e) {
			console.error('Error loading mailboxes:', e);
			mailboxes = [];
			toast.error(`${e}`);
		}
	};

	const loadChannels = async () => {
		try {
			availableChannels = await getChannels(localStorage.token) ?? [];
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
					result.is_active
						? $i18n.t('Mailbox activated')
						: $i18n.t('Mailbox deactivated')
				);
			}
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	onMount(async () => {
		await Promise.all([loadMailboxes(), loadChannels()]);
		loaded = true;
	});
</script>

<svelte:head>
	<title>{$i18n.t('Emails')} • {$WEBUI_NAME}</title>
</svelte:head>

<!-- Delete Confirmation Dialog -->
<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete Mailbox')}
	message={$i18n.t('Are you sure you want to delete this email mailbox? This will also delete all associated email records.')}
	on:confirm={() => {
		if (selectedMailbox) {
			handleDeleteMailbox(selectedMailbox);
			selectedMailbox = null;
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
	>
		<div class="bg-white dark:bg-gray-900 rounded-2xl shadow-xl max-w-lg w-full mx-4 p-6">
			<h2 class="text-xl font-semibold mb-4">{$i18n.t('Create Email Mailbox')}</h2>

			<div class="space-y-4">
				<div>
					<label class="block text-sm font-medium mb-1">{$i18n.t('Name')} *</label>
					<input
						type="text"
						bind:value={newMailboxName}
						placeholder={$i18n.t('E.g., Support Inbox')}
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
					/>
				</div>

				<div>
					<label class="block text-sm font-medium mb-1">{$i18n.t('Description')}</label>
					<input
						type="text"
						bind:value={newMailboxDescription}
						placeholder={$i18n.t('Optional description')}
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
					/>
				</div>

				<div>
					<label class="block text-sm font-medium mb-1">{$i18n.t('Email Address')} *</label>
					<input
						type="email"
						bind:value={newMailboxAddress}
						placeholder={$i18n.t('E.g., support@company.com')}
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
					/>
				</div>

				<div>
					<label class="block text-sm font-medium mb-1">{$i18n.t('Mailbox Type')} *</label>
					<select
						bind:value={newMailboxType}
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-700 rounded-lg bg-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
					>
						<option value="personal">{$i18n.t('Personal Mailbox')}</option>
						<option value="shared">{$i18n.t('Shared Mailbox')}</option>
					</select>
				</div>

				<div>
					<label class="block text-sm font-medium mb-1">{$i18n.t('Channel')} *</label>
					<select
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
					<label class="block text-sm font-medium mb-1">{$i18n.t('AI Model')}</label>
					<select
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
	>
		<div class="bg-white dark:bg-gray-900 rounded-2xl shadow-xl max-w-2xl w-full mx-4 p-6 max-h-[90vh] overflow-y-auto">
			<h2 class="text-xl font-semibold mb-4">{$i18n.t('Power Automate Setup')}</h2>

			<div class="space-y-4">
				<div>
					<label class="block text-sm font-medium mb-1">{$i18n.t('Webhook URL')}</label>
					<div class="flex gap-2">
						<input
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

				<div class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
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
					<label class="block text-sm font-medium mb-1">{$i18n.t('Request Body Template')}</label>
					<div class="relative">
						<pre class="bg-gray-100 dark:bg-gray-800 rounded-lg p-4 text-xs overflow-x-auto">{JSON.stringify(webhookInfo.instructions.body_template, null, 2)}</pre>
						<button
							class="absolute top-2 right-2 px-2 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 transition"
							on:click={() =>
								copyToClipboard(JSON.stringify(webhookInfo?.instructions.body_template, null, 2))}
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
	<div class="flex items-center justify-between mb-6">
		<div>
			<h1 class="text-2xl font-bold">{$i18n.t('Emails')}</h1>
			<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
				{$i18n.t('Monitor email mailboxes via Power Automate integration')}
			</p>
		</div>
		<button
			class="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
			on:click={() => (showCreateModal = true)}
		>
			<Plus className="size-4" />
			{$i18n.t('Add Mailbox')}
		</button>
	</div>

	{#if !loaded}
		<div class="flex items-center justify-center py-12">
			<Spinner className="size-8" />
		</div>
	{:else if mailboxes.length === 0}
		<div class="text-center py-12 bg-gray-50 dark:bg-gray-800/50 rounded-xl">
			<div class="text-6xl mb-4">📧</div>
			<h3 class="text-lg font-medium mb-2">{$i18n.t('No email mailboxes configured')}</h3>
			<p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
				{$i18n.t('Create a mailbox to start monitoring emails via Power Automate')}
			</p>
			<button
				class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
				on:click={() => (showCreateModal = true)}
			>
				{$i18n.t('Create your first mailbox')}
			</button>
		</div>
	{:else}
		<div class="grid gap-4">
			{#each mailboxes as mailbox}
				<div
					class="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-4 hover:shadow-md transition {!mailbox.is_active ? 'opacity-60' : ''}"
				>
					<div class="flex items-start justify-between">
						<div class="flex-1">
							<div class="flex items-center gap-2">
								<h3 class="font-semibold text-lg">{mailbox.name}</h3>
								<span
									class="px-2 py-0.5 text-xs font-medium rounded-full {mailbox.mailbox_type === 'shared'
										? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300'
										: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'}"
								>
									{mailbox.mailbox_type === 'shared'
										? $i18n.t('Shared')
										: $i18n.t('Personal')}
								</span>
								{#if !mailbox.is_active}
									<span
										class="px-2 py-0.5 text-xs font-medium rounded-full bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"
									>
										{$i18n.t('Inactive')}
									</span>
								{/if}
							</div>
							{#if mailbox.description}
								<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
									{mailbox.description}
								</p>
							{/if}
							<p class="text-sm text-gray-600 dark:text-gray-300 mt-2">
								📬 {mailbox.mailbox_address}
							</p>
							<div class="flex items-center gap-4 mt-2 text-sm text-gray-500 dark:text-gray-400">
								<span>
									📨 {mailbox.email_count}
									{$i18n.t('emails received')}
								</span>
								{#if mailbox.last_email_at}
									<span>
										{$i18n.t('Last:')}
										{dayjs(mailbox.last_email_at / 1000000).fromNow()}
									</span>
								{/if}
								{#if mailbox.channel_name}
									<button
										class="text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
										on:click={() => goToChannel(mailbox.channel_id)}
									>
										#{mailbox.channel_name}
									</button>
								{/if}
							</div>
						</div>

						<div class="flex items-center gap-2">
							<Tooltip content={$i18n.t('Power Automate Setup')}>
								<button
									class="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition"
									on:click={() => openWebhookModal(mailbox)}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="size-5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244"
										/>
									</svg>
								</button>
							</Tooltip>

							<Tooltip
								content={mailbox.is_active
									? $i18n.t('Deactivate')
									: $i18n.t('Activate')}
							>
								<button
									class="p-2 text-gray-500 hover:text-yellow-600 hover:bg-yellow-50 dark:hover:bg-yellow-900/20 rounded-lg transition"
									on:click={() => toggleMailboxActive(mailbox)}
								>
									{#if mailbox.is_active}
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke-width="1.5"
											stroke="currentColor"
											class="size-5"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M14.25 9v6m-4.5 0V9M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
											/>
										</svg>
									{:else}
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke-width="1.5"
											stroke="currentColor"
											class="size-5"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
											/>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M15.91 11.672a.375.375 0 010 .656l-5.603 3.113a.375.375 0 01-.557-.328V8.887c0-.286.307-.466.557-.327l5.603 3.112z"
											/>
										</svg>
									{/if}
								</button>
							</Tooltip>

							<Tooltip content={$i18n.t('Go to Channel')}>
								<button
									class="p-2 text-gray-500 hover:text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded-lg transition"
									on:click={() => goToChannel(mailbox.channel_id)}
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="size-5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
										/>
									</svg>
								</button>
							</Tooltip>

							<Tooltip content={$i18n.t('Delete')}>
								<button
									class="p-2 text-gray-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition"
									on:click={() => {
										selectedMailbox = mailbox;
										showDeleteConfirm = true;
									}}
								>
									<GarbageBin className="size-5" />
								</button>
							</Tooltip>
						</div>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

