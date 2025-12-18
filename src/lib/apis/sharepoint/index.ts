import { WEBUI_API_BASE_URL } from '$lib/constants';

export interface SyncLogEntry {
	timestamp: number;
	level: string; // info, success, error, skip, warning
	message: string;
	file_name?: string;
}

export interface SharePointSync {
	id: string;
	user_id: string;
	name: string;
	knowledge_id: string;
	drive_id: string;
	item_id: string;
	folder_path: string;
	sharepoint_endpoint: string;
	last_sync_at: number | null;
	file_count: number;
	sync_status: string;
	sync_error: string | null;
	sync_logs: SyncLogEntry[] | null;
	created_at: number;
	updated_at: number;
}

export interface SharePointSyncForm {
	name: string;
	knowledge_id: string;
	drive_id: string;
	item_id: string;
	folder_path: string;
	sharepoint_endpoint: string;
}

export const getSharePointSyncs = async (token: string): Promise<SharePointSync[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/sharepoint/`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res ?? [];
};

export const getSharePointSyncById = async (
	token: string,
	id: string
): Promise<SharePointSync | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/sharepoint/${id}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const createSharePointSync = async (
	token: string,
	formData: SharePointSyncForm
): Promise<SharePointSync | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/sharepoint/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(formData)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteSharePointSync = async (token: string, id: string): Promise<boolean> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/sharepoint/${id}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res?.status ?? false;
};

export const executeSharePointSync = async (
	token: string,
	id: string,
	accessToken: string
): Promise<{ status: boolean; message: string; sync_status: string }> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/sharepoint/${id}/sync`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ access_token: accessToken })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSyncStatus = async (
	token: string,
	id: string
): Promise<{
	id: string;
	sync_status: string;
	sync_error: string | null;
	file_count: number;
	last_sync_at: number | null;
}> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/sharepoint/${id}/status`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const listSharePointFolder = async (
	token: string,
	accessToken: string,
	endpoint: string,
	driveId: string,
	itemId: string
): Promise<{ files: any[]; count: number }> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/sharepoint/list-folder`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			access_token: accessToken,
			endpoint: endpoint,
			drive_id: driveId,
			item_id: itemId
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res ?? { files: [], count: 0 };
};
