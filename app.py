import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# 1. 網頁基本設定
st.set_page_config(page_title="全球資產管理與策略平台", layout="wide")

# --- 核心功能：數據抓取 ---
@st.cache_data(ttl=3600)
def get_market_data():
    try:
        fx_data = yf.download("TWD=X", period="1d", progress=False)
        fx = float(fx_data['Close'].iloc[-1])
        gold_data = yf.download("GOLDTWD=X", period="1d", progress=False)
        gold_gram_twd = float(gold_data['Close'].iloc[-1]) / 31.1035
        return fx, gold_gram_twd
    except:
        return 32.5, 2800.0 

current_fx_rate, current_gold_price = get_market_data()

# --- 分析函式 ---
def get_stock_analysis(ticker):
    if ticker == "GOLD_PASSBOOK": return "N/A", "N/A", current_gold_price, None
    try:
        df = yf.download(ticker, period="6mo", progress=False, auto_adjust=True)
        if df.empty: return "讀取失敗", "數據不足", 0, None
        close_series = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
        current_p = float(close_series.iloc[-1])
        ma20 = close_series.rolling(window=20).mean()
        t20 = "📈 站上月線" if current_p > ma20.iloc[-1] else "📉 跌破月線"
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=close_series, name="收盤價", line=dict(color='white', width=1)))
        fig.add_trace(go.Scatter(x=df.index, y=ma20, name="20MA", line=dict(color='#ff9900', width=2)))
        fig.update_layout(height=200, template="plotly_dark", margin=dict(l=5, r=5, t=5, b=5))
        return t20, "", current_p, fig
    except: return "錯誤", "", 0, None

# --- 多分頁選單 ---
st.sidebar.title("🧭 選單")
page = st.sidebar.radio("選擇功能", ["📊 資產現況與 AI 診斷", "🎯 4%法則策略模擬"])

# ------------------------------------------------------------------
# 分頁 1：資產現況與 AI 診斷 (保留原邏輯)
# ------------------------------------------------------------------
if page == "📊 資產現況與 AI 診斷":
    st.title("🚀 全球資產執行平台")
    with st.sidebar:
        st.header("💰 現有庫存設定")
        cash_on_hand = st.number_input("手頭現金 (萬)", value=100.0)
        monthly_investment = st.number_input("每月投入 (萬)", value=5.0)
        target_ratios = {}
        holdings_qty = {}
        for ticker in ["2330.TW", "TLT", "GOLD_PASSBOOK"]:
            st.markdown(f"---")
            target_ratios[ticker] = st.slider(f"{ticker} 目標 %", 0, 100, 25, key=f"t_{ticker}")
            holdings_qty[ticker] = st.number_input(f"{ticker} 庫存", min_value=0.0, key=f"q_{ticker}")

    portfolio_data = []
    total_val = 0
    for ticker in ["2330.TW", "TLT", "GOLD_PASSBOOK"]:
        t20, t60, last_p, chart = get_stock_analysis(ticker)
        is_us = ".TW" not in ticker and ticker != "GOLD_PASSBOOK"
        v = (holdings_qty[ticker] * last_p * (current_fx_rate if is_us else 1)) / 10000 if ticker != "GOLD_PASSBOOK" else (holdings_qty[ticker] * last_p) / 10000
        total_val += v
        portfolio_data.append({"標的": ticker, "市值(萬)": v, "目標%": target_ratios[ticker], "20MA": t20, "現價": last_p, "is_us": is_us, "chart": chart})

    actual_total = cash_on_hand + total_val
    st.metric("當前總資產 (萬)", f"{actual_total:.2f}")
    st.plotly_chart(px.pie(pd.DataFrame([{"標的": i["標的"], "市值": i["市值(萬)"]} for i in portfolio_data] + [{"標的": "現金", "市值": cash_on_hand}]), values='市值', names='標的', hole=0.4), use_container_width=True)

# ------------------------------------------------------------------
# 分頁 2：4% 法則策略模擬
# ------------------------------------------------------------------
elif page == "🎯 4%法則策略模擬":
    st.title("🎯 4% 法則：財富自由路徑模擬")
    st.info("根據 4% 法則，你的退休金應為『年支出』的 25 倍。")

    col_input, col_result = st.columns([1, 2])

    with col_input:
        st.subheader("⚙️ 生活開銷設定")
        target_monthly_spend = st.number_input("退休後每月生活費 (萬)", value=10.0, step=0.5)
        # 計算 4% 法則目標金額 (年支出的 25 倍)
        fire_target_amount = target_monthly_spend * 12 * 25
        
        st.success(f"📌 您的退休目標金額：**{fire_target_amount:.0f} 萬**")
        
        st.markdown("---")
        st.subheader("📈 累積期參數")
        sim_start_cash = st.number_input("目前初始本金 (萬)", value=100.0)
        sim_monthly = st.number_input("每月預計投入 (萬)", value=5.0)
        expected_roi = st.slider("預期年化報酬率 (%)", 0, 20, 8) / 100
        sim_years = st.slider("模擬時程 (年)", 5, 40, 20)

    with col_result:
        # 計算財富累積曲線
        months = sim_years * 12
        sim_list = []
        for m in range(months + 1):
            val = sim_start_cash * ((1 + expected_roi/12)**m) + (sim_monthly * (((1 + expected_roi/12)**m - 1) / (expected_roi/12)))
            sim_list.append({"月份": m, "資產價值": round(val, 2)})
        
        df_sim = pd.DataFrame(sim_list)
        final_amt = df_sim['資產價值'].iloc[-1]
        
        # 顯示主要數據
        c1, c2 = st.columns(2)
        with c1:
            st.metric(f"{sim_years}年後資產", f"{final_amt:,.0f} 萬")
        with c2:
            current_withdraw = (final_amt * 0.04) / 12
            st.metric("屆時每月可領取 (4%法則)", f"{current_withdraw:,.2f} 萬")

        # 繪圖
        fig = px.area(df_sim, x='月份', y='資產價值', title="財富累積 vs. 退休目標")
        fig.add_hline(y=fire_target_amount, line_dash="dash", line_color="red", annotation_text=f"目標 {fire_target_amount}萬")
        st.plotly_chart(fig, use_container_width=True)

        # 深度分析
        st.subheader("🤖 AI 策略診斷")
        if final_amt >= fire_target_amount:
            reach_month = df_sim[df_sim['資產價值'] >= fire_target_amount]['月份'].iloc[0]
            st.balloons()
            st.success(f"✅ 達成目標！預計在第 **{reach_month}** 個月（約 {reach_month//12} 年 {reach_month%12} 個月）達成財富自由。")
        else:
            gap = fire_target_amount - final_amt
            st.warning(f"⚠️ 距離目標還差 **{gap:,.0f} 萬**。")
            
            # 反推建議
            suggested_monthly = (fire_target_amount - sim_start_cash*((1+expected_roi/12)**months)) / (((1+expected_roi/12)**months-1)/(expected_roi/12))
            st.write(f"💡 若想在 {sim_years} 年內準時達標，建議將每月投入提高至：**{max(0.0, suggested_monthly):.2f} 萬**")
            
        st.markdown("""
        ---
        ### 📖 什麼是 4% 法則？
        1. **源起**：由 William Bengen 提出，後經「崔尼蒂研究」(Trinity Study) 證實。
        2. **運作方式**：將資產配置在股債組合（例如 60/40），每年提取 4% 應付生活。
        3. **安全邊際**：此法則已考慮到市場波動，目的是讓你的本金即便在提取過程中，也能因市場成長而維持領取 30 年。
        """)