import streamlit as st
import pandas as pd
import urllib.parse

# === 1. 設定區 (請確認這裡) ===
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQWueqZqoUXP7YM_UDDAedhAjYQI80RoNapxH8YyKbyLkq8L_CprL2eeQ7DEPBqdxqJCRVCiaRp9l6S/pub?output=csv"
PASSWORD = "888"

# 請確認這是您目前的 Streamlit 網址
SITE_URL = "https://swd-voice.streamlit.app"

# === 2. 頁面設定 ===
st.set_page_config(page_title="全家配音試聽", layout="centered")

# CSS: 優化手機按鈕樣式 + 隱藏播放器右鍵選單
st.markdown("""
    <style>
        .big-btn {
            display: inline-block;
            width: 100%;
            padding: 12px;
            background-color: #0097DA;
            color: white !important;
            text-align: center;
            text-decoration: none;
            font-weight: bold;
            border-radius: 8px;
            margin-top: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .big-btn:hover { background-color: #007bb5; }
        
        /* 微調 st.code 的樣式，讓它看起來不那麼像程式碼 */
        .stCodeBlock { margin-top: -10px; }
    </style>
""", unsafe_allow_html=True)

# === 3. 讀取資料 ===
@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(CSV_URL)
        df.columns = df.columns.str.strip()
        
        def get_col(candidates):
            for c in df.columns:
                if any(x in c.lower() for x in candidates): return c
            return None

        col_name = get_col(["filename", "name", "檔名"])
        col_link = get_col(["link_source", "link", "連結"])
        col_voice = get_col(["voice", "category", "聲線"])
        col_style = get_col(["style", "type", "風格"])

        if not col_link: return pd.DataFrame()

        df = df.rename(columns={col_name: 'Name', col_link: 'Link', col_voice: 'Voice', col_style: 'Style'})
        return df.dropna(subset=['Link'])
    except:
        return pd.DataFrame()

# === 4. 連結處理 ===
def get_link(raw_link, mode="play"):
    if not isinstance(raw_link, str): return ""
    clean = raw_link.replace('&download=1', '').replace('?download=1', '')
    connector = '&' if '?' in clean else '?'
    return clean + connector + 'download=1'

# === 5. 安全播放器元件 (關鍵修改) ===
def render_safe_player(url):
    """
    使用 HTML5 audio 標籤並加上 controlsList="nodownload"
    這能強制隱藏瀏覽器原生的下載按鈕
    """
    html_code = f"""
        <audio controls controlsList="nodownload" style="width: 100%; margin-bottom: 10px;">
            <source src="{url}" type="audio/mp3">
            您的瀏覽器不支援播放功能
        </audio>
    """
    st.markdown(html_code, unsafe_allow_html=True)

# === 6. 主程式 ===
def main():
    params = st.query_params
    target_name = params.get("n", None)
    
    df = load_data()
    if df.empty: return

    # --- [模式 A] 客戶單一播放模式 ---
    if target_name:
        row = df[df['Name'] == target_name]
        
        if not row.empty:
            item = row.iloc[0]
            play_url = get_link(item['Link'], "play")
            
            with st.container(border=True):
                st.subheader(f"🎵 {item['Name']}")
                st.caption(f"{item.get('Voice','')} | {item.get('Style','')}")
                
                # 1. 安全播放器 (無下載鈕)
                render_safe_player(play_url)
                
                # 2. 手機版救援按鈕
                st.markdown(f'''
                    <a href="{play_url}" target="_blank" class="big-btn">
                        📲 手機點此播放 (解決無法播放問題)
                    </a>
                ''', unsafe_allow_html=True)

                st.divider()
                st.warning("⚠️ 僅供內部試聽，禁止下載")

            if st.button("🏠 回首頁"):
                st.query_params.clear()
                st.rerun()
        else:
            st.error("找不到檔案")

    # --- [模式 B] 管理員模式 ---
    else:
        st.title("全家配音資料庫 📂")

        if "logged_in" not in st.session_state: st.session_state.logged_in = False
        if not st.session_state.logged_in:
            pw = st.text_input("密碼", type="password")
            if st.button("登入"):
                if pw == PASSWORD:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("錯誤")
            return

        # 搜尋介面
        keyword = st.text_input("🔍 搜尋檔名")
        
        filtered_df = df
        if keyword:
            filtered_df = df[df['Name'].str.contains(keyword, case=False, na=False)]

        # 列表顯示
        for _, row in filtered_df.head(20).iterrows():
            with st.expander(f"📄 {row['Name']}"):
                # 安全播放器
                play_url = get_link(row['Link'], "play")
                render_safe_player(play_url)
                
                # 產生分享連結
                safe_name = urllib.parse.quote(row['Name'])
                share_link = f"{SITE_URL}?n={safe_name}"
                
                st.caption("🌏 外部分享連結 (點擊右上方圖示複製)：")
                # 【一鍵複製神器】st.code 自帶複製按鈕
                st.code(share_link, language="text")
                
                # 內部連結按鈕
                st.link_button("🏢 OneDrive 原始檔", row['Link'])

if __name__ == "__main__":
    main()
