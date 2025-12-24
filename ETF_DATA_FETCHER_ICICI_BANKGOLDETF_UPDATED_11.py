# ============================================
#  ANSCom Terminal v4.4 - Windows Fix
#  Fixes: Unicode '₹' Crash, ZeroDivisionError, "As of DATE" refining
# ============================================

import time
import statistics
from datetime import datetime, timedelta, timezone
import collections
import warnings
import re   # IMPORTED IT TO IGNORE NATIONAL STOCK EXCHANGE'S WEBSITE "As of DATE" refining
import sys

# Suppress YFinance/Pandas FutureWarnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# External Libraries
import MetaTrader5 as mt5
from selenium import webdriver
from selenium.webdriver.common.by import By
import pandas as pd
import numpy as np
import yfinance as yf

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
import matplotlib.dates as mdates
from matplotlib.collections import LineCollection

# ==================================================
#  THEME & STYLING CONFIGURATION
# ==================================================

COLOR_BG = '#050505'       # Ultra Dark
COLOR_PANEL = '#111111'    # Panel Background
COLOR_GRID = '#1A1A1A'     # Subtle Grid
COLOR_TEXT_W = '#FFFFFF'   # Neutral White
COLOR_TEXT_G = '#888888'   # Label Grey
COLOR_UP = '#00FF41'       # Neon Green
COLOR_DN = '#FF2A00'       # Neon Red
COLOR_SMA = '#FFC400'      # Gold/Yellow

FONT_MONO = 'Consolas'

def apply_anscom_theme():
    plt.rcParams['figure.facecolor'] = COLOR_BG
    plt.rcParams['axes.facecolor'] = COLOR_BG
    plt.rcParams['axes.edgecolor'] = COLOR_GRID
    plt.rcParams['axes.labelcolor'] = COLOR_TEXT_G
    plt.rcParams['xtick.color'] = COLOR_TEXT_G
    plt.rcParams['ytick.color'] = COLOR_TEXT_G
    plt.rcParams['grid.color'] = COLOR_GRID
    plt.rcParams['text.color'] = COLOR_TEXT_W
    plt.rcParams['font.family'] = FONT_MONO

def add_branding_header(fig):
    brand_box = FancyBboxPatch(
        (0.005, 0.94), width=0.12, height=0.05,
        boxstyle="round,pad=0.01",
        facecolor=COLOR_PANEL, edgecolor='#333333',
        transform=fig.transFigure, clip_on=False, zorder=10
    )
    fig.patches.append(brand_box)
    
    fig.text(0.015, 0.955, 'AnsCom', transform=fig.transFigure,
             fontsize=12, weight='bold', color=COLOR_TEXT_W, zorder=11)
    fig.text(0.065, 0.955, 'Terminal', transform=fig.transFigure,
             fontsize=12, weight='bold', color=COLOR_SMA, zorder=11)

    fig.text(0.5, 0.96, "ICICI PRUDENTIAL GOLD ETF AFTER MARKET HOURS RUNNING PRICE", 
             transform=fig.transFigure, ha='center', va='center',
             fontsize=16, weight='bold', color=COLOR_SMA, zorder=11)

# ============================
#  ⭐ PRE-LOADING ENGINE ⭐
# ============================

def clean_console_str(text):
    """Removes non-ASCII chars like ₹ to prevent Windows console crashes"""
    return str(text).encode('ascii', 'ignore').decode('ascii').strip()

