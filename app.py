import streamlit as st
import time
import random
import os
import urllib.request
from io import BytesIO
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# 0. 自動準備中文字體 (解決中文顯示問題)
# ==========================================
@st.cache_resource
def get_chinese_font(size):
    font_path = "NotoSansTC-Regular.ttf"
    # 如果本地沒有這個字體檔案，自動從開源庫下載
    if not os.path.exists(font_path):
        url = "https://github.com/googlefonts/noto-cjk/raw/main/Sans/ttf/NotoSansTC-Regular.ttf"
        try:
            urllib.request.urlretrieve(url, font_path)
        except Exception as e:
            st.error(f"字體下載失敗，請手動下載中文字體並命名為 {font_path}")
            return ImageFont.load_default()
    
    try:
        return ImageFont.truetype(font_path, size)
    except:
        return ImageFont.load_default()

# ==========================================
# 1. 初始化全局狀態 (跨使用者共享)
# ==========================================
@st.cache_resource
def get_auction_state():
    return {
        "round": 1,               
        "image": None,            
        "highest_bid": 0,         
        "highest_bidder": None,   
        "last_bid_time": None,    
        "auction_ended": False,   
        "online_users": set(),    
        "bid_history": [],
        "cert_template": None     # 儲存使用者自訂的獎狀底圖
    }

state = get_auction_state()

HYPE_MESSAGES = [
    "🔥 霸氣出手！{user} 將價格推向 ${amount}，勢在必得！",
    "⚡ 閃電搶標！{user} 豪擲 ${amount}，還有人要跟嗎？",
    "😱 全場震驚！{user} 喊出了 ${amount} 的天價！",
    "💥 毫不猶豫！{user} 以 ${amount} 碾壓全場，還有誰敢挑戰？",
    "💎 志在必得！{user} 的 ${amount} 出價讓其他人瑟瑟發抖！"
]

# ==========================================
# 2. 圖片處理函數 (產生精美「獎狀」)
# ==========================================
def generate_winner_image():
    cert_width, cert_height = 1000, 800
    
    # --- 步驟 A：準備底圖 (自訂樣板 vs 預設精美底圖) ---
    if state["cert_template"] is not None:
        # 使用使用者上傳的樣板
        cert = state["cert_template"].copy()
        cert = cert.resize((cert_width, cert_height))
        draw = ImageDraw.Draw(cert)
    else:
        # 產生高質感的預設底圖
        cert = Image.new("RGB", (cert_width, cert_height), "#FCF9F2") # 典雅米白色
        draw = ImageDraw.Draw(cert)
        
        # 繪製精緻外框
        draw.rectangle([25, 25, cert_width-25, cert_height-25], outline="#B8860B", width=12) # 暗金色粗框
        draw.rectangle([45, 45, cert_width-45, cert_height-45], outline="#DAA520", width=3)  # 亮金色細框
        
        # 繪製角落裝飾 (簡單的方形幾何)
        for x, y in [(25, 25), (cert_width-25-20, 25), (25, cert_height-25-20), (cert_width-25-20, cert_height-25-20)]:
            draw.rectangle([x, y, x+20, y+20], fill="#8B0000") # 深紅角落

    # 載入字體
    font_title = get_chinese_font(48)
    font_text = get_chinese_font(32)
    font_price = get_chinese_font(42)
    font_seal = get_chinese_font(28)

    # --- 步驟 B：文字排版 ---
    # 標題
    title = "拍 賣 得 標 證 明 書"
    title_bbox = draw.textbbox((0, 0), title, font=font_title)
    title_w = title_bbox[2] - title_bbox[0]
    draw.text(((cert_width - title_w) / 2, 80), title, fill="#333333", font=font_title)

    # 內文
    info_1 = f"茲證明買家：【 {state['highest_bidder']} 】"
    info_2 = f"於第 {state['round']} 場拍賣會中，以最高金額"
    info_3 = f"NT$ {state['highest_bid']}"
    info_4 = "成功競標取得此拍品，特發此證以資證明。"
    
    draw.text((120, 180), info_1, fill="#111111", font=font_text)
    draw.text((120, 240), info_2, fill="#111111", font=font_text)
    draw.text((120, 300), info_3, fill="#8B0000", font=font_price) # 金額用深紅色放大
    draw.text((120, 380), info_4, fill="#111111", font=font_text)

    # --- 步驟 C：處理與貼上拍賣品照片 ---
    item_img = state["image"].copy()
    # 將圖片等比例縮小 (放在畫面右下方或正下方)
    item_img.thumbnail((360, 280))
    img_w, img_h = item_img.size
    
    paste_x = 120
    paste_y = 450
    
    # 畫照片的外框與陰影
    draw.rectangle([paste_x-5, paste_y-5, paste_x+img_w+4, paste_y+img_h+4], fill="#DDDDDD")
    draw.rectangle([paste_x-2, paste_y-2, paste_x+img_w+1, paste_y+img_h+1], fill="#FFFFFF")
    cert.paste(item_img, (paste_x, paste_y))

    # --- 步驟 D：印鑑與落款 ---
    current_date = datetime.now().strftime("%Y-%m-%d")
    draw.text((cert_width - 380, cert_height - 180), f"發證日期：{current_date}", fill="#333333", font=font_text)
    
    # 畫一個仿古代的紅色圓形印章「拍賣認證」
    seal_r = 50
    seal_x = cert_width - 200
    seal_y = cert_height - 250
    draw.ellipse([seal_x-seal_r, seal_y-seal_r, seal_x+seal_r, seal_y+seal_r], outline="#C11B17", width=5)
    draw.ellipse([seal_x-seal_r+8, seal_y-seal_r+8, seal_x+seal_r-8, seal_y+seal_r-8], outline="#C11B17", width=2)
    
    seal_text = "拍賣\n認證"
    seal_bbox = draw.multiline_textbbox((0, 0), seal_text, font=font_seal, align="center")
    seal_w = seal_bbox[2] - seal_bbox[0]
    seal_h = seal_bbox[3] - seal_bbox[1]
    draw.multiline_text((seal_x - seal_w/2, seal_y - seal_h/2 - 5), seal_text, fill="#C11B17", font=font_seal, align="center")

    # 轉為 Bytes
    buf = BytesIO()
    cert.save(buf, format="PNG")
    return buf.getvalue()

