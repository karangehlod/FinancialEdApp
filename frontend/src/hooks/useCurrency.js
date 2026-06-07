import { useProfileStore } from '../store/index'
import { formatCurrency } from '../utils/helpers'

/**
 * Custom hook to use global currency context
 * Returns the current currency and a formatCurrency function that uses it
 */
export const useCurrency = () => {
  const { currency } = useProfileStore()

  const formatCurrencyWithGlobal = (value) => {
    return formatCurrency(value, currency)
  }

  return {
    currency,
    formatCurrency: formatCurrencyWithGlobal,
  }
}