def get_etf_data_selenium(symbol="GOLDIETF"):
    print(" [1/4] Contacting NSE (Selenium)...")
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless") 
    driver = webdriver.Chrome(options=options)
    
    try:
        url = f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}"
        driver.get(url)
        driver.minimize_window()
        time.sleep(5) 

        # Grab Data
        try:
            inav = driver.find_element(By.XPATH, '//*[@id="dashboard"]/div/div/div[2]/div/div[2]/div[5]/div/div/div[2]').text
        except: inav = "0"
            
        try:
            close_price = driver.find_element(By.XPATH, '//*[@id="midBody"]/div[2]/div[2]/div/div[1]/div/div[1]/span[2]').text
        except: close_price = "0"
            
        try:
            raw_date = driver.find_element(By.XPATH, '//*[@id="midBody"]/div[2]/div[1]/div[2]/div[2]/div').text
        except: 
            raw_date = datetime.now().strftime("%d-%b-%Y")
        
        # [FIX] Sanitize strings before printing to avoid charmap error
        safe_price = clean_console_str(close_price)
        safe_date = clean_console_str(raw_date)
        
        print(f"       NSE Data: LTP {safe_price} | Date: '{safe_date}'")
        return inav, close_price, raw_date
        
    except Exception as e:
        # [FIX] Handle logging error safely
        safe_err = clean_console_str(e)
        print(f"       NSE Error: {safe_err}")
        return "0", "0", datetime.now().strftime("%d-%b-%Y")
    finally:
        driver.quit()

def parse_nse_date(raw):
    try:
        match = re.search(r"(\d{2}-[a-zA-Z]{3}-\d{4})", str(raw))
        if match:
            clean_date_str = match.group(1)
            dt = datetime.strptime(clean_date_str, "%d-%b-%Y")
            return dt.date().isoformat()
        
        dt = datetime.strptime(str(raw).strip(), "%d-%b-%Y %H:%M:%S")
        return dt.date().isoformat()
    except Exception as e:
        # Fallback to today if parsing fails
        return datetime.now().strftime("%Y-%m-%d")

def get_gold_1530_mt5(india_date_str, symbol="XAUUSD"):
    print(f" [3/4] Fetching Gold Ref for {india_date_str}...")
    TARGET_HOUR = 15
    TARGET_MIN = 30
    
    try:
        y, m, d = map(int, india_date_str.split("-"))
        anchor = datetime(y, m, d, TARGET_HOUR, TARGET_MIN)
        start = anchor - timedelta(minutes=20)
        end = anchor + timedelta(minutes=5)

        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, end)

        if rates is None or len(rates) == 0:
            print("       No Gold data found.")
            return None

        anchor_ts = int(anchor.timestamp())
        best = None
        for r in rates:
            if int(r["time"]) <= anchor_ts:
                if best is None or int(r["time"]) > int(best["time"]):
                    best = r

        if best:
            price = float(best["close"])
            print(f"       Gold Ref @ 15:30: {price}")
            return price
        return None
    except Exception as e:
        print(f"       Gold Hist Error: {e}")
        return None

def get_usdinr_at_1530_yf(india_date_str):
    print(f" [4/4] Fetching USDINR Ref for {india_date_str} (YFinance)...")
    
    try:
        y, m, d = map(int, india_date_str.split("-"))
        ist = timezone(timedelta(hours=5, minutes=30))
        anchor_ist = datetime(y, m, d, 15, 30, tzinfo=ist)
        anchor_utc = anchor_ist.astimezone(timezone.utc).replace(tzinfo=None)

        start_utc = anchor_utc - timedelta(minutes=30)
        end_utc   = anchor_utc + timedelta(minutes=5)

        data = yf.download("USDINR=X", start=start_utc, end=end_utc, interval="1m", progress=False, auto_adjust=True)

        if data.empty:
            print("       No USDINR data found.")
            return None

        idx = data.index
        if isinstance(idx, pd.DatetimeIndex) and idx.tz is not None:
            data.index = idx.tz_convert(None)

        data = data.sort_index()
        data_le = data[data.index <= anchor_utc]

        if not data_le.empty:
            row = data_le.iloc[-1]
        else:
            diffs = (data.index - anchor_utc).to_series().abs()
            row = data.loc[diffs.idxmin()]

        price = float(row["Close"].iloc[0] if isinstance(row["Close"], pd.Series) else row["Close"])
        print(f"       USDINR Ref @ 15:30: {price}")
        return price

    except Exception as e:
        print(f"       USDINR Hist Error: {e}")
        return None

