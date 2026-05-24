import streamlit as st
import time
import random
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# ==========================================
# 1. 初始化全局狀態 (跨使用者共享)
# ==========================================
@st.cache_resource
def get_auction_state():
    return {
        "round": 1,               # 紀錄目前是第幾次拍賣
        "image": None,            # 拍賣的圖片物件 (PIL Image)
        "highest_bid": 0,         # 目前最高出價
        "highest_bidder": None,   # 目前最高出價者
        "last_bid_time": None,    # 最後一次出價的時間戳
        "auction_ended": False,   # 拍賣是否已結束
        "online_users": set(),    # 紀錄曾登入的買家
        "bid_history": []         # 紀錄喊價歷史與情緒語錄
    }

state = get_auction_state()

# 情緒價值語錄庫 (隨機抽取)
HYPE_MESSAGES = [
    "🔥 霸氣出手！{user} 將價格推向 ${amount}，勢在必得！",
    "⚡ 閃電搶標！{user} 豪擲 ${amount}，還有人要跟嗎？",
    "😱 全場震驚！{user} 喊出了 ${amount} 的天價！",
    "💥 毫不猶豫！{user} 以 ${amount} 碾壓全場，還有誰敢挑戰？",
    "💎 志在必得！{user} 的 ${amount} 出價讓其他人瑟瑟發抖！"
]

# ==========================================
# 2. 圖片處理函數 (產生得標結果圖)
# ==========================================
def generate_winner_image():
    original = state["image"]
    width, height = original.size
    
    new_height = height + 100
    new_img = Image.new("RGB", (width, new_height), "white")
    new_img.paste(original, (0, 0))
    
    draw = ImageDraw.Draw(new_img)
    
    try:
        font = ImageFont.truetype("msjh.ttc", max(24, int(width/25))) 
    except:
        try:
            font = ImageFont.truetype("PingFang.ttc", max(24, int(width/25)))
        except:
            font = ImageFont.load_default()
            
    winner_text = f"第 {state['round']} 場得標者: {state['highest_bidder']} | 金額: ${state['highest_bid']}"
    
    text_bbox = draw.textbbox((0, 0), winner_text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    x = (width - text_width) / 2
    y = height + (100 - text_height) / 2 - 10
    
    draw.text((x, y), winner_text, fill="black", font=font)
    
    buf = BytesIO()
    new_img.save(buf, format="PNG")
    return buf.getvalue()

# ==========================================
# 3. 主程式 UI 與 邏輯
# ==========================================
st.set_page_config(page_title="即時圖片拍賣系統", page_icon="🔨", layout="wide")

if "username" not in st.session_state:
    st.session_state.username = ""

# --- 側邊欄：自由登入與線上名單 ---
with st.sidebar:
    st.header("👤 參與者登入")
    st.info("觀看拍賣不需登入，欲參與喊價請先設定名稱。")
    name_input = st.text_input("請輸入您的名稱", value=st.session_state.username)
    if st.button("進入拍賣會"):
        if name_input.strip():
            st.session_state.username = name_input.strip()
            state["online_users"].add(st.session_state.username) # 加入全域廣播名單
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

# 標題
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
            state["bid_history"] = [] # 清空歷史紀錄
            st.rerun()

# --- 階段 B：拍賣進行中 ---
else:
    # 使用左右分欄：左邊放圖片，右邊放計時器與出價歷史
    col_img, col_info = st.columns([1, 1])
    
    with col_img:
        st.image(state["image"], use_container_width=True, caption=f"第 {state['round']} 場競標拍賣品")

    with col_info:
        # 每秒自動更新的計時與狀態看板
        @st.fragment(run_every=1)
        def auction_display_board():
            # 1. 顯示倒數計時與當前最高價
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
            
            # 2. 顯示拍賣熱絡歷史 (最新出價在最上面)
            st.subheader("📜 現場戰況")
            with st.container(height=250): # 固定高度產生捲動軸
                if not state["bid_history"]:
                    st.write("靜待第一位勇者出價...")
                else:
                    for msg in state["bid_history"]:
                        st.markdown(msg)

        auction_display_board()

    st.divider()

    # --- 互動區塊 (出價操作區) ---
    if not state["auction_ended"]:
        if not st.session_state.username:
            st.warning("👈 您目前正在觀看拍賣。若要參與喊價，請先在左側欄位設定名稱並「進入拍賣會」！")
        else:
            st.subheader(f"💰 {st.session_state.username}，請進行喊價")
            min_bid = state["highest_bid"] + 1
            
            # 排版：輸入框、確認按鈕、快速加碼按鈕
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                new_bid = st.number_input("自由輸入出價金額", min_value=min_bid, step=10, label_visibility="collapsed")
            with c2:
                btn_custom = st.button("確認出價", use_container_width=True, type="primary")
            with c3:
                btn_plus_500 = st.button("🚀 霸氣加價 $500", use_container_width=True)

            # 處理出價邏輯
            if btn_custom or btn_plus_500:
                # 決定實際出價金額
                actual_bid = state["highest_bid"] + 500 if btn_plus_500 else new_bid
                
                # 再次驗證是否逾時
                if state["last_bid_time"] is not None and (time.time() - state["last_bid_time"]) >= 10:
                    st.error("很抱歉，拍賣剛剛已經結束！出價無效。")
                    state["auction_ended"] = True
                    st.rerun()
                elif actual_bid > state["highest_bid"]:
                    state["highest_bid"] = actual_bid
                    state["highest_bidder"] = st.session_state.username
                    state["last_bid_time"] = time.time()
                    
                    # 產生情緒價值語錄並加入歷史紀錄最前方 (新在上方)
                    hype_text = random.choice(HYPE_MESSAGES).format(user=st.session_state.username, amount=actual_bid)
                    state["bid_history"].insert(0, hype_text)
                    
                    st.rerun()
                else:
                    st.error("出價必須高於目前最高金額！")
                    
    else:
        st.success("🎉 本場拍賣已結束！")
        
        if st.session_state.username and st.session_state.username == state["highest_bidder"]:
            st.balloons()
            st.markdown("### 👑 恭喜您得標！請下載您的專屬證明圖片：")
            img_bytes = generate_winner_image()
            st.download_button(
                label="📥 下載得標圖片",
                data=img_bytes,
                file_name=f"auction_round_{state['round']}_winner.png",
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
