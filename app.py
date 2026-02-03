import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import urllib.parse

# === 1. 設定區 ===
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQWueqZqoUXP7YM_UDDAedhAjYQI80RoNapxH8YyKbyLkq8L_CprL2eeQ7DEPBqdxqJCRVCiaRp9l6S/pub?output=csv"
PASSWORD = "888"
# 【關鍵】請確認這是您 App 的網址 (結尾不要有斜線)
SITE_URL = "https://swd-voice.streamlit.app"

# === 2. 頁面與 CSS 設定 ===
st.set_page_config(page_title="全家配音試聽", layout="centered")

st.markdown("""
    <style>
        /* === RWD 分流：手機 vs 電腦 === */
        
        /* 電腦版 (寬度 > 768px)：隱藏手機專用按鈕 */
        @media (min-width: 769px) {
            .mobile-only { display: none !important; }
        }
        
        /* 手機版 (寬度 <= 768px)：隱藏電腦播放器，顯示手機按鈕 */
        @media (max-width: 768px) {
            .pc-only { display: none !important; }
            .mobile-only { display: block !important; }
        }

        /* 隱藏原生播放器的下載選單 */
        audio::-webkit-media-controls-enclosure { overflow: hidden; }
        audio::-webkit-media-controls-panel { width: calc(100% + 30px); }
        
        /* 按鈕樣式優化 */
        .stButton button { border-radius: 8px; font-weight: bold; }
        
        /* 標籤按鈕文字加大 */
        div[data-testid="stCheckbox"] label { font-size: 16px !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# === 3. 核心功能：自製「一鍵複製」按鈕 (HTML/JS) ===
def render_copy_ui(text_to_copy):
    """
    這段程式碼會產生一個「網址框 + 綠色大按鈕」，
    完全模擬您提供的截圖介面，解決手機複製困難的問題。
    """
    html_code = f"""
    <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px;">
        <label style="font-size:14px; color:#333; font-weight:bold; margin-bottom:5px; display:block;">👇 連結網址</label>
        <input type="text" value="{text_to_copy}" id="copyInput" readonly 
            style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; color: #555; background-color: #fff; margin-bottom: 10px;">
        
        <button onclick="copyToClipboard()" 
            style="width: 100%; padding: 12px; background-color: #28a745; color: white; border: none; border-radius: 5px; font-size: 16px; font-weight: bold; cursor: pointer; transition: 0.3s;">
            📋 複製連結
        </button>
        
        <script>
            function copyToClipboard() {{
                var copyText = document.getElementById("copyInput");
                copyText.select();
                copyText.setSelectionRange(0, 99999); /* For mobile devices */
                navigator.clipboard.writeText(copyText.value).then(function() {{
                    alert("✅ 複製成功！");
                }}, function(err) {{
                    alert("❌ 複製失敗，請手動複製");
                }});
            }}
        </script>
    </div>
    """
    components.html(html_code, height=180)

# === 4. 彈出視窗 ===
@st.dialog("🔗 分享連結")
def show_share_dialog(title, link):
    st.caption(f"{title}")
    # 呼叫上面的自製元件
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

        # 欄位對應
        col_name = get_col(["filename", "name", "檔名"])
        col_link = get_col(["link_source", "link", "連結"])
        col_voice = get_col(["voice", "category", "聲線"]) # 通常是男女
        col_main = get_col(["style", "主風格"]) # Sheet裡的 Style
        col_sec = get_col(["sec style", "副風格"]) # Sheet裡的 Sec Style

        if not col_link: return pd.DataFrame()

        rename_map = {
            col_name: 'Name', col_link: 'Link', 
            col_voice: 'Voice', col_main: 'Main_Style'
        }
        if col_sec: rename_map[col_sec] = 'Sec_Style'
        
        df = df.rename(columns=rename_map)
        
        # 補空值
        if 'Sec_Style' not in df.columns: df['Sec_Style'] = ""
        df['Main_Style'] = df['Main_Style'].fillna("未分類")
        df['Sec_Style'] = df['Sec_Style'].fillna("")
        
        return df.dropna(subset=['Link'])
    except:
        return pd.DataFrame()

# === 6. 連結處理 ===
def get_clean_link(link):
    if not isinstance(link, str): return ""
    return link.replace('&download=1', '').replace('?download=1', '')

def get_player_link(link):
    clean = get_clean_link(link)
    return clean + ('&download=1' if '?' in clean else '?download=1')

# === 7. UI 元件：手機按鈕 ===
def render_mobile_btn(url):
    st.markdown(f"""
        <div class="mobile-only" style="margin-bottom: 10px;">
            <a href="{url}" target="_blank" style="
                display: block; width: 100%; padding: 15px; 
                background-color: #FF4B4B; color: white; 
                text-align: center; text-decoration: none; 
                font-size: 16px; font-weight: bold; border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                ▶️ 試聽 (開啟 OneDrive)
            </a>
        </div>
    """, unsafe_allow_html=True)

# === 8. 主程式 ===
def main():
    params = st.query_params
    target_name = params.get("n", None)
    df = load_data()
    if df.empty: return

    # --- [模式 A] 客戶單一播放模式 (外部分享) ---
    if target_name:
        row = df[df['Name'] == target_name]
        
        if not row.empty:
            item = row.iloc[0]
            clean_link = get_clean_link(item['Link'])
            play_link = get_player_link(clean_link)
            
            with st.container(border=True):
                st.subheader(f"🎵 {item['Name']}")
                
                # PC: 顯示安全播放器
                st.markdown(f"""
                    <div class="pc-only">
                        <audio controls controlsList="nodownload" style="width: 100%;">
                            <source src="{play_link}" type="audio/mp3">
                        </audio>
                    </div>
                """, unsafe_allow_html=True)
                
                # Mobile: 顯示試聽按鈕
                render_mobile_btn(clean_link)
                
                st.divider()
                st.warning("⚠️ 僅供內部試聽，禁止下載")
                
            if st.button("🏠 回搜尋首頁"):
                st.query_params.clear()
                st.rerun()
        else:
            st.error("找不到檔案")

    # --- [模式 B] 管理員模式 ---
    else:
        st.title("全家配音資料庫 📂")

        if "logged_in" not in st.session_state: st.session_state.logged_in = False
        if not st.session_state.logged_in:
            # 單一輸入框直接登入
            pw = st.text_input("請輸入密碼", type="password")
            if pw and st.button("登入"):
                if pw == PASSWORD:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("密碼錯誤")
            return

        # === 搜尋與篩選區 ===
        with st.container(border=True):
            # 1. 搜尋 Bar
            search_name = st.text_input("🔍 配音員名稱 / 關鍵字", placeholder="例如：林佩璇...")
            
            # 2. 標籤按鈕 (Tags)
            col_t1, col_t2, col_t3 = st.columns(3)
            with col_t1: filter_male = st.checkbox("🙋‍♂️ 男聲")
            with col_t2: filter_female = st.checkbox("🙋‍♀️ 女聲")
            with col_t3: filter_remote = st.checkbox("🏠 可遠距")
            
            # 3. 風格連動選單
            c1, c2 = st.columns(2)
            with c1:
                # 主風格 (Style)
                main_opts = ["全部"] + sorted([x for x in df['Main_Style'].unique() if x != "未分類"])
                sel_main = st.selectbox("📂 主風格", main_opts)
            with c2:
                # 副風格 (Sec Style) - 根據主風格連動
                if sel_main == "全部":
                    sec_source = df
                else:
                    sec_source = df[df['Main_Style'] == sel_main]
                
                # 排除空值
                valid_secs = [x for x in sec_source['Sec_Style'].unique() if x != ""]
                sel_sec = st.selectbox("🏷️ 副風格", ["全部"] + sorted(valid_secs))

        # === 執行篩選 ===
        mask = pd.Series([True] * len(df))
        
        # 關鍵字
        if search_name: mask &= df['Name'].str.contains(search_name, case=False, na=False)
        
        # 性別 (全選或不選 = 全部)
        if filter_male and not filter_female:
            mask &= df['Voice'].str.contains("男", na=False)
        elif filter_female and not filter_male:
            mask &= df['Voice'].str.contains("女", na=False)
        
        # 遠距
        if filter_remote:
            mask &= df['Name'].str.contains("遠距", na=False)
            
        # 風格
        if sel_main != "全部": mask &= (df['Main_Style'] == sel_main)
        if sel_sec != "全部": mask &= (df['Sec_Style'] == sel_sec)

        results = df[mask]
        st.caption(f"🎯 共找到 {len(results)} 筆資料")

        # === 列表顯示 ===
        for _, row in results.head(20).iterrows():
            with st.expander(f"📄 {row['Name']}"):
                clean_link = get_clean_link(row['Link'])
                play_link = get_player_link(clean_link)
                
                # 1. PC 播放器
                st.markdown(f"""
                    <div class="pc-only">
                        <audio controls controlsList="nodownload" style="width: 100%; margin-bottom: 10px;">
                            <source src="{play_link}" type="audio/mp3">
                        </audio>
                    </div>
                """, unsafe_allow_html=True)
                
                # 2. 手機試聽按鈕
                render_mobile_btn(clean_link)
                
                # 3. 分享按鈕區
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("📋 內部分享", key=f"in_{row['Name']}"):
                        show_share_dialog("內部分享連結 (OneDrive)", clean_link)
                with b2:
                    if st.button("🌏 外部分享", key=f"out_{row['Name']}"):
                        # 產生 Streamlit 外部分享連結
                        safe_name = urllib.parse.quote(row['Name'])
                        share_link = f"{SITE_URL}?n={safe_name}"
                        show_share_dialog("外部分享連結 (客戶試聽用)", share_link)

if __name__ == "__main__":
    main()
