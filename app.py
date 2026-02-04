import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import requests
import base64

# === 1. 設定區 ===
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQWueqZqoUXP7YM_UDDAedhAjYQI80RoNapxH8YyKbyLkq8L_CprL2eeQ7DEPBqdxqJCRVCiaRp9l6S/pub?output=csv"
PASSWORD = "888"
SITE_URL = "https://swd-voice.streamlit.app"

# === 2. 核心技術：Base64 抓取函數 ===
@st.cache_data(ttl=600)
def get_audio_base64(url):
    if not isinstance(url, str) or url == "": return None
    target_url = url.split('?')[0] + "?download=1" if "sharepoint.com" in url else url
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(target_url, headers=headers, timeout=20)
        if resp.status_code == 200:
            b64 = base64.b64encode(resp.content).decode('utf-8')
            return f"data:audio/mpeg;base64,{b64}"
    except: return None
    return None

# === 3. 頁面配置與 CSS ===
st.set_page_config(page_title="全家配音試聽", layout="centered")

st.markdown("""
    <style>
        /* 隱藏原生播放器的下載選單 (針對 Webkit) */
        audio::-webkit-media-controls-enclosure { overflow: hidden; }
        audio::-webkit-media-controls-panel { width: calc(100% + 30px); }
        .stButton button { border-radius: 8px; font-weight: bold; }
        
        /* 針對 PC 的額外保護：禁用右鍵 */
        audio { pointer-events: auto; }
    </style>
""", unsafe_allow_html=True)

# === 4. 資料讀取 (恢復完整欄位) ===
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
        col_voice = get_col(["voice", "category", "聲線"])
        col_main = get_col(["style", "主風格"])
        col_sec = get_col(["sec style", "副風格"])

        rename_map = { col_name: 'Name', col_link: 'Link_Source', col_voice: 'Voice', col_main: 'Main_Style', col_sec: 'Sec_Style' }
        if col_id: rename_map[col_id] = 'ID'
        
        df = df.rename(columns=rename_map)
        if 'ID' not in df.columns: df['ID'] = df['Name'].astype(str)
        df['Main_Style'] = df['Main_Style'].fillna("未分類")
        df['Sec_Style'] = df['Sec_Style'].fillna("")
        return df.dropna(subset=['Link_Source'])
    except: return pd.DataFrame()

# === 5. 播放器渲染 (隱藏下載鈕) ===
def render_player(b64_data):
    # 使用 HTML5 屬性禁用下載按鈕
    st.markdown(f"""
        <div style="background:#f1f3f4; padding:10px; border-radius:10px; border:1px solid #ddd;">
            <audio controls controlsList="nodownload" oncontextmenu="return false;" style="width:100%;">
                <source src="{b64_data}" type="audio/mpeg">
            </audio>
        </div>
    """, unsafe_allow_html=True)

# === 6. 主程式 ===
def main():
    params = st.query_params
    target_id = params.get("id", None)
    df = load_data()
    if df.empty: return

    # --- [模式 A] 外部分享 ---
    if target_id:
        target_row = df[df['ID'] == str(target_id)]
        if not target_row.empty:
            item = target_row.iloc[0]
            st.subheader(f"🎵 {item['Name']}")
            with st.spinner("載入中..."):
                b64_audio = get_audio_base64(item['Link_Source'])
            if b64_audio: render_player(b64_audio)
            else: st.error("音檔讀取失敗")
            
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
            if st.form_submit_button("登入") and pw == PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
        return

    # 搜尋與篩選區 (找回主/副風格)
    with st.container(border=True):
        search_name = st.text_input("👤 搜尋關鍵字")
        c1, c2, c3 = st.columns(3)
        with c1: filter_male = st.checkbox("🙋‍♂️ 男聲")
        with c2: filter_female = st.checkbox("🙋‍♀️ 女聲")
        with c3: filter_remote = st.checkbox("🏠 可遠距")
        
        # 找回風格選單
        sel_c1, sel_c2 = st.columns(2)
        with sel_c1:
            main_opts = ["全部"] + sorted([x for x in df['Main_Style'].unique() if x != "未分類"])
            sel_main = st.selectbox("📂 主風格", main_opts)
        with sel_c2:
            if sel_main == "全部": sec_df = df
            else: sec_df = df[df['Main_Style'] == sel_main]
            sec_opts = ["全部"] + sorted([x for x in sec_df['Sec_Style'].unique() if x != ""])
            sel_sec = st.selectbox("🏷️ 副風格", sec_opts)

    # 過濾邏輯
    mask = pd.Series([True] * len(df))
    if search_name: mask &= df['Name'].str.contains(search_name, case=False, na=False)
    if filter_male and not filter_female: mask &= df['Voice'].str.contains("男", na=False)
    elif filter_female and not filter_male: mask &= df['Voice'].str.contains("女", na=False)
    if filter_remote: mask &= df['Name'].str.contains("遠距", na=False)
    if sel_main != "全部": mask &= (df['Main_Style'] == sel_main)
    if sel_sec != "全部": mask &= (df['Sec_Style'] == sel_sec)
    
    results = df[mask]
    st.caption(f"🎯 共找到 {len(results)} 筆資料")

    for _, row in results.head(20).iterrows():
        with st.expander(f"📄 {row['Name']}"):
            if st.button(f"▶️ 載入播放器", key=f"p_{row['ID']}"):
                b64_data = get_audio_base64(row['Link_Source'])
                if b64_data: render_player(b64_data)
                else: st.error("載入失敗")
            
            # 分享連結
            if st.button("🌏 產生外部分享連結", key=f"s_{row['ID']}"):
                share_url = f"{SITE_URL}?id={row['ID']}"
                st.code(share_url, language=None)
                st.success("請複製上方網址給客戶")

if __name__ == "__main__":
    main()
