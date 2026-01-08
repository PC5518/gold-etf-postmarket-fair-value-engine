# AnsCom Quantitative Suite-> POST-MARKET Gold ETF Fair-Value Engine  [FINANCIAL MODELLING] (A market-structure repair system)

## 📄 Access the Research Paper: https://doi.org/10.5281/zenodo.18185485
### AnsCom Terminal – Real-Time Synthetic Price for GOLDIETF
> A live terminal that approximates the **ICICI Prudential Gold ETF (GOLDIETF)** price **after NSE market hours**, using XAUUSD and USDINR in real-time.

---
## System Design:
Overview (powered by Mermaid charts)
<img width="1151" height="316" alt="image" src="https://github.com/user-attachments/assets/5f46b70a-c371-4e48-b1f5-4486b6fdc55d" />
![WhatsApp Image 2025-12-09 at 19 12 38_2dbe13b1](https://github.com/user-attachments/assets/3d89047d-4ec2-4683-842a-bfa0ba3d0175)




## 🎥 Demo & Tutorial

- **Project Demo (YouTube)**:[ _DEMO: ](https://www.youtube.com/watch?v=Pi3xI19eqHs)


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
SyntheticETF_live =
    ETF_close
    × (XAUUSD_live / XAUUSD_ref_15:30)
    × (USDINR_live / USDINR_ref_15:30)



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

## 🏛 System Design – (ROUGH SYSTEM) Whiteboard → Code    [Basically, my logic is presented below; the way i thought initially to make the program]

This project was first designed completely on a **system-design board** and then turned into code.  
Each diagram has a direct mapping to the Python modules and functions.

<img width="1783" height="1048" alt="image" src="https://github.com/user-attachments/assets/47fed271-e80b-4cd6-a03d-d018f0b81e18" />
<img width="1425" height="688" alt="image" src="https://github.com/user-attachments/assets/44eb70bc-c0cf-4dad-ad49-97eaabd2e489" />
<img width="1557" height="845" alt="image" src="https://github.com/user-attachments/assets/93938a91-de08-4a7d-8847-1c2ea020d8bb" />

FINAL OUTPUT :<img width="1919" height="938" alt="image" src="https://github.com/user-attachments/assets/0e4e96bc-4792-4895-9f3d-5fac7253af48" />
# Clone the repository
git clone https://github.com/PC5518/gold-etf-postmarket-fair-value-engine.git

# Install dependencies
pip install -r requirements.txt

# Run the engine (Ensure MT5 is open)
python src/run_terminal.py
---

### 1. Pre-Data Loading Engine (Reference Snapshot)

```text
Status: BEFORE the live loop starts
Goal: Build a stable reference state at India close (15:30 IST)
