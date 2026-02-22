from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# Cache TTLs
MEMORY_CACHE_TTL_HOURS = 24
FILE_CACHE_TTL_HOURS = 24
SP500_LIST_CACHE_DAYS = 7

# Scheduler: daily refresh at 17:30 ET (22:30 UTC)
REFRESH_HOUR_UTC = 22
REFRESH_MINUTE_UTC = 30

# Rate limiting for yfinance calls
YFINANCE_REQUEST_DELAY_SECONDS = 0.3

# Screener defaults
DEFAULT_MAX_PCT_ABOVE_52W_LOW = 15.0
DEFAULT_MAX_TRAILING_PE = 20.0
DEFAULT_MIN_EPS_CAGR = 5.0
DEFAULT_MIN_DIVIDEND_YIELD = 2.0
MIN_DATA_QUALITY_SCORE = 0.5
MIN_EPS_YEARS = 3

# Portfolio defaults
DEFAULT_MAX_SECTOR_WEIGHT = 0.30
DEFAULT_MAX_SINGLE_STOCK_WEIGHT = 0.15
MAX_PORTFOLIO_ITERATIONS = 20

# Dow Jones Industrial Average 30 tickers
DJIA_TICKERS = [
    "AAPL", "AMGN", "AXP", "BA", "CAT", "CRM", "CSCO", "CVX", "DIS", "DOW",
    "GS", "HD", "HON", "IBM", "INTC", "JNJ", "JPM", "KO", "MCD", "MMM",
    "MRK", "MSFT", "NKE", "PG", "SHW", "TRV", "UNH", "V", "VZ", "WMT",
]

# Nasdaq 100 tickers (as of early 2026)
NDX_TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "TSLA", "GOOGL", "GOOG", "AVGO", "COST",
    "NFLX", "TMUS", "ASML", "AMD", "PEP", "LIN", "CSCO", "ADBE", "TXN", "QCOM",
    "INTU", "AMGN", "ISRG", "BKNG", "AMAT", "HON", "VRTX", "MU", "ADP", "PANW",
    "GILD", "ADI", "SBUX", "MELI", "LRCX", "INTC", "MDLZ", "CTAS", "KLAC", "CEG",
    "REGN", "PYPL", "CRWD", "SNPS", "CDNS", "MAR", "ORLY", "MNST", "FTNT", "MRVL",
    "CSX", "PCAR", "ABNB", "WDAY", "ADSK", "NXPI", "CHTR", "PAYX", "MCHP", "ROST",
    "CPRT", "KDP", "AEP", "FAST", "IDXX", "DDOG", "TEAM", "ODFL", "VRSK", "TTD",
    "EA", "BKR", "GEHC", "EXC", "CTSH", "FANG", "XEL", "ON", "GFS", "BIIB",
    "DLTR", "KHC", "WBD", "SIRI", "ZS", "ANSS", "ILMN", "SPLK", "ALGN", "ENPH",
    "LCID", "RIVN", "DXCM", "WBA", "CCEP", "CDW", "SMCI", "ARM", "DASH", "APP",
]

# Fallback S&P 500 large-cap subset (used if Wikipedia fetch fails)
SP500_FALLBACK = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "GOOG", "BRK-B", "LLY", "AVGO",
    "JPM", "TSLA", "UNH", "XOM", "V", "MA", "PG", "COST", "HD", "JNJ",
    "ABBV", "BAC", "MRK", "ORCL", "KO", "CVX", "WMT", "CRM", "NFLX", "PEP",
    "TMO", "AMD", "LIN", "ACN", "MCD", "ABT", "ADBE", "DHR", "PM", "CSCO",
    "TXN", "CAT", "ISRG", "GE", "AMGN", "GS", "NEE", "RTX", "BKNG", "PFE",
    "SPGI", "AXP", "HON", "IBM", "INTU", "LOW", "VRTX", "T", "CMCSA", "ELV",
    "TJX", "SCHW", "C", "UPS", "BSX", "BLK", "SYK", "DE", "GILD", "MDT",
    "MMC", "ADP", "BA", "DUK", "MU", "NOW", "SBUX", "ZTS", "CI", "SO",
    "BMY", "PLD", "WFC", "CL", "CB", "ETN", "MO", "AON", "REGN", "ICE",
    "CVS", "CME", "HCA", "NOC", "SLB", "FI", "EMR", "ITW", "WM", "MCO",
]
