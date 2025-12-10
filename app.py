import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os

# --- 設定網頁 ---
st.set_page_config(page_title="施昇輝 K值儀表板 (自選股版)", page_icon="📈")

# --- 檔案儲存設定 (讓清單可以永久保存) ---
DATA_FILE = "my_stocks.json"

# 預設清單 (如果第一次執行，會用這個建立檔案)
DEFAULT_STOCKS = {
    "0050.TW": "元大台灣50",
    "0056.TW": "元大高股息",
    "0052.TW": "富邦科技",
    "00646.TW": "元大S&P500",
    "2002.TW": "中鋼"
}

# --- 讀取與寫入資料的函數 ---
def load_stock_list():
    """從 JSON 檔案讀取股票清單，如果沒有檔案就用預設值"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return DEFAULT_STOCKS
    return DEFAULT_STOCKS

def save_stock_list(data):
    """將股票清單寫入 JSON 檔案"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- 初始化 Session State ---
if 'stock_dict' not in st.session_state:
    st.session_state.stock_dict = load_stock_list()

# --- 側邊欄：新增與刪除功能 ---
st.sidebar.title("⚙️ 管理自選股")

# 1. 新增股票區塊
with st.sidebar.expander("➕ 新增股票", expanded=True):
    new_ticker = st.text_input("股票代號", placeholder="例如: 2330 或 00878")
    new_name = st.text_input("股票名稱 (選填)", placeholder="例如: 台積電")
    
    if st.button("加入清單"):
        if new_ticker:
            # 自動修正代號：如果是4-5位數字且沒打.TW，自動幫加上
            ticker_formatted = new_ticker.strip().upper()
            if ticker_formatted.isdigit() and len(ticker_formatted) >= 4:
                ticker_formatted += ".TW"
            
            # 如果沒填名稱，就用代號當名稱
            name_to_save = new_name if new_name else ticker_formatted
            
            # 更新狀態並存檔
            st.session_state.stock_dict[ticker_formatted] = name_to_save
            save_stock_list(st.session_state.stock_dict)
            st.success(f"已新增: {name_to_save}")
            st.rerun() # 重新整理頁面
        else:
            st.warning("請輸入股票代號")

# 2. 刪除股票區塊
with st.sidebar.expander("🗑️ 刪除股票"):
    # 製作選單選項
    options = list(st.session_state.stock_dict.keys())
    # 顯示格式：名稱 (代號)
    format_func = lambda x: f"{st.session_state.stock_dict[x]} ({x})"
    
    delete_list = st.multiselect("選擇要移除的股票", options, format_func=format_func)
    
    if st.button("確認刪除"):
        if delete_list:
            for item in delete_list:
                del st.session_state.stock_dict[item]
            save_stock_list(st.session_state.stock_dict)
            st.success("刪除成功！")
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(f"目前監控中: {len(st.session_state.stock_dict)} 檔")

# --- 主畫面：儀表板 ---
st.title("📈 樂活投資 K值偵測")
st.caption("策略：K<20 買進 (綠色) | K>80 賣出 (紅色)")

# 重新整理按鈕
if st.button('🔄 更新最新股價'):
    st.cache_data.clear()
    st.rerun()

st.write("---")

# --- 核心計算邏輯 (保持不變) ---
def get_k_value(ticker):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="60d")
        if df.empty: return None, 0
        
        current_price = df['Close'].iloc[-1]
        
        df['L9'] = df['Low'].rolling(window=9).min()
        df['H9'] = df['High'].rolling(window=9).max()
        df['RSV'] = (df['Close'] - df['L9']) / (df['H9'] - df['L9']) * 100
        df = df.dropna()
        
        k = 50
        for rsv in df['RSV']:
            k = (2/3) * k + (1/3) * rsv
            
        return current_price, k
    except:
        return None, 0

# --- 迴圈顯示每一張卡片 ---
# 為了美觀，如果沒有股票要提示
if not st.session_state.stock_dict:
    st.info("目前清單是空的，請從左側側邊欄新增股票！")
else:
    for ticker, name in st.session_state.stock_dict.items():
        price, k = get_k_value(ticker)
        
        if price:
            # 判斷邏輯
            if k < 20:
                color = "#2e7d32" # 深綠
                action = "🟢 進場訊號 (買)"
                bg_color = "#e8f5e9" # 淡綠底
            elif k > 80:
                color = "#c62828" # 深紅
                action = "🔴 過熱訊號 (賣)"
                bg_color = "#ffebee" # 淡紅底
            else:
                color = "#ef6c00" # 橘色
                action = "🟡 觀望持有"
                bg_color = "#fff3e0" # 淡橘底
                
            # HTML 卡片設計
            st.markdown(
                f"""
                <div style="padding:15px; border-radius:12px; margin-bottom:12px; background-color:{bg_color}; border:1px solid rgba(0,0,0,0.1); box-shadow: 2px 2px 5px rgba(0,0,0,0.05);">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div>
                            <h3 style="margin:0; color:#333; font-size:1.3em;">{name}</h3>
                            <span style="font-size:0.85em; color:#666; font-family:monospace;">{ticker}</span>
                        </div>
                        <div style="text-align:right;">
                            <strong style="color:{color}; font-size:1.1em;">{action}</strong>
                        </div>
                    </div>
                    <hr style="margin:10px 0; border:0; border-top:1px dashed #ccc;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <span style="font-size:0.8em; color:#777;">現價</span><br>
                            <strong style="font-size:1.4em; color:#333;">{price:.2f}</strong>
                        </div>
                        <div style="text-align:right;">
                            <span style="font-size:0.8em; color:#777;">K值 (9,3,3)</span><br>
                            <strong style="font-size:1.4em; color:{color};">{k:.2f}</strong>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.error(f"❌ {name} ({ticker}): 讀取失敗，請檢查代號是否正確")

st.markdown("---")
st.caption("資料儲存於伺服器: my_stocks.json")
