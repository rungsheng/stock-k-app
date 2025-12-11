import streamlit as st
import yfinance as yf
import pandas as pd
import io

# --- 設定網頁 ---
st.set_page_config(page_title="K值儀表板 (個人版)", page_icon="📈")

# --- 預設清單 ---
DEFAULT_STOCKS = {
    "0050.TW": "元大台灣50",
    "0056.TW": "元大高股息",
    "0052.TW": "富邦科技",
    "00646.TW": "元大S&P500",
    "2002.TW": "中鋼"
}

# --- 核心邏輯：資料載入與同步 ---
def init_session_state():
    """
    優先順序：
    1. 網址參數 (URL Query Params) - 為了讓加入書籤能運作
    2. 預設清單
    """
    if 'stock_dict' not in st.session_state:
        # 嘗試從網址讀取 ?tickers=0050.TW,2330.TW...
        query_params = st.query_params
        url_tickers = query_params.get("tickers", None)
        
        if url_tickers:
            # 如果網址有參數，解析它 (網址只存代號，名稱需重新抓或暫時用代號)
            tickers_list = url_tickers.split(",")
            st.session_state.stock_dict = {t: t for t in tickers_list} # 暫時用代號當名稱
            # 這裡可以做優化：如果代號在預設清單中，就用預設名稱
            for t in st.session_state.stock_dict:
                if t in DEFAULT_STOCKS:
                    st.session_state.stock_dict[t] = DEFAULT_STOCKS[t]
        else:
            # 使用預設值
            st.session_state.stock_dict = DEFAULT_STOCKS.copy()

def update_url():
    """將目前的清單寫入網址參數，讓使用者可以存成書籤"""
    tickers = ",".join(st.session_state.stock_dict.keys())
    st.query_params["tickers"] = tickers

# 初始化
init_session_state()

# --- 側邊欄：CSV 管理與編輯 ---
st.sidebar.title("📂 清單管理")

# 1. CSV 下載 (匯出)
# 將 dict 轉為 DataFrame 再轉 CSV
export_df = pd.DataFrame(list(st.session_state.stock_dict.items()), columns=["代號", "名稱"])
csv_buffer = export_df.to_csv(index=False).encode('utf-8-sig') # 加上 sig 讓 Excel 打開不會亂碼

st.sidebar.download_button(
    label="⬇️ 下載目前清單 (CSV)",
    data=csv_buffer,
    file_name="my_k_stocks.csv",
    mime="text/csv"
)

# 2. CSV 上傳 (匯入)
uploaded_file = st.sidebar.file_uploader("⬆️ 上傳清單 (CSV)", type=["csv"])

if uploaded_file is not None:
    try:
        # 讀取 CSV
        df_import = pd.read_csv(uploaded_file)
        # 檢查欄位
        if "代號" in df_import.columns:
            new_dict = {}
            for index, row in df_import.iterrows():
                code = str(row["代號"]).strip().upper()
                name = str(row["名稱"]).strip() if "名稱" in df_import.columns else code
                # 確保代號格式
                if code.isdigit() and len(code) >= 4:
                    code += ".TW"
                new_dict[code] = name
            
            # 更新 Session
            st.session_state.stock_dict = new_dict
            update_url() # 同步更新網址
            st.sidebar.success(f"成功匯入 {len(new_dict)} 檔股票！")
            uploaded_file = None # 重置
        else:
            st.sidebar.error("CSV 格式錯誤：必須包含「代號」欄位")
    except Exception as e:
        st.sidebar.error(f"讀取失敗: {e}")

st.sidebar.markdown("---")

# 3. 手動新增/刪除 (維持之前的設計)
with st.sidebar.expander("➕ / 🗑️ 手動編輯", expanded=False):
    # 新增
    col1, col2 = st.columns([2, 3])
    new_ticker = st.text_input("代號", placeholder="2330")
    new_name = st.text_input("名稱", placeholder="台積電")
    
    if st.button("加入"):
        if new_ticker:
            code = new_ticker.strip().upper()
            if code.isdigit() and len(code) >= 4: code += ".TW"
            name = new_name if new_name else code
            st.session_state.stock_dict[code] = name
            update_url() # 更新網址
            st.rerun()

    # 刪除
    del_options = list(st.session_state.stock_dict.keys())
    del_list = st.multiselect("移除股票", del_options, format_func=lambda x: f"{st.session_state.stock_dict[x]}")
    if st.button("確認移除"):
        for item in del_list:
            del st.session_state.stock_dict[item]
        update_url() # 更新網址
        st.rerun()

# --- 主畫面 ---
st.title("📈 樂活投資 K值偵測")
st.caption("K<20 買進 (綠) | K>80 賣出 (紅) | 網址即為您的專屬設定，請加入書籤保存。")

if st.button('🔄 更新股價'):
    st.cache_data.clear()
    st.rerun()

st.write("---")

# --- 核心計算 (KD) ---
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

# --- 顯示列表 ---
if not st.session_state.stock_dict:
    st.info("目前沒有股票，請上傳 CSV 或手動新增。")
else:
    for ticker, name in st.session_state.stock_dict.items():
        price, k = get_k_value(ticker)
        
        if price:
            if k < 20:
                color, action, bg = "#2e7d32", "🟢 買進", "#e8f5e9"
            elif k > 80:
                color, action, bg = "#c62828", "🔴 賣出", "#ffebee"
            else:
                color, action, bg = "#ef6c00", "🟡 觀望", "#fff3e0"
            
            st.markdown(
                f"""
                <div style="padding:15px; border-radius:10px; margin-bottom:10px; background-color:{bg}; border:1px solid #ddd;">
                    <div style="display:flex; justify-content:space-between;">
                        <div>
                            <strong style="font-size:1.2em; color:#333;">{name}</strong>
                            <div style="font-size:0.8em; color:#666;">{ticker}</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="color:{color}; font-weight:bold;">{action}</div>
                        </div>
                    </div>
                    <hr style="margin:8px 0; border-top:1px dashed #ccc;">
                    <div style="display:flex; justify-content:space-between;">
                        <span>現價: <b>{price:.2f}</b></span>
                        <span style="color:{color}">K值: <b>{k:.2f}</b></span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.error(f"❌ {name}: 讀取失敗")