# ============================
#  LIVE DATA & ENGINE
# ============================

class USDINRSource:
    def __init__(self):
        self.last_price = 84.0
        self.last_update = 0

    def get_mid(self):
        now = time.time()
        if now - self.last_update > 30: 
            try:
                d = yf.download("USDINR=X", period="1d", interval="1m", progress=False, auto_adjust=True)
                if not d.empty:
                    val = d['Close'].iloc[-1]
                    self.last_price = float(val.iloc[0] if isinstance(val, pd.Series) else val)
                    self.last_update = now
            except: pass
        return self.last_price

class SyntheticETFEngine:
    def __init__(self, etf_ref, gold_ref, fx_ref, nav_ref):
        self.etf_ref = etf_ref    
        self.gold_ref = gold_ref  
        self.fx_ref = fx_ref      
        self.nav_ref = nav_ref
        
        # [FIX] Zero Division Check
        if nav_ref > 0:
            self.premium_close = (etf_ref / nav_ref) - 1.0 
        else:
            self.premium_close = 0.0

    def calculate(self, gold_now, fx_now):
        # [FIX] Zero Division Check
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

def calc_vol(prices_list):
    if len(prices_list) < 10: return 0.0
    arr = list(prices_list)[-150:] 
    
    # [FIX] Zero Division Protection
    returns = []
    for i in range(1, len(arr)):
        if arr[i-1] != 0:
            r = (arr[i] - arr[i-1]) / arr[i-1]
            returns.append(r)
        else:
            returns.append(0.0)
            
    if not returns: return 0.0
    return statistics.stdev(returns) * 10000

# ============================================
#  HELPER: MULTI-COLOR PLOTTING
# ============================================

