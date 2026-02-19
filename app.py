import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# 1. 網頁基本設定
st.set_page_config(page_title="全球資產管理與策略平台", layout="wide")

# --- 核心功能：即時數據抓取 ---
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

# --- 數據分析函式 ---
def get_stock_analysis(ticker):
    if ticker == "GOLD_PASSBOOK":
        return "N/A", "N/A", current_gold_price, None
    try:
        df = yf.download(ticker, period="6mo", progress=False, auto_adjust=True)
        if df.empty or len(df) < 2:
            return "讀取失敗", "數據不足", 0, None
        close_series = df['Close'].iloc[:, 0] if isinstance(df['Close'], pd.DataFrame) else df['Close']
        current_p = float(close_series.iloc[-1])
        ma20 = close_series.rolling(window=20).mean()
        ma60 = close_series.rolling(window=60).mean()
        t20 = "📈 站上月線" if current_p > ma20.iloc[-1] else "📉 跌破月線"
        t60 = "🚀 站上季線" if current_p > ma60.iloc[-1] else "🧊 跌破季線"
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=close_series, name="收盤價", line=dict(color='white', width=1)))
        fig.add_trace(go.Scatter(x=df.index, y=ma20, name="20MA", line=dict(color='#ff9900', width=2)))
        fig.add_trace(go.Scatter(x=df.index, y=ma60, name="60MA", line=dict(color='#00ccff', width=2)))
        fig.update_layout(height=250, template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10))
        return t20, t60, current_p, fig
    except:
        return "讀取失敗", "系統錯誤", 0, None

# --- 多分頁導覽列 ---
st.sidebar.title("🧭 導覽選單")
app_mode = st.sidebar.radio("請選擇功能分頁：", ["📊 資產現況與 AI 診斷", "🎯 4%法則策略模擬器"])

# ------------------------------------------------------------------
# 分頁一：資產監控與診斷 (功能擴充版)
# ------------------------------------------------------------------
if app_mode == "📊 資產現況與 AI 診斷":
    st.title("🚀 10年台幣4000萬：全球資產執行平台")
    
    if 'holding_list' not in st.session_state:
        st.session_state.holding_list = ["2330.TW", "TLT", "GOLD_PASSBOOK"]
    
    with st.sidebar:
        st.header("💰 財務與成本設定")
        st.write(f"💵 目前匯率：**{current_fx_rate:.2f}**")
        cash_on_hand = st.number_input("手頭現金 (萬台幣)", value=100.0)
        monthly_investment = st.number_input("每月預計投入 (萬台幣)", value=5.0)
        fee_rate = st.slider("手續費率 (%)", 0.0, 0.5, 0.1425, step=0.01)
        tax_rate = st.slider("交易稅率 (%)", 0.0, 0.5, 0.3, step=0.05)
        
        target_ratios = {}
        holdings_qty = {}
        for ticker in st.session_state.holding_list:
            st.markdown(f"---")
            target_ratios[ticker] = st.slider(f"{ticker} 目標 %", 0, 100, 25, key=f"t_{ticker}")
            holdings_qty[ticker] = st.number_input(f"{ticker} 目前庫存", min_value=0.0, key=f"q_{ticker}")

    # 數據整理與計算
    portfolio_data = []
    total_holding_value_wan = 0
    
    for item in st.session_state.holding_list:
        t20, t60, last_p, chart_fig = get_stock_analysis(item)
        is_us = ".TW" not in item and ".TWO" not in item and item != "GOLD_PASSBOOK"
        
        # 換算市值 (萬台幣)
        if item == "GOLD_PASSBOOK":
            val_wan = (holdings_qty[item] * last_p) / 10000
        else:
            val_wan = (holdings_qty[item] * last_p * (current_fx_rate if is_us else 1)) / 10000
            
        total_holding_value_wan += val_wan
        portfolio_data.append({
            "標的": item, 
            "市值(萬)": val_wan, 
            "目標%": target_ratios[item], 
            "20MA": t20, 
            "60MA": t60, 
            "現價": last_p, 
            "is_us": is_us,
            "chart": chart_fig
        })

    actual_total = cash_on_hand + total_holding_value_wan

    # --- 1. 10年財富路徑預測 ---
    st.subheader("📈 10年財富路徑預測")
    # 預測邏輯：年化 10% 複利計算
    df_growth = pd.DataFrame([
        {
            "月份": m, 
            "資產價值": round(actual_total * ((1 + 0.10/12)**m) + (monthly_investment * (((1 + 0.10/12)**m - 1) / (0.10/12))), 2)
        } for m in range(121)
    ])
    
    col_chart, col_stat = st.columns([2, 1])
    with col_chart:
        fig_growth = px.line(df_growth, x='月份', y='資產價值', title="預期複利增長 (10% 年化)")
        fig_growth.add_hline(y=4000, line_dash="dash", line_color="red", annotation_text="4000萬目標線")
        st.plotly_chart(fig_growth, use_container_width=True)
    
    with col_stat:
        # --- 2. 現況統計 ---
        st.subheader("🏦 現況統計")
        st.metric("總資產 (萬)", f"{actual_total:,.2f}")
        st.metric("目前庫存市值 (萬)", f"{total_holding_value_wan:,.2f}")
        st.metric("手頭現金額 (萬)", f"{cash_on_hand:,.2f}")

    st.markdown("---")

    # --- 3. 資產配置現況 ---
    col_pie, col_ai = st.columns([1, 1])
    with col_pie:
        st.subheader("⚖️ 資產配置現況")
        pie_df = pd.DataFrame([{"標的": i["標的"], "市值": i["市值(萬)"]} for i in portfolio_data] + [{"標的": "現金", "市值": cash_on_hand}])
        st.plotly_chart(px.pie(pie_df, values='市值', names='標的', hole=0.4), use_container_width=True)
        st.table(pd.DataFrame(portfolio_data)[["標的", "市值(萬)", "目標%"]])

    # --- 4. AI 投資建議與採購計算 ---
    with col_ai:
        st.subheader("🤖 AI 投資建議與採購計算")
        if st.button("🔍 執行全維度深度分析"):
            
            # (1) 10年期深度分析
            st.markdown("#### 🏛️ 10年期深度分析")
            final_val = df_growth['資產價值'].iloc[-1]
            if final_val >= 4000:
                st.success(f"按照目前投入速度，10 年後預計達 **{final_val:,.0f} 萬**。狀態：✅ 達標")
            else:
                st.warning(f"10 年後預計 **{final_val:,.0f} 萬**。距目標尚差 **{4000-final_val:,.0f} 萬**。建議增加每月加碼額。")
            
            st.markdown("---")
            
            # (2) 本週趨勢分析
            st.markdown("#### 📅 本週趨勢分析")
            for item in portfolio_data:
                if item["chart"]:
                    st.write(f"**{item['標的']}** 現況：{item['20MA']} / {item['60MA']}")
                    st.plotly_chart(item["chart"], use_container_width=True)
            
            st.markdown("---")
            
            # (3) 執行採購策略建議 (再平衡計算)
            st.markdown("#### 🛠️ 執行採購策略建議")
            for item in portfolio_data:
                actual_ratio = (item["市值(萬)"] / actual_total) * 100 if actual_total > 0 else 0
                diff = item["目標%"] - actual_ratio
                
                if diff > 1: # 權重不足，建議買入
                    needed_twd = (diff / 100) * actual_total * 10000
                    price_in_twd = item["現價"] * (current_fx_rate if item["is_us"] else 1)
                    if price_in_twd > 0:
                        buy_qty = needed_twd / price_in_twd
                        st.info(f"🚀 **{item['標的']}** (低配)：建議加碼 **{buy_qty:.2f}** 股/克 (約台幣 {needed_twd:,.0f} 元)")
                elif diff < -5: # 權重過高，建議減碼
                    st.error(f"🔴 **{item['標的']}** (超配)：建議減碼 {abs(diff):.1f}% 權重以平衡風險。")
                else:
                    st.write(f"✅ **{item['標的']}**：比例正常，無需變動。")

