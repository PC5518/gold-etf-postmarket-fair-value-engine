# AnsCom Quantitative Suite — POST-MARKET Gold ETF Fair-Value Engine

**An **opensource** market-structure repair system for ICICI Prudential Gold ETF (NSE: GOLDIETF)**
Real-time synthetic NAV approximation during NSE off-hours using live XAUUSD and USDINR feeds.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18185485.svg)](https://doi.org/10.5281/zenodo.18185485)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MetaTrader5](https://img.shields.io/badge/Requires-MetaTrader%205-8B4FFF)](https://www.metatrader5.com/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D4?logo=windows)](https://www.microsoft.com/windows)
[![Selenium](https://img.shields.io/badge/Scraper-Selenium-43B02A?logo=selenium&logoColor=white)](https://selenium.dev/)
[![License](https://img.shields.io/badge/License-MIT-22C55E)](LICENSE)

📄 [Research Paper (Zenodo)](https://doi.org/10.5281/zenodo.18185485) · ▶ [Full Demo (YouTube)](https://www.youtube.com/watch?v=Pi3xI19eqHs)

---

> ### AnsCom Terminal – Real-Time Synthetic Price for GOLDIETF
> A live terminal that approximates the **ICICI Prudential Gold ETF (GOLDIETF)** price **after NSE market hours**, using XAUUSD and USDINR in real-time.

---

## Table of Contents

1. [What This Is — In One Paragraph](#1-what-this-is--in-one-paragraph)
2. [Background: Indian Gold ETFs and the Pricing Gap](#2-background-indian-gold-etfs-and-the-pricing-gap)
3. [Problem Statement: The Off-Hours Blind Spot](#3-problem-statement-the-off-hours-blind-spot)
4. [System Design Overview](#4-system-design-overview)
5. [Core Quantitative Model](#5-core-quantitative-model)
   - [The Fair-Value Formula](#51-the-fair-value-formula)
   - [Why Multiplicative Decomposition?](#52-why-multiplicative-decomposition)
   - [NAV vs. ETF Price: The Premium-Discount Problem](#53-nav-vs-etf-price-the-premium-discount-problem)
   - [Derived Metrics and Their Meaning](#54-derived-metrics-and-their-meaning)
   - [Model Assumptions and Known Limitations](#55-model-assumptions-and-known-limitations)
6. [Two-Phase Architecture](#6-two-phase-architecture)
   - [Phase 1 — Pre-Load Engine (Reference Snapshot)](#61-phase-1--pre-load-engine-reference-snapshot)
   - [Phase 2 — Live Loop (Tick Streaming)](#62-phase-2--live-loop-tick-streaming)
7. [Complete Function-by-Function Code Walkthrough](#7-complete-function-by-function-code-walkthrough)
8. [Data Pipeline and Sources](#8-data-pipeline-and-sources)
9. [The AnsCom Terminal UI](#9-the-anscom-terminal-ui)
10. [Design-to-Code: Whiteboard Methodology](#10-design-to-code-whiteboard-methodology)
11. [Installation and Setup](#11-installation-and-setup)
12. [Startup Sequence Explained](#12-startup-sequence-explained)
13. [Versioning and Bug Fixes (v4.4 Changelog)](#13-versioning-and-bug-fixes-v44-changelog)
14. [Engineering Decisions and Tradeoffs](#14-engineering-decisions-and-tradeoffs)
15. [Potential Extensions and Future Work](#15-potential-extensions-and-future-work)
16. [Demo & Tutorial](#16-demo--tutorial)
17. [Research Paper](#17-research-paper)
18. [Contributing](#18-contributing)

---

## 1. What This Is — In One Paragraph

This project is a **real-time financial modelling engine** that estimates the fair-value price of India's most traded gold ETF — **ICICI Prudential Gold ETF (NSE: GOLDIETF)** — during periods when the National Stock Exchange is closed. It does this by anchoring a reference state at 15:30 IST (NSE close), then continuously scaling the last known ETF price using live movements in **spot gold (XAUUSD)** and the **USD/INR exchange rate**, the two underlying drivers of the ETF's NAV. The result is displayed in a custom-built, real-time visual terminal called the **AnsCom Terminal**, showing the synthetic ETF level, its component return drivers, premium vs. close, and rolling tick volatility — all updating live.

---

## 2. Background: Indian Gold ETFs and the Pricing Gap

### What is GOLDIETF?

ICICI Prudential Gold ETF (ticker: **GOLDIETF**) is an open-ended exchange-traded fund listed on the NSE that tracks the domestic price of 24-karat gold. Each unit of GOLDIETF approximately represents 1 gram of physical gold (the exact gram-equivalent varies slightly by fund due to tracking costs and expense ratios, currently ~0.995g per unit for GOLDIETF).

The fund's **Net Asset Value (NAV)** is determined by:

1. The international spot price of gold in USD per troy ounce (**XAUUSD**)
2. The prevailing **USD/INR exchange rate**
3. A gram conversion factor (1 troy oz = 31.1035 grams)
4. Fund-specific adjustments (expense ratio accrual, physical gold holding costs)

Simplified NAV per unit:

$$
\text{NAV}_{\text{approx}} = \frac{\text{XAUUSD} \times \text{USDINR}}{31.1035} \times \text{GramsPerUnit} \times (1 - \text{TER}_{\text{daily}})
$$

### Why Gold ETFs Trade at a Premium or Discount

On NSE, GOLDIETF trades like a stock — buyers and sellers transact at the **market price**, which is determined by supply and demand in the order book. The **iNAV** (indicative NAV) is published by the fund house every 15 seconds during market hours to guide the market price.

Authorized Participants (large institutions) can create or redeem ETF units in exchange for gold, which arbitrages away large deviations between market price and iNAV. However, small premiums and discounts persist due to:

- Liquidity and bid-ask spreads
- Lag between iNAV publication and price update
- Market microstructure friction

### The Off-Hours Problem

NSE market hours: **09:15 IST to 15:30 IST**, Monday to Friday (excluding Indian public holidays).

After 15:30 IST, **no new official ETF price is published**. However:

- COMEX and LBMA gold spot (XAUUSD) trade globally until ~23:00 EST, and resume at ~23:00 EST Sunday-Thursday
- USD/INR (NDF and spot) trades in Singapore, Dubai, London, and New York overnight
- Gold moves significantly on US economic data (CPI, Fed minutes, non-farm payrolls), geopolitical events, and currency moves

This creates an **information vacuum**: Indian investors who hold GOLDIETF, or want to trade it at tomorrow's open, have no live proxy for what the ETF *would* be worth right now. This engine fills that vacuum.

---

## 3. Problem Statement: The Off-Hours Blind Spot

```
+-----------------------------------------------------------------+
|                                                                 |
|   09:15 IST                            15:30 IST               |
|      |<--------- NSE TRADING HOURS ---------->|                |
|      |                                        |                |
|      |  ETF price updates live                | ETF PRICE      |
|      |  iNAV published every 15s              | STOPS UPDATING |
|      |                                        |                |
|                                               |<-------------> |
|                               REST OF THE WORLD (Gold, FX)     |
|                               continues moving 24x7            |
|                                                                 |
|  Problem: What is GOLDIETF worth at, say, 22:00 IST tonight?   |
|                                                                 |
|  Answer:  SyntheticETF = ETF_close x R_gold x R_fx             |
|                                                                 |
+-----------------------------------------------------------------+
```

### Who Needs This?

**Retail Investors** — An investor who holds GOLDIETF and wakes up at 6 AM to news that gold surged 2% overnight in New York wants to know: "Has my portfolio already recovered? Should I buy more before open?" Without a proxy, they are completely blind.

**Swing Traders** — Someone planning an entry or exit at tomorrow's NSE open wants to estimate the likely gap-up or gap-down before placing limit orders. A live synthetic level lets them set meaningful pre-market alerts.

**Portfolio Risk Managers** — A fund or family office running a gold position via GOLDIETF needs to mark the position to market for end-of-day risk reports. The last NSE close (potentially 6–18 hours old) is a stale input; a synthetic level is significantly more accurate.

**Quantitative Researchers** — Anyone building a continuous price series for GOLDIETF (e.g., for backtesting a gold hedging strategy) needs to fill the overnight gaps. This engine provides the methodology for that reconstruction.

**No commercial data vendor currently offers a free, open-source, publicly available post-market synthetic price for Indian gold ETFs.** This project builds the entire pipeline from scratch.

> **Traders and investors often want to know:**
> *"If NSE was open right now, approximately where would GOLDIETF be trading?"*
>
> This project builds a **real-time proxy fair-value engine** that answers exactly that, by:
> 1. Fixing a **reference point** at **15:30 IST** (Indian close)
> 2. Streaming live **XAUUSD** and **USDINR** prices
> 3. Scaling the last ETF close using proportional returns in gold and FX
> 4. Displaying everything in a **live visual terminal** with volatility, premium and driver breakdowns

---

## 4. System Design Overview

### Architecture Diagram

![System Overview](https://github.com/user-attachments/assets/5f46b70a-c371-4e48-b1f5-4486b6fdc55d)

The engine is architecturally separated into two non-overlapping phases that run sequentially:

```
STARTUP (runs once)                    LIVE LOOP (runs continuously)
-----------------------------          ------------------------------------------
[NSE Selenium Scrape]                  [MT5 Tick] ----> [Engine.calculate()]
      |                                    |                   |
      v                                    v                   v
[ETF Close, iNAV, Date]            [Gold Now]       [Synthetic ETF Price]
      |                                                        |
[MT5 History Query]                [YF 30s cache]             v
      |                                |           [AnsCom Terminal Update]
      v                                v               (Matplotlib, 10 Hz)
[XAUUSD @ 15:30]               [USDINR Now]
      |
[YFinance History Query]
      |
      v
[USDINR @ 15:30]
      |
      v
[SyntheticETFEngine initialized]
      |
      v
[Live Loop begins]
```

**Design principles driving this architecture:**

- **Reference immutability:** Once the 15:30 snapshot is locked at startup, it never changes during the session. This ensures the synthetic price is always a coherent delta from a single anchor point.
- **Separation of concerns:** Data fetching, computation, and rendering are three independent layers. The engine class does not know or care about the UI. The UI does not know about the data sources.
- **Graceful degradation:** Every external call (NSE, MT5, Yahoo Finance) has a documented fallback. The engine will run in a degraded-but-functional state even if historical data is unavailable.
- **Windows-safe output:** All console output passes through an ASCII sanitizer to prevent charmap crashes on Windows terminals that cannot render `₹`.

---

## 5. Core Quantitative Model

### 5.1 The Fair-Value Formula

The central formula of the engine is:

$$
\boxed{
\text{SyntheticETF}_{\text{live}} = \text{ETF}_{\text{close}} \times \frac{\text{XAUUSD}_{\text{live}}}{\text{XAUUSD}_{\text{ref}}} \times \frac{\text{USDINR}_{\text{live}}}{\text{USDINR}_{\text{ref}}}
}
$$

**Complete variable definitions:**

| Symbol | Full Name | Unit | Source |
|---|---|---|---|
| $\text{ETF}_{\text{close}}$ | Last official GOLDIETF closing price on NSE | INR per unit | NSE via Selenium |
| $\text{XAUUSD}_{\text{ref}}$ | Gold spot price at exactly 15:30 IST on the reference date | USD per troy oz | MetaTrader 5 (1-min history) |
| $\text{USDINR}_{\text{ref}}$ | USD/INR exchange rate at 15:30 IST on the reference date | INR per USD | Yahoo Finance (1-min history) |
| $\text{XAUUSD}_{\text{live}}$ | Current live gold spot price (bid-ask midpoint) | USD per troy oz | MetaTrader 5 tick feed |
| $\text{USDINR}_{\text{live}}$ | Current live USD/INR rate | INR per USD | Yahoo Finance (30s cache) |
| $\text{SyntheticETF}_{\text{live}}$ | Estimated fair-value GOLDIETF price right now | INR per unit | Computed by engine |

### 5.2 Why Multiplicative Decomposition?

The formula uses **ratio-of-ratios (multiplicative returns)** rather than additive changes. This is the mathematically correct approach because:

**The underlying NAV is a product, not a sum.**

The INR value of gold is:

$$
\text{Gold}_{\text{INR}} = \text{XAUUSD} \times \text{USDINR}
$$

Since both XAUUSD and USDINR are multiplicative inputs to the ETF price, changes compound rather than add. Consider a worked example:

- Gold goes from $2000 to $2020 → +1% increase in USD terms
- INR weakens from 84.00 to 84.84 → +1% depreciation (gold becomes more expensive in INR)

**Additive approach (incorrect):** adds percentage changes: +1% + 1% = +2.00% total

**Multiplicative approach (correct):** compounds the ratios: 1.01 × 1.01 = 1.0201 → +**2.01%** total

For small overnight moves this difference is tiny. For large events (e.g. gold +3%, INR -2% simultaneously on a Fed announcement night), compounding makes a material difference. The multiplicative formula is also dimensionally consistent: it does not matter what absolute levels are used, only the proportional changes from the reference anchor.

### 5.3 NAV vs. ETF Price: The Premium-Discount Problem

The engine tracks two related but distinct concepts:

**iNAV (Indicative NAV):** The theoretical per-unit value of the ETF's gold holdings, computed from live gold prices. Published by ICICI AMC every 15 seconds during market hours.

**Market Price (LTP):** What GOLDIETF actually traded at on NSE. This is the `ETF_close` input to the engine.

The difference between them is the **premium/discount**:

$$
\text{Premium}_{t} = \frac{\text{LTP}_t}{\text{iNAV}_t} - 1
$$

This is computed at startup as `engine.premium_close`. In normal market conditions, GOLDIETF trades very close to its iNAV (within 0.1–0.2%). During high-volatility events, liquidity crunches, or near-market-close, larger deviations can occur.

The synthetic price inherits the premium/discount that existed at the 15:30 close. It assumes this relationship is constant over the off-hours period — a simplifying assumption that is reasonable for short intervals but degrades over longer ones.

### 5.4 Derived Metrics and Their Meaning

Beyond the synthetic price, the engine computes and displays four additional live metrics:

**Gold Return %**

$$
\text{GoldReturn\%} = \left(\frac{\text{XAUUSD}_{\text{live}}}{\text{XAUUSD}_{\text{ref}}} - 1\right) \times 100
$$

How much gold has moved in USD terms since NSE closed. Positive means gold has appreciated in global markets, pushing the synthetic ETF price up. This is typically the dominant driver of overnight GOLDIETF moves.

**FX Return %**

$$
\text{FXReturn\%} = \left(\frac{\text{USDINR}_{\text{live}}}{\text{USDINR}_{\text{ref}}} - 1\right) \times 100
$$

How much the USD/INR rate has moved since NSE closed. Positive means INR has weakened (more INR per USD), which increases the INR-denominated cost of gold and pushes the synthetic ETF price up. This driver becomes significant during RBI interventions, US dollar index moves, or EM currency stress events.

**Premium vs. Close %**

$$
\text{PremiumVsClose\%} = \left(\frac{\text{SyntheticETF}_{\text{live}}}{\text{ETF}_{\text{close}}} - 1\right) \times 100
$$

The total combined effect — how much the synthetic price has moved from the last NSE close. This is the most actionable metric for a trader trying to estimate tomorrow's open. If this shows +1.5%, they can reasonably expect a ~1.5% gap-up at the next NSE open, all else being equal.

**Volatility (bps)**

$$
\text{Vol}_{\text{bps}} = \sigma\!\left(\left\{\frac{p_i - p_{i-1}}{p_{i-1}}\right\}_{i=1}^{N}\right) \times 10{,}000
$$

Where $\{p_i\}$ is the rolling window of the last 150 synthetic ETF ticks and $\sigma(\cdot)$ is the sample standard deviation of tick-to-tick returns. Multiplying by 10,000 converts from decimal returns to basis points. This is a **realized tick volatility** measure — not annualized — that captures how actively the synthetic price is moving right now. Rising vol in bps signals a period of active gold or FX movement.

### 5.5 Model Assumptions and Known Limitations

Understanding what the model assumes is as important as understanding what it computes.

| Assumption | What It Means in Practice | When It Breaks Down |
|---|---|---|
| Linear NAV relationship | GOLDIETF price moves proportionally with gold × FX | Always approximately true; breaks only in extreme events |
| Constant premium/discount | The ETF-to-iNAV premium at 15:30 persists overnight | Diverges if fund-specific news or large creation/redemption occurs overnight |
| USDINR proxy via Yahoo Finance | Yahoo Finance `USDINR=X` is a sufficient FX proxy | During thin liquidity or data feed outages, YF may stale or diverge from NDF markets |
| 15:30 IST as the anchor | NSE always closes at 15:30 IST | Market holidays, early closes, or technical halts shift the anchor; manual correction required |
| No expense ratio accrual | Daily TER is not modeled | Introduces ~0.0004% error per day — negligible for short periods |
| No gold import duty changes | Domestic gold premium over international is constant | Budget announcements or sudden duty changes would invalidate the model until next NSE open |

---

## 6. Two-Phase Architecture

### 6.1 Phase 1 — Pre-Load Engine (Reference Snapshot)

> **Original Design Note:** This phase was titled *"Pre-Data Loading Engine"* in the system whiteboard (see Section 10). Goal: build a stable reference state at India close (15:30 IST) before the live loop starts.

The pre-load phase runs **once at startup** and establishes a stable, internally consistent reference state. All four steps must complete before the live loop begins.

```
PHASE 1: PRE-LOAD SEQUENCE
=================================================================

Step 1: NSE Scrape (Selenium)
---------------------------------
  Input:  Symbol = "GOLDIETF"
  Action: Launch Chrome -> Navigate to NSE equity quote page
          -> Wait 5s for JS render -> Extract via XPath:
            - GOLDIETF LTP (close price in Rs)
            - iNAV (indicative NAV in Rs)
            - Trade date string (raw, may contain "As of ...")
  Output: (inav_str, close_str, raw_date_str)

Step 2: Date Parsing
---------------------------------
  Input:  raw_date_str (e.g., "As of 09-Dec-2025 15:30:00")
  Action: Regex extract DD-MMM-YYYY pattern
          -> datetime.strptime -> .isoformat()
  Output: ref_date_iso (e.g., "2025-12-09")

Step 3: Gold Reference @ 15:30 IST (MetaTrader 5)
---------------------------------
  Input:  ref_date_iso, symbol = "XAUUSD"
  Action: Compute anchor = datetime(Y, M, D, 15, 30)
          -> Query MT5 copy_rates_range() for 1-min bars
             from anchor-20min to anchor+5min
          -> Walk backwards through bars
          -> Select last bar whose timestamp <= anchor
  Output: gold_ref (float, USD/oz)

Step 4: USDINR Reference @ 15:30 IST (Yahoo Finance)
---------------------------------
  Input:  ref_date_iso
  Action: Convert 15:30 IST -> UTC (subtract 5h30m)
          -> yf.download("USDINR=X", interval="1m",
               start=anchor_utc-30min, end=anchor_utc+5min)
          -> Handle timezone-aware index -> convert to naive UTC
          -> Select last row <= anchor_utc
  Output: fx_ref (float, INR/USD)

=================================================================
  On completion: SyntheticETFEngine(etf_close, gold_ref, fx_ref,
  inav_val) is initialized. Phase 2 begins immediately.
=================================================================
```

**Fallback chain:** If any data fetch fails, the engine does not crash. Instead:
- Missing `gold_ref` → uses the current live tick price from MT5 as the reference (meaning Phase 2 tracks from "now" rather than from 15:30)
- Missing `fx_ref` → defaults to 84.50 (configurable hardcoded fallback)
- Failed NSE scrape → `etf_close` defaults to 1.0 (engine runs but premium metrics are meaningless)

### 6.2 Phase 2 — Live Loop (Tick Streaming)

After initialization, the engine enters an infinite loop:

```
PHASE 2: LIVE LOOP (runs indefinitely until Ctrl+C)
=================================================================

Every ~1ms (tick-rate):
  1. mt5.symbol_info_tick("XAUUSD")
     -> bid, ask -> mid_gold = (bid + ask) / 2

  2. usd_source.get_mid()
     -> Returns cached USDINR (refreshes from YF every 30s)

  3. engine.calculate(mid_gold, fx_val)
     -> Returns { synthetic, gold_return, fx_return }

  4. Append to time-series:
     times[], prices_etf[], prices_gold[]

Every 100ms (UI refresh rate = 10 Hz):
  5. Update large price text (Rs with color + directional arrow)
  6. Update XAUUSD spot display
  7. Redraw multi-color line charts (ETF + Gold)
  8. Recompute and render Data Factory panel:
       - Section 1: Engine outputs (synthetic, refs)
       - Section 2: Live drivers (gold now, fx now, % changes)
       - Section 3: Premium & risk (premium%, vol bps, ref date)
  9. plt.pause(0.001) -> yields control to Matplotlib event loop

On Ctrl+C:
  10. mt5.shutdown()
  11. plt.close('all')
  12. Graceful exit
=================================================================
```

**Why `plt.pause(0.001)` instead of `plt.draw()`?**
`plt.pause()` calls the Matplotlib event loop, which is necessary for the window to remain interactive (draggable, resizable) while updating. A bare `plt.draw()` does not process GUI events and leads to a frozen, unresponsive window on most backends.

---

## 7. Complete Function-by-Function Code Walkthrough

### `clean_console_str(text)`

```python
def clean_console_str(text):
    return str(text).encode('ascii', 'ignore').decode('ascii').strip()
```

**Purpose:** Windows uses `cp1252` encoding for console output by default. The Rupee symbol `₹` (U+20B9) is not in `cp1252`, causing a `UnicodeEncodeError: 'charmap' codec can't encode character` on every print statement containing a price. This function encodes the string as ASCII, silently dropping any non-ASCII character, then decodes back to a clean string. `₹` is only used in Matplotlib (which handles Unicode correctly via font rendering), never in raw `print()` calls.

---

### `get_etf_data_selenium(symbol="GOLDIETF")`

**Purpose:** Retrieves three critical data points from NSE's live equity quote page — the ETF's last traded price, its indicative NAV, and the date of the last trade.

**Why Selenium is necessary:** NSE's equity quote page renders all price data via JavaScript after the initial HTML load. Standard HTTP scraping with `requests` or `httpx` returns an empty HTML skeleton with no price data. Selenium drives a real Chrome browser that executes the JavaScript, waits for the DOM to populate (5-second `time.sleep`), and extracts elements by XPath.

**XPath selector fragility:** NSE periodically updates their frontend, which changes the HTML DOM structure and invalidates XPath selectors. The selectors in the code target specific `div` indices within a nested layout. If NSE restructures their page, these will break silently (returning "0"). The utility script `find_goldietf_params.py` exists specifically to help re-discover the correct XPaths after an NSE update.

**Chrome window handling:** The browser is launched non-headless (for debugging visibility) but immediately minimized with `driver.minimize_window()`. The `finally` block guarantees `driver.quit()` is always called regardless of success or exception, preventing orphaned Chrome processes from accumulating.

---

### `parse_nse_date(raw)`

**Purpose:** Converts NSE's raw date string into a clean `YYYY-MM-DD` ISO format string for use in historical data queries.

**The parsing challenge:** NSE's date element may contain:
- Just `"09-Dec-2025"` — clean case
- `"As of 09-Dec-2025 15:30:00"` — wrapped in context prefix
- `"As of 09-Dec-2025"` — date only with prefix

The function first applies regex `r"(\d{2}-[a-zA-Z]{3}-\d{4})"` to extract the DD-MMM-YYYY pattern regardless of surrounding text. This is more robust than `str.split()` or `str.replace()` because it makes no assumptions about surrounding structure. Only if regex extraction fails does it attempt direct `strptime` parsing. Both paths fall back to `datetime.now()` if they fail, keeping the engine runnable.

---

### `get_gold_1530_mt5(india_date_str, symbol="XAUUSD")`

**Purpose:** Retrieves the XAUUSD price prevailing at exactly 15:30 IST on the reference date from MetaTrader 5's historical bar database.

**Bar selection logic:** MT5 stores OHLCV bars indexed by their **open timestamp** (start of the bar). A bar opened at 15:29:00 covers 15:29:00–15:30:00. This bar represents market conditions at 15:30 IST well. The function searches for the **last bar whose timestamp is ≤ the anchor**, not the first bar after it. This ensures the reference captures the gold price *at or immediately before* 15:30 IST rather than after close.

**Time window:** The query covers anchor−20 minutes to anchor+5 minutes. The −20 minute buffer handles cases where MT5's data has small gaps or where the session was thin near close.

**Note on MT5 timestamps:** MT5 bar timestamps are in **broker time**, which varies by broker. Most retail brokers use UTC+2 or UTC+3 (EET/EEST). The current implementation uses naive local timestamps, which may introduce a ±1 bar error depending on the broker's timezone. A production version would explicitly convert IST to the broker's registered timezone.

---

### `get_usdinr_at_1530_yf(india_date_str)`

**Purpose:** Retrieves the USD/INR exchange rate at 15:30 IST on the reference date from Yahoo Finance.

**Timezone handling — the tricky part:** Yahoo Finance returns intraday data with timezone-aware `DatetimeIndex` objects (typically UTC or market timezone). Comparing these with a naive `datetime` raises `TypeError: can't compare offset-naive and offset-aware datetimes`. The function:
1. Converts 15:30 IST to UTC by subtracting 5h 30m → 10:00 UTC
2. Downloads data in UTC
3. Checks `if idx.tz is not None` and converts to naive UTC via `tz_convert(None)`
4. Filters for rows ≤ anchor UTC, takes the last one

**Why not MT5 for USDINR?** Most retail MT5 brokers offering gold do not carry `USDINR`, since it is an EM pair primarily traded in the NDF (Non-Deliverable Forward) market. Yahoo Finance provides a convenient free source via `USDINR=X`. However, Yahoo Finance's USDINR quotes carry a ~15-minute delay during Indian market hours. For the reference snapshot (which is historical by definition) and for off-hours use (when the NDF market is itself slow-moving), this delay is acceptable.

---

### `USDINRSource` class

```python
class USDINRSource:
    def __init__(self):
        self.last_price = 84.0
        self.last_update = 0

    def get_mid(self):
        now = time.time()
        if now - self.last_update > 30:
            # Refresh from Yahoo Finance
            ...
        return self.last_price
```

**Purpose:** A lightweight caching wrapper around the Yahoo Finance USDINR polling call.

**Why cache?** The main live loop runs at approximately 1ms intervals (up to 1000 iterations per second). If every iteration called `yf.download()`, Yahoo Finance would immediately rate-limit the connection, adding ~200–500ms network latency per call. The 30-second cache means Yahoo Finance is queried at most twice per minute — well within any implicit rate limit — while the FX rate in computation is at most 30 seconds stale. For USD/INR, which moves slowly compared to gold, this staleness is acceptable.

**Thread safety note:** The live loop is single-threaded (no `threading` or `asyncio`), so there is no race condition risk on `self.last_price`. A multi-threaded extension would require a `threading.Lock` around the cache update.

---

### `SyntheticETFEngine` class

```python
class SyntheticETFEngine:
    def __init__(self, etf_ref, gold_ref, fx_ref, nav_ref):
        self.etf_ref = etf_ref
        self.gold_ref = gold_ref
        self.fx_ref = fx_ref
        if nav_ref > 0:
            self.premium_close = (etf_ref / nav_ref) - 1.0
        else:
            self.premium_close = 0.0

    def calculate(self, gold_now, fx_now):
        if self.gold_ref == 0 or self.fx_ref == 0:
            return {"synthetic": self.etf_ref, "gold_return": 0, "fx_return": 0}
        gold_return = gold_now / self.gold_ref
        fx_return = fx_now / self.fx_ref
        etf_live = self.etf_ref * gold_return * fx_return
        return {
            "synthetic": etf_live,
            "gold_return": gold_return - 1,
            "fx_return": fx_return - 1
        }
```

**Purpose:** The core mathematical engine. Initialized once with the reference triplet and iNAV; `calculate()` is called on every tick.

**Zero-division guards:** Both `__init__` and `calculate()` include explicit zero checks. `nav_ref` could be zero if NSE scraping failed and defaulted to "0". `gold_ref` or `fx_ref` could be zero if both primary fetch and fallback failed. Rather than crashing with `ZeroDivisionError` inside the live loop (which would terminate the terminal), the engine returns the reference ETF price with zero returns — a safe degraded state that keeps the terminal alive.

**Why return `gold_return - 1` and `fx_return - 1`?** The raw ratios are multiplicative returns (e.g., 1.012 for a 1.2% move). Subtracting 1 converts to additive returns (0.012) which are then multiplied by 100 in the UI layer for percentage display. This keeps the engine layer pure (ratios) and the display layer responsible for formatting.

---

### `calc_vol(prices_list)`

```python
def calc_vol(prices_list):
    if len(prices_list) < 10: return 0.0
    arr = list(prices_list)[-150:]
    returns = []
    for i in range(1, len(arr)):
        if arr[i-1] != 0:
            r = (arr[i] - arr[i-1]) / arr[i-1]
            returns.append(r)
        else:
            returns.append(0.0)
    if not returns: return 0.0
    return statistics.stdev(returns) * 10000
```

**Purpose:** Computes rolling realized volatility in basis points from the most recent synthetic ETF ticks.

**Window:** Last 150 ticks. At the ~10Hz UI update rate, this covers approximately 15 seconds of recent activity — making this a very short-term (tick) volatility measure.

**Sample vs. population std dev:** `statistics.stdev` computes the **sample standard deviation** (denominator N−1), which is statistically correct when treating the window as a sample of the underlying vol process. `numpy.std` defaults to population std (denominator N). For small windows (N = 150), this is a ~0.3% difference — minor but principled.

**Interpretation:** A value of 2.5 bps means the synthetic ETF price is moving about 0.025% per tick on average. During calm off-hours sessions, this might be 0.1–0.5 bps. During active New York sessions with gold moving on economic data releases, this can spike to 5–20+ bps.

---

### `plot_multicolor_line(ax, dates, values)`

**Purpose:** Renders a price chart where each line segment is independently colored green (price up) or red (price down) relative to the previous tick. This is standard in professional trading terminals (TradingView, Bloomberg) and gives an immediate visual read on price direction history without requiring a legend.

**Implementation:** Uses Matplotlib's `LineCollection`, which accepts an array of line segments and a parallel array of colors. Each segment is defined by two consecutive (x, y) points. This is significantly more efficient than N separate `ax.plot()` calls (one per segment), which creates N separate artist objects that must each be tracked, updated, and garbage-collected on every redraw.

---

### `MetricTracker` class

**Purpose:** Tracks the previous value of each named metric and returns a display color and directional arrow (▲/▼) based on whether the current value is higher, lower, or unchanged. Drives the Bloomberg-style live indicators in the Data Factory panel.

**Dead zone:** The comparison uses ±0.0000001 tolerance to avoid false direction changes from floating-point rounding. Without this, a value that should show as "unchanged" might jitter between ▲ and ▼ due to sub-nanosecond floating-point imprecision in repeated division operations.

---

## 8. Data Pipeline and Sources

### Complete Data Flow

```
+----------------------------------------------------------------------+
|                        DATA SOURCES                                  |
|                                                                      |
|  NSE Website          MetaTrader 5          Yahoo Finance            |
|  nseindia.com         broker feed           finance.yahoo.com        |
|      |                    |   |                    |   |             |
|      | [Selenium]         |   | [Python MT5 API]   |   | [yfinance]  |
|      v                    v   v                    v   v             |
|  ETF LTP/iNAV     XAUUSD History       USDINR History               |
|  Trade Date        @ 15:30 IST          @ 15:30 IST                  |
|  (startup only)   (startup only)       (startup only)               |
|                                                                      |
|                    XAUUSD Live              USDINR Live              |
|                    (every ~1ms)            (every 30s, cached)       |
|                                                                      |
|                           |                    |                     |
|                           +--------+-----------+                     |
|                                    v                                 |
|                         SyntheticETFEngine.calculate()              |
|                                    |                                 |
|                                    v                                 |
|                             AnsCom Terminal                          |
|                          (Matplotlib @ 10 Hz)                        |
+----------------------------------------------------------------------+
```

### Data Source Specifications

| Data Point | Symbol / Ticker | Source | API / Method | Refresh Rate | Notes |
|---|---|---|---|---|---|
| GOLDIETF LTP | `GOLDIETF` on NSE | NSE India website | Selenium XPath | Once at startup | 5s JS render delay |
| GOLDIETF iNAV | NSE quote page | NSE India website | Selenium XPath | Once at startup | Used for premium calc |
| Trade date | NSE quote page | NSE India website | Selenium + regex | Once at startup | Determines anchor date |
| XAUUSD history | `XAUUSD` | MetaTrader 5 | `copy_rates_range` M1 | Once at startup | Bar closest to 15:30 IST |
| USDINR history | `USDINR=X` | Yahoo Finance | `yf.download` 1m | Once at startup | ~15min delayed |
| XAUUSD live | `XAUUSD` | MetaTrader 5 | `symbol_info_tick` | Every iteration (~1ms) | Bid-ask mid used |
| USDINR live | `USDINR=X` | Yahoo Finance | `yf.download` 1d | Every 30 seconds | Cached to avoid rate limit |

---

## 9. The AnsCom Terminal UI

### Final Output

![AnsCom Terminal](https://github.com/user-attachments/assets/0e4e96bc-4792-4895-9f3d-5fac7253af48)

### Panel Architecture

The terminal uses Matplotlib with `GridSpec(2, 3)` — 2 rows, 3 columns, with a 25%/75% height split:

```
+---------------------+---------------------+---------------------+
|  TOP LEFT           |  TOP CENTER         |  TOP RIGHT          |
|  -----------------  |  -----------------  |  -----------------  |
|  SYNTHETIC ETF      |  XAUUSD SPOT PRICE  |  [system info]      |
|  PRICE (LARGE)      |                     |                     |
|  Rs 189.22 (38pt)   |  $ 2041.30 (18pt)   |                     |
+---------------------+---------------------+---------------------+
|  BOTTOM LEFT        |  BOTTOM CENTER      |  BOTTOM RIGHT       |
|  -----------------  |  -----------------  |  -----------------  |
|  Synthetic ETF      |  XAUUSD Spot        |  DATA FACTORY       |
|  Price Chart        |  Price Chart        |  -----------------  |
|  (multi-color line) |  (multi-color line) |  1. ENGINE OUTPUTS  |
|  Time axis HH:MM    |  Time axis HH:MM    |  2. LIVE DRIVERS    |
|                     |                     |  3. PREMIUM & RISK  |
+---------------------+---------------------+---------------------+
     "AnsCom Terminal" branding header spans top of figure
```

### Color System

| Hex Code | Name | Assigned Role |
|---|---|---|
| `#050505` | Ultra Dark | Figure background |
| `#111111` | Panel Dark | Panel background, branding box |
| `#1A1A1A` | Grid Dark | Axis grid lines |
| `#FFFFFF` | White | Primary values, neutral numbers |
| `#888888` | Label Grey | Metric labels, axis ticks |
| `#00FF41` | Neon Green | Price moving up, up-tick arrows (▲) |
| `#FF2A00` | Neon Red | Price moving down, down-tick arrows (▼) |
| `#FFC400` | Gold Yellow | Section headers, branding accent |

### Data Factory Panel — Live Metrics Display

The Data Factory renders three organized sections of live metrics as positioned Matplotlib text objects inside an `axis('off')` axes — using Matplotlib as a text layout engine, with precise (x, y) positioning rather than a fixed table structure:

```
1. ENGINE OUTPUTS          <- Section header (gold bold)
   Synth Value    ^ Rs 189.22
   ETF Ref (NSE)    Rs 187.45
   Gold Ref         $ 2038.10
   USD/INR Ref      84.231

2. LIVE DRIVERS
   Gold Now       ^ $ 2041.30
   USD/INR Now      84.415
   Gold Chg %     ^ +0.157%
   USD/INR Chg %  ^ +0.219%

3. PREMIUM & RISK
   vs Close %     ^ +0.38%
   Vol (bps)        1.24
   Ref Date         2025-12-09
```

Each numeric value is passed through `MetricTracker` to get its directional color and arrow, creating a live Bloomberg terminal-style data feed effect.

---

## 10. Design-to-Code: Whiteboard Methodology

This project was designed **entirely on paper before any code was written**. The whiteboard diagrams below are the original design artifacts that directly correspond to the final code.

### Pre-Data Loading Design

![Whiteboard Phase 1](https://github.com/user-attachments/assets/47fed271-e80b-4cd6-a03d-d018f0b81e18)

This diagram shows the four-step pre-load sequence: NSE scrape → date parse → gold historical fetch → FX historical fetch. Each box on the whiteboard maps to a function in the codebase.

### Live Running Algorithm Design

![Whiteboard Phase 2](https://github.com/user-attachments/assets/44eb70bc-c0cf-4dad-ad49-97eaabd2e489)

This diagram shows the live loop: MT5 tick → engine calculation → display update. The feedback arrow (data accumulates in rolling buffers) maps to the `times[]`, `prices_etf[]`, and `prices_gold[]` lists in the code.

### Final Model Architecture

![Whiteboard Final](https://github.com/user-attachments/assets/93938a91-de08-4a7d-8847-1c2ea020d8bb)

The complete system view showing how the two phases connect, where the reference anchor sits, and how the terminal is driven by the synthetic computation.

### Why Whiteboard-First?

Designing on a whiteboard before coding forces the builder to resolve questions about data flow, failure modes, and interface contracts before getting lost in implementation details. Specific design decisions made on the whiteboard that survived into the final code:

- The decision to use a **ratio-of-ratios** formula, not additive deltas
- The two-phase separation (pre-load vs. live loop)
- Using MT5 for gold tick data and Yahoo Finance for FX
- The 30-second USDINR cache to protect against rate limits
- The 15:30 IST anchor as the single fixed reference point

---

## 11. Installation and Setup

### System Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| OS | Windows 10 | Windows 11 |
| Python | 3.10 | 3.11+ |
| RAM | 4 GB | 8 GB |
| MetaTrader 5 | Any version | Latest (build 4000+) |
| Chrome | Any recent | Latest stable |
| ChromeDriver | Must match Chrome version exactly | Must match Chrome version exactly |
| Network | Stable broadband | Low-latency, stable |

### Step-by-Step Setup

**Step 1: Clone the repository**
```bash
git clone https://github.com/PC5518/gold-etf-postmarket-fair-value-engine.git
cd gold-etf-postmarket-fair-value-engine
```

**Step 2: Install Python dependencies**
```bash
pip install -r requirements.txt
```

Dependencies covered:
```
MetaTrader5    # MT5 Python bridge (Windows only)
selenium       # Browser automation for NSE scraping
pandas         # DataFrame handling for yfinance data
numpy          # Array operations for chart rendering
yfinance       # Yahoo Finance data (USDINR=X)
matplotlib     # Visual terminal rendering
```

**Step 3: Install and configure MetaTrader 5**
1. Download MT5 from [metatrader5.com](https://www.metatrader5.com/) or your broker's portal
2. Log into a live or demo account at a broker that provides XAUUSD (e.g., IC Markets, FP Markets, Pepperstone)
3. In MT5 Market Watch, right-click → `Show All` to ensure XAUUSD is visible and has data
4. Keep MT5 running in the background while the engine is active

**Step 4: Install ChromeDriver**
1. Check your Chrome version: Chrome menu → Help → About Google Chrome
2. Download the matching ChromeDriver from [googlechromelabs.github.io/chrome-for-testing/](https://googlechromelabs.github.io/chrome-for-testing/)
3. Place `chromedriver.exe` in your system PATH, or in the same directory as `run_terminal.py`

**Step 5: Run the engine**
```bash
python src/run_terminal.py
```

---

## 12. Startup Sequence Explained

When you run `python src/run_terminal.py`, this is the exact sequence of events:

```
$ python src/run_terminal.py
starting the terminal

=== SYSTEM BOOT: PRE-LOADING REFERENCE DATA ===

 [1/4] Contacting NSE (Selenium)...
        -> Chrome opens (non-headless, immediately minimized)
        -> Navigates to nseindia.com/get-quotes/equity?symbol=GOLDIETF
        -> Waits 5 seconds for JavaScript to render the price DOM
        -> Extracts LTP, iNAV, date string via XPath selectors
        NSE Data: LTP 187.45 | Date: '09-Dec-2025'

 [3/4] Fetching Gold Ref for 2025-12-09...
        -> Queries MT5: XAUUSD 1-min bars from 15:10 to 15:35 IST
        -> Finds last bar whose timestamp <= 15:30 IST
        Gold Ref @ 15:30: 2038.10

 [4/4] Fetching USDINR Ref for 2025-12-09 (YFinance)...
        -> Converts 15:30 IST to 10:00 UTC
        -> Downloads USDINR=X 1-min bars: 09:30-10:05 UTC
        -> Strips timezone awareness from DatetimeIndex
        -> Finds last bar whose timestamp <= 10:00 UTC
        USDINR Ref @ 15:30: 84.231

>>> ENGINE READY: Date=2025-12-09 | ETF=187.45 | GoldRef=2038.10 | FxRef=84.231

[1 second readability pause]

[AnsCom Terminal window opens]
[Live loop begins - terminal updates in real-time]
[Press Ctrl+C to shut down]
```

---

## 13. Versioning and Bug Fixes (v4.4 Changelog)

Version 4.4 specifically addressed four Windows deployment bugs discovered during live testing:

### Bug 1: `UnicodeEncodeError` — Rupee Symbol Crashing Windows Console

**Root cause:** Python's `print()` on Windows uses the system default code page (`cp1252`). The Rupee sign `₹` (Unicode U+20B9, introduced in Unicode 6.0) is not in `cp1252`, causing `UnicodeEncodeError: 'charmap' codec can't encode character '\u20b9'` on every price log line.

**Fix:** `clean_console_str()` — encodes to ASCII with `errors='ignore'` before any `print()` call. The `₹` is dropped silently from console output. Matplotlib rendering is unaffected since it uses font-based Unicode rendering independent of the console encoding.

### Bug 2: `ZeroDivisionError` in Engine or Premium Calculation

**Root cause:** If NSE scraping returned "0" for the price (failed scrape), `float("0") = 0.0`. In `SyntheticETFEngine.__init__`, computing `etf_ref / nav_ref` with `nav_ref = 0` raises `ZeroDivisionError`. Similarly in `calculate()` if `gold_ref = 0`.

**Fix:** `if nav_ref > 0` guard before premium calculation. `if self.gold_ref == 0 or self.fx_ref == 0` guard before division in `calculate()`. Non-zero fallback `etf_close = 1.0` if NSE parse fails ensures initialization never receives zero.

### Bug 3: NSE "As of DATE" String Failing Date Parse

**Root cause:** NSE's date DOM element sometimes renders as `"As of 09-Dec-2025 15:30:00"`. `datetime.strptime(raw, "%d-%b-%Y")` raises `ValueError` on the prefix characters, falling through to today's date — meaning historical data would be fetched for the *wrong* date. On weekends, MT5 returns empty data for that date.

**Fix:** Regex extraction `r"(\d{2}-[a-zA-Z]{3}-\d{4})"` finds the DD-MMM-YYYY pattern anywhere in the string. This is robust to any prefix or suffix NSE adds.

### Bug 4: yfinance Returns Timezone-Aware `DatetimeIndex`

**Root cause:** `yf.download()` with intraday intervals returns `DatetimeIndex` with `tz=UTC` attached. Comparing with a naive `datetime` object raises `TypeError: can't compare offset-naive and offset-aware datetimes`.

**Fix:** After download, check `if idx.tz is not None: data.index = idx.tz_convert(None)` to produce naive UTC timestamps, making all comparisons consistent.

---

## 14. Engineering Decisions and Tradeoffs

### Decision 1: Single-Process, Synchronous Architecture

The engine runs everything in one Python process with a synchronous loop — no `threading`, no `asyncio`, no multiprocessing.

**Pro:** Simple to reason about, debug, and maintain. No race conditions. No deadlocks. Failure modes are linear and predictable.

**Con:** The 30-second Yahoo Finance refresh blocks the main loop for ~500ms while the HTTP request completes. During this 500ms, MT5 ticks accumulate but the UI does not update.

**Tradeoff accepted:** For a solo monitoring tool with a 100ms UI refresh rate, a 500ms freeze every 30 seconds is acceptable. A production-grade version would move the YF refresh to a `threading.Thread` with a `threading.Lock`-protected shared variable.

### Decision 2: Matplotlib for the Terminal UI

**Pro:** No additional UI framework required. Matplotlib is already a dependency for charting, so using it for the terminal avoids adding PyQt, tkinter, or a web framework. Animations, text updates, and line charts are all natively supported.

**Con:** Matplotlib is not designed for real-time terminal applications. The `plt.pause()` mechanism and `LineCollection` redraw approach work but impose CPU overhead. At 10Hz with two animated line charts and a text panel, CPU usage can reach 20–40% on older hardware.

**Alternatives considered:** `rich` (pure console terminal), `PyQtGraph` (high-performance Qt charting). Not pursued to keep the dependency footprint minimal.

### Decision 3: 15:30 IST as the Reference Anchor

The most natural choice because: it is the official NSE closing price, the last price at which real trades occurred, and represents the market's collective valuation at the most recent close. The premium/discount captured at this moment is the most relevant baseline for off-hours analysis.

### Decision 4: `statistics.stdev` Over `numpy.std` for Volatility

`statistics.stdev` computes **sample standard deviation** (denominator N−1), which is statistically correct when treating the rolling window as a sample of the underlying volatility process, not the complete population. `numpy.std` defaults to population std (denominator N). For a window of 150, this is a ~0.3% difference — small but principled.

---

## 15. Potential Extensions and Future Work

The engine is architecturally clean enough that several natural extensions are straightforward:

**Multi-ETF support:** Add `GOLDBEES`, `NIPGOLD`, `AXISGOLD`, etc. The `SyntheticETFEngine` class is generic — only the NSE symbol and reference triplet need to change per ETF.

**Continuous price recording:** Add a CSV/SQLite writer in the live loop logging `(timestamp, synthetic_price, gold_now, fx_now, vol_bps)`. This builds a continuous off-hours price series that does not currently exist for Indian gold ETFs anywhere.

**Next-open gap estimator:** Display an explicit "Expected Gap at Open %" in a prominent panel, along with a historical confidence interval derived from past overnight-to-open tracking error measurements.

**Alert system:** When synthetic ETF moves >X% from close, or vol crosses a threshold, trigger a desktop notification via `plyer` or a Telegram alert via the bot API.

**Headless mode:** Run without Matplotlib GUI (e.g., on a server or Raspberry Pi), outputting to a `rich` console table or a simple structured log. Useful for overnight monitoring without keeping a display active.

**Backtesting the model accuracy:** Compare the synthetic level at various overnight times against the next day's NSE open price. Measure mean absolute error and R² of the synthetic vs. actual open. This would empirically validate (or quantify the limitations of) the proportional returns assumption.

**MT5 timezone normalization:** Make the gold reference fetch timezone-aware by querying the broker's server timezone from MT5 and adjusting accordingly, eliminating the current ±1 bar ambiguity on brokers with non-UTC+0 server time.

---

## 16. Demo & Tutorial

**Project Demo (YouTube):** [_DEMO_](https://www.youtube.com/watch?v=Pi3xI19eqHs)
`https://www.youtube.com/watch?v=Pi3xI19eqHs`

The demo walks through:

- How the engine fetches data (NSE + MT5 + Yahoo Finance)
- How the synthetic ETF price is computed tick-by-tick
- How to read each panel in the ANSCom Terminal UI
- Live behavior during periods of active gold price movement

---

## 18. Research Paper

This project is formally documented and published on Zenodo with a permanent DOI:

**AnsCom Quantitative Suite: POST-MARKET Gold ETF Fair-Value Engine**

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18185485.svg)](https://doi.org/10.5281/zenodo.18185485)

The paper covers: theoretical motivation, full model derivation, data pipeline specification, system architecture, empirical observations from live sessions, and discussion of model limitations and extensions.

**Citation (BibTeX):**
```bibtex
@misc{pc5518_goldietf_engine_2025,
  author    = {PC5518},
  title     = {AnsCom Quantitative Suite: POST-MARKET Gold ETF Fair-Value Engine},
  year      = {2025},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.18185485},
  url       = {https://doi.org/10.5281/zenodo.18185485}
}
```

---

## 19. Contributing

Contributions are welcome across all areas: model improvements, data source upgrades, UI enhancements, bug fixes, and documentation.

### Most Common Maintenance Need: NSE XPath Updates

NSE periodically updates their website frontend, invalidating the XPath selectors used in `get_etf_data_selenium()`. When this happens, the scraper silently returns "0" for the ETF price — the most common failure mode of this engine.

**To find new XPaths:**
1. Open Chrome and navigate to `https://www.nseindia.com/get-quotes/equity?symbol=GOLDIETF`
2. Wait for the page to fully load (watch for prices to appear — JavaScript render)
3. Right-click on the price element → `Inspect`
4. In DevTools, right-click the highlighted HTML element → `Copy → Copy XPath`
5. Paste the new XPath into `get_etf_data_selenium()` in `run_terminal.py`
6. Use `find_goldietf_params.py` to test XPaths without running the full engine

The selectors to update are clearly commented in the source:

```python
# XPath may change — check and update before execution.
# Go to NSE's webpage, inspect the element, copy XPath, paste here.
inav = driver.find_element(By.XPATH, '//*[@id="dashboard"]/...').text
close_price = driver.find_element(By.XPATH, '//*[@id="midBody"]/...').text
raw_date = driver.find_element(By.XPATH, '//*[@id="midBody"]/...').text
```

### Contribution Workflow

```bash
# 1. Fork the repository on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/gold-etf-postmarket-fair-value-engine.git

# 3. Create a feature branch with a descriptive name
git checkout -b fix/nse-xpath-update-dec2025

# 4. Make changes and test locally
python src/run_terminal.py

# 5. Commit with a clear, conventional commit message
git commit -m "fix: update NSE XPath selectors after frontend redesign (Dec 2025)"

# 6. Push and open a Pull Request
git push origin fix/nse-xpath-update-dec2025
```

### Opening Issues

For bugs, include: Python version and OS, MT5 version and broker name, full traceback, and a screenshot of the AnsCom Terminal if relevant.

For XPath breakage specifically, include the date you noticed failure and the new XPath you found (if discovered). This helps future maintainers track when NSE updates occur.

---

## License

Released under the MIT License. See [LICENSE](LICENSE) for full terms.

---

Built by [PC5518](https://github.com/PC5518) · AnsCom Quantitative Suite · Gold ETF Post-Market Fair-Value Engine · v4.4

*If this project helped you — star the repo, cite the paper, or open a pull request.*

[Research Paper](https://doi.org/10.5281/zenodo.18185485) · [Demo](https://www.youtube.com/watch?v=Pi3xI19eqHs) · [GitHub](https://github.com/PC5518/gold-etf-postmarket-fair-value-engine)