def plot_multicolor_line(ax, dates, values):
    """Draws a line that is Green when going Up, Red when going Down"""
    if len(dates) < 2: return

    num_dates = mdates.date2num(dates)
    points = np.array([num_dates, values]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    colors = []
    for i in range(1, len(values)):
        if values[i] >= values[i-1]:
            colors.append(COLOR_UP)
        else:
            colors.append(COLOR_DN)
    
    lc = LineCollection(segments, colors=colors, linewidths=1.5)
    ax.add_collection(lc)
    ax.autoscale_view()
    ax.set_xlim(min(num_dates), max(num_dates))
    
    mn, mx = min(values), max(values)
    pad = (mx - mn) * 0.1 if mx != mn else 0.01
    ax.set_ylim(mn - pad, mx + pad)

# ============================================
#  HELPER: COLOR TRACKING FOR TEXT
# ============================================

class MetricTracker:
    def __init__(self):
        self.prev_values = {}

    def get_color_and_arrow(self, key, current_val):
        prev = self.prev_values.get(key, current_val)
        self.prev_values[key] = current_val
        
        if current_val > prev + 0.0000001:
            return COLOR_UP, "▲"
        elif current_val < prev - 0.0000001:
            return COLOR_DN, "▼"
        else:
            return COLOR_TEXT_W, " "

# ============================================
#  VISUAL TERMINAL MAIN LOOP
# ============================================

def run_terminal(gold_symbol="XAUUSD"):
    if not mt5.initialize():
        print("MT5 Init Failed. Ensure MetaTrader 5 is running.")
        return
    
    if not mt5.symbol_select(gold_symbol, True):
        print(f"Symbol {gold_symbol} not found in MT5")
        return

    print("\n=== SYSTEM BOOT: PRE-LOADING REFERENCE DATA ===")
    
    # 1. Get NSE Data
    inav_str, close_str, raw_date_str = get_etf_data_selenium("GOLDIETF")
    
    # 2. Parse Numbers
    try:
        etf_close = float(str(close_str).replace(',', '').replace('₹',''))
        inav_val = float(str(inav_str).replace(',', '').replace('₹',''))
    except:
        print("       [Error] Could not parse prices. Defaulting to 1.0 to prevent crash.")
        etf_close = 1.0 # Non-zero fallback
        inav_val = 1.0
    
    if etf_close == 0: etf_close = 1.0 # Safety Net
    
    # 3. Parse Date 
    ref_date_iso = parse_nse_date(raw_date_str)
    
    # 4. Get Reference Prices
    gold_ref = get_gold_1530_mt5(ref_date_iso, gold_symbol)
    fx_ref = get_usdinr_at_1530_yf(ref_date_iso)
    
    # Fallbacks
    if gold_ref is None:
        print("       [Info] Using Current Tick as Gold Ref (Fallback)")
        tick = mt5.symbol_info_tick(gold_symbol)
        gold_ref = tick.ask if tick else 2650.0
    if fx_ref is None:
        print("       [Info] Using Default 84.50 as Fx Ref (Fallback)")
        fx_ref = 84.50 

    print(f"\n>>> ENGINE READY: Date={ref_date_iso} | ETF={etf_close} | GoldRef={gold_ref} | FxRef={fx_ref}")
    time.sleep(1)

    engine = SyntheticETFEngine(etf_close, gold_ref, fx_ref, inav_val)
    usd_source = USDINRSource()
    tracker = MetricTracker() 

    apply_anscom_theme()
    plt.ion()
    fig = plt.figure(figsize=(14, 9), constrained_layout=True)
    add_branding_header(fig)
    
    # GRID SETUP
    gs = gridspec.GridSpec(2, 3, figure=fig, height_ratios=[0.25, 0.75], width_ratios=[1, 1, 0.8])
    
    # TOP ROW
    ax_price = fig.add_subplot(gs[0, 0])
    ax_spot  = fig.add_subplot(gs[0, 1])
    ax_info  = fig.add_subplot(gs[0, 2])
    
    # BOTTOM ROW
    ax_chart_etf  = fig.add_subplot(gs[1, 0])
    ax_chart_gold = fig.add_subplot(gs[1, 1])
    ax_data_fact  = fig.add_subplot(gs[1, 2])

    for ax in [ax_price, ax_spot, ax_info, ax_data_fact]:
        ax.axis('off')

    ax_chart_etf.set_title(f"Synthetic ETF (INR)", color=COLOR_TEXT_W, fontsize=10, loc='left', pad=10)
    ax_chart_gold.set_title(f"{gold_symbol} Spot (USD)", color=COLOR_TEXT_W, fontsize=10, loc='left', pad=10)
    
    times = []
    prices_etf = []
    prices_gold = []
    
    txt_big_price = ax_price.text(0.5, 0.5, "---.--", fontsize=38, ha='center', va='center', weight='bold', color=COLOR_TEXT_W)
    txt_spot_mid  = ax_spot.text(0.5, 0.4, "---.--", fontsize=18, ha='center', va='center', weight='bold', color=COLOR_TEXT_W)
    
    last_ui_update = 0

    try:
        while True:
            # --- HIGH FREQ DATA ---
            tick = mt5.symbol_info_tick(gold_symbol)
            if tick is None: 
                time.sleep(0.1)
                continue
            
            bid, ask = tick.bid, tick.ask
            mid_gold = (bid + ask) / 2.0
            fx_val = usd_source.get_mid()

            # --- ENGINE CALC ---
            res = engine.calculate(mid_gold, fx_val)
            synth_price = res['synthetic']
            
            # --- STORAGE ---
            now = datetime.now()
            times.append(now)
            prices_etf.append(synth_price)
            prices_gold.append(mid_gold)

            # --- UI UPDATE ---
            if time.time() - last_ui_update > 0.1:
                
                # 1. Update Big Price
                col, arrow = tracker.get_color_and_arrow("synth", synth_price)
                txt_big_price.set_text(f"₹ {arrow}{synth_price:.2f}")
                txt_big_price.set_color(col)
                
                # 2. Update Spot
                col_g, _ = tracker.get_color_and_arrow("spot_mid", mid_gold)
                txt_spot_mid.set_text(f"$ {mid_gold:.2f}")
                txt_spot_mid.set_color(col_g)
                
                # 3. Update Charts
                for ax in [ax_chart_etf, ax_chart_gold]:
                    [c.remove() for c in ax.collections] 
                
                plot_multicolor_line(ax_chart_etf, times, prices_etf)
                plot_multicolor_line(ax_chart_gold, times, prices_gold)
                
                ax_chart_etf.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                ax_chart_gold.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

                # 4. Data Factory
                ax_data_fact.clear()
                ax_data_fact.axis('off')
                
                gold_pct = res['gold_return'] * 100
                fx_pct = res['fx_return'] * 100
                prem_vs_close = (synth_price / etf_close - 1) * 100 if etf_close != 0 else 0
                vol_etf = calc_vol(prices_etf)
                
                y_pos = 0.95
                x_lbl = 0.05
                x_val = 0.60
                line_h = 0.06
                
                def print_row(label, val_fmt, key, is_header=False):
                    nonlocal y_pos
                    if is_header:
                        ax_data_fact.text(x_lbl, y_pos, label, color=COLOR_SMA, weight='bold', fontsize=10)
                        y_pos -= (line_h * 1.2)
                        return

                    ax_data_fact.text(x_lbl, y_pos, label, color=COLOR_TEXT_G, fontsize=9, fontname=FONT_MONO)
                    
                    if key:
                        try:
                            numeric_part = str(val_fmt).replace('₹', '').replace('$', '').strip()
                            numeric_part = numeric_part.replace('%', '').strip()
                            numeric_val = float(numeric_part)
                            c, a = tracker.get_color_and_arrow(key, numeric_val)
                            disp_str = f"{a} {val_fmt}"
                        except:
                            c = COLOR_TEXT_W
                            disp_str = str(val_fmt)
                    else:
                        c = COLOR_TEXT_W
                        disp_str = str(val_fmt)
                        
                    ax_data_fact.text(x_val, y_pos, disp_str, color=c, fontsize=9, weight='bold', fontname=FONT_MONO)
                    y_pos -= line_h

                print_row("1. ENGINE OUTPUTS", "", None, True)
                print_row("Synth Value", f"₹ {synth_price:.2f}", "synth")
                print_row("ETF Ref (NSE)", f"₹ {etf_close:.2f}", None)
                print_row("Gold Ref", f"$ {gold_ref:.2f}", None)
                print_row("USD/INR Ref", f"{fx_ref:.3f}", None)
                
                y_pos -= 0.02
                
                print_row("2. LIVE DRIVERS", "", None, True)
                print_row("Gold Now", f"$ {mid_gold:.2f}", "gold_n")
                print_row("USD/INR Now", f"{fx_val:.3f}", "fx_n")
                print_row("Gold Chg %", f"{gold_pct:+.3f}%", "g_pct")
                print_row("USD/INR Chg %", f"{fx_pct:+.3f}%", "f_pct")
                
                y_pos -= 0.02
                
                print_row("3. PREMIUM & RISK", "", None, True)
                print_row("vs Close %", f"{prem_vs_close:+.2f}%", "p_cls")
                print_row("Vol (bps)", f"{vol_etf:.2f}", "vol")
                print_row("Ref Date", f"{ref_date_iso}", None)

                last_ui_update = time.time()

            plt.pause(0.001)

    except KeyboardInterrupt:
        print("Shutdown.")
    finally:
        mt5.shutdown()
        plt.close('all')

if __name__ == "__main__":
    run_terminal("XAUUSD")

