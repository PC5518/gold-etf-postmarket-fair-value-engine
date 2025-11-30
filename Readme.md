# POST-MARKET Gold ETF Fair-Value Engine  
### ANSCom Terminal – Real-Time Synthetic Price for GOLDIETF

> A live terminal that approximates the **ICICI Prudential Gold ETF (GOLDIETF)** price **after NSE market hours**, using XAUUSD and USDINR in real-time.

---

## 🎥 Demo & Tutorial

- **Project Demo (YouTube)**: _coming soon_  
  👉 

`https://www.youtube.com/watch?v=Pi3xI19eqHs`

- The demo will walk through:
  - How the engine fetches data (NSE + MT5 + Yahoo Finance)
  - How the synthetic ETF price is computed
  - How to read each panel in the ANSCom Terminal UI

---

## 🧠 Problem Statement

Indian Gold ETFs like **GOLDIETF** trade only during **NSE market hours**.  
However, **gold (XAUUSD)** and **USDINR** move 24×7 in global markets.

Traders and investors often want to know:

> “If NSE was open right now, approximately where would GOLDIETF be trading?”

This project builds a **real-time proxy fair-value engine** that answers exactly that, by:

1. Fixing a **reference point** at **15:30 IST** (Indian close)  
2. Streaming live **XAUUSD** and **USDINR** prices  
3. Scaling the last ETF close using proportional returns in gold and FX  
4. Displaying everything in a **live visual terminal** with volatility, premium and driver breakdowns.

---

## 🧮 Core Quant Model

The synthetic ETF level is approximated by:

\[
\text{ETF}_\text{live} =
\text{ETF}_\text{close}
\times
\frac{\text{XAUUSD}_\text{live}}{\text{XAUUSD}_\text{ref(15:30 IST)}}
\times
\frac{\text{USDINR}_\text{live}}{\text{USDINR}_\text{ref(15:30 IST)}}
\]

Where:

- **ETF_close** – last GOLDIETF close from NSE  
- **XAUUSD_ref(15:30 IST)** – gold price at India close, from MT5 history  
- **USDINR_ref(15:30 IST)** – FX rate at India close, from yfinance history  
- **XAUUSD_live, USDINR_live** – current prices (streamed live)

The engine also tracks:

- **Gold return** vs 15:30 ref  
- **FX return** vs 15:30 ref  
- **Premium vs last close** in %  
- **Volatility (bps)** from recent synthetic ETF ticks  

All of this is displayed in the **ANSCom Terminal** interface.

---

## 🏛 System Design – Whiteboard → Code

This project was first designed completely on a **system-design board** and then turned into code.  
Each diagram has a direct mapping to the Python modules and functions.

> Put your **three hand-drawn design screenshots** in `docs/images/` and link them as below.

---

### 1. Pre-Data Loading Engine (Reference Snapshot)

```text
Status: BEFORE the live loop starts
Goal: Build a stable reference state at India close (15:30 IST)
