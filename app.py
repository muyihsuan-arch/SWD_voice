import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import requests
import base64
import urllib.parse

# === 1. 設定區 ===
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQWueqZqoUXP7YM_UDDAedhAjYQI80RoNapxH8YyKbyLkq8L_CprL2eeQ7DEPBqdxqJCRVCiaRp9l6S/pub?output=csv"
PASSWORD = "888"
SITE_URL = "https://swd-voice.streamlit.app"

# === 2. 核心技術：Base64 抓取函數 ===
@st.cache_data(ttl=600)
def get_audio_base64(url):
    """
    由伺服器端抓取音檔並轉為 Base64 字串，徹底繞過 Safari 對於 SharePoint 轉址的封鎖。
    """
    if not isinstance(url, str) or url == "":
        return None
    
    # 強制轉為直連網址
    target_url = url.split('?')[0] + "?download=1" if "sharepoint.com" in url else url
    
    try:
        # 模擬瀏覽器請求，避免被 SharePoint 阻擋
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(target_url, headers=headers, timeout=20)
        if resp.status_code == 200:
            b64 = base64.b64encode(resp.content).decode('utf-8')
            return f"data:audio/mpeg;base64,{b64}"
    except Exception as e:
        return None
    return None

# === 3. 頁面配置與 CSS ===
st.set_page_config(page_title="全家配音試聽", layout="centered")

st.markdown("""
    <style>
        @media (min-width: 901px) { .mobile-only { display: none !important; } }
        @media (max-width: 900px) {
            .pc-only { display: none !important; }
            .mobile-only { display: block !important; }
        }
        audio::-webkit-media-controls-enclosure { overflow: hidden; }
        audio::-webkit-media-controls-panel { width: calc(100% + 30px); }
        .stButton button { border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# === 4. 複製按鈕 UI ===
def render_copy_ui(text_to_copy):
    html_code = f"""
    <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px;">
        <input type="text" value="{text_to_copy}" id="copyInput" readonly style="width: 100%; padding: 10px; margin-bottom: 10px;">
        <button onclick="navigator.clipboard.writeText('{text_to_copy}').then(()=>alert('✅ 複製成功！'))" 
            style="width: 100%; padding: 12px; background-color: #28a745; color: white; border: none; border-radius: 5px; font-weight: bold; cursor: pointer;">
            📋 點此一鍵複製
        </button>
    </div>
    """
    components.html(html_code, height=150)

@st.dialog("🔗 分享連結")
def show_share_dialog(title, link):
    st.caption(f"{title}")
    render_copy_ui(link)

# === 5. 資料讀取 (恢復您原本的欄位判斷邏輯) ===
@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(CSV_URL)
        df.columns = df.columns.str.strip()
        
        def get_col(candidates):
            for c in df.columns:
                if any(x in c.lower() for x in candidates): return c
            return None

        col_id = get_col(["id", "編號"])
        col_name = get_col(["filename", "name", "檔名"])
        col_link = get_col(["link_source", "link", "連結"])
        col_player = get_col(["link_player", "player", "播放連結"]) 
        col_voice = get_col(["voice", "category", "聲線"])
        col_main = get_col(["style", "主風格"])
        col_sec = get_col(["sec style", "副風格"])

        if not col_link: return pd.DataFrame()

        rename_map = { col_name: 'Name', col_link: 'Link_Source', col_voice: 'Voice', col_main: 'Main_Style' }
        if col_id: rename_map[col_id] = 'ID'
        if col_player: rename_map[col_player] = 'Link_Player'
        if col_sec: rename_map[col_sec] = 'Sec_Style'
        
        df = df.rename(columns=rename_map)
        if 'ID' not in df.columns: df['ID'] = df['Name']
        if 'Link_Player' not in df.columns: df['Link_Player'] = df['Link_Source']
        df['Link_Player'] = df['Link_Player'].fillna(df['Link_Source'])
        df['Main_Style'] = df['Main_Style'].fillna("未分類")
        df['Sec_Style'] = df['Sec_Style'].fillna("")
        
        return df.dropna(subset=['Link_Source'])
    except:
        return pd.DataFrame()

# === 6. 主程式 ===
def main():
    params = st.query_params
    target_id = params.get("id", None)
    
    df = load_data()
    if df.empty:
        st.error("無法載入資料，請檢查 Google Sheet 連結。")
        return

    # --- [模式 A] 外部分享 (客戶頁面) ---
    if target_id:
        target_row = df[df['ID'] == str(target_id)]
        if not target_row.empty:
            item = target_row.iloc[0]
            st.subheader(f"🎵 {item['Name']}")
            
            # 針對 Safari 進行 Base64 轉換
            with st.spinner("音檔載入中 (解決手機播放問題)..."):
                b64_audio = get_audio_base64(item['Link_Player'])
            
            if b64_audio:
                st.markdown(f"""
                    <div style="background:#f9f9f9; padding:20px; border-radius:15px; border:1px solid #ddd;">
                        <audio controls style="width:100%;"><source src="{b64_audio}" type="audio/mpeg"></audio>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.error("音檔載入失敗，可能因公司網路限制。請點擊下方紅按鈕試試。")
                st.link_button("▶️ 嘗試直接開啟音檔", item['Link_Source'], use_container_width=True)
            
            st.divider()
            if st.button("🏠 回搜尋首頁"):
                st.query_params.clear()
                st.rerun()
            return

    # --- [模式 B] 內部列表 ---
    st.title("全家配音資料庫 📂")
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in:
        with st.form("login"):
            pw = st.text_input("請輸入密碼", type="password")
            if st.form_submit_button("登入", type="primary"):
                if pw == PASSWORD:
                    st.session_state.logged_in = True
                    st.rerun()
                else: st.error("密碼錯誤")
        return

    # 篩選區
    with st.container(border=True):
        search_name = st.text_input("👤 搜尋關鍵字")
        c1, c2, c3 = st.columns(3)
        with c1: filter_male = st.checkbox("🙋‍♂️ 男聲")
        with c2: filter_female = st.checkbox("🙋‍♀️ 女聲")
        with c3: filter_remote = st.checkbox("🏠 可遠距")

    # 過濾邏輯
    mask = pd.Series([True] * len(df))
    if search_name: mask &= df['Name'].str.contains(search_name, case=False, na=False)
    if filter_male and not filter_female: mask &= df['Voice'].str.contains("男", na=False)
    elif filter_female and not filter_male: mask &= df['Voice'].str.contains("女", na=False)
    if filter_remote: mask &= df['Name'].str.contains("遠距", na=False)
    
    results = df[mask]
    st.caption(f"🎯 共找到 {len(results)} 筆資料")

    for _, row in results.head(20).iterrows():
        with st.expander(f"📄 {row['Name']}"):
            # 只有點擊按鈕才執行 Base64 轉換，避免頁面卡死
            if st.button(f"▶️ 載入播放器", key=f"play_{row['ID']}"):
                b64_data = get_audio_base64(row['Link_Player'])
                if b64_data:
                    st.markdown(f'<audio controls style="width:100%;"><source src="{b64_data}" type="audio/mpeg"></audio>', unsafe_allow_html=True)
                else:
                    st.error("載入失敗")

            b1, b2 = st.columns(2)
            with b1:
                if st.button("📋 內部分享", key=f"in_{row['ID']}"):
                    show_share_dialog("內部分享連結", row['Link_Source'])
            with b2:
                if st.button("🌏 外部分享", key=f"out_{row['ID']}"):
                    st.write(f"複製此代碼: {SITE_URL}?id={row['ID']}")

if __name__ == "__main__":
    main()
