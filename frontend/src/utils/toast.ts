/**
 * Toast notification utilities — thin wrapper around react-hot-toast.
 */

import toast from 'react-hot-toast'

const DEFAULT_OPTS = { position: 'top-right' as const, duration: 3000 }

export function showSuccessToast(message: string): void {
  toast.success(message, DEFAULT_OPTS)
}

export function showErrorToast(message: string): void {
  toast.error(message, DEFAULT_OPTS)
}

export function showLoadingToast(message: string): string {
  return toast.loading(message, { position: 'top-right' })
}

export function updateToast(
  toastId: string,
  message: string,
  type: 'success' | 'error' = 'success',
): void {
  toast.dismiss(toastId)
  if (type === 'success') {
    toast.success(message, DEFAULT_OPTS)
  } else {
    toast.error(message, DEFAULT_OPTS)
  }
}
