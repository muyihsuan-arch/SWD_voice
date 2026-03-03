import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import requests
import base64
import time  # 用於判斷 30 分鐘時效

# === 1. 設定區 ===
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQWueqZqoUXP7YM_UDDAedhAjYQI80RoNapxH8YyKbyLkq8L_CprL2eeQ7DEPBqdxqJCRVCiaRp9l6S/pub?output=csv"
PASSWORD = "888"
SITE_URL = "https://swd-voice.streamlit.app"
TIMEOUT_SECONDS = 1800  # 30 分鐘 = 1800 秒

# === 2. 核心技術：Base64 抓取函數 (解決 Safari 轉址問題) ===
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

# === 3. 頁面與 CSS 設定 ===
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
        div[data-testid="stCheckbox"] label { font-size: 16px !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# === 4. 複製按鈕與 Dialog 元件 ===
def render_copy_ui(text_to_copy):
    html_code = f"""
    <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px;">
        <label style="font-size:14px; color:#333; font-weight:bold; margin-bottom:5px; display:block;">👇 連結網址</label>
        <input type="text" value="{text_to_copy}" id="copyInput" readonly 
            style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; color: #555; background-color: #fff; margin-bottom: 10px;">
        <button onclick="copyToClipboard()" 
            style="width: 100%; padding: 12px; background-color: #28a745; color: white; border: none; border-radius: 5px; font-size: 16px; font-weight: bold; cursor: pointer;">
            📋 點此一鍵複製
        </button>
        <script>
            function copyToClipboard() {{
                var copyText = document.getElementById("copyInput");
                copyText.select();
                copyText.setSelectionRange(0, 99999);
                navigator.clipboard.writeText(copyText.value).then(function() {{
                    alert("✅ 複製成功！");
                }});
            }}
        </script>
    </div>
    """
    components.html(html_code, height=180)

@st.dialog("🔗 分享連結")
def show_share_dialog(title, link):
    st.caption(f"{title}")
    render_copy_ui(link)

# === 5. 資料讀取 ===
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

# === 6. 主程式 ===
def main():
    # --- A. 初始化與自動登出邏輯 ---
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "login_time" not in st.session_state:
        st.session_state.login_time = 0

    # 檢查登入是否超時
    if st.session_state.logged_in:
        elapsed_time = time.time() - st.session_state.login_time
        if elapsed_time > TIMEOUT_SECONDS:
            st.session_state.logged_in = False
            st.warning("登入已超過 30 分鐘，為了安全已自動登出。")

    params = st.query_params
    target_id = params.get("id", None)
    df = load_data()
    if df.empty: return

    # --- B. [模式 A] 外部分享頁面 (客戶看) ---
    if target_id:
        target_row = df[df['ID'] == str(target_id)]
        if not target_row.empty:
            item = target_row.iloc[0]
            # 調整標題格式以符合參考圖
            st.subheader(f"🎵 作品預覽 : {item['Name']}")
            
            with st.spinner("音檔載入中..."):
                b64_data = get_audio_base64(item['Link_Source'])
            
            if b64_data:
                # 插入警示語語塊
                st.warning("⚠️ 此連結未經授權請勿分享或錄製，如有違規可能涉及法律裁罰，請務必遵守。")
                
                # 播放器
                st.markdown(f'<audio controls controlsList="nodownload" style="width:100%;"><source src="{b64_data}" type="audio/mpeg"></audio>', unsafe_allow_html=True)
            else: st.error("載入失敗")
            
            st.divider()
            
            # 回首頁按鈕：調整文字以符合參考圖
            if st.button("🏠 回到首頁"):
                st.query_params.clear()
                st.rerun()
            return

    # --- C. [模式 B] 內部列表 ---
    st.title("全家配音員資料庫 📂")
    
    # 登入檢查
    if not st.session_state.logged_in:
        with st.form("login_form"):
            st.write("請輸入密碼以進入資料庫")
            pw = st.text_input("Password", type="password", label_visibility="collapsed")
            if st.form_submit_button("登入", type="primary", use_container_width=True):
                if pw == PASSWORD:
                    st.session_state.logged_in = True
                    st.session_state.login_time = time.time()  # 紀錄登入時間
                    st.rerun()
                else:
                    st.error("密碼錯誤")
        return

    # --- D. 搜尋與篩選介面 ---
    with st.container(border=True):
        search_name = st.text_input("👤 搜尋關鍵字")
        c1, c2, c3 = st.columns(3)
        with c1: filter_male = st.checkbox("🙋‍♂️ 男聲")
        with c2: filter_female = st.checkbox("🙋‍♀️ 女聲")
        with c3: filter_remote = st.checkbox("🏠 可遠距")
        
        sel_c1, sel_c2 = st.columns(2)
        with sel_c1:
            main_opts = ["全部"] + sorted([x for x in df['Main_Style'].unique() if x != "未分類"])
            sel_main = st.selectbox("📂 主風格", main_opts)
        with sel_c2:
            if sel_main == "
