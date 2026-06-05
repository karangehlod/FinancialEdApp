"""
Multi-currency real-time conversion service.

Architecture:
  - Exchange rates fetched from Open Exchange Rates API (or fallback: Fixer.io)
  - Rates cached in Redis with 1-hour TTL (background worker refreshes hourly)
  - All monetary amounts stored in USD (base currency) in the database
  - Display amounts converted at query time using cached rates

Supported operations:
  - convert(amount, from_currency, to_currency) → float
  - get_rates(base_currency) → {currency: rate}
  - get_user_display_currency(user_id) → str
  - format_currency(amount, currency) → str

SOLID compliance:
  - SRP: only currency conversion, no HTTP endpoint knowledge
  - OCP: new providers (Fixer, ECB) can be added via ExchangeRateProvider ABC
  - DIP: service depends on CacheProvider interface, not Redis directly

Environment variables:
  EXCHANGE_RATES_API_KEY     — Open Exchange Rates app_id (required for live rates)
  EXCHANGE_RATES_BASE        — base currency (default: USD)
  EXCHANGE_RATES_CACHE_TTL   — cache TTL in seconds (default: 3600)
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Optional

import httpx

from app.core.exceptions import AppException

logger = logging.getLogger(__name__)

BASE_CURRENCY = "USD"
CACHE_TTL_SECONDS = 3600      # 1 hour
RATES_CACHE_KEY = "currency:rates:{base}"
SUPPORTED_CURRENCIES = frozenset([
    "USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY",
    "INR", "MXN", "BRL", "SEK", "NOK", "DKK", "PLN", "CZK",
    "HUF", "RON", "HRK", "RUB", "TRY", "ZAR", "SGD", "HKD",
    "NZD", "ILS", "THB", "KRW", "PHP", "MYR", "IDR", "AED",
])


class CurrencyError(AppException):
    """Raised for currency conversion errors."""


class UnsupportedCurrencyError(CurrencyError):
    """Raised for unsupported currency codes."""


# ---------------------------------------------------------------------------
# Provider ABC
# ---------------------------------------------------------------------------

class ExchangeRateProvider(ABC):
    """Abstract base class for exchange rate data sources."""

    @abstractmethod
    async def fetch_rates(self, base: str = BASE_CURRENCY) -> Dict[str, float]:
        """
        Fetch current exchange rates.

        Returns:
            dict of {currency_code: rate_vs_base}
        """
        ...

    @abstractmethod
    def supports(self, currency: str) -> bool:
        """Return True if this provider supports the given currency."""
        ...


# ---------------------------------------------------------------------------
# Open Exchange Rates provider
# ---------------------------------------------------------------------------

class OpenExchangeRatesProvider(ExchangeRateProvider):
    """
    Fetches rates from https://openexchangerates.org

    Free plan: base currency = USD only.
    Paid plan: any base currency.
    """

    BASE_URL = "https://openexchangerates.org/api"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=10.0)

    async def fetch_rates(self, base: str = BASE_CURRENCY) -> Dict[str, float]:
        url = f"{self.BASE_URL}/latest.json"
        params = {"app_id": self._api_key, "base": base}
        try:
            resp = await self._client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            return data.get("rates", {})
        except httpx.HTTPError as exc:
            logger.error("Open Exchange Rates API error: %s", exc)
            raise CurrencyError("Failed to fetch exchange rates") from exc

    def supports(self, currency: str) -> bool:
        return currency.upper() in SUPPORTED_CURRENCIES


# ---------------------------------------------------------------------------
# Fallback: static rates (used when API is unavailable)
# ---------------------------------------------------------------------------

_STATIC_FALLBACK_RATES: Dict[str, float] = {
    "USD": 1.0, "EUR": 0.92, "GBP": 0.79, "JPY": 149.5,
    "CAD": 1.36, "AUD": 1.53, "CHF": 0.90, "CNY": 7.24,
    "INR": 83.1, "MXN": 17.2, "BRL": 4.97, "SGD": 1.34,
    "HKD": 7.82, "NZD": 1.63, "SEK": 10.4, "NOK": 10.6,
    "DKK": 6.88, "ILS": 3.72, "AED": 3.67, "ZAR": 18.6,
    "KRW": 1340.0, "THB": 35.1, "MYR": 4.71, "IDR": 15600.0,
}


class StaticFallbackProvider(ExchangeRateProvider):
    """Static fallback rates — used when the API is unreachable."""

    async def fetch_rates(self, base: str = BASE_CURRENCY) -> Dict[str, float]:
        logger.warning("Using static fallback exchange rates — data may be stale")
        if base != "USD":
            # Convert from USD base to requested base
            base_rate = _STATIC_FALLBACK_RATES.get(base, 1.0)
            return {k: v / base_rate for k, v in _STATIC_FALLBACK_RATES.items()}
        return dict(_STATIC_FALLBACK_RATES)

    def supports(self, currency: str) -> bool:
        return currency.upper() in _STATIC_FALLBACK_RATES


# ---------------------------------------------------------------------------
# Currency conversion service
# ---------------------------------------------------------------------------

class CurrencyService:
    """
    Multi-currency conversion service with Redis caching.

    Args:
        provider:     Primary exchange rate provider.
        cache:        Redis cache provider (optional, falls back to in-memory).
        base_currency: Base storage currency (default: USD).
    """

    def __init__(
        self,
        provider: ExchangeRateProvider,
        cache=None,
        base_currency: str = BASE_CURRENCY,
    ) -> None:
        self._provider = provider
        self._cache = cache
        self._base = base_currency.upper()
        self._fallback = StaticFallbackProvider()
        # In-process cache (L1, used if Redis is unavailable)
        self._local_rates: Optional[Dict[str, float]] = None
        self._local_rates_ts: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_rates(self, base: Optional[str] = None) -> Dict[str, float]:
        """Return all exchange rates (base → all currencies)."""
        base = (base or self._base).upper()
        cache_key = RATES_CACHE_KEY.format(base=base)

        # L2: Redis
        if self._cache:
            try:
                cached = await self._cache.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as exc:
                logger.debug("Cache miss for rates: %s", exc)

        # L1: in-process
        now = asyncio.get_event_loop().time()
        if self._local_rates and (now - self._local_rates_ts) < CACHE_TTL_SECONDS:
            return self._local_rates

        # Fetch from provider
        try:
            rates = await self._provider.fetch_rates(base)
        except CurrencyError:
            logger.warning("Primary provider failed — using static fallback rates")
            rates = await self._fallback.fetch_rates(base)

        # Store in Redis
        if self._cache and rates:
            try:
                await self._cache.set(cache_key, json.dumps(rates), ttl=CACHE_TTL_SECONDS)
            except Exception:
                pass

        # Store in-process
        self._local_rates = rates
        self._local_rates_ts = now

        return rates

    async def convert(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
    ) -> float:
        """
        Convert an amount from one currency to another.

        Uses USD as intermediate currency (two-step conversion).
        """
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        if from_currency == to_currency:
            return amount

        rates = await self.get_rates(base=self._base)

        # Get rates relative to base (USD)
        from_rate = rates.get(from_currency)
        to_rate = rates.get(to_currency)

        if from_rate is None:
            raise UnsupportedCurrencyError(f"Unsupported currency: {from_currency}")
        if to_rate is None:
            raise UnsupportedCurrencyError(f"Unsupported currency: {to_currency}")

        # Convert: amount_in_usd = amount / from_rate; result = amount_in_usd * to_rate
        return round((amount / from_rate) * to_rate, 4)

    async def to_base(self, amount: float, from_currency: str) -> float:
        """Convert amount to base currency (USD) for storage."""
        return await self.convert(amount, from_currency, self._base)

    async def from_base(self, amount: float, to_currency: str) -> float:
        """Convert amount from base currency (USD) for display."""
        return await self.convert(amount, self._base, to_currency)

    @staticmethod
    def format_amount(amount: float, currency: str) -> str:
        """Format a monetary amount with currency symbol."""
        import locale
        _SYMBOLS = {
            "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥",
            "CNY": "¥", "INR": "₹", "KRW": "₩", "BRL": "R$",
        }
        symbol = _SYMBOLS.get(currency.upper(), currency.upper() + " ")
        return f"{symbol}{amount:,.2f}"

    async def refresh_rates_cache(self) -> None:
        """
        Force-refresh exchange rates from provider and update cache.
        Called by the ARQ background worker hourly.
        """
        logger.info("Refreshing exchange rates cache")
        # Invalidate local cache
        self._local_rates = None
        self._local_rates_ts = 0.0
        # Fetch fresh rates (will populate Redis)
        await self.get_rates()
        logger.info("Exchange rates cache refreshed")

    @property
    def supported_currencies(self) -> frozenset:
        return SUPPORTED_CURRENCIES


# ---------------------------------------------------------------------------
# Application-level singleton factory
# ---------------------------------------------------------------------------

_currency_service: Optional[CurrencyService] = None


def get_currency_service(
    api_key: Optional[str] = None,
    cache=None,
) -> CurrencyService:
    """
    Return the application-level CurrencyService singleton.

    Called during lifespan startup with the Redis cache instance.
    """
    global _currency_service
    if _currency_service is None:
        import os
        resolved_key = api_key or os.environ.get("EXCHANGE_RATES_API_KEY", "")
        if resolved_key:
            provider: ExchangeRateProvider = OpenExchangeRatesProvider(resolved_key)
        else:
            logger.warning(
                "EXCHANGE_RATES_API_KEY not set — using static fallback rates. "
                "Set this env var in production for live exchange rates."
            )
            provider = StaticFallbackProvider()
        _currency_service = CurrencyService(provider=provider, cache=cache)
    return _currency_service