# ==========================================
# 3. 主程式 UI 與 邏輯
# ==========================================
st.set_page_config(page_title="即時圖片拍賣系統", page_icon="🔨", layout="wide")

if "username" not in st.session_state:
    st.session_state.username = ""

# --- 側邊欄設計 ---
with st.sidebar:
    st.header("👤 參與者登入")
    st.info("觀看拍賣不需登入，欲參與喊價請先設定名稱。")
    name_input = st.text_input("請輸入您的名稱", value=st.session_state.username)
    if st.button("進入拍賣會"):
        if name_input.strip():
            st.session_state.username = name_input.strip()
            state["online_users"].add(st.session_state.username)
            st.success(f"歡迎大老闆：{st.session_state.username}！")
        else:
            st.error("名稱不能為空！")
            
    st.divider()
    st.subheader("🟢 現場買家名單")
    if state["online_users"]:
        for user in state["online_users"]:
            st.markdown(f"- 🤵 **{user}**")
    else:
        st.write("目前尚無買家入座")
        
    st.divider()
    with st.expander("⚙️ 系統設定 (管理員專用)"):
        st.write("上傳自訂的獎狀底圖 (建議尺寸比例 5:4，如 1000x800 px)")
        template_file = st.file_uploader("匯入獎狀樣板", type=["jpg", "png", "jpeg"])
        if template_file:
            state["cert_template"] = Image.open(template_file)
            st.success("自訂獎狀樣板已套用！")
        elif state["cert_template"] is not None:
            if st.button("清除自訂樣板，恢復預設"):
                state["cert_template"] = None
                st.rerun()

st.title(f"🔨 即時圖片拍賣系統 - 第 {state['round']} 場")

