/**
 * OAuthButtons — Social login button group (P2-6)
 *
 * Renders "Continue with Google" and "Continue with Apple" buttons.
 * Designed to drop into any Login / Register page.
 *
 * Props:
 *   redirectUri   string  The callback URL sent to the provider (must match
 *                         the registered redirect URI in provider settings).
 *   onSuccess     fn      Called with token response after successful OAuth login.
 *   onError       fn      Called with Error when OAuth fails.
 *   className     string  Optional extra Tailwind classes for the wrapper div.
 *
 * Usage:
 *   <OAuthButtons
 *     redirectUri={`${window.location.origin}/auth/callback`}
 *     onSuccess={(tokens) => { store tokens; navigate('/dashboard') }}
 *     onError={(err) => toast.error(err.message)}
 *   />
 */

import React from 'react';
import useOAuth from '../hooks/useOAuth';

// ---------------------------------------------------------------------------
// SVG icons (inlined to avoid extra assets)
// ---------------------------------------------------------------------------

const GoogleIcon = () => (
  <svg viewBox="0 0 24 24" className="" style={{ width: 'var(--icon-sm)', height: 'var(--icon-sm)' }} aria-hidden="true">
    <path
      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      fill="#4285F4"
    />
    <path
      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      fill="#34A853"
    />
    <path
      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
      fill="#FBBC05"
    />
    <path
      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      fill="#EA4335"
    />
  </svg>
);

const AppleIcon = () => (
  <svg viewBox="0 0 24 24" className="" style={{ width: 'var(--icon-sm)', height: 'var(--icon-sm)' }} aria-hidden="true" fill="currentColor">
    <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z" />
  </svg>
);

// ---------------------------------------------------------------------------
// OAuthButton (single provider button)
// ---------------------------------------------------------------------------

function OAuthButton({ provider, label, icon: Icon, onClick, disabled, variant = 'outline' }) {
  const baseClasses =
    'flex w-full items-center justify-center gap-3 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60';

  const variantClasses =
    variant === 'dark'
      ? 'border-gray-800 bg-gray-900 text-white hover:bg-gray-800 focus:ring-gray-700'
      : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700';

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      className={`${baseClasses} ${variantClasses}`}
    >
      <Icon />
      <span>{label}</span>
    </button>
  );
}

// ---------------------------------------------------------------------------
// OAuthButtons (exported)
// ---------------------------------------------------------------------------

export default function OAuthButtons({ redirectUri, onSuccess, onError, className = '' }) {
  const { loginWithGoogle, loginWithApple, isLoading, error } = useOAuth(onSuccess, onError);

  const cbUri = redirectUri || `${window.location.origin}/auth/callback`;

  return (
    <div className={`flex flex-col gap-3 ${className}`}>
      {/* Divider */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-200 dark:border-gray-700" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-white px-2 text-gray-500 dark:bg-gray-900 dark:text-gray-400">
            or continue with
          </span>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div
          role="alert"
          className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-400"
        >
          {error}
        </div>
      )}

      {/* Google */}
      <OAuthButton
        provider="google"
        label="Continue with Google"
        icon={GoogleIcon}
        disabled={isLoading}
        onClick={() => loginWithGoogle(cbUri)}
        variant="outline"
      />

      {/* Apple */}
      <OAuthButton
        provider="apple"
        label="Continue with Apple"
        icon={AppleIcon}
        disabled={isLoading}
        onClick={() => loginWithApple(cbUri)}
        variant="dark"
      />
    </div>
  );
}
