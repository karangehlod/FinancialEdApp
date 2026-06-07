/**
 * OAuthCallbackPage — handles the redirect from Google / Apple after consent (P2-6)
 *
 * Mount this at /auth/callback in your router.
 *
 * Google: redirects back with ?code=...&state=...
 * Apple:  POSTs code, id_token, state, user to the redirect URI.
 *         For a SPA running in a browser, Apple's form_post means the page
 *         receives URL-encoded body parameters. We read them from the hash or
 *         a server-side relay that turns the POST into a GET with query params.
 *
 * If you use Vite's dev server proxy or a backend relay, the easiest approach
 * is to have the backend receive Apple's POST and redirect the user to
 * /auth/callback?provider=apple&code=...&state=...&id_token=...
 *
 * This page:
 *   1. Reads provider + code + state (+ id_token for Apple) from URL params.
 *   2. Calls handleOAuthCallback to exchange the code for app tokens.
 *   3. On success: stores tokens via onSuccess → navigates to dashboard.
 *   4. On error:   displays error → link back to login.
 */

import React, { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useOAuth } from '../hooks/useOAuth';
import tokenManager from '../utils/tokenManager';
import { useAuthStore } from '../store/authStore';

const REDIRECT_URI = `${window.location.origin}/auth/callback`;

export default function OAuthCallbackPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState('loading'); // 'loading' | 'success' | 'error'
  const [errorMsg, setErrorMsg] = useState('');
  const processed = useRef(false);  // prevent double-execution in React StrictMode

  // Retrieve tokens and store them using the shared tokenManager
  const handleSuccess = (tokens) => {
    tokenManager.storeToken(tokens.access_token, tokens.refresh_token);
    useAuthStore.getState().fetchCurrentUser();
    setStatus('success');
    setTimeout(() => navigate('/dashboard', { replace: true }), 1200);
  };

  const handleError = (err) => {
    setErrorMsg(err.message || 'Authentication failed. Please try again.');
    setStatus('error');
  };

  const { handleOAuthCallback } = useOAuth(handleSuccess, handleError);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    const provider = searchParams.get('provider') || 'google';
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const idToken = searchParams.get('id_token');   // Apple only
    const user = searchParams.get('user');           // Apple only (first sign-in)
    const oauthError = searchParams.get('error');

    if (oauthError) {
      setErrorMsg(`Provider returned error: ${oauthError}`);
      setStatus('error');
      return;
    }

    if (!code || !state) {
      setErrorMsg('Missing OAuth parameters. Please try signing in again.');
      setStatus('error');
      return;
    }

    const params = { code, state };
    if (idToken) params.id_token = idToken;
    if (user) params.user = user;

    handleOAuthCallback(provider, params, REDIRECT_URI).catch(() => {
      // error state already set via handleError callback
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  if (status === 'loading') {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-gray-50 dark:bg-gray-900">
        <div style={{ width: 'var(--spinner-md)', height: 'var(--spinner-md)' }} className="animate-spin rounded-full border-4 border-indigo-500 border-t-transparent" />
        <p className="text-sm text-gray-500 dark:text-gray-400">Completing sign-in…</p>
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-gray-50 dark:bg-gray-900">
        <div className="flex items-center justify-center rounded-full" style={{ width: 'var(--spinner-md)', height: 'var(--spinner-md)', backgroundColor: 'var(--success-bg, #ecfdf5)' }}>
          <svg style={{ width: 'var(--icon-md)', height: 'var(--icon-md)' }} className="text-green-600 dark:text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <p className="text-sm font-medium text-gray-700 dark:text-gray-200">
          Signed in! Redirecting…
        </p>
      </div>
    );
  }

  // Error
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-gray-50 p-6 dark:bg-gray-900">
      <div className="w-full" style={{ maxWidth: 'var(--content-max-width)' }}>
        <div className="rounded-xl bg-white p-8 shadow dark:bg-gray-800">
          <div className="mb-4 flex items-center gap-3">
            <div className="flex items-center justify-center rounded-full" style={{ width: 'var(--icon-md)', height: 'var(--icon-md)', backgroundColor: 'var(--danger-bg, #fff1f2)' }}>
              <svg style={{ width: 'calc(var(--icon-md) * 0.75)', height: 'calc(var(--icon-md) * 0.75)' }} className="text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h1 className="text-lg font-semibold text-gray-800 dark:text-gray-100">Sign-in failed</h1>
          </div>
          <p className="mb-6 text-sm text-gray-600 dark:text-gray-400">{errorMsg}</p>
          <button
            onClick={() => navigate('/login', { replace: true })}
            className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
          >
            Back to Login
          </button>
        </div>
      </div>
    </div>
  );
}
