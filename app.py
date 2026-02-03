import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import urllib.parse

# === 1. 設定區 ===
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQWueqZqoUXP7YM_UDDAedhAjYQI80RoNapxH8YyKbyLkq8L_CprL2eeQ7DEPBqdxqJCRVCiaRp9l6S/pub?output=csv"
PASSWORD = "888"
# 【關鍵】請確認這是您 App 的網址
SITE_URL = "https://swd-voice.streamlit.app"

# === 2. 頁面與 CSS 設定 ===
st.set_page_config(page_title="全家配音試聽", layout="centered")

st.markdown("""
    <style>
        /* === RWD 分流設定 === */
        
        /* 電腦版 (螢幕 > 900px)：隱藏手機按鈕 */
        @media (min-width: 901px) {
            .mobile-only { display: none !important; }
        }
        
        /* 手機/平板版 (螢幕 <= 900px)：隱藏電腦播放器，顯示手機按鈕 */
        @media (max-width: 900px) {
            .pc-only { display: none !important; }
            .mobile-only { display: block !important; }
        }

        /* 隱藏原生播放器的下載選單 */
        audio::-webkit-media-controls-enclosure { overflow: hidden; }
        audio::-webkit-media-controls-panel { width: calc(100% + 30px); }
        
        /* 調整按鈕 */
        .stButton button { border-radius: 8px; font-weight: bold; }
        div[data-testid="stCheckbox"] label { font-size: 16px !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# === 3. 核心功能：自製「一鍵複製」按鈕 ===
def render_copy_ui(text_to_copy):
    html_code = f"""
    <div style="background-color: #f0f2f6; padding: 15px; border-radius: 10px;">
        <label style="font-size:14px; color:#333; font-weight:bold; margin-bottom:5px; display:block;">👇 連結網址</label>
        <input type="text" value="{text_to_copy}" id="copyInput" readonly 
            style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; color: #555; background-color: #fff; margin-bottom: 10px;">
        
        <button onclick="copyToClipboard()" 
            style="width: 100%; padding: 12px; background-color: #28a745; color: white; border: none; border-radius: 5px; font-size: 16px; font-weight: bold; cursor: pointer; transition: 0.3s;">
            📋 點此一鍵複製
        </button>
        
        <script>
            function copyToClipboard() {{
                var copyText = document.getElementById("copyInput");
                copyText.select();
                copyText.setSelectionRange(0, 99999);
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

        # 自動對應欄位
        col_id = get_col(["id", "編號"])
        col_name = get_col(["filename", "name", "檔名"])
        col_link = get_col(["link_source", "link", "連結"])
        col_voice = get_col(["voice", "category", "聲線"])
        col_main = get_col(["style", "主風格"])
        col_sec = get_col(["sec style", "副風格"])

        if not col_link: return pd.DataFrame()

        rename_map = { 
            col_name: 'Name', 
            col_link: 'Link', 
            col_voice: 'Voice', 
            col_main: 'Main_Style' 
        }
        if col_id: rename_map[col_id] = 'ID'
        if col_sec: rename_map[col_sec] = 'Sec_Style'
        
        df = df.rename(columns=rename_map)
        
        # 確保 ID 存在且為字串
        if 'ID' not in df.columns: 
            df['ID'] = df['Name'] # 沒 ID 欄位時用檔名頂替
        else:
            df['ID'] = df['ID'].astype(str)

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

# === 7. 播放器與按鈕元件 (結構優化) ===

def render_hybrid_player(url, unique_id, mode="internal"):
    """
    mode="internal": 
      - PC 顯示播放器 (class=pc-only)
      - Mobile 顯示紅按鈕 (class=mobile-only)
    mode="external":
      - 全裝置顯示播放器 (無 class 限制)，嚴格禁止下載
    """
    
    # 播放器 HTML (加上 unique_id 確保不重複)
    player_html = f"""
        <audio id="audio_{unique_id}" controls controlsList="nodownload" oncontextmenu="return false;" style="width: 100%; margin-bottom: 5px;">
            <source src="{url}" type="audio/mp3">
            您的瀏覽器不支援播放
        </audio>
    """
    
    # 手機紅按鈕 HTML
    btn_html = f"""
        <div class="mobile-only" style="margin-bottom: 10px;">
            <a href="{url}" target="_blank" style="
                display: block; width: 100%; padding: 15px; 
                background-color: #FF4B4B; color: white; 
                text-align: center; text-decoration: none; 
                font-size: 18px; font-weight: bold; border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                ▶️ 手機點此播放音檔
            </a>
            <div style="text-align:center; color:#666; font-size:12px; margin-top:5px;">
                (開啟新視窗播放，無法隱藏下載)
            </div>
        </div>
    """

    if mode == "internal":
        # 【關鍵修正】把 div 包在 HTML 裡面，不要分開寫
        full_html = f"""
            <div class="pc-only">
                {player_html}
            </div>
            {btn_html}
        """
        st.markdown(full_html, unsafe_allow_html=True)
        
    else: # mode == "external"
        # 外部分享：只顯示播放器 (為了不讓下載)，不做隱藏
        st.markdown(player_html, unsafe_allow_html=True)

# === 8. 主程式 ===
def main():
    params = st.query_params
    target_id = params.get("id", None)
    target_name = params.get("n", None)
    
    df = load_data()
    if df.empty: return

    # -------------------------------------------------------
    # 【模式 A】客戶單一播放模式 (外部分享)
    # -------------------------------------------------------
    target_row = pd.DataFrame()
    if target_id:
        target_row = df[df['ID'] == target_id]
    elif target_name:
        target_row = df[df['Name'] == target_name]
        
    if not target_row.empty:
        item = target_row.iloc[0]
        clean_link = get_clean_link(item['Link'])
        play_link = get_player_link(clean_link)
        
        with st.container(border=True):
            st.subheader(f"🎵 {item['Name']}")
            
            # 外部模式：只顯示播放器 (為了禁下載)
            render_hybrid_player(play_link, item['ID'], mode="external")
            
            st.divider()
            st.warning("⚠️ 僅供內部試聽，禁止下載")
            
        if st.button("🏠 回搜尋首頁"):
            st.query_params.clear()
            st.rerun()
            
    elif (target_id or target_name) and target_row.empty:
        st.error("找不到檔案，請確認連結是否正確。")

    # -------------------------------------------------------
    # 【模式 B】管理員模式 (內部使用)
    # -------------------------------------------------------
    else:
        st.title("全家配音資料庫 📂")

        if "logged_in" not in st.session_state: st.session_state.logged_in = False
        
        if not st.session_state.logged_in:
            with st.form("login_form"):
                st.write("請輸入密碼")
                pw = st.text_input("Password", type="password", label_visibility="collapsed")
                if st.form_submit_button("登入", type="primary", use_container_width=True):
                    if pw == PASSWORD:
                        st.session_state.logged_in = True
                        st.rerun()
                    else:
                        st.error("密碼錯誤")
            return

        with st.container(border=True):
            search_name = st.text_input("👤 配音員名稱 / 關鍵字", placeholder="例如：林佩璇...")
            
            col_t1, col_t2, col_t3 = st.columns(3)
            with col_t1: filter_male = st.checkbox("🙋‍♂️ 男聲")
            with col_t2: filter_female = st.checkbox("🙋‍♀️ 女聲")
            with col_t3: filter_remote = st.checkbox("🏠 可遠距")
            
            c1, c2 = st.columns(2)
            with c1:
                main_opts = ["全部"] + sorted([x for x in df['Main_Style'].unique() if x != "未分類"])
                sel_main = st.selectbox("📂 主風格", main_opts)
            with c2:
                if sel_main == "全部": sec_source = df
                else: sec_source = df[df['Main_Style'] == sel_main]
                valid_secs = [x for x in sec_source['Sec_Style'].unique() if x != ""]
                sel_sec = st.selectbox("🏷️ 副風格", ["全部"] + sorted(valid_secs))

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
                clean_link = get_clean_link(row['Link'])
                play_link = get_player_link(clean_link)
                
                # 內部模式：PC 顯示播放器，手機顯示紅按鈕
                render_hybrid_player(play_link, row['ID'], mode="internal")
                
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("📋 內部分享", key=f"in_{row['ID']}"):
                        show_share_dialog("內部分享連結 (OneDrive)", clean_link)
                with b2:
                    if st.button("🌏 外部分享", key=f"out_{row['ID']}"):
                        share_link = f"{SITE_URL}?id={row['ID']}"
                        show_share_dialog("外部分享連結 (客戶試聽用)", share_link)

if __name__ == "__main__":
    main()
