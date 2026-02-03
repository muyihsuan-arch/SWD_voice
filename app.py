import streamlit as st
import pandas as pd
import urllib.parse

# === 1. 設定區 ===
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQWueqZqoUXP7YM_UDDAedhAjYQI80RoNapxH8YyKbyLkq8L_CprL2eeQ7DEPBqdxqJCRVCiaRp9l6S/pub?output=csv"
PASSWORD = "888"
SITE_URL = "https://swd-voice.streamlit.app"  # 請確認您的網址

# === 2. 頁面與 CSS 設定 (RWD 分流核心) ===
st.set_page_config(page_title="全家配音試聽", layout="centered")

st.markdown("""
    <style>
        /* === 手機/電腦 分流控制 (關鍵 CSS) === */
        
        /* 預設(電腦版)：顯示播放器，隱藏手機按鈕 */
        .pc-player-area { display: block; }
        .mobile-btn-area { display: none; }
        
        /* 當螢幕小於 768px (手機版) 時：隱藏播放器，顯示手機按鈕 */
        @media (max-width: 768px) {
            .pc-player-area { display: none !important; }
            .mobile-btn-area { display: block !important; }
        }

        /* === UI 優化 === */
        /* 隱藏原生播放器下載鈕 */
        audio::-webkit-media-controls-enclosure { overflow: hidden; }
        audio::-webkit-media-controls-panel { width: calc(100% + 30px); }
        
        /* 調整按鈕樣式 */
        .stButton button { width: 100%; border-radius: 8px; font-weight: bold; }
        
        /* 標籤按鈕優化 */
        div[data-testid="stCheckbox"] label { font-weight: bold; font-size: 16px; }
    </style>
""", unsafe_allow_html=True)

# === 3. 彈窗：優化複製體驗 ===
@st.dialog("🔗 複製連結")
def show_copy_modal(title, link):
    st.write(f"👇 {title}")
    # 改用 text_input，手機上比較好複製，不會被遮擋
    st.text_input("請全選複製下方連結", value=link, key="copy_input")
    st.caption("💡 手機長按上方網址即可全選複製")

# === 4. 資料讀取與處理 ===
@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(CSV_URL)
        df.columns = df.columns.str.strip()
        
        # 自動對應欄位
        def get_col(candidates):
            for c in df.columns:
                if any(x in c.lower() for x in candidates): return c
            return None

        col_name = get_col(["filename", "name", "檔名"])
        col_link = get_col(["link_source", "link", "連結"])
        col_voice = get_col(["voice", "category", "聲線"]) # 通常是男女聲
        col_style = get_col(["style", "main_style", "風格"]) # 主風格

        if not col_link: return pd.DataFrame()

        df = df.rename(columns={
            col_name: 'Name', 
            col_link: 'Link', 
            col_voice: 'Voice', # 性別/聲線
            col_style: 'Main_Style' # 主風格
        })
        
        # --- 自動產生「Sec_Style (副風格)」---
        # 邏輯：從檔名去拆解標籤 (例如：F01_可遠距_專業 -> 專業)
        # 這裡簡單實作：把檔名裡的底線切開，當作標籤庫
        def extract_tags(row):
            parts = str(row['Name']).split('_')
            # 過濾掉無意義的短字，收集成標籤
            return [p for p in parts if len(p) >= 2]
        
        df['Tags'] = df.apply(extract_tags, axis=1)
        
        return df.dropna(subset=['Link'])
    except:
        return pd.DataFrame()

# === 5. 連結處理工具 ===
def get_clean_link(link):
    if not isinstance(link, str): return ""
    return link.replace('&download=1', '').replace('?download=1', '')

def get_player_link(link):
    clean = get_clean_link(link)
    return clean + ('&download=1' if '?' in clean else '?download=1')

