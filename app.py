import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# 1. 網頁基本設定
st.set_page_config(page_title="全球資產管理與策略平台", layout="wide")

# --- 核心功能：即時數據抓取 ---
@st.cache_data(ttl=300) 
def get_market_data():
    try:
        # 匯率即時更新
        fx_data = yf.download("TWD=X", period="1d", progress=False)
        fx = float(fx_data['Close'].iloc[-1])
        # 金價即時更新
        gold_data = yf.download("GOLDTWD=X", period="1d", progress=False)
        gold_gram_twd = float(gold_data['Close'].iloc[-1]) / 31.1035
        return fx, gold_gram_twd, datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    except:
        return 32.5, 2800.0, "更新失敗"

current_fx_rate, current_gold_price, last_update_time = get_market_data()

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

# --- Session State 初始化 ---
if 'holding_list' not in st.session_state:
    st.session_state.holding_list = ["2330.TW", "TLT", "GOLD_PASSBOOK"]
if 'watch_list' not in st.session_state:
    st.session_state.watch_list = ["TSLA", "AAPL"]
if 'target_ratios' not in st.session_state:
    st.session_state.target_ratios = {k: 25 for k in st.session_state.holding_list}

# --- 多分頁導覽列 ---
st.sidebar.title("🧭 導覽選單")
app_mode = st.sidebar.radio("請選擇功能分頁：", ["📊 資產現況與 AI 診斷", "🎯 4%法則策略模擬器", "🔍 代碼查詢工具"])

# ------------------------------------------------------------------
# 分頁一：資產監控與診斷
# ------------------------------------------------------------------
if app_mode == "📊 資產現況與 AI 診斷":
    st.title("🚀 全球資產執行平台")
    
    with st.sidebar:
        st.header("💰 財務與清單管理")
        st.info(f"💵 即時匯率：{current_fx_rate:.2f}\n(更新於: {last_update_time})")
        
        # 1. 我的持股清單管理
        st.subheader("📋 我的持股清單")
        new_h = st.text_input("輸入新持股代碼", key="input_h").upper()
        if st.button("➕ 新增至持股"):
            if new_h and new_h not in st.session_state.holding_list:
                st.session_state.holding_list.append(new_h)
                st.session_state.target_ratios[new_h] = 0
                st.rerun()
        
        for h_item in st.session_state.holding_list:
            col_h1, col_h2 = st.columns([3, 1])
            col_h1.write(h_item)
            if col_h2.button("🗑️", key=f"del_h_{h_item}"):
                st.session_state.holding_list.remove(h_item)
                st.rerun()

        st.markdown("---")
        # 2. 建議配置模板
        st.subheader("💡 建議配置模板")
        c_p1, c_p2, c_p3 = st.columns(3)
        if c_p1.button("⚖️ 保守"):
            st.session_state.target_ratios = {k: 0 for k in st.session_state.holding_list}
            if "TLT" in st.session_state.target_ratios: st.session_state.target_ratios["TLT"] = 60
            if "GOLD_PASSBOOK" in st.session_state.target_ratios: st.session_state.target_ratios["GOLD_PASSBOOK"] = 20
            st.rerun()
        if c_p2.button("📈 穩健"):
            avg = 100 // (len(st.session_state.holding_list) if len(st.session_state.holding_list)>0 else 1)
            st.session_state.target_ratios = {k: avg for k in st.session_state.holding_list}
            st.rerun()
        if c_p3.button("🚀 積極"):
            st.session_state.target_ratios = {k: 0 for k in st.session_state.holding_list}
            if "2330.TW" in st.session_state.target_ratios: st.session_state.target_ratios["2330.TW"] = 70
            st.rerun()

        st.markdown("---")
        cash_on_hand = st.number_input("手頭現金 (萬台幣)", value=100.0)
        monthly_investment = st.number_input("每月預計投入 (萬台幣)", value=5.0)
        fee_rate = st.slider("手續費率 (%)", 0.0, 0.5, 0.1425, step=0.01)

    # 主畫面：標的設定
    st.subheader("⚖️ 資產再平衡與目標設定")
    holdings_qty = {}
    target_ratios = {}
    for ticker in st.session_state.holding_list:
        col1, col2 = st.columns([1, 1])
        target_ratios[ticker] = col1.number_input(f"{ticker} 目標 %", 0, 100, st.session_state.target_ratios.get(ticker, 0), key=f"t_{ticker}")
        holdings_qty[ticker] = col2.number_input(f"{ticker} 庫存數量", 0.0, value=0.0, key=f"q_{ticker}")

    # 計算資產數據
    portfolio_data = []
    total_holding_value_wan = 0
    for item in st.session_state.holding_list:
        t20, t60, last_p, chart_fig = get_stock_analysis(item)
        is_us = ".TW" not in item and ".TWO" not in item and item != "GOLD_PASSBOOK"
        val_wan = (holdings_qty[item] * last_p * (current_fx_rate if is_us else 1)) / 10000 if item != "GOLD_PASSBOOK" else (holdings_qty[item] * last_p) / 10000
        total_holding_value_wan += val_wan
        portfolio_data.append({
            "標的": item, "市值(萬)": val_wan, "目標%": target_ratios[item], 
            "20MA": t20, "60MA": t60, "現價": last_p, "is_us": is_us, "chart": chart_fig
        })
    actual_total = cash_on_hand + total_holding_value_wan

    # --- 1. 10年財富路徑預測 ---
    st.markdown("---")
    st.subheader("📈 10年財富路徑預測")
    df_growth = pd.DataFrame([{"月份": m, "資產價值": round(actual_total * ((1 + 0.10/12)**m) + (monthly_investment * (((1 + 0.10/12)**m - 1) / (0.10/12))), 2)} for m in range(121)])
    
    col_path, col_status = st.columns([2, 1])
    with col_path:
        fig_path = px.line(df_growth, x='月份', y='資產價值', title="複利增長預測 (預設年化10%)")
        fig_path.add_hline(y=4000, line_dash="dash", line_color="red", annotation_text="4000萬目標線")
        st.plotly_chart(fig_path, use_container_width=True)
    
    with col_status:
        # --- 2. 現況統計 ---
        st.subheader("🏦 現況統計")
        st.metric("總資產 (萬)", f"{actual_total:,.2f}")
        st.metric("現金資產 (萬)", f"{cash_on_hand:,.2f}")
        st.metric("證券價值 (萬)", f"{total_holding_value_wan:,.2f}")

    # --- 3. 資產配置現況 ---
    st.markdown("---")
    col_pie, col_list = st.columns([1, 1])
    with col_pie:
        st.subheader("⚖️ 資產配置現況")
        pie_df = pd.DataFrame([{"標的": i["標的"], "市值": i["市值(萬)"]} for i in portfolio_data] + [{"標的": "現金", "市值": cash_on_hand}])
        st.plotly_chart(px.pie(pie_df, values='市值', names='標的', hole=0.4), use_container_width=True)
    with col_list:
        st.subheader("📋 標的清單清單與權重")
        list_df = pd.DataFrame(portfolio_data)
        if not list_df.empty:
            list_df["實際權重%"] = (list_df["市值(萬)"] / actual_total * 100).round(1)
            st.table(list_df[["標的", "市值(萬)", "目標%", "實際權重%"]])

    # --- 4. AI 投資建議與採購計算 ---
    st.markdown("---")
    st.subheader("🤖 AI 投資建議與採購計算")
    if st.button("🔍 執行全維度 AI 分析"):
        # (1) 10年期深度分析
        st.markdown("#### 🏛️ 10年期深度分析")
        final_val = df_growth['資產價值'].iloc[-1]
        if final_val >= 4000:
            st.success(f"按照目前投入速度，10年後預估達 **{final_val:,.0f} 萬**。狀態：✅ 已達標")
        else:
            st.warning(f"10年後預估達 **{final_val:,.0f} 萬**。距4000萬目標尚有 **{4000-final_val:,.0f} 萬** 缺口。")
        
        # (2) 本週趨勢分析
        st.markdown("#### 📅 本週趨勢分析")
        t_cols = st.columns(len(portfolio_data)) if len(portfolio_data) > 0 else []
        for idx, item in enumerate(portfolio_data):
            with st.expander(f"查看 {item['標的']} 趨勢圖"):
                st.write(f"狀態：{item['20MA']} | {item['60MA']}")
                if item["chart"]:
                    st.plotly_chart(item["chart"], use_container_width=True)

        # (3) 執行採購策略建議
        st.markdown("#### 🛠️ 執行採購策略建議")
        for item in portfolio_data:
            actual_ratio = (item["市值(萬)"] / actual_total) * 100 if actual_total > 0 else 0
            diff = item["目標%"] - actual_ratio
            if diff > 1: # 偏差超過 1%
                needed_twd = (diff / 100) * actual_total * 10000
                price_in_twd = item["現價"] * (current_fx_rate if item["is_us"] else 1)
                if price_in_twd > 0:
                    buy_qty = needed_twd / price_in_twd
                    st.info(f"🚀 **{item['標的']}**：偏離目標 {diff:.1f}%，建議買入 **{buy_qty:.2f}** 單位 (約台幣 {needed_twd:,.0f} 元)")
            elif diff < -5:
                st.error(f"🔴 **{item['標的']}**：高於目標 {abs(diff):.1f}%，建議停止投入或部分減碼。")
            else:
                st.write(f"✅ **{item['標的']}**：配置符合目標。")

