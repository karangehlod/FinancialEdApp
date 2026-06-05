/**
 * Currency formatting hook — uses global currency preference.
 */

import { useCallback } from 'react'
import { useProfileStore } from '@/store/index'
import { formatCurrency } from '@/utils/helpers'

interface UseCurrencyReturn {
  readonly currency: string
  readonly formatCurrency: (value: number) => string
}

export function useCurrency(): UseCurrencyReturn {
  const currency = useProfileStore((s) => s.currency)

  const format = useCallback(
    (value: number): string => formatCurrency(value, currency),
    [currency],
  )

  return { currency, formatCurrency: format }
}
