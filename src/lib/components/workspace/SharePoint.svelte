<script lang="ts">
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { toast } from 'svelte-sonner';
	import { onMount, onDestroy, getContext, tick } from 'svelte';
	const i18n = getContext('i18n');

	import { WEBUI_NAME, config, knowledge, user } from '$lib/stores';
	import { getKnowledgeBaseList } from '$lib/apis/knowledge';
	import {
		getSharePointSyncs,
		createSharePointSync,
		deleteSharePointSync,
		executeSharePointSync,
		getSyncStatus,
		type SharePointSync
	} from '$lib/apis/sharepoint';
	import {
		openSharePointFolderPicker,
		getSharePointAccessToken,
		type SharePointFolderInfo
	} from '$lib/utils/onedrive-file-picker';

	import DeleteConfirmDialog from '../common/ConfirmDialog.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Plus from '../icons/Plus.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import ArrowPath from '../icons/ArrowPath.svelte';
	import FolderOpen from '../icons/FolderOpen.svelte';
	import Cloud from '../icons/Cloud.svelte';

	let loaded = false;
	let syncs: SharePointSync[] = [];
	let knowledgeBases: any[] = [];

	let showDeleteConfirm = false;
	let selectedSync: SharePointSync | null = null;

	let showCreateModal = false;
	let showLogsModal = false;
	let logsSync: SharePointSync | null = null;
	let creating = false;
	let syncingIds: Set<string> = new Set();

	// Create form state
	let newSyncName = '';
	let selectedKnowledgeId = '';
	let selectedFolder: SharePointFolderInfo | null = null;

	const loadSyncs = async () => {
		try {
			syncs = await getSharePointSyncs(localStorage.token);
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const loadKnowledgeBases = async () => {
		try {
			knowledgeBases = await getKnowledgeBaseList(localStorage.token);
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	const openFolderPicker = async () => {
		try {
			const folder = await openSharePointFolderPicker();
			if (folder) {
				selectedFolder = folder;
				if (!newSyncName) {
					newSyncName = folder.name;
				}
			}
		} catch (e) {
			console.error('SharePoint folder picker error:', e);
			toast.error($i18n.t('Failed to open SharePoint folder picker'));
		}
	};

	const handleCreateSync = async () => {
		if (!selectedFolder || !selectedKnowledgeId || !newSyncName) {
			toast.error($i18n.t('Please fill in all required fields'));
			return;
		}

		creating = true;
		try {
			const result = await createSharePointSync(localStorage.token, {
				name: newSyncName,
				knowledge_id: selectedKnowledgeId,
				drive_id: selectedFolder.driveId,
				item_id: selectedFolder.id,
				folder_path: selectedFolder.path,
				sharepoint_endpoint: selectedFolder.endpoint
			});

			if (result) {
				toast.success($i18n.t('SharePoint sync created successfully'));
				syncs = [...syncs, result];
				resetCreateForm();
				showCreateModal = false;
			}
		} catch (e) {
			toast.error(`${e}`);
		} finally {
			creating = false;
		}
	};

	const handleDeleteSync = async (sync: SharePointSync) => {
		try {
			const result = await deleteSharePointSync(localStorage.token, sync.id);
			if (result) {
				syncs = syncs.filter((s) => s.id !== sync.id);
				toast.success($i18n.t('SharePoint sync deleted successfully'));
			}
		} catch (e) {
			toast.error(`${e}`);
		}
	};

	// Polling intervals for status checks
	let pollIntervals: Map<string, ReturnType<typeof setInterval>> = new Map();

	const startPolling = (syncId: string) => {
		// Don't start if already polling
		if (pollIntervals.has(syncId)) return;

		const interval = setInterval(async () => {
			try {
				const status = await getSyncStatus(localStorage.token, syncId);

				// Update the sync in our local list
				syncs = syncs.map((s) =>
					s.id === syncId
						? {
								...s,
								sync_status: status.sync_status,
								sync_error: status.sync_error,
								file_count: status.file_count,
								last_sync_at: status.last_sync_at,
								sync_logs: status.sync_logs
							}
						: s
				);

				// Also update the logs modal if it's open for this sync
				if (logsSync && logsSync.id === syncId) {
					logsSync = {
						...logsSync,
						sync_status: status.sync_status,
						sync_error: status.sync_error,
						file_count: status.file_count,
						last_sync_at: status.last_sync_at,
						sync_logs: status.sync_logs
					};
				}

				// If sync is complete, stop polling
				if (status.sync_status !== 'syncing') {
					stopPolling(syncId);
					syncingIds.delete(syncId);
					syncingIds = syncingIds;

					if (status.sync_status === 'synced') {
						toast.success($i18n.t('Sync completed: {{count}} files', { count: status.file_count }));
						// Refresh knowledge stores
						knowledge.set(await getKnowledgeBaseList(localStorage.token));
					} else if (status.sync_status === 'error') {
						toast.error(
							$i18n.t('Sync failed: {{error}}', { error: status.sync_error || 'Unknown error' })
						);
					}
				}
			} catch (e) {
				console.error('Error polling sync status:', e);
			}
		}, 3000); // Poll every 3 seconds

		pollIntervals.set(syncId, interval);
	};

	const stopPolling = (syncId: string) => {
		const interval = pollIntervals.get(syncId);
		if (interval) {
			clearInterval(interval);
			pollIntervals.delete(syncId);
		}
	};

	const handleExecuteSync = async (sync: SharePointSync) => {
		syncingIds.add(sync.id);
		syncingIds = syncingIds;

		try {
			const accessToken = await getSharePointAccessToken();
			const result = await executeSharePointSync(localStorage.token, sync.id, accessToken);

			if (result.status) {
				// Update local sync status immediately
				syncs = syncs.map((s) => (s.id === sync.id ? { ...s, sync_status: 'syncing' } : s));

				toast.info($i18n.t('Sync started in background. You can leave this page.'));

				// Start polling for status
				startPolling(sync.id);
			}
		} catch (e) {
			toast.error(`${e}`);
			syncingIds.delete(sync.id);
			syncingIds = syncingIds;
		}
	};

	// Cleanup polling on component destroy
	onDestroy(() => {
		pollIntervals.forEach((interval) => clearInterval(interval));
		pollIntervals.clear();
	});

	const resetCreateForm = () => {
		newSyncName = '';
		selectedKnowledgeId = '';
		selectedFolder = null;
	};

	const getKnowledgeName = (knowledgeId: string) => {
		const kb = knowledgeBases.find((k) => k.id === knowledgeId);
		return kb?.name || knowledgeId;
	};

	onMount(async () => {
		await Promise.all([loadSyncs(), loadKnowledgeBases()]);
		loaded = true;

		// Resume polling for any syncs that are already in progress
		syncs.forEach((sync) => {
			if (sync.sync_status === 'syncing') {
				syncingIds.add(sync.id);
				syncingIds = syncingIds;
				startPolling(sync.id);
			}
		});
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('SharePoint')} • {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<DeleteConfirmDialog
		bind:show={showDeleteConfirm}
		on:confirm={() => {
			if (selectedSync) {
				handleDeleteSync(selectedSync);
			}
		}}
	/>

	<!-- Create Sync Modal -->
	{#if showCreateModal}
		<div
			class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
			on:click={() => {
				showCreateModal = false;
				resetCreateForm();
			}}
			on:keydown={(e) => {
				if (e.key === 'Escape') {
					showCreateModal = false;
					resetCreateForm();
				}
			}}
		>
			<div
				class="bg-white dark:bg-gray-900 rounded-2xl p-6 w-full max-w-lg mx-4 shadow-xl"
				on:click|stopPropagation
				on:keydown|stopPropagation
			>
				<h2 class="text-lg font-semibold mb-4">{$i18n.t('New SharePoint Sync')}</h2>

				<div class="space-y-4">
					<!-- Sync Name -->
					<div>
						<label class="block text-sm font-medium mb-1">{$i18n.t('Sync Name')}</label>
						<input
							type="text"
							bind:value={newSyncName}
							placeholder={$i18n.t('Enter a name for this sync')}
							class="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
						/>
					</div>

					<!-- SharePoint Folder -->
					<div>
						<label class="block text-sm font-medium mb-1">{$i18n.t('SharePoint Folder')}</label>
						{#if selectedFolder}
							<div
								class="flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
							>
								<FolderOpen className="size-5 text-blue-500" />
								<div class="flex-1 min-w-0">
									<div class="font-medium truncate">{selectedFolder.name}</div>
									<div class="text-xs text-gray-500 truncate">{selectedFolder.path}</div>
								</div>
								<button
									class="text-sm text-blue-500 hover:text-blue-600"
									on:click={openFolderPicker}
								>
									{$i18n.t('Change')}
								</button>
							</div>
						{:else}
							<button
								class="w-full px-4 py-3 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg hover:border-blue-500 dark:hover:border-blue-500 transition flex items-center justify-center gap-2 text-gray-500 hover:text-blue-500"
								on:click={openFolderPicker}
							>
								<FolderOpen className="size-5" />
								{$i18n.t('Select SharePoint Folder')}
							</button>
						{/if}
					</div>

					<!-- Knowledge Collection -->
					<div>
						<label class="block text-sm font-medium mb-1">{$i18n.t('Knowledge Collection')}</label>
						<select
							bind:value={selectedKnowledgeId}
							class="w-full px-3 py-2 border border-gray-200 dark:border-gray-700 rounded-lg bg-transparent focus:outline-none focus:ring-2 focus:ring-blue-500"
						>
							<option value="">{$i18n.t('Select a knowledge collection')}</option>
							{#each knowledgeBases as kb}
								<option value={kb.id}>{kb.name}</option>
							{/each}
						</select>
					</div>
				</div>

				<div class="flex justify-end gap-2 mt-6">
					<button
						class="px-4 py-2 text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
						on:click={() => {
							showCreateModal = false;
							resetCreateForm();
						}}
					>
						{$i18n.t('Cancel')}
					</button>
					<button
						class="px-4 py-2 text-sm font-medium bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
						disabled={creating || !selectedFolder || !selectedKnowledgeId || !newSyncName}
						on:click={handleCreateSync}
					>
						{#if creating}
							<Spinner className="size-4" />
						{/if}
						{$i18n.t('Create Sync')}
					</button>
				</div>
			</div>
		</div>
	{/if}

	<!-- Logs Modal -->
	{#if showLogsModal && logsSync}
		<div
			class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
			on:click={() => {
				showLogsModal = false;
				logsSync = null;
			}}
			on:keydown={(e) => {
				if (e.key === 'Escape') {
					showLogsModal = false;
					logsSync = null;
				}
			}}
		>
			<div
				class="bg-white dark:bg-gray-900 rounded-2xl p-6 w-full max-w-2xl mx-4 shadow-xl max-h-[80vh] flex flex-col"
				on:click|stopPropagation
				on:keydown|stopPropagation
			>
				<div class="flex items-center justify-between mb-4">
					<h2 class="text-lg font-semibold">{logsSync.name} - {$i18n.t('Sync Logs')}</h2>
					<button
						class="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
						on:click={() => {
							showLogsModal = false;
							logsSync = null;
						}}
					>
						<svg class="size-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M6 18L18 6M6 6l12 12"
							/>
						</svg>
					</button>
				</div>

				<!-- Sync Info -->
				<div class="mb-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg text-sm">
					<div class="grid grid-cols-2 gap-2">
						<div>
							<span class="text-gray-500">{$i18n.t('Status')}:</span>
							<span
								class="font-medium {logsSync.sync_status === 'synced'
									? 'text-green-600'
									: logsSync.sync_status === 'error'
										? 'text-red-600'
										: logsSync.sync_status === 'syncing'
											? 'text-yellow-600'
											: ''}"
							>
								{logsSync.sync_status}
							</span>
						</div>
						<div>
							<span class="text-gray-500">{$i18n.t('Files')}:</span>
							<span class="font-medium">{logsSync.file_count}</span>
						</div>
						<div>
							<span class="text-gray-500">{$i18n.t('Last sync')}:</span>
							<span class="font-medium"
								>{logsSync.last_sync_at
									? dayjs(logsSync.last_sync_at * 1000).format('YYYY-MM-DD HH:mm:ss')
									: 'Never'}</span
							>
						</div>
						<div>
							<span class="text-gray-500">{$i18n.t('Folder')}:</span>
							<span class="font-medium truncate">{logsSync.folder_path}</span>
						</div>
					</div>
					{#if logsSync.sync_error}
						<div class="mt-2 text-red-600 text-xs">{$i18n.t('Error')}: {logsSync.sync_error}</div>
					{/if}
				</div>

				<!-- Logs List -->
				<div class="flex-1 overflow-y-auto">
					{#if logsSync.sync_logs && logsSync.sync_logs.length > 0}
						<div class="space-y-1">
							{#each logsSync.sync_logs as logEntry}
								<div
									class="flex items-start gap-2 text-sm py-1 px-2 rounded {logEntry.level ===
									'success'
										? 'bg-green-50 dark:bg-green-900/20'
										: logEntry.level === 'error'
											? 'bg-red-50 dark:bg-red-900/20'
											: logEntry.level === 'skip'
												? 'bg-gray-50 dark:bg-gray-800/50'
												: 'bg-blue-50 dark:bg-blue-900/20'}"
								>
									<span class="text-xs text-gray-400 whitespace-nowrap">
										{dayjs(logEntry.timestamp * 1000).format('HH:mm:ss')}
									</span>
									<span
										class="font-medium {logEntry.level === 'success'
											? 'text-green-600 dark:text-green-400'
											: logEntry.level === 'error'
												? 'text-red-600 dark:text-red-400'
												: logEntry.level === 'skip'
													? 'text-gray-500'
													: 'text-blue-600 dark:text-blue-400'}"
									>
										{#if logEntry.level === 'success'}✓
										{:else if logEntry.level === 'error'}✗
										{:else if logEntry.level === 'skip'}○
										{:else}●{/if}
									</span>
									{#if logEntry.file_name}
										<span class="truncate font-medium">{logEntry.file_name}</span>
										<span class="text-gray-500">-</span>
									{/if}
									<span class="text-gray-600 dark:text-gray-300">{logEntry.message}</span>
								</div>
							{/each}
						</div>
					{:else}
						<div class="text-center text-gray-500 py-8">
							<p>{$i18n.t('No logs available')}</p>
							<p class="text-sm mt-1">{$i18n.t('Run a sync to see logs here')}</p>
						</div>
					{/if}
				</div>

				<div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex justify-end">
					<button
						class="px-4 py-2 text-sm font-medium bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition"
						on:click={() => {
							showLogsModal = false;
							logsSync = null;
						}}
					>
						{$i18n.t('Close')}
					</button>
				</div>
			</div>
		</div>
	{/if}

	<div class="flex flex-col gap-1 px-1 mt-1.5 mb-3">
		<div class="flex justify-between items-center">
			<div class="flex items-center md:self-center text-xl font-medium px-0.5 gap-2 shrink-0">
				<Cloud className="size-6" />
				<div>
					{$i18n.t('SharePoint Sync')}
				</div>

				<div class="text-lg font-medium text-gray-500 dark:text-gray-500">
					{syncs.length}
				</div>
			</div>

			<div class="flex w-full justify-end gap-1.5">
				{#if $config?.features?.enable_onedrive_integration && $config?.features?.enable_onedrive_business}
					<button
						class="px-2 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black transition font-medium text-sm flex items-center"
						on:click={() => {
							showCreateModal = true;
						}}
					>
						<Plus className="size-3" strokeWidth="2.5" />
						<div class="hidden md:block md:ml-1 text-xs">{$i18n.t('New Sync')}</div>
					</button>
				{/if}
			</div>
		</div>
	</div>

	{#if !$config?.features?.enable_onedrive_integration || !$config?.features?.enable_onedrive_business}
		<div
			class="py-8 px-4 bg-white dark:bg-gray-900 rounded-3xl border border-gray-100/30 dark:border-gray-850/30"
		>
			<div class="text-center text-gray-500">
				<Cloud className="size-12 mx-auto mb-3 opacity-50" />
				<p class="font-medium">{$i18n.t('SharePoint Integration Not Enabled')}</p>
				<p class="text-sm mt-1">
					{$i18n.t(
						'Please enable OneDrive Business integration in admin settings to use SharePoint sync.'
					)}
				</p>
			</div>
		</div>
	{:else if syncs.length === 0}
		<div
			class="py-8 px-4 bg-white dark:bg-gray-900 rounded-3xl border border-gray-100/30 dark:border-gray-850/30"
		>
			<div class="text-center text-gray-500">
				<FolderOpen className="size-12 mx-auto mb-3 opacity-50" />
				<p class="font-medium">{$i18n.t('No SharePoint Syncs')}</p>
				<p class="text-sm mt-1">
					{$i18n.t(
						'Create a sync to keep a SharePoint folder synchronized with a knowledge collection.'
					)}
				</p>
				<button
					class="mt-4 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition text-sm font-medium"
					on:click={() => {
						showCreateModal = true;
					}}
				>
					{$i18n.t('Create Your First Sync')}
				</button>
			</div>
		</div>
	{:else}
		<div
			class="py-2 bg-white dark:bg-gray-900 rounded-3xl border border-gray-100/30 dark:border-gray-850/30"
		>
			<div class="divide-y divide-gray-100 dark:divide-gray-800">
				{#each syncs as sync}
					<div class="px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-850/50 transition">
						<div class="flex items-start gap-3">
							<button
								class="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg hover:bg-blue-200 dark:hover:bg-blue-900/50 transition"
								on:click={() => {
									logsSync = sync;
									showLogsModal = true;
								}}
							>
								<FolderOpen className="size-5 text-blue-500" />
							</button>

							<button
								class="flex-1 min-w-0 text-left"
								on:click={() => {
									logsSync = sync;
									showLogsModal = true;
								}}
							>
								<div class="flex items-center gap-2">
									<span class="font-medium hover:text-blue-500 transition">{sync.name}</span>
									{#if sync.sync_status === 'syncing'}
										<span
											class="px-2 py-0.5 text-xs bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400 rounded-full flex items-center gap-1"
										>
											<Spinner className="size-3" />
											{$i18n.t('Syncing...')}
										</span>
									{:else if sync.sync_status === 'synced'}
										<span
											class="px-2 py-0.5 text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 rounded-full flex items-center gap-1"
										>
											<svg class="size-3" viewBox="0 0 20 20" fill="currentColor">
												<path
													fill-rule="evenodd"
													d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
													clip-rule="evenodd"
												/>
											</svg>
											{$i18n.t('Synced')}
										</span>
									{:else if sync.sync_status === 'error'}
										<Tooltip content={sync.sync_error || ''}>
											<span
												class="px-2 py-0.5 text-xs bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-full cursor-help"
											>
												{$i18n.t('Error')}
											</span>
										</Tooltip>
									{/if}
								</div>

								<div class="text-sm text-gray-500 mt-0.5 truncate">
									{sync.folder_path}
								</div>

								<div class="flex items-center gap-4 mt-1 text-xs text-gray-400">
									<span>
										→ {getKnowledgeName(sync.knowledge_id)}
									</span>
									{#if sync.file_count > 0}
										<span>{sync.file_count} {$i18n.t('files')}</span>
									{/if}
									{#if sync.last_sync_at}
										<span>
											{$i18n.t('Last sync')}: {dayjs(sync.last_sync_at * 1000).fromNow()}
										</span>
									{/if}
								</div>
							</button>

							<div class="flex items-center gap-1">
								<Tooltip content={$i18n.t('Sync Now')}>
									<button
										class="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition disabled:opacity-50"
										disabled={syncingIds.has(sync.id) || sync.sync_status === 'syncing'}
										on:click={() => handleExecuteSync(sync)}
									>
										{#if syncingIds.has(sync.id)}
											<Spinner className="size-4" />
										{:else}
											<ArrowPath className="size-4" />
										{/if}
									</button>
								</Tooltip>

								<Tooltip content={$i18n.t('Delete')}>
									<button
										class="p-2 hover:bg-red-100 dark:hover:bg-red-900/30 text-red-500 rounded-lg transition"
										on:click={() => {
											selectedSync = sync;
											showDeleteConfirm = true;
										}}
									>
										<GarbageBin className="size-4" />
									</button>
								</Tooltip>
							</div>
						</div>
					</div>
				{/each}
			</div>
		</div>
	{/if}
{:else}
	<div class="flex justify-center py-8">
		<Spinner className="size-6" />
	</div>
{/if}