# ------------------------------------------------------------------
# 分頁二：4% 法則策略模擬器 (保留原代碼)
# ------------------------------------------------------------------
elif app_mode == "🎯 4%法則策略模擬器":
    # [這裡完整保留您提供的 4% 法則代碼部分...]
    st.title("🎯 4% 法則：財富自由與通膨壓力試算")
    # ... (省略 4% 法則部分以節省篇幅，內容完全依照您提供的原稿執行)
    col_sim_in, col_sim_out = st.columns([1, 2])
    with col_sim_in:
        st.subheader("⚙️ 退休生活與通膨設定")
        monthly_expense_today = st.number_input("以『今日購買力』計算之退休月支出 (萬)", value=10.0, step=0.5)
        inflation_rate = st.slider("預期長期年通膨率 (%)", 0.0, 5.0, 2.0, step=0.1) / 100
        st.markdown("---")
        st.subheader("📈 累積期參數")
        init_capital = st.number_input("模擬啟始本金 (萬)", value=100.0)
        monthly_save = st.number_input("模擬每月加碼 (萬)", value=5.0)
        roi_annual = st.slider("預期投資年報酬率 (%)", 0, 20, 8) / 100
        years_to_sim = st.slider("模擬時程 (年)", 5, 40, 20)
        fire_target_today = monthly_expense_today * 12 * 25
        fire_target_future = fire_target_today * ((1 + inflation_rate) ** years_to_sim)
        st.warning(f"📌 今日 4% 目標：{fire_target_today:,.0f} 萬")
        st.error(f"🚨 {years_to_sim} 年後通膨校正目標：{fire_target_future:,.0f} 萬")

    with col_sim_out:
        months_sim = years_to_sim * 12
        sim_data_list = []
        for m in range(months_sim + 1):
            nom_val = init_capital * ((1 + roi_annual/12)**m) + (monthly_save * (((1 + roi_annual/12)**m - 1) / (roi_annual/12)))
            real_val = nom_val / ((1 + inflation_rate/12)**m)
            sim_data_list.append({"月份": m, "名目價值": nom_val, "實質購買力": real_val})
        df_sim_res = pd.DataFrame(sim_data_list)
        final_nom_val = df_sim_res['名目價值'].iloc[-1]
        final_real_val = df_sim_res['實質購買力'].iloc[-1]
        c1, c2, c3 = st.columns(3)
        with c1: st.metric(f"{years_to_sim}年後名目資產", f"{final_nom_val:,.0f} 萬")
        with c2: st.metric("折合今日購買力", f"{final_real_val:,.0f} 萬")
        with c3: st.metric("實質月領能力", f"{(final_real_val * 0.04) / 12:.2f} 萬")
        fig_sim = go.Figure()
        fig_sim.add_trace(go.Scatter(x=df_sim_res['月份'], y=df_sim_res['名目價值'], name="名目資產", fill='tonexty'))
        fig_sim.add_trace(go.Scatter(x=df_sim_res['月份'], y=df_sim_res['實質購買力'], name="實質資產 (扣除通膨)", line=dict(dash='dash')))
        fig_sim.update_layout(title="財富累積：名目資產 vs. 實質購買力", template="plotly_dark")
        st.plotly_chart(fig_sim, use_container_width=True)