# --- 階段 A：上傳圖片 ---
if state["image"] is None:
    st.info("目前尚未有拍賣進行中，您可以直接上傳圖片來發起本回合的拍賣。")
    uploaded_file = st.file_uploader("上傳一張欲拍賣的圖片", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        if st.button("開始拍賣！", type="primary"):
            state["image"] = Image.open(uploaded_file)
            state["highest_bid"] = 0
            state["highest_bidder"] = None
            state["last_bid_time"] = None
            state["auction_ended"] = False
            state["bid_history"] = [] 
            st.rerun()

# --- 階段 B：拍賣進行中 ---
else:
    col_img, col_info = st.columns([1, 1])
    
    with col_img:
        st.image(state["image"], use_container_width=True, caption=f"第 {state['round']} 場競標拍賣品")

    with col_info:
        @st.fragment(run_every=1)
        def auction_display_board():
            if state["last_bid_time"] is not None and not state["auction_ended"]:
                elapsed = time.time() - state["last_bid_time"]
                time_left = 10.0 - elapsed
                
                if time_left <= 0:
                    state["auction_ended"] = True
                    st.rerun()
                else:
                    st.metric("🏆 當前最高出價", f"${state['highest_bid']}", f"出價者: {state['highest_bidder']}")
                    st.error(f"⏳ 結標倒數： **{time_left:.1f} 秒** (若無人加價即結標)")
                    
            elif not state["auction_ended"]:
                st.success("✨ 拍賣已開始！快來搶下第一標！")
                st.metric("🏆 當前最高出價", "$0", "尚無人出價")
                
            elif state["auction_ended"]:
                st.metric("🏆 最終得標金額", f"${state['highest_bid']}", f"得標者: {state['highest_bidder']}")

            st.divider()
            st.subheader("📜 現場戰況")
            with st.container(height=250):
                if not state["bid_history"]:
                    st.write("靜待第一位勇者出價...")
                else:
                    for msg in state["bid_history"]:
                        st.markdown(msg)

        auction_display_board()

    st.divider()

    # --- 互動區塊 ---
    if not state["auction_ended"]:
        if not st.session_state.username:
            st.warning("👈 您目前正在觀看拍賣。若要參與喊價，請先在左側欄位設定名稱並「進入拍賣會」！")
        else:
            st.subheader(f"💰 {st.session_state.username}，請進行喊價")
            min_bid = state["highest_bid"] + 1
            
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                new_bid = st.number_input("自由輸入出價金額", min_value=min_bid, step=10, label_visibility="collapsed")
            with c2:
                btn_custom = st.button("確認出價", use_container_width=True, type="primary")
            with c3:
                btn_plus_500 = st.button("🚀 霸氣加價 $500", use_container_width=True)

            if btn_custom or btn_plus_500:
                actual_bid = state["highest_bid"] + 500 if btn_plus_500 else new_bid
                
                if state["last_bid_time"] is not None and (time.time() - state["last_bid_time"]) >= 10:
                    st.error("很抱歉，拍賣剛剛已經結束！出價無效。")
                    state["auction_ended"] = True
                    st.rerun()
                elif actual_bid > state["highest_bid"]:
                    state["highest_bid"] = actual_bid
                    state["highest_bidder"] = st.session_state.username
                    state["last_bid_time"] = time.time()
                    
                    hype_text = random.choice(HYPE_MESSAGES).format(user=st.session_state.username, amount=actual_bid)
                    state["bid_history"].insert(0, hype_text)
                    st.rerun()
                else:
                    st.error("出價必須高於目前最高金額！")
                    
    else:
        st.success("🎉 本場拍賣已結束！")
        
        if st.session_state.username and st.session_state.username == state["highest_bidder"]:
            st.balloons()
            st.markdown("### 👑 恭喜您得標！為您頒發專屬證書：")
            
            img_bytes = generate_winner_image()
            st.image(img_bytes, width=700, caption="您的專屬得標證明書")
            
            st.download_button(
                label="📥 下載得標獎狀",
                data=img_bytes,
                file_name=f"auction_certificate_{state['round']}.png",
                mime="image/png",
                type="primary"
            )
        else:
            if state['highest_bidder']:
                st.info(f"本次拍賣由 **{state['highest_bidder']}** 得標！")
            else:
                st.info("本次拍賣無人出價，流標！")
            
        st.divider()
        if st.button("開啟下一輪拍賣"):
            state["image"] = None
            state["highest_bid"] = 0
            state["highest_bidder"] = None
            state["last_bid_time"] = None
            state["auction_ended"] = False
            state["bid_history"] = []
            state["round"] += 1 
            st.rerun()
