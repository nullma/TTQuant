/// Symbol format conversion utilities for different exchanges
///
/// Different exchanges use different symbol formats:
/// - Binance: BTCUSDT (no separator)
/// - OKX: BTC-USDT (hyphen separator)
///
/// This module provides utilities to convert between formats.

/// Normalize a symbol to the internal format (no separator, uppercase)
///
/// # Examples
/// ```
/// assert_eq!(normalize_symbol("BTC-USDT", "okx"), "BTCUSDT");
/// assert_eq!(normalize_symbol("BTCUSDT", "binance"), "BTCUSDT");
/// ```
pub fn normalize_symbol(symbol: &str, exchange: &str) -> String {
    match exchange {
        "binance" => symbol.to_uppercase().replace("-", ""),
        "okx" => symbol.to_uppercase().replace("-", ""),
        _ => symbol.to_uppercase(),
    }
}

/// Convert a symbol to the exchange-specific format
///
/// # Examples
/// ```
/// assert_eq!(to_exchange_format("BTCUSDT", "okx"), "BTC-USDT");
/// assert_eq!(to_exchange_format("BTCUSDT", "binance"), "BTCUSDT");
/// ```
pub fn to_exchange_format(symbol: &str, exchange: &str) -> String {
    let normalized = normalize_symbol(symbol, exchange);

    match exchange {
        "binance" => normalized,
        "okx" => insert_hyphen(&normalized),
        _ => normalized,
    }
}

/// Insert hyphen before the quote currency (USDT, USDC, USD, BTC, ETH)
///
/// # Examples
/// ```
/// assert_eq!(insert_hyphen("BTCUSDT"), "BTC-USDT");
/// assert_eq!(insert_hyphen("ETHUSDT"), "ETH-USDT");
/// assert_eq!(insert_hyphen("BNBBTC"), "BNB-BTC");
/// ```
fn insert_hyphen(symbol: &str) -> String {
    // Common quote currencies
    let quote_currencies = ["USDT", "USDC", "USD", "BTC", "ETH", "BNB"];

    for quote in &quote_currencies {
        if symbol.ends_with(quote) {
            let base = &symbol[..symbol.len() - quote.len()];
            return format!("{}-{}", base, quote);
        }
    }

    // If no known quote currency found, return as-is
    symbol.to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_normalize_symbol() {
        assert_eq!(normalize_symbol("BTC-USDT", "okx"), "BTCUSDT");
        assert_eq!(normalize_symbol("btc-usdt", "okx"), "BTCUSDT");
        assert_eq!(normalize_symbol("BTCUSDT", "binance"), "BTCUSDT");
        assert_eq!(normalize_symbol("btcusdt", "binance"), "BTCUSDT");
    }

    #[test]
    fn test_to_exchange_format() {
        assert_eq!(to_exchange_format("BTCUSDT", "okx"), "BTC-USDT");
        assert_eq!(to_exchange_format("ETHUSDT", "okx"), "ETH-USDT");
        assert_eq!(to_exchange_format("BTCUSDT", "binance"), "BTCUSDT");
        assert_eq!(to_exchange_format("BTC-USDT", "binance"), "BTCUSDT");
    }

    #[test]
    fn test_insert_hyphen() {
        assert_eq!(insert_hyphen("BTCUSDT"), "BTC-USDT");
        assert_eq!(insert_hyphen("ETHUSDT"), "ETH-USDT");
        assert_eq!(insert_hyphen("BNBBTC"), "BNB-BTC");
        assert_eq!(insert_hyphen("ETHBTC"), "ETH-BTC");
        assert_eq!(insert_hyphen("BTCUSDC"), "BTC-USDC");
    }
}
