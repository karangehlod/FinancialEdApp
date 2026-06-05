/**
 * OAuth hook — social login flow for Google / Apple.
 */

import { useState, useCallback } from 'react'
import { env } from '@/config/env'
import type { OAuthProvider, LoginResponse } from '@/types'

const OAUTH_STATE_KEY = 'oauth_state'
const OAUTH_PROVIDER_KEY = 'oauth_provider'

type OAuthSuccessCallback = (tokens: LoginResponse) => void
type OAuthErrorCallback = (error: Error) => void

interface OAuthCallbackParams {
  readonly code: string
  readonly state: string
  readonly id_token?: string
  readonly user?: string
}

interface UseOAuthReturn {
  readonly loginWithGoogle: (redirectUri: string) => Promise<void>
  readonly loginWithApple: (redirectUri: string) => Promise<void>
  readonly handleOAuthCallback: (
    provider: OAuthProvider,
    params: OAuthCallbackParams,
    redirectUri: string,
  ) => Promise<LoginResponse>
  readonly isLoading: boolean
  readonly error: string | null
}

async function initiateOAuthFlow(provider: OAuthProvider, redirectUri: string): Promise<void> {
  const url = new URL(`${env.apiUrl}/api/v1/auth/oauth/${provider}/authorize`)
  url.searchParams.set('redirect_uri', redirectUri)

  const resp = await fetch(url.toString(), { credentials: 'include' })
  if (!resp.ok) {
    const body = (await resp.json().catch(() => ({}))) as { detail?: string }
    throw new Error(body.detail ?? `Failed to start ${provider} login`)
  }
  const data = (await resp.json()) as { auth_url: string; state: string }

  sessionStorage.setItem(OAUTH_STATE_KEY, data.state)
  sessionStorage.setItem(OAUTH_PROVIDER_KEY, provider)
  window.location.href = data.auth_url
}

async function exchangeOAuthCode(
  provider: OAuthProvider,
  payload: Record<string, string>,
): Promise<LoginResponse> {
  const resp = await fetch(`${env.apiUrl}/api/v1/auth/oauth/${provider}/callback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  })
  if (!resp.ok) {
    const body = (await resp.json().catch(() => ({}))) as { detail?: string }
    throw new Error(body.detail ?? `${provider} authentication failed`)
  }
  return resp.json() as Promise<LoginResponse>
}

export function useOAuth(
  onSuccess?: OAuthSuccessCallback,
  onError?: OAuthErrorCallback,
): UseOAuthReturn {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loginWithGoogle = useCallback(
    async (redirectUri: string): Promise<void> => {
      setIsLoading(true)
      setError(null)
      try {
        await initiateOAuthFlow('google', redirectUri)
      } catch (err) {
        const e = err instanceof Error ? err : new Error(String(err))
        setError(e.message)
        setIsLoading(false)
        onError?.(e)
      }
    },
    [onError],
  )

  const loginWithApple = useCallback(
    async (redirectUri: string): Promise<void> => {
      setIsLoading(true)
      setError(null)
      try {
        await initiateOAuthFlow('apple', redirectUri)
      } catch (err) {
        const e = err instanceof Error ? err : new Error(String(err))
        setError(e.message)
        setIsLoading(false)
        onError?.(e)
      }
    },
    [onError],
  )

  const handleOAuthCallback = useCallback(
    async (
      provider: OAuthProvider,
      params: OAuthCallbackParams,
      redirectUri: string,
    ): Promise<LoginResponse> => {
      setIsLoading(true)
      setError(null)

      try {
        const savedState = sessionStorage.getItem(OAUTH_STATE_KEY)
        const savedProvider = sessionStorage.getItem(OAUTH_PROVIDER_KEY)
        sessionStorage.removeItem(OAUTH_STATE_KEY)
        sessionStorage.removeItem(OAUTH_PROVIDER_KEY)

        if (savedState !== params.state || savedProvider !== provider) {
          throw new Error('OAuth state mismatch — possible CSRF attack. Please try again.')
        }

        const payload: Record<string, string> = { code: params.code, state: params.state }
        if (provider === 'google') {
          payload['redirect_uri'] = redirectUri
        }
        if (params.id_token) payload['id_token'] = params.id_token
        if (params.user) payload['user'] = params.user

        const tokens = await exchangeOAuthCode(provider, payload)
        onSuccess?.(tokens)
        return tokens
      } catch (err) {
        const e = err instanceof Error ? err : new Error(String(err))
        setError(e.message)
        onError?.(e)
        throw e
      } finally {
        setIsLoading(false)
      }
    },
    [onSuccess, onError],
  )

  return { loginWithGoogle, loginWithApple, handleOAuthCallback, isLoading, error }
}

export default useOAuth