# --- 分頁二：4% 法則 (保留完整邏輯) ---
elif app_mode == "🎯 4%法則策略模擬器":
    st.title("🎯 4% 法則：財富自由與通膨壓力試算")
    col_sim_in, col_sim_out = st.columns([1, 2])
    with col_sim_in:
        st.subheader("⚙️ 退休生活與通膨設定")
        monthly_expense_today = st.number_input("以『今日購買力』計算之退休月支出 (萬)", value=10.0, step=0.5)
        inflation_rate = st.slider("預期長期年通膨率 (%)", 0.0, 5.0, 2.0, step=0.1) / 100
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
        sim_data = []
        for m in range(months_sim + 1):
            nom_val = init_capital * ((1 + roi_annual/12)**m) + (monthly_save * (((1 + roi_annual/12)**m - 1) / (roi_annual/12)))
            real_val = nom_val / ((1 + inflation_rate/12)**m)
            sim_data.append({"月份": m, "名目價值": nom_val, "實質購買力": real_val})
        df_sim = pd.DataFrame(sim_data)
        st.plotly_chart(px.line(df_sim, x="月份", y=["名目價值", "實質購買力"], title="資產成長 vs 實質購買力"), use_container_width=True)
        st.metric("最終實質購買力 (萬)", f"{df_sim['實質購買力'].iloc[-1]:,.0f}")

# --- 分頁三：代碼查詢工具 (保留) ---
elif app_mode == "🔍 代碼查詢工具":
    st.title("🔍 代碼查詢工具")
    st.markdown("常用參考：台積電 `2330.TW`, 標普500 `VOO`, 納斯達克 `QQQ`, 美債 `TLT`")
    search_q = st.text_input("輸入名稱搜尋 (Yahoo Finance)")
    if search_q:
        st.link_button(f"前往 Yahoo Finance 搜尋: {search_q}", f"https://finance.yahoo.com/lookup?s={search_q}")