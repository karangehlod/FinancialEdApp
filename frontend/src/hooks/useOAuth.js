/**
 * useOAuth — React hook for Google / Apple OAuth social login (P2-6)
 *
 * Usage:
 *   const { loginWithGoogle, loginWithApple, isLoading, error } = useOAuth();
 *
 * Flow:
 *   1. Call loginWithGoogle(redirectUri) or loginWithApple(redirectUri)
 *   2. Hook fetches { auth_url, state } from /api/v1/auth/oauth/{provider}/authorize
 *   3. Stores state in sessionStorage (survives the redirect)
 *   4. Redirects the browser to auth_url (provider's consent screen)
 *   5. After consent, provider redirects to `redirectUri` with ?code=...&state=...
 *   6. The callback page calls handleOAuthCallback(provider, params)
 *   7. Hook POSTs to /api/v1/auth/oauth/{provider}/callback → receives app JWT tokens
 *   8. Tokens stored in authStore (same as password login)
 *
 * Apple note:
 *   Apple uses form_post so the frontend callback page receives a POST body,
 *   not query params. Ensure your callback route handles both.
 */

import { useState, useCallback } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';
const OAUTH_STATE_KEY = 'oauth_state';
const OAUTH_PROVIDER_KEY = 'oauth_provider';

/**
 * Fetch the authorization URL from the backend and redirect the user.
 */
async function initiateOAuthFlow(provider, redirectUri) {
  const url = new URL(`${API_BASE}/auth/oauth/${provider}/authorize`);
  url.searchParams.set('redirect_uri', redirectUri);

  const resp = await fetch(url.toString(), { credentials: 'include' });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.detail || `Failed to start ${provider} login`);
  }
  const { auth_url, state } = await resp.json();

  // Store state for CSRF validation when the user returns
  sessionStorage.setItem(OAUTH_STATE_KEY, state);
  sessionStorage.setItem(OAUTH_PROVIDER_KEY, provider);

  // Redirect to the provider's consent page
  window.location.href = auth_url;
}

/**
 * Exchange the authorization code (and optional id_token / user) for app tokens.
 */
async function exchangeOAuthCode(provider, payload) {
  const resp = await fetch(`${API_BASE}/auth/oauth/${provider}/callback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.detail || `${provider} authentication failed`);
  }
  return resp.json(); // { access_token, refresh_token, token_type, user }
}

export function useOAuth(onSuccess, onError) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Start Google OAuth flow.
   * @param {string} redirectUri  The frontend URL Google should redirect back to.
   */
  const loginWithGoogle = useCallback(async (redirectUri) => {
    setIsLoading(true);
    setError(null);
    try {
      await initiateOAuthFlow('google', redirectUri);
      // After this line the browser navigates away; setIsLoading(false) won't run.
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
      onError?.(err);
    }
  }, [onError]);

  /**
   * Start Apple Sign-in flow.
   * @param {string} redirectUri  Must be an HTTPS URL registered with Apple.
   */
  const loginWithApple = useCallback(async (redirectUri) => {
    setIsLoading(true);
    setError(null);
    try {
      await initiateOAuthFlow('apple', redirectUri);
    } catch (err) {
      setError(err.message);
      setIsLoading(false);
      onError?.(err);
    }
  }, [onError]);

  /**
   * Handle the OAuth callback after the user returns from the provider.
   *
   * Call this in the component that renders at your redirectUri.
   *
   * @param {string} provider   "google" | "apple"
   * @param {object} params     For Google: { code, state }
   *                            For Apple:  { code, state, id_token?, user? }
   * @param {string} redirectUri The exact redirect URI used in the authorize call.
   */
  const handleOAuthCallback = useCallback(async (provider, params, redirectUri) => {
    setIsLoading(true);
    setError(null);

    try {
      // Validate state (CSRF guard)
      const savedState = sessionStorage.getItem(OAUTH_STATE_KEY);
      const savedProvider = sessionStorage.getItem(OAUTH_PROVIDER_KEY);
      sessionStorage.removeItem(OAUTH_STATE_KEY);
      sessionStorage.removeItem(OAUTH_PROVIDER_KEY);

      if (savedState !== params.state || savedProvider !== provider) {
        throw new Error('OAuth state mismatch — possible CSRF attack. Please try again.');
      }

      const payload = { ...params };
      if (provider === 'google') {
        payload.redirect_uri = redirectUri;
      }

      const tokens = await exchangeOAuthCode(provider, payload);
      onSuccess?.(tokens);
      return tokens;
    } catch (err) {
      setError(err.message);
      onError?.(err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [onSuccess, onError]);

  return {
    loginWithGoogle,
    loginWithApple,
    handleOAuthCallback,
    isLoading,
    error,
  };
}

export default useOAuth;
