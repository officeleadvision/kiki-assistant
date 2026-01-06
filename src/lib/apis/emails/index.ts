import { WEBUI_API_BASE_URL } from '$lib/constants';

export type EmailMailbox = {
	id: string;
	user_id: string;
	name: string;
	description?: string;
	mailbox_address: string;
	mailbox_type: 'personal' | 'shared';
	channel_id: string;
	model_id?: string;
	webhook_token: string;
	data?: Record<string, unknown>;
	meta?: Record<string, unknown>;
	access_control?: Record<string, unknown>;
	is_active: boolean;
	last_email_at?: number;
	email_count: number;
	created_at: number;
	updated_at: number;
	channel_name?: string;
};

export type EmailMessage = {
	id: string;
	mailbox_id: string;
	channel_id: string;
	message_id?: string;
	email_id?: string;
	subject?: string;
	sender?: string;
	sender_name?: string;
	recipients?: string[];
	cc?: string[];
	body_preview?: string;
	has_attachments: boolean;
	attachments?: Array<{ name: string; size?: number; type?: string }>;
	received_at?: number;
	importance?: 'low' | 'normal' | 'high';
	processed: boolean;
	agent_response?: string;
	data?: Record<string, unknown>;
	meta?: Record<string, unknown>;
	created_at: number;
	updated_at: number;
};

export type EmailMailboxForm = {
	name: string;
	description?: string;
	mailbox_address: string;
	mailbox_type: 'personal' | 'shared';
	channel_id: string;
	model_id?: string;
	data?: Record<string, unknown>;
	meta?: Record<string, unknown>;
	access_control?: Record<string, unknown>;
};

export type EmailMailboxUpdateForm = {
	name?: string;
	description?: string;
	model_id?: string;
	mailbox_type?: 'personal' | 'shared';
	channel_id?: string;
	is_active?: boolean;
	data?: Record<string, unknown>;
	meta?: Record<string, unknown>;
	access_control?: Record<string, unknown>;
};

export type WebhookInfo = {
	webhook_url: string;
	webhook_token: string;
	instructions: {
		title: string;
		steps: string[];
		body_template: Record<string, string>;
		body_template_text?: string;
	};
};

export const getMailboxes = async (token: string = ''): Promise<EmailMailbox[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/emails/`, {
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
			error = err.detail || err.message || 'Failed to fetch mailboxes';
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res ?? [];
};

export const createMailbox = async (
	token: string = '',
	mailbox: EmailMailboxForm
): Promise<EmailMailbox | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/emails/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(mailbox)
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

export const getMailboxById = async (
	token: string = '',
	id: string
): Promise<EmailMailbox | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/emails/${id}`, {
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

export const updateMailbox = async (
	token: string = '',
	id: string,
	mailbox: EmailMailboxUpdateForm
): Promise<EmailMailbox | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/emails/${id}/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(mailbox)
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

export const regenerateWebhookToken = async (
	token: string = '',
	id: string
): Promise<{ webhook_token: string } | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/emails/${id}/regenerate-token`, {
		method: 'POST',
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

export const deleteMailbox = async (token: string = '', id: string): Promise<boolean> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/emails/${id}/delete`, {
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

	return res;
};

export const getEmailsByMailbox = async (
	token: string = '',
	id: string,
	skip: number = 0,
	limit: number = 50
): Promise<EmailMessage[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/emails/${id}/emails?skip=${skip}&limit=${limit}`, {
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

export const getWebhookInfo = async (
	token: string = '',
	id: string
): Promise<WebhookInfo | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/emails/${id}/webhook-info`, {
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
