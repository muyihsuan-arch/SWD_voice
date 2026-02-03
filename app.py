import streamlit as st
import pandas as pd
import urllib.parse

# === 1. 設定區 (請務必修改這裡) ===
# 您的 Google Sheet CSV 連結
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQWueqZqoUXP7YM_UDDAedhAjYQI80RoNapxH8YyKbyLkq8L_CprL2eeQ7DEPBqdxqJCRVCiaRp9l6S/pub?output=csv"
PASSWORD = "888"

# 【關鍵】請填入您部署後的 Streamlit App 網址
# 網址結尾不要有斜線 /
# 例如： https://familymart-voice.streamlit.app
SITE_URL = "https://familymart-voice.streamlit.app" 

# === 2. 頁面設定與 CSS 黑魔法 (隱藏下載按鈕) ===
st.set_page_config(page_title="全家配音試聽", layout="centered")

# 這段 CSS 會強制把播放器的「下載按鈕」藏起來
st.markdown("""
    <style>
        /* 隱藏 Chrome/Edge/Safari 播放器的下載選單 */
        audio::-webkit-media-controls-enclosure {
            overflow: hidden;
        }
        audio::-webkit-media-controls-panel {
            width: calc(100% + 30px); /* 加寬把右邊的點點擠出去 */
        }
        /* 針對 Streamlit 的微調 */
        .stAudio {
            margin-top: 10px;
            margin-bottom: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# === 3. 讀取資料 ===
@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(CSV_URL)
        df.columns = df.columns.str.strip() # 清除欄位空白
        
        # 自動找欄位
        def get_col(candidates):
            for c in df.columns:
                if any(x in c.lower() for x in candidates):
                    return c
            return None

        col_name = get_col(["filename", "name", "檔名"])
        col_link = get_col(["link_source", "link", "連結"])
        col_voice = get_col(["voice", "category", "聲線"])
        col_style = get_col(["style", "type", "風格"])

        if not col_link:
            st.error("❌ 資料讀取錯誤：找不到連結欄位")
            return pd.DataFrame()

        df = df.rename(columns={
            col_name: 'Name', col_link: 'Link',
            col_voice: 'Voice', col_style: 'Style'
        })
        return df.dropna(subset=['Link'])
    except Exception as e:
        st.error(f"讀取失敗: {e}")
        return pd.DataFrame()

# === 4. 連結處理工具 ===
def get_player_link(raw_link):
    """確保連結可以串流播放 (強制 download=1)"""
    if not isinstance(raw_link, str): return ""
    clean = raw_link.replace('&download=1', '').replace('?download=1', '')
    return clean + ('&download=1' if '?' in clean else '?download=1')

# === 5. 主程式 ===
def main():
    # 抓取網址參數 ?n=...
    params = st.query_params
    target_name = params.get("n", None)
    
    df = load_data()
    if df.empty: return

    # -------------------------------------------------------
    # 【模式 A】客戶模式：網址有帶 ?n=檔名
    # -------------------------------------------------------
    if target_name:
        # 進行搜尋
        row = df[df['Name'] == target_name]
        
        if not row.empty:
            item = row.iloc[0]
            
            # --- 單一播放器介面 ---
            with st.container(border=True):
                st.subheader(f"🎵 {item['Name']}")
                st.caption(f"全家配音資料庫 | {item.get('Voice','')} | {item.get('Style','')}")
                
                # 1. 播放器 (已隱藏下載鈕)
                st.audio(get_player_link(item['Link']), format="audio/mp3")
                
                st.warning("⚠️ 僅供內部試聽，請勿下載或外流")
                
                st.divider()
                
                # 2. 手機版救援按鈕
                st.caption("若手機無法播放，請點擊下方按鈕：")
                st.link_button("↗ 開啟備用播放連結", get_player_link(item['Link']))

            # 讓客戶可以回首頁 (選用)
            if st.button("🏠 返回搜尋首頁"):
                st.query_params.clear()
                st.rerun()
                
        else:
            st.error("找不到該檔案，可能是連結錯誤或檔案已移除。")
            if st.button("回首頁"):
                st.query_params.clear()
                st.rerun()

    # -------------------------------------------------------
    # 【模式 B】管理員模式：網址乾淨
    # -------------------------------------------------------
    else:
        st.title("全家配音資料庫 (管理端)")

        # 登入檢查
        if "logged_in" not in st.session_state:
            st.session_state.logged_in = False

        if not st.session_state.logged_in:
            with st.form("login"):
                pw = st.text_input("請輸入管理密碼", type="password")
                if st.form_submit_button("登入"):
                    if pw == PASSWORD:
                        st.session_state.logged_in = True
                        st.rerun()
                    else:
                        st.error("密碼錯誤")
            return

        # --- 登入後介面 ---
        col1, col2 = st.columns(2)
        with col1:
            v_filter = st.selectbox("聲線", ["全部"] + list(df['Voice'].unique()))
        with col2:
            s_filter = st.selectbox("風格", ["全部"] + list(df['Style'].unique()))
        
        keyword = st.text_input("🔍 搜尋檔名", placeholder="輸入關鍵字...")

        # 篩選邏輯
        mask = pd.Series([True] * len(df))
        if v_filter != "全部": mask &= (df['Voice'] == v_filter)
        if s_filter != "全部": mask &= (df['Style'] == s_filter)
        if keyword: mask &= df['Name'].str.contains(keyword, case=False, na=False)
        
        results = df[mask]
        st.write(f"共找到 {len(results)} 筆")

        # 顯示列表 (限制 20 筆以免太長)
        for _, row in results.head(20).iterrows():
            with st.expander(f"📄 {row['Name']}"):
                # 播放器
                st.audio(get_player_link(row['Link']), format='audio/mp3')
                
                # 產生分享連結 (網址編碼處理)
                # 使用 urllib.parse.quote 確保中文字不會變成亂碼導致無法開啟
                safe_name = urllib.parse.quote(row['Name'])
                share_link = f"{SITE_URL}?n={safe_name}"
                
                st.text_input("🌏 外部分享連結 (客戶只能看到這個檔)", value=share_link, key=f"link_{row['Name']}")
                
                st.caption("👆 複製上方連結傳給客戶即可")

if __name__ == "__main__":
    main()
