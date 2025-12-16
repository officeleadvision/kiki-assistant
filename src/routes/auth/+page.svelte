<script lang="ts">
	import DOMPurify from 'dompurify';
	import { marked } from 'marked';

	import { toast } from 'svelte-sonner';

	import { onMount, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import { ldapUserSignIn, getSessionUser, userSignIn, userSignUp } from '$lib/apis/auths';

	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';

	import { generateInitialsImage, canvasPixelTest } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import OnBoarding from '$lib/components/OnBoarding.svelte';
	import SensitiveInput from '$lib/components/common/SensitiveInput.svelte';
	import { redirect } from '@sveltejs/kit';

	const i18n = getContext('i18n');

	let loaded = false;

	let mode = $config?.features.enable_ldap ? 'ldap' : 'signin';

	let form = null;

	let name = '';
	let email = '';
	let password = '';
	let confirmPassword = '';

	let ldapUsername = '';

	const setSessionUser = async (sessionUser, redirectPath: string | null = null) => {
		if (sessionUser) {
			console.log(sessionUser);
			toast.success($i18n.t(`You're now logged in.`));
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}
			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());

			if (!redirectPath) {
				redirectPath = $page.url.searchParams.get('redirect') || '/';
			}

			goto(redirectPath);
			localStorage.removeItem('redirectPath');
		}
	};

	const signInHandler = async () => {
		const sessionUser = await userSignIn(email, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const signUpHandler = async () => {
		if ($config?.features?.enable_signup_password_confirmation) {
			if (password !== confirmPassword) {
				toast.error($i18n.t('Passwords do not match.'));
				return;
			}
		}

		const sessionUser = await userSignUp(name, email, password, generateInitialsImage(name)).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		await setSessionUser(sessionUser);
	};

	const ldapSignInHandler = async () => {
		const sessionUser = await ldapUserSignIn(ldapUsername, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		await setSessionUser(sessionUser);
	};

	const submitHandler = async () => {
		if (mode === 'ldap') {
			await ldapSignInHandler();
		} else if (mode === 'signin') {
			await signInHandler();
		} else {
			await signUpHandler();
		}
	};

	const oauthCallbackHandler = async () => {
		// Get the value of the 'token' cookie
		function getCookie(name) {
			const match = document.cookie.match(
				new RegExp('(?:^|; )' + name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + '=([^;]*)')
			);
			return match ? decodeURIComponent(match[1]) : null;
		}

		const token = getCookie('token');
		if (!token) {
			return;
		}

		const sessionUser = await getSessionUser(token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (!sessionUser) {
			return;
		}

		localStorage.token = token;
		await setSessionUser(sessionUser, localStorage.getItem('redirectPath') || null);
	};

	let onboarding = false;

	async function setLogoImage() {
		await tick();
		const logo = document.getElementById('logo');

		if (logo) {
			// Always use regular favicon for white theme
			logo.src = `${WEBUI_BASE_URL}/static/logo.svg`;
		}
	}

	onMount(async () => {
		const redirectPath = $page.url.searchParams.get('redirect');
		if ($user !== undefined) {
			goto(redirectPath || '/');
		} else {
			if (redirectPath) {
				localStorage.setItem('redirectPath', redirectPath);
			}
		}

		const error = $page.url.searchParams.get('error');
		if (error) {
			toast.error(error);
		}

		await oauthCallbackHandler();
		form = $page.url.searchParams.get('form');

		loaded = true;
		setLogoImage();

		if (($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false) {
			await signInHandler();
		} else {
			onboarding = $config?.onboarding ?? false;
		}
	});
</script>

<svelte:head>
	<title>
		{`${$WEBUI_NAME}`}
	</title>
</svelte:head>

<OnBoarding
	bind:show={onboarding}
	getStartedHandler={() => {
		onboarding = false;
		mode = $config?.features.enable_ldap ? 'ldap' : 'signup';
	}}
/>

<div class="w-full h-screen max-h-[100dvh] text-primary relative overflow-hidden" id="auth-page">
	<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region z-50" />

	{#if loaded}
		<div class="flex h-full w-full">
			<!-- Left Side - Hero Image -->
			<div
				class="hidden lg:flex lg:w-1/2 xl:w-3/5 relative overflow-hidden bg-slate-50 dark:bg-gray-900"
			>
				<div
					class="absolute inset-0 bg-gradient-to-br from-slate-900/10 to-slate-900/20 z-10"
				></div>
				<img
					src="{WEBUI_BASE_URL}/static/kiki-login.png"
					alt="Welcome"
					class="w-full h-full object-cover object-left"
				/>
			</div>

			<!-- Right Side - Login Form -->
			<div class="w-full lg:w-1/2 xl:w-2/5 flex flex-col bg-white dark:bg-gray-900 relative">
				<!-- Mobile Logo -->
				<div class="lg:hidden absolute inset-0 flex items-start justify-center pt-10 z-20">
					<img
						id="logo"
						crossorigin="anonymous"
						src="{WEBUI_BASE_URL}/static/logo.svg"
						class="w-32 h-32 rounded-2xl shadow-lg"
						alt=""
					/>
				</div>

				<!-- Desktop Logo -->
				{#if !$config?.metadata?.auth_logo_position}
					<div class="hidden lg:block absolute top-8 left-8 z-20">
						<div class="flex items-center space-x-3">
							<img
								id="logo"
								crossorigin="anonymous"
								src="{WEBUI_BASE_URL}/static/logo.svg"
								class="w-20 h-20 rounded-xl shadow-lg"
								alt=""
							/>
						</div>
					</div>
				{/if}

				<!-- Form Container -->
				<div class="flex-1 flex flex-col justify-center px-8 sm:px-12 lg:px-16 xl:px-20 py-12">
					{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
						<div class="w-full max-w-md mx-auto">
							<div
								class="flex items-center justify-center gap-3 text-xl sm:text-2xl text-center font-medium text-gray-900 dark:text-white"
							>
								<div>
									{$i18n.t('Signing in to {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}
								</div>
								<div>
									<Spinner className="size-5" />
								</div>
							</div>
						</div>
					{:else}
						<div
							class="w-full max-w-md mx-auto bg-white/90 dark:bg-gray-800/70 backdrop-blur border border-gray-100 dark:border-gray-700 rounded-2xl shadow-xl shadow-slate-200/50 dark:shadow-black/30 px-6 sm:px-8 py-8"
						>
							{#if $config?.metadata?.auth_logo_position === 'center'}
								<div class="flex justify-center mb-8">
									<img
										id="logo"
										crossorigin="anonymous"
										src="{WEBUI_BASE_URL}/static/logo.svg"
										class="size-20 rounded-2xl shadow-xl animate-pulse"
										alt=""
									/>
								</div>
							{/if}

							<!-- Header -->
							<div class="mb-8">
								<h1 class="text-3xl font-bold text-gray-900 dark:text-white tracking-tight">
									{#if $config?.onboarding ?? false}
										{$i18n.t(`Get started`)}
									{:else if mode === 'ldap'}
										{$i18n.t(`Welcome back`)}
									{:else if mode === 'signin'}
										{$i18n.t('Signing in to {{WEBUI_NAME}}', { WEBUI_NAME: $WEBUI_NAME })}
									{:else}
										{$i18n.t(`Create account`)}
									{/if}
								</h1>
								<p class="mt-2 text-gray-500 dark:text-gray-400">
									{#if $config?.onboarding ?? false}
										{$i18n.t(`Set up your {{WEBUI_NAME}} account`, { WEBUI_NAME: $WEBUI_NAME })}
									{:else if mode === 'ldap'}
										{$i18n.t(`Sign in with LDAP to continue`)}
									{:else if mode === 'signin'}
										{$i18n.t(`Sign in to continue to {{WEBUI_NAME}}`, { WEBUI_NAME: $WEBUI_NAME })}
									{:else}
										{$i18n.t(`Join {{WEBUI_NAME}} today`, { WEBUI_NAME: $WEBUI_NAME })}
									{/if}
								</p>

								{#if $config?.onboarding ?? false}
									<div
										class="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-100 dark:border-blue-800"
									>
										<p class="text-xs text-blue-700 dark:text-blue-300 flex items-start gap-2">
											<svg
												class="w-4 h-4 mt-0.5 flex-shrink-0"
												fill="currentColor"
												viewBox="0 0 20 20"
											>
												<path
													fill-rule="evenodd"
													d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
													clip-rule="evenodd"
												/>
											</svg>
											<span
												>{$WEBUI_NAME}
												{$i18n.t(
													'does not make any external connections, and your data stays securely on your locally hosted server.'
												)}</span
											>
										</p>
									</div>
								{/if}
							</div>

							<!-- Form -->
							<form
								class="space-y-5"
								on:submit={(e) => {
									e.preventDefault();
									submitHandler();
								}}
							>
								{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
									<div class="space-y-4">
										{#if mode === 'signup'}
											<div>
												<label
													for="name"
													class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
												>
													{$i18n.t('Name')}
												</label>
												<input
													bind:value={name}
													type="text"
													id="name"
													class="w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 outline-none"
													autocomplete="name"
													placeholder={$i18n.t('Enter Your Full Name')}
													required
												/>
											</div>
										{/if}

										{#if mode === 'ldap'}
											<div>
												<label
													for="username"
													class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
												>
													{$i18n.t('Username')}
												</label>
												<input
													bind:value={ldapUsername}
													type="text"
													class="w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 outline-none"
													autocomplete="username"
													name="username"
													id="username"
													placeholder={$i18n.t('Enter Your Username')}
													required
												/>
											</div>
										{:else}
											<div>
												<label
													for="email"
													class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
												>
													{$i18n.t('Email')}
												</label>
												<input
													bind:value={email}
													type="email"
													id="email"
													class="w-full text-sm py-0.5 bg-transparent password outline-hidden placeholder:text-gray-500 dark:placeholder:text-gray-600"
													autocomplete="email"
													name="email"
													placeholder={$i18n.t('Enter Your Email')}
													required
												/>
											</div>
										{/if}

										<div>
											<label
												for="password"
												class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
											>
												{$i18n.t('Password')}
											</label>
											<div class="relative">
												<SensitiveInput
													bind:value={password}
													type="password"
													id="password"
													class="w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 outline-none"
													placeholder={$i18n.t('Enter Your Password')}
													autocomplete={mode === 'signup' ? 'new-password' : 'current-password'}
													name="password"
													required
												/>
											</div>
										</div>

										{#if mode === 'signup' && $config?.features?.enable_signup_password_confirmation}
											<div>
												<label
													for="confirm-password"
													class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2"
												>
													{$i18n.t('Confirm Password')}
												</label>
												<SensitiveInput
													bind:value={confirmPassword}
													type="password"
													id="confirm-password"
													class="w-full text-sm py-0.5 bg-transparent password  outline-hidden placeholder:text-gray-500 dark:placeholder:text-gray-600"
													placeholder={$i18n.t('Confirm Your Password')}
													autocomplete="new-password"
													name="confirm-password"
													required
												/>
											</div>
										{/if}
									</div>
								{/if}

								<!-- Submit Button -->
								<div class="pt-2">
									{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
										{#if mode === 'ldap'}
											<button
												class="w-full py-3.5 px-4 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-semibold rounded-xl shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 transform hover:-translate-y-0.5 transition-all duration-200"
												type="submit"
											>
												{$i18n.t('Authenticate')}
											</button>
										{:else}
											<button
												class="w-full py-3.5 px-4 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white font-semibold rounded-xl shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 transform hover:-translate-y-0.5 transition-all duration-200"
												type="submit"
											>
												{mode === 'signin'
													? $i18n.t('Sign in')
													: ($config?.onboarding ?? false)
														? $i18n.t('Create Admin Account')
														: $i18n.t('Create Account')}
											</button>

											{#if $config?.features.enable_signup && !($config?.onboarding ?? false)}
												<div class="mt-6 text-center">
													<span class="text-gray-500 dark:text-gray-400">
														{mode === 'signin'
															? $i18n.t("Don't have an account?")
															: $i18n.t('Already have an account?')}
													</span>
													<button
														class="ml-1 font-semibold text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
														type="button"
														on:click={() => {
															if (mode === 'signin') {
																mode = 'signup';
															} else {
																mode = 'signin';
															}
														}}
													>
														{mode === 'signin' ? $i18n.t('Sign up') : $i18n.t('Sign in')}
													</button>
												</div>
											{/if}
										{/if}
									{/if}
								</div>
							</form>

							<!-- OAuth Providers -->
							{#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
								<div class="relative my-8">
									<div class="absolute inset-0 flex items-center">
										<div class="w-full border-t border-gray-200 dark:border-gray-700"></div>
									</div>
									{#if $config?.features.enable_login_form || $config?.features.enable_ldap || form}
										<div class="relative flex justify-center text-sm">
											<span class="px-4 bg-white dark:bg-gray-900 text-gray-500 dark:text-gray-400"
												>{$i18n.t('or')}</span
											>
										</div>
									{/if}
								</div>

								<div class="space-y-3">
									{#if $config?.oauth?.providers?.google}
										<button
											class="flex items-center justify-center w-full py-3 px-4 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 font-medium transition-all duration-200 hover:shadow-md"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 48 48"
												class="w-5 h-5 mr-3"
											>
												<path
													fill="#EA4335"
													d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
												/>
												<path
													fill="#4285F4"
													d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
												/>
												<path
													fill="#FBBC05"
													d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
												/>
												<path
													fill="#34A853"
													d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
												/>
											</svg>
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'Google' })}</span>
										</button>
									{/if}

									{#if $config?.oauth?.providers?.microsoft}
										<button
											class="flex items-center justify-center w-full py-3 px-4 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 font-medium transition-all duration-200 hover:shadow-md"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 21 21"
												class="w-5 h-5 mr-3"
											>
												<rect x="1" y="1" width="9" height="9" fill="#f25022" />
												<rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
												<rect x="11" y="1" width="9" height="9" fill="#7fba00" />
												<rect x="11" y="11" width="9" height="9" fill="#ffb900" />
											</svg>
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'Microsoft' })}</span
											>
										</button>
									{/if}

									{#if $config?.oauth?.providers?.github}
										<button
											class="flex items-center justify-center w-full py-3 px-4 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 font-medium transition-all duration-200 hover:shadow-md"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/github/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 24 24"
												class="w-5 h-5 mr-3"
											>
												<path
													fill="currentColor"
													d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.92 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57C20.565 21.795 24 17.31 24 12c0-6.63-5.37-12-12-12z"
												/>
											</svg>
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'GitHub' })}</span>
										</button>
									{/if}

									{#if $config?.oauth?.providers?.oidc}
										<button
											class="flex items-center justify-center w-full py-3 px-4 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 font-medium transition-all duration-200 hover:shadow-md"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="1.5"
												stroke="currentColor"
												class="w-5 h-5 mr-3"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z"
												/>
											</svg>
											<span
												>{$i18n.t('Continue with {{provider}}', {
													provider: $config?.oauth?.providers?.oidc ?? 'SSO'
												})}</span
											>
										</button>
									{/if}

									{#if $config?.oauth?.providers?.feishu}
										<button
											class="flex items-center justify-center w-full py-3 px-4 border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 font-medium transition-all duration-200 hover:shadow-md"
											on:click={() => {
												window.location.href = `${WEBUI_BASE_URL}/oauth/feishu/login`;
											}}
										>
											<span>{$i18n.t('Continue with {{provider}}', { provider: 'Feishu' })}</span>
										</button>
									{/if}
								</div>
							{/if}

							<!-- LDAP Toggle -->
							{#if $config?.features.enable_ldap && $config?.features.enable_login_form}
								<div class="mt-6 text-center">
									<button
										class="text-sm text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
										type="button"
										on:click={() => {
											if (mode === 'ldap')
												mode = ($config?.onboarding ?? false) ? 'signup' : 'signin';
											else mode = 'ldap';
										}}
									>
										{mode === 'ldap'
											? $i18n.t('Continue with Email')
											: $i18n.t('Continue with LDAP')}
									</button>
								</div>
							{/if}

							<!-- Login Footer -->
							{#if $config?.metadata?.login_footer}
								<div class="mt-8 text-center">
									<div class="text-xs text-gray-500 dark:text-gray-400 marked">
										{@html DOMPurify.sanitize(marked($config?.metadata?.login_footer))}
									</div>
								</div>
							{/if}
						</div>
					{/if}
				</div>

				<!-- Powered by LeadVision -->
				<div class="px-8 pb-8 flex justify-center">
					<a
						href="https://LeadVision.bg"
						target="_blank"
						rel="noreferrer"
						class="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
					>
						<span>Powered by</span>
						<!-- Light theme logo -->
						<img
							src="{WEBUI_BASE_URL}/static/leadvision-logo.svg"
							alt="LeadVision"
							class="h-10 dark:hidden"
						/>
						<!-- Dark theme logo -->
						<img
							src="{WEBUI_BASE_URL}/static/leadvision-white-logo.svg"
							alt="LeadVision"
							class="h-10 hidden dark:block"
						/>
					</a>
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	/* Keep markdown links readable in both themes without Tailwind @apply */
	:global(.marked a) {
		color: #2563eb; /* blue-600 */
		text-decoration: underline;
	}
	:global(.dark .marked a) {
		color: #60a5fa; /* blue-400 */
	}
</style>
