import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# 1. 網頁基本設定
st.set_page_config(page_title="全球資產管理與策略平台", layout="wide")

# --- 核心功能：即時數據抓取 ---
@st.cache_data(ttl=600)  # 縮短快取時間至10分鐘以實現「即時更新」
def get_market_data():
    try:
        # 匯率即時更新
        fx_data = yf.download("TWD=X", period="1d", progress=False)
        fx = float(fx_data['Close'].iloc[-1])
        # 金價
        gold_data = yf.download("GOLDTWD=X", period="1d", progress=False)
        gold_gram_twd = float(gold_data['Close'].iloc[-1]) / 31.1035
        return fx, gold_gram_twd, datetime.now().strftime("%H:%M:%S")
    except:
        return 32.5, 2800.0, "無法更新"

current_fx_rate, current_gold_price, last_update = get_market_data()

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
        fig.update_layout(height=200, template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10))
        return t20, t60, current_p, fig
    except:
        return "讀取失敗", "系統錯誤", 0, None

# --- 初始化 Session State ---
if 'holding_list' not in st.session_state:
    st.session_state.holding_list = ["2330.TW", "TLT"]
if 'watch_list' not in st.session_state:
    st.session_state.watch_list = ["AAPL", "0050.TW"]
if 'target_ratios' not in st.session_state:
    st.session_state.target_ratios = {"2330.TW": 50, "TLT": 50}

# --- 多分頁導覽列 ---
st.sidebar.title("🧭 導覽選單")
app_mode = st.sidebar.radio("請選擇功能分頁：", ["📊 資產現況與 AI 診斷", "🎯 4%法則策略模擬器", "🔍 代碼查詢工具"])

# ------------------------------------------------------------------
# 分頁一：資產監控與診斷
# ------------------------------------------------------------------
if app_mode == "📊 資產現況與 AI 診斷":
    st.title("🚀 全球資產執行平台")
    
    with st.sidebar:
        st.header("⚙️ 持股與配置管理")
        st.write(f"💵 匯率: **{current_fx_rate:.2f}** ({last_update})")
        
        # 1. 我的持股清單 (獨立輸入與刪除)
        st.subheader("📋 我的持股清單")
        new_holding = st.text_input("輸入新持股代碼 (如: TSLA)", key="add_h").upper()
        if st.button("確認新增持股"):
            if new_holding and new_holding not in st.session_state.holding_list:
                st.session_state.holding_list.append(new_holding)
                st.session_state.target_ratios[new_holding] = 0
                st.rerun()

        for h in st.session_state.holding_list:
            col_h1, col_h2 = st.columns([3, 1])
            col_h1.write(h)
            if col_h2.button("🗑️", key=f"del_{h}"):
                st.session_state.holding_list.remove(h)
                st.rerun()

        st.markdown("---")
        # 2. 追蹤清單設定 (獨立輸入)
        st.subheader("👀 追蹤清單設定")
        new_watch = st.text_input("輸入追蹤代碼 (如: NVDA)", key="add_w").upper()
        if st.button("確認新增追蹤"):
            if new_watch and new_watch not in st.session_state.watch_list:
                st.session_state.watch_list.append(new_watch)
                st.rerun()
        st.caption(f"目前追蹤: {', '.join(st.session_state.watch_list)}")

        st.markdown("---")
        # 3. 一鍵套用建議配置
        st.subheader("💡 快速配置方案")
        col_set1, col_set2 = st.columns(2)
        if col_set1.button("⚖️ 穩健型"):
            for h in st.session_state.holding_list: st.session_state.target_ratios[h] = 100 // len(st.session_state.holding_list)
            st.rerun()
        if col_set2.button("🚀 積極型"):
            if "2330.TW" in st.session_state.target_ratios: st.session_state.target_ratios["2330.TW"] = 80
            st.rerun()

    # 主畫面計算
    cash_on_hand = st.number_input("手頭現金 (萬台幣)", value=100.0)
    
    st.subheader("🛠️ 再平衡目標設定")
    cols = st.columns(len(st.session_state.holding_list))
    for i, h in enumerate(st.session_state.holding_list):
        st.session_state.target_ratios[h] = cols[i].number_input(f"{h} 目標%", value=st.session_state.target_ratios.get(h, 0))
    
    # 庫存數量輸入
    holdings_qty = {}
    st.write("📝 請輸入目前庫存數量：")
    qty_cols = st.columns(len(st.session_state.holding_list))
    for i, h in enumerate(st.session_state.holding_list):
        holdings_qty[h] = qty_cols[i].number_input(f"{h} 數量", min_value=0.0, key=f"qty_{h}")

    # 資產計算邏輯
    portfolio_data = []
    total_holding_value_wan = 0
    for item in st.session_state.holding_list:
        t20, t60, last_p, chart_fig = get_stock_analysis(item)
        is_us = ".TW" not in item and ".TWO" not in item and item != "GOLD_PASSBOOK"
        val_wan = (holdings_qty[item] * last_p * (current_fx_rate if is_us else 1)) / 10000
        total_holding_value_wan += val_wan
        portfolio_data.append({"標的": item, "市值(萬)": val_wan, "目標%": st.session_state.target_ratios[item], "20MA": t20, "現價": last_p, "is_us": is_us})

    actual_total = cash_on_hand + total_holding_value_wan
    
    # --- 資產再平衡提醒 ---
    st.markdown("---")
    st.subheader("⚖️ 資產再平衡提醒")
    rebalance_data = []
    for p in portfolio_data:
        current_ratio = (p["市值(萬)"] / actual_total) * 100 if actual_total > 0 else 0
        diff_ratio = p["目標%"] - current_ratio
        status = "✅ 正常"
        if diff_ratio > 5: status = "📢 建議增碼"
        elif diff_ratio < -5: status = "⚠️ 建議減碼"
        rebalance_data.append({"標的": p["標的"], "當前權重%": round(current_ratio, 1), "目標權重%": p["目標%"], "偏移量%": round(diff_ratio, 1), "動作": status})
    st.table(pd.DataFrame(rebalance_data))

    # 圖表顯示
    col_pie, col_growth = st.columns(2)
    with col_pie:
        pie_df = pd.DataFrame([{"標的": i["標的"], "市值": i["市值(萬)"]} for i in portfolio_data] + [{"標的": "現金", "市值": cash_on_hand}])
        st.plotly_chart(px.pie(pie_df, values='市值', names='標的', hole=0.4, title="資產比例現況"), use_container_width=True)
    with col_growth:
        df_growth = pd.DataFrame([{"月份": m, "資產價值": round(actual_total * ((1 + 0.08/12)**m), 2)} for m in range(121)])
        st.plotly_chart(px.line(df_growth, x='月份', y='資產價值', title="預估增長 (年化8%)"), use_container_width=True)

# ------------------------------------------------------------------
# 分頁二：4% 法則策略模擬器 (保留原邏輯)
# ------------------------------------------------------------------
elif app_mode == "🎯 4%法則策略模擬器":
    st.title("🎯 4% 法則進階模擬器")
    # ... (此處保留您上一版本完整的 4% 法則代碼)
    st.write("請套用先前提供的 4% 法則代碼區塊...")

# ------------------------------------------------------------------
# 分頁三：代碼查詢工具
# ------------------------------------------------------------------
elif app_mode == "🔍 代碼查詢工具":
    st.title("🔍 全球股市代碼查詢")
    st.write("如果不確定代碼，請在下方輸入關鍵字（例如: 台積電、Apple）")
    search_q = st.text_input("輸入公司名稱或關鍵字")
    if search_q:
        st.info(f"正在搜尋 '{search_q}' 相關代碼...")
        # 這裡提供常用代碼指引，實際複雜查詢建議連結至 Yahoo Finance
        st.markdown("""
        **常見代碼指南：**
        - 台股：`2330.TW` (台積電), `0050.TW` (元大台灣50)
        - 美股：`AAPL` (蘋果), `TSLA` (特斯拉), `NVDA` (輝達)
        - 債券/其他：`TLT` (20年美債), `GLD` (黃金ETF)
        """)
        st.link_button("前往 Yahoo Finance 官網查詢精確代碼", f"https://finance.yahoo.com/lookup?s={search_q}")