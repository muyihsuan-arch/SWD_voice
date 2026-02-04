import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import requests
import base64

# === 1. 設定區 ===
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQWueqZqoUXP7YM_UDDAedhAjYQI80RoNapxH8YyKbyLkq8L_CprL2eeQ7DEPBqdxqJCRVCiaRp9l6S/pub?output=csv"
PASSWORD = "888"
SITE_URL = "https://swd-voice.streamlit.app"

# === 2. 核心技術：Base64 暴力解法 (解決 Safari 轉址問題) ===
@st.cache_data(ttl=300)  # 緩存 5 分鐘，避免重複抓取
def get_audio_base64(url):
    """
    直接從 SharePoint 抓取音檔並轉為 Base64。
    這能徹底解決 iPhone Safari 對於轉址兩次的安全性限制。
    """
    if not isinstance(url, str) or url == "":
        return None
    
    # 確保是直連網址
    target_url = url.split('?')[0] + "?download=1" if "sharepoint.com" in url else url

    try:
        # 由 Streamlit 伺服器發起請求，繞過客戶端瀏覽器限制
        resp = requests.get(target_url, timeout=15)
        if resp.status_code == 200:
            b64 = base64.b64encode(resp.content).decode('utf-8')
            return f"data:audio/mpeg;base64,{b64}"
    except Exception as e:
        st.error(f"連線失敗: {e}")
    return None

# === 3. 頁面設定 ===
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
    </style>
""", unsafe_allow_html=True)

# === 4. 資料讀取與複製元件 ===
@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(CSV_URL)
        df.columns = df.columns.str.strip()
        # 欄位映射簡化版 (邏輯與您原本一致)
        col_id = next((c for c in df.columns if "id" in c.lower() or "編號" in c), None)
        col_name = next((c for c in df.columns if "name" in c.lower() or "檔名" in c), None)
        col_link = next((c for c in df.columns if "link" in c.lower() or "連結" in c), None)
        df = df.rename(columns={col_id: 'ID', col_name: 'Name', col_link: 'Link_Source'})
        if 'ID' not in df.columns: df['ID'] = df['Name']
        df['Link_Player'] = df['Link_Source'] # 預設 Player 連結與 Source 一致
        df['Main_Style'] = df.get('主風格', '未分類').fillna('未分類')
        df['Sec_Style'] = df.get('副風格', '').fillna('')
        df['Voice'] = df.get('聲線', '未知').fillna('未知')
        return df.dropna(subset=['Link_Source'])
    except:
        return pd.DataFrame()

def show_share_dialog(title, link):
    st.caption(f"{title}")
    html_code = f"""<input type="text" value="{link}" id="cp" readonly style="width:100%;padding:10px;"><button onclick="navigator.clipboard.writeText('{link}').then(()=>alert('✅ 複製成功'))" style="width:100%;margin-top:5px;padding:10px;background:#28a745;color:white;border:none;border-radius:5px;cursor:pointer;">📋 點此複製</button>"""
    components.html(html_code, height=120)

# === 5. 主程式 ===
def main():
    params = st.query_params
    target_id = params.get("id", None)
    df = load_data()
    if df.empty: return

    # --- 【模式 A】 外部分享 (當網址帶有 ?id= 時) ---
    if target_id:
        target_row = df[df['ID'] == target_id]
        if not target_row.empty:
            item = target_row.iloc[0]
            st.subheader(f"🎵 {item['Name']}")
            
            # 使用暴力解法：轉 Base64
            with st.spinner("音檔載入中 (Safari 專用解決方案)..."):
                b64_data = get_audio_base64(item['Link_Source'])
            
            if b64_data:
                st.markdown(f'<audio controls style="width:100%;"><source src="{b64_data}" type="audio/mpeg"></audio>', unsafe_allow_html=True)
            else:
                st.error("此音檔無法開啟，請檢查來源網址。")
            
            if st.button("🏠 回首頁"):
                st.query_params.clear()
                st.rerun()
            return

    # --- 【模式 B】 內部列表 (首頁與搜尋) ---
    st.title("全家配音資料庫 📂")
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if not st.session_state.logged_in:
        with st.form("login"):
            pw = st.text_input("請輸入密碼", type="password")
            if st.form_submit_button("登入") and pw == PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
        return

    # 搜尋過濾 UI
    search_name = st.text_input("👤 搜尋名稱")
    results = df[df['Name'].str.contains(search_name, na=False)] if search_name else df

    for _, row in results.head(20).iterrows():
        with st.expander(f"📄 {row['Name']}"):
            # 只有點開 expander 時，才會去請求 Base64
            if st.button("▶️ 點我載入播放器", key=f"btn_{row['ID']}"):
                b64_data = get_audio_base64(row['Link_Source'])
                if b64_data:
                    st.markdown(f'<audio controls style="width:100%;"><source src="{b64_data}" type="audio/mpeg"></audio>', unsafe_allow_html=True)
                else:
                    st.error("載入失敗")
            
            st.write(f"風格: {row['Main_Style']} / {row['Sec_Style']}")
            if st.button("🌍 產生外部分享連結", key=f"share_{row['ID']}"):
                show_share_dialog("客戶試聽連結", f"{SITE_URL}?id={row['ID']}")

if __name__ == "__main__":
    main()