# === 6. HTML5 播放器 (電腦用) ===
def render_pc_player(url):
    html = f"""
        <div class="pc-player-area">
            <audio controls controlsList="nodownload" style="width: 100%; margin-bottom: 5px;">
                <source src="{url}" type="audio/mp3">
            </audio>
        </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# === 7. 手機版按鈕 (手機用) ===
def render_mobile_btn(url):
    # 使用 HTML link 模擬按鈕，確保在新視窗開啟
    html = f"""
        <div class="mobile-btn-area">
            <a href="{url}" target="_blank" style="
                display: block; width: 100%; padding: 12px; 
                background-color: #FF5733; color: white; 
                text-align: center; text-decoration: none; 
                font-weight: bold; border-radius: 8px; margin-bottom: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                ▶️ 試聽 (開啟 OneDrive)
            </a>
        </div>
    """
    st.markdown(html, unsafe_allow_html=True)

# === 8. 主程式邏輯 ===
def main():
    params = st.query_params
    target_name = params.get("n", None)
    
    df = load_data()
    if df.empty: return

    # -------------------------------------------------------
    # 【模式 A】客戶單一播放模式
    # -------------------------------------------------------
    if target_name:
        row = df[df['Name'] == target_name]
        
        if not row.empty:
            item = row.iloc[0]
            clean_link = get_clean_link(item['Link'])
            play_link = get_player_link(clean_link)
            
            with st.container(border=True):
                st.subheader(f"🎵 {item['Name']}")
                
                # RWD 分流：電腦顯示 Player，手機顯示 Button
                render_pc_player(play_link)
                render_mobile_btn(clean_link) # 手機直接開原始連結
                
                st.divider()
                st.warning("⚠️ 僅供內部試聽，禁止下載")
                
            if st.button("🏠 回搜尋首頁"):
                st.query_params.clear()
                st.rerun()
        else:
            st.error("找不到該檔案")

    # -------------------------------------------------------
    # 【模式 B】管理員模式
    # -------------------------------------------------------
    else:
        st.title("全家配音資料庫 📂")

        if "logged_in" not in st.session_state: st.session_state.logged_in = False
        if not st.session_state.logged_in:
            with st.form("login"):
                if st.form_submit_button("登入") and st.text_input("密碼", type="password") == PASSWORD:
                    st.session_state.logged_in = True
                    st.rerun()
            return

        # === 篩選區塊 ===
        with st.container(border=True):
            st.write("🔍 **搜尋條件**")
            
            # 1. 配音員搜尋
            search_name = st.text_input("👤 配音員名稱", placeholder="輸入名字...")
            
            # 2. 標籤按鈕 (男/女/遠距) - 複選
            c1, c2, c3 = st.columns(3)
            with c1: filter_male = st.checkbox("🙋‍♂️ 男聲")
            with c2: filter_female = st.checkbox("🙋‍♀️ 女聲")
            with c3: filter_remote = st.checkbox("🏠 可遠距")

            # 3. 連動式下拉選單
            col_main, col_sec = st.columns(2)
            
            with col_main:
                # 取得所有主風格
                all_main_styles = ["全部"] + sorted(list(df['Main_Style'].dropna().unique()))
                sel_main = st.selectbox("📂 主風格 (Main Style)", all_main_styles)
            
            with col_sec:
                # [核心邏輯] 根據選的主風格，動態找出剩下的標籤當作「副風格」
                if sel_main == "全部":
                    available_tags = []
                else:
                    # 篩選出符合主風格的資料
                    sub_df = df[df['Main_Style'] == sel_main]
                    # 把這些資料的所有標籤收集起來
                    tags_set = set()
                    for tags in sub_df['Tags']:
                        tags_set.update(tags)
                    available_tags = sorted(list(tags_set))
                
                sel_sec = st.selectbox("🏷️ 副風格 (Sec Style)", ["全部"] + available_tags)

        # === 執行篩選邏輯 ===
        mask = pd.Series([True] * len(df))
        
        # 名稱搜尋
        if search_name: mask &= df['Name'].str.contains(search_name, case=False, na=False)
        
        # 標籤篩選 (複選邏輯：有勾就要有)
        # 假設 Voice 欄位有寫 "男"/"女"，Name 或 Tags 有寫 "可遠距"
        if filter_male: mask &= df['Voice'].str.contains("男", na=False)
        if filter_female: mask &= df['Voice'].str.contains("女", na=False)
        if filter_remote: 
            # 搜尋檔名或標籤裡有沒有「遠距」
            mask &= df['Name'].str.contains("遠距", na=False)

        # 風格篩選
        if sel_main != "全部": mask &= (df['Main_Style'] == sel_main)
        if sel_sec != "全部":
            # 檢查 Tags 列表裡有沒有選到的副風格
            mask &= df['Tags'].apply(lambda x: sel_sec in x)

        results = df[mask]
        st.markdown(f"**🎯 共找到 {len(results)} 筆資料**")

        # === 列表顯示 ===
        for _, row in results.head(20).iterrows():
            with st.expander(f"📄 {row['Name']}"):
                clean_link = get_clean_link(row['Link'])
                play_link = get_player_link(clean_link)
                
                # RWD 分流顯示
                render_pc_player(play_link)
                # 電腦版也稍微顯示一下連結按鈕，方便預覽，但手機版這個會變大按鈕
                st.markdown(f'<a href="{clean_link}" target="_blank" style="font-size:12px; color:#666;">🔗 開啟 OneDrive 來源</a>', unsafe_allow_html=True)
                
                # 功能按鈕
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("📋 內部分享", key=f"in_{row['Name']}"):
                        show_copy_modal("內部分享連結", clean_link)
                with b2:
                    if st.button("🌏 外部分享", key=f"out_{row['Name']}"):
                        safe_name = urllib.parse.quote(row['Name'])
                        share_link = f"{SITE_URL}?n={safe_name}"
                        show_copy_modal("外部分享連結", share_link)

if __name__ == "__main__":
    main()
