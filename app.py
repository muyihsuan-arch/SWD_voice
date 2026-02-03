import streamlit as st
import pandas as pd

# === 1. 設定區 ===
# 您的 Google Sheet CSV 連結
CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQWueqZqoUXP7YM_UDDAedhAjYQI80RoNapxH8YyKbyLkq8L_CprL2eeQ7DEPBqdxqJCRVCiaRp9l6S/pub?output=csv"
PASSWORD = "888"

# 設定網頁標題與寬度
st.set_page_config(page_title="全家配音資料庫", layout="centered")

# === 2. 核心功能：讀取與清理資料 ===
@st.cache_data(ttl=600)  # 快取 10 分鐘，避免一直讀取 Sheet
def load_data():
    try:
        df = pd.read_csv(CSV_URL)
        # 清理欄位名稱 (去除前後空白)
        df.columns = df.columns.str.strip()
        
        # 自動對應欄位 (不分大小寫)
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
            st.error("❌ 錯誤：找不到連結欄位 (Link_Source)")
            return pd.DataFrame()

        # 重新命名以便後續操作
        df = df.rename(columns={
            col_name: 'Name',
            col_link: 'Link',
            col_voice: 'Voice',
            col_style: 'Style'
        })
        
        # 移除沒有連結的空資料
        df = df.dropna(subset=['Link'])
        return df
    except Exception as e:
        st.error(f"資料讀取失敗: {e}")
        return pd.DataFrame()

# === 3. 連結處理工具 ===
def process_link(raw_link, for_player=True):
    """
    處理 OneDrive 連結
    for_player=True:  強制加上 download=1 (給播放器用)
    for_player=False: 強制移除 download=1 (給手機按鈕/預覽用)
    """
    if not isinstance(raw_link, str): return ""
    clean = raw_link.replace('&download=1', '').replace('?download=1', '')
    
    if for_player:
        return clean + ('&download=1' if '?' in clean else '?download=1')
    else:
        return clean

# === 4. 主程式邏輯 ===
def main():
    # 讀取網址參數 (例如 ?n=林佩璇)
    params = st.query_params
    target_name = params.get("n", None)

    # 載入資料
    df = load_data()
    if df.empty:
        return

    # -------------------------------------------------------
    # 【模式 A】客戶單一播放模式 (網址有帶 ?n=...)
    # -------------------------------------------------------
    if target_name:
        # 搜尋該檔案 (模糊比對，避免中文字編碼問題)
        # case=False (不分大小寫), na=False (忽略空值)
        results = df[df['Name'].str.contains(target_name, case=False, na=False)]

        if not results.empty:
            item = results.iloc[0] # 取第一筆結果
            
            st.markdown(f"### 🎧 {item['Name']}")
            st.caption(f"分類：{item.get('Voice', '未分類')} | 風格：{item.get('Style', '未分類')}")

            # 播放器 (PC/Mobile 通用)
            # Streamlit 的 st.audio 非常穩定
            player_url = process_link(item['Link'], for_player=True)
            st.audio(player_url, format="audio/mp3")

            st.info("💡 僅供內部試聽，請勿外流")

            st.divider()
            
            # 手機版救援按鈕 (如果播放器跑不動，點這個去 OneDrive)
            preview_url = process_link(item['Link'], for_player=False)
            st.link_button("↗ 若無法播放，請點此開啟來源 (OneDrive)", preview_url)

            # 讓客戶可以回到首頁 (選用)
            if st.button("🔍 回到搜尋首頁"):
                st.query_params.clear() # 清除參數
                st.rerun() # 重新整理
        else:
            st.error(f"❌ 找不到檔案：{target_name}")
            if st.button("回首頁"):
                st.query_params.clear()
                st.rerun()

    # -------------------------------------------------------
    # 【模式 B】管理員/搜尋模式 (網址乾淨)
    # -------------------------------------------------------
    else:
        st.title("全家配音資料庫 📂")

        # 登入驗證 (Session State)
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
            return # 沒登入就停在這裡

        # --- 登入後的介面 ---
        
        # 1. 頂部篩選區
        col1, col2 = st.columns(2)
        with col1:
            voices = ["全部"] + list(df['Voice'].unique())
            selected_voice = st.selectbox("聲線分類", voices)
        with col2:
            styles = ["全部"] + list(df['Style'].unique())
            selected_style = st.selectbox("風格分類", styles)

        # 2. 關鍵字搜尋
        keyword = st.text_input("🔍 搜尋檔名", placeholder="請輸入關鍵字...")

        # 3. 執行篩選
        filtered_df = df.copy()
        if selected_voice != "全部":
            filtered_df = filtered_df[filtered_df['Voice'] == selected_voice]
        if selected_style != "全部":
            filtered_df = filtered_df[filtered_df['Style'] == selected_style]
        if keyword:
            filtered_df = filtered_df[filtered_df['Name'].str.contains(keyword, case=False, na=False)]

        st.markdown(f"**共找到 {len(filtered_df)} 筆資料**")

        # 4. 顯示列表
        # 為了效能，如果沒搜尋關鍵字，只顯示前 10 筆，避免 OneDrive 爆炸
        show_limit = 10 if not keyword else 100
        
        for index, row in filtered_df.head(show_limit).iterrows():
            with st.expander(f"🎵 {row['Name']}"):
                # 播放器
                play_link = process_link(row['Link'], for_player=True)
                st.audio(play_link, format='audio/mp3')
                
                # 按鈕區
                c1, c2 = st.columns(2)
                with c1:
                    # 內部連結
                    view_link = process_link(row['Link'], for_player=False)
                    st.link_button("🏢 內部連結 (OneDrive)", view_link)
                
                with c2:
                    # 產生單一分享連結
                    # 注意：這裡會自動抓取當前 app 的網址
                    # 如果在本機測試，它會是 localhost，部署後會是 share.streamlit.io...
                    base_url = "https://share.streamlit.io" # 部署後請確認您的實際網址前綴
                    # 不過 Streamlit 很聰明，我們只要顯示參數部分即可
                    
                    share_link = f"?n={row['Name']}"
                    st.code(share_link, language="text")
                    st.caption("👆 複製上方參數，加在網址後面即可分享")

        if len(filtered_df) > show_limit:
            st.info("...還有更多資料，請輸入關鍵字縮小範圍")

if __name__ == "__main__":
    main()
