import streamlit as st
import pandas as pd
import urllib.parse

# === 1. 設定區 ===
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQWueqZqoUXP7YM_UDDAedhAjYQI80RoNapxH8YyKbyLkq8L_CprL2eeQ7DEPBqdxqJCRVCiaRp9l6S/pub?output=csv"
PASSWORD = "888"

# 【請確認】這是您目前的 App 網址
SITE_URL = "https://swd-voice.streamlit.app"

# === 2. 頁面設定 ===
st.set_page_config(page_title="全家配音試聽", layout="centered")

# CSS: 隱藏下載按鈕 + 優化按鈕樣式
st.markdown("""
    <style>
        /* 隱藏原生播放器的下載選單 */
        audio::-webkit-media-controls-enclosure { overflow: hidden; }
        audio::-webkit-media-controls-panel { width: calc(100% + 30px); }
        
        /* 調整按鈕間距 */
        .stButton button { width: 100%; }
    </style>
""", unsafe_allow_html=True)

# === 3. 彈出視窗 (Dialog) ===
# 這是 Streamlit 新功能，專門用來做漂亮的彈窗
@st.dialog("複製連結")
def show_copy_modal(title, link):
    st.write(f"👇 {title}")
    # st.code 自帶複製按鈕，放在彈窗裡非常清楚，不會被擋住
    st.code(link, language="text")
    st.caption("點擊代碼框右上角的 📄 小圖示即可複製")

# === 4. 資料讀取 ===
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
        col_link = get_col(["link_source", "link", "連結"]) # D欄
        col_voice = get_col(["voice", "category", "聲線"])
        col_style = get_col(["style", "type", "風格"])

        if not col_link: return pd.DataFrame()

        df = df.rename(columns={col_name: 'Name', col_link: 'Link', col_voice: 'Voice', col_style: 'Style'})
        return df.dropna(subset=['Link'])
    except:
        return pd.DataFrame()

# === 5. 連結處理 ===
def get_link(raw_link):
    """回傳最原始的 OneDrive 連結 (Link_Source)"""
    if not isinstance(raw_link, str): return ""
    # 確保連結是乾淨的，沒有被加過奇怪參數
    clean = raw_link.replace('&download=1', '').replace('?download=1', '')
    return clean

def get_player_link(clean_link):
    """播放器專用：強制加上 download=1"""
    return clean_link + ('&download=1' if '?' in clean_link else '?download=1')

# === 6. HTML5 安全播放器 ===
def render_player(url):
    html_code = f"""
        <audio controls controlsList="nodownload" style="width: 100%; margin-bottom: 5px;">
            <source src="{url}" type="audio/mp3">
        </audio>
    """
    st.markdown(html_code, unsafe_allow_html=True)

# === 7. 主程式 ===
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
            clean_link = get_link(item['Link'])
            play_url = get_player_link(clean_link)
            
            with st.container(border=True):
                st.subheader(f"🎵 {item['Name']}")
                st.caption(f"{item.get('Voice','')} | {item.get('Style','')}")
                
                # 1. 播放器 (電腦用)
                render_player(play_url)
                
                # 2. 手機版按鈕 (應要求改名為「試聽」)
                # type="primary" 會讓按鈕變紅色/強調色，很顯眼
                st.link_button("▶️ 試聽 (開啟 OneDrive)", clean_link, type="primary", use_container_width=True)

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
            with st.form("login"):
                pw = st.text_input("密碼", type="password")
                if st.form_submit_button("登入"):
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
                clean_link = get_link(row['Link'])
                play_url = get_player_link(clean_link)
                
                # 播放器
                render_player(play_url)
                
                # 組合按鈕區 (使用 columns 排版)
                c1, c2 = st.columns(2)
                
                with c1:
                    # 按鈕 1：複製內部分享連結 (彈窗)
                    if st.button("📋 複製內部分享", key=f"in_{row['Name']}"):
                        show_copy_modal("內部分享連結 (OneDrive)", clean_link)
                
                with c2:
                    # 按鈕 2：複製外部分享連結 (彈窗)
                    if st.button("🌏 複製外部分享", key=f"out_{row['Name']}"):
                        safe_name = urllib.parse.quote(row['Name'])
                        share_link = f"{SITE_URL}?n={safe_name}"
                        show_copy_modal("外部分享連結 (單一Player)", share_link)

if __name__ == "__main__":
    main()
