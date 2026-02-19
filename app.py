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
page = st.sidebar.radio("選擇功能", ["📊 資產現況與 AI 診斷", "🧪 策略規劃模擬器"])

# ------------------------------------------------------------------
# 分頁 1：資產現況與 AI 診斷
# ------------------------------------------------------------------
if page == "📊 資產現況與 AI 診斷":
    st.title("🚀 10年台幣4000萬：全球資產執行平台")
    
    with st.sidebar:
        st.header("💰 現有庫存設定")
        cash_on_hand = st.number_input("手頭現金 (萬)", value=100.0)
        monthly_investment = st.number_input("每月投入 (萬)", value=5.0)
        fee_rate = st.slider("手續費率 (%)", 0.0, 0.5, 0.1425, step=0.01)
        
        target_ratios = {}
        holdings_qty = {}
        for ticker in ["2330.TW", "TLT", "GOLD_PASSBOOK"]:
            st.markdown(f"---")
            target_ratios[ticker] = st.slider(f"{ticker} 目標 %", 0, 100, 25, key=f"t_{ticker}")
            holdings_qty[ticker] = st.number_input(f"{ticker} 庫存", min_value=0.0, key=f"q_{ticker}")

    # 計算資產與顯示圖表 (與原程式邏輯相同)
    portfolio_data = []
    total_val = 0
    for ticker in ["2330.TW", "TLT", "GOLD_PASSBOOK"]:
        t20, t60, last_p, chart = get_stock_analysis(ticker)
        is_us = ".TW" not in ticker and ticker != "GOLD_PASSBOOK"
        v = (holdings_qty[ticker] * last_p * (current_fx_rate if is_us else 1)) / 10000 if ticker != "GOLD_PASSBOOK" else (holdings_qty[ticker] * last_p) / 10000
        total_val += v
        portfolio_data.append({"標的": ticker, "市值(萬)": v, "目標%": target_ratios[ticker], "20MA": t20, "現價": last_p, "is_us": is_us, "chart": chart})

    actual_total = cash_on_hand + total_val
    
    # 介面展示
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("🏦 資產統計")
        st.metric("總資產 (萬)", f"{actual_total:.2f}")
        pie_df = pd.DataFrame([{"標的": i["標的"], "市值": i["市值(萬)"]} for i in portfolio_data] + [{"標的": "現金", "市值": cash_on_hand}])
        st.plotly_chart(px.pie(pie_df, values='市值', names='標的', hole=0.4), use_container_width=True)

    with col2:
        st.subheader("🤖 AI 投資建議")
        if st.button("🔍 執行深度分析"):
            for item in portfolio_data:
                diff = item["目標%"] - (item["市值(萬)"]/actual_total*100)
                if diff > 1:
                    st.write(f"🚀 **{item['標的']}**")
                    st.info(f"建議補足 {diff:.1f}%，約 {diff/100*actual_total:.1f} 萬")
                    if item["chart"]: st.plotly_chart(item["chart"], use_container_width=True)

# ------------------------------------------------------------------
# 分頁 2：策略規劃模擬器
# ------------------------------------------------------------------
elif page == "🧪 策略規劃模擬器":
    st.title("🧪 不同投資策略規劃與試算")
    st.info("在此分頁你可以設定不同的年化報酬率，試算財富達成時間，而不影響你的現有庫存數據。")
    
    col_input, col_result = st.columns([1, 2])
    
    with col_input:
        st.subheader("⚙️ 模擬參數")
        sim_start_cash = st.number_input("初始本金 (萬)", value=100.0)
        sim_monthly = st.number_input("模擬每月投入 (萬)", value=5.0)
        sim_years = st.slider("模擬年數", 1, 30, 10)
        
        st.markdown("---")
        st.write("📈 **不同策略年化報酬率預設：**")
        strategies = {
            "保守型 (定存/債券)": 0.03,
            "穩健型 (高股息/ETF)": 0.07,
            "進取型 (台美龍頭股)": 0.12,
            "自定義策略": st.slider("自定義報酬率 (%)", 0, 30, 10) / 100
        }
        selected_strategy = st.selectbox("選擇模擬劇本", list(strategies.keys()))
        expected_roi = strategies[selected_strategy]

    with col_result:
        months = sim_years * 12
        sim_data = []
        for m in range(months + 1):
            # 複利公式：FV = PV*(1+r)^n + PMT * [((1+r)^n - 1) / r]
            val = sim_start_cash * ((1 + expected_roi/12)**m) + (sim_monthly * (((1 + expected_roi/12)**m - 1) / (expected_roi/12)))
            sim_data.append({"月份": m, "資產價值": round(val, 2)})
        
        df_sim = pd.DataFrame(sim_data)
        
        st.subheader(f"📊 {selected_strategy} 模擬結果")
        final_amt = df_sim['資產價值'].iloc[-1]
        st.metric(f"{sim_years} 年後預估資產", f"{final_amt:,.0f} 萬", 
                  delta=f"較初始成長 {final_amt - sim_start_cash:,.0f} 萬")
        
        fig_sim = px.area(df_sim, x='月份', y='資產價值', title="財富累積曲線")
        fig_sim.add_hline(y=4000, line_dash="dash", line_color="red", annotation_text="4000萬目標")
        st.plotly_chart(fig_sim, use_container_width=True)
        
        # 達標分析
        if final_amt >= 4000:
            reach_month = df_sim[df_sim['資產價值'] >= 4000]['月份'].iloc[0]
            st.success(f"🎊 依照此策略，你將在第 **{reach_month}** 個月（約 {reach_month//12} 年）達成 4000 萬目標！")
        else:
            st.warning(f"⚠️ 依照此策略，{sim_years} 年後尚未達標。建議將月投提高至 {((4000 - sim_start_cash*((1+expected_roi/12)**months)) / (((1+expected_roi/12)**months-1)/(expected_roi/12))):.1f} 萬以利達標。")