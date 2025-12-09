import streamlit as st
import yfinance as yf
import pandas as pd

# --- 設定網頁標題與排版 ---
st.set_page_config(page_title="施昇輝 K值儀表板", page_icon="📈")

st.title("📈 樂活投資 K值偵測")
st.caption("基於施昇輝《只買一支股》策略：K<20買，K>80賣")

# --- 定義股票清單 ---
default_stocks = {
    "0050.TW": "元大台灣50",
    "0056.TW": "元大高股息",
    "0052.TW": "富邦科技",
    "00646.TW": "元大S&P500",
    "2002.TW": "中鋼"
}

# --- 側邊欄：讓使用者可以選股或加股 ---
st.sidebar.header("設定")
selected_tickers = st.sidebar.multiselect(
    "選擇觀察名單",
    options=list(default_stocks.keys()),
    default=list(default_stocks.keys()),
    format_func=lambda x: f"{default_stocks.get(x, x)} ({x})"
)

# --- 核心計算邏輯 (KD 9,3,3) ---
def get_k_value(ticker):
    try:
        stock = yf.Ticker(ticker)
        # 抓取資料
        df = stock.history(period="60d")
        if df.empty: return None, 0
        
        current_price = df['Close'].iloc[-1]
        
        # 計算 RSV
        df['L9'] = df['Low'].rolling(window=9).min()
        df['H9'] = df['High'].rolling(window=9).max()
        df['RSV'] = (df['Close'] - df['L9']) / (df['H9'] - df['L9']) * 100
        df = df.dropna()
        
        # 計算 K值 (遞迴計算以求精確)
        k = 50
        for rsv in df['RSV']:
            k = (2/3) * k + (1/3) * rsv
            
        return current_price, k
    except:
        return None, 0

# --- 顯示按鈕 ---
if st.button('🔄 更新最新數據'):
    st.cache_data.clear()

# --- 執行分析並顯示結果 ---
st.write("---")

for ticker in selected_tickers:
    name = default_stocks.get(ticker, ticker)
    price, k = get_k_value(ticker)
    
    if price:
        # 判斷顏色與訊號
        if k < 20:
            color = "green"
            action = "🟢 進場訊號 (買)"
            bg_color = "#e6fffa" # 淡綠底
        elif k > 80:
            color = "red"
            action = "🔴 過熱訊號 (賣)"
            bg_color = "#fff5f5" # 淡紅底
        else:
            color = "orange" # 使用 orange 代替 gold 確保顯示
            action = "🟡 觀望持有"
            bg_color = "#fffff0" # 淡黃底
            
        # 使用 HTML/CSS 美化顯示卡片 (手機易讀版)
        st.markdown(
            f"""
            <div style="padding:15px; border-radius:10px; margin-bottom:10px; background-color:{bg_color}; border:1px solid #ddd;">
                <h3 style="margin:0; color:#333;">{name} <span style="font-size:0.8em; color:#666;">{ticker}</span></h3>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:10px;">
                    <div>
                        <span style="font-size:0.9em; color:#888;">現價</span><br>
                        <strong style="font-size:1.2em;">{price:.2f}</strong>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-size:0.9em; color:#888;">K值 (9,3,3)</span><br>
                        <strong style="font-size:1.2em; color:{color};">{k:.2f}</strong>
                    </div>
                </div>
                <hr style="margin:10px 0; border:0; border-top:1px dashed #ccc;">
                <strong style="color:{color};">{action}</strong>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.error(f"❌ {name}: 無法讀取數據")

st.caption(f"數據來源: Yahoo Finance | 注意: 盤中報價可能延遲 20 分鐘")
