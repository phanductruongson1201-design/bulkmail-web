import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
import time
import requests
import hashlib
import string
import random
import base64
import os
import re 
import json
from bs4 import BeautifulSoup 
from streamlit_quill import st_quill 

# 1. Cấu hình trang Web (Giao diện rộng, sidebar mở sẵn)
st.set_page_config(page_title="BulkMail Pro - Trường Sơn", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# API CƠ SỞ DỮ LIỆU & HỆ THỐNG
# ==========================================
DB_URL = st.secrets.get("DB_URL", "")
SYS_EMAIL = st.secrets.get("SENDER_EMAIL", "")
SYS_PWD = st.secrets.get("APP_PASSWORD", "")

def load_users():
    if not DB_URL: return {"users": {}, "logs": []}
    try: 
        res = requests.get(DB_URL).json()
        if isinstance(res, dict) and "users" in res: return res
        return {"users": res, "logs": []}
    except: return {"users": {}, "logs": []}

def save_user_api(username, password_hash, email):
    if not DB_URL: return
    try: requests.post(DB_URL, json={"action": "register", "username": username, "password": password_hash, "email": email})
    except: pass

def reset_password_api(username, email, new_password_hash, is_reset_status):
    if not DB_URL: return False
    try:
        res = requests.post(DB_URL, json={"action": "reset", "username": username, "email": email, "new_password": new_password_hash, "is_reset": is_reset_status}).json()
        return res.get("status") == "success"
    except: return False

def save_config_api(username, tele_token, tele_chat_id):
    if not DB_URL: return False
    try:
        res = requests.post(DB_URL, json={"action": "update_config", "username": username, "tele_token": tele_token, "tele_chat_id": tele_chat_id}).json()
        return res.get("status") == "success"
    except: return False

def hash_password(password): return hashlib.sha256(password.encode()).hexdigest()
def generate_otp(length=6): return "".join(random.choices(string.digits, k=length))

def send_otp_email(to_email, username, otp_code):
    if not SYS_EMAIL or not SYS_PWD: return False
    try:
        msg = MIMEMultipart()
        msg["From"] = f"Hệ thống xác thực <{SYS_EMAIL}>"
        msg["To"] = to_email; msg["Subject"] = f"{otp_code} là mã xác thực của bạn"
        body = f"<h3>Chào {username},</h3><p>Mã OTP: <b style='font-size: 20px;'>{otp_code}</b></p>"
        msg.attach(MIMEText(body, "html"))
        s = smtplib.SMTP("smtp.gmail.com", 587); s.starttls(); s.login(SYS_EMAIL, SYS_PWD); s.send_message(msg); s.quit()
        return True
    except: return False

def send_tele_msg(token, chat_id, message):
    if token and chat_id:
        try: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=5)
        except: pass

def send_tele_file(token, chat_id, file_content, file_name):
    if token and chat_id:
        try:
            files = {"document": (file_name, file_content)}
            requests.post(f"https://api.telegram.org/bot{token}/sendDocument", data={"chat_id": chat_id}, files=files, timeout=10)
        except: pass

def get_image_base64(path):
    try:
        with open(path, "rb") as img_file: return base64.b64encode(img_file.read()).decode("utf-8")
    except: return None

def play_success_sound():
    components.html("""<audio autoplay><source src="https://actions.google.com/sounds/v1/cartoon/magic_chime.ogg" type="audio/ogg"></audio>""", height=0)

# ==========================================
# GIAO DIỆN CSS MỚI (SIDEBAR & GLASSMORPHISM)
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif !important; }
    #MainMenu, footer, header, .stDeployButton, [data-testid="viewerBadge"], iframe[title="Streamlit Toolbar"] {display: none !important; visibility: hidden !important;}
    .block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; max-width: 95% !important;}
    
    /* Hình nền cho app */
    .stApp { background-color: #f8fafc; background-image: radial-gradient(at 0% 0%, hsla(220,100%,95%,0.5) 0, transparent 50%), radial-gradient(at 100% 0%, hsla(280,100%,95%,0.5) 0, transparent 50%); }
    
    .gradient-text { background: linear-gradient(90deg, #2563eb 0%, #7c3aed 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; font-size: 38px; margin-bottom: 5px; letter-spacing: -1px; }

    /* 🌟 HUY HIỆU VIP */
    .vip-badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 800; color: white; margin-left: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.15); text-transform: uppercase; animation: shine 2s infinite; }
    .badge-dong { background: linear-gradient(135deg, #cd7f32, #8b5a2b); }
    .badge-bac { background: linear-gradient(135deg, #c0c0c0, #808080); color: #333; }
    .badge-vang { background: linear-gradient(135deg, #FFD700, #FFA500); color: #8B4500; }
    .badge-kimcuong { background: linear-gradient(135deg, #00f2fe, #4facfe); }
    @keyframes shine { 0% { opacity: 0.8; transform: scale(1); } 50% { opacity: 1; transform: scale(1.05); box-shadow: 0 0 15px rgba(255,255,255,0.6); } 100% { opacity: 0.8; transform: scale(1); } }

    /* 🌟 TÙY CHỈNH SIDEBAR CHUẨN SAAS */
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; box-shadow: 2px 0 10px rgba(0,0,0,0.02); }
    /* Định dạng Radio Button thành Menu */
    div[role="radiogroup"] > label { padding: 12px 15px; border-radius: 12px; margin-bottom: 8px; transition: all 0.3s ease; border: 1px solid transparent; cursor: pointer; }
    div[role="radiogroup"] > label:hover { background-color: #f1f5f9; border-color: #e2e8f0; transform: translateX(5px); }
    div[role="radiogroup"] > label[data-checked="true"] { background: linear-gradient(90deg, #eff6ff 0%, #ffffff 100%); border-left: 4px solid #3b82f6; border-radius: 4px 12px 12px 4px; box-shadow: 0 2px 5px rgba(59,130,246,0.1); }
    div[role="radiogroup"] > label > div:first-child { display: none; /* Ẩn cái chấm tròn mặc định */ }
    div[role="radiogroup"] > label p { font-weight: 700 !important; color: #334155 !important; font-size: 15px !important; margin: 0 !important; }
    div[role="radiogroup"] > label[data-checked="true"] p { color: #1e40af !important; }
    
    /* GLASSMORPHISM CHO CÁC KHỐI */
    .glass-box, div[data-testid="stMetric"], div[data-testid="stExpander"], div[data-testid="stFileUploader"] { background: rgba(255, 255, 255, 0.8) !important; backdrop-filter: blur(12px) !important; -webkit-backdrop-filter: blur(12px) !important; border: 1px solid rgba(255, 255, 255, 0.6) !important; box-shadow: 0 8px 20px 0 rgba(31, 38, 135, 0.05) !important; border-radius: 16px; }
    
    .news-panel { background: white; border-radius: 16px; border: 1px solid #e2e8f0; padding: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.03); }
    .news-item { border-left: 3px solid #3b82f6; padding-left: 12px; margin-bottom: 15px; }
    .news-date { font-size: 12px; color: #64748b; margin-bottom: 3px; display: flex; align-items: center; gap: 5px; }
    .news-title { font-size: 14px; font-weight: 600; color: #0f172a; margin: 0; line-height: 1.4; }

    .stButton>button[kind="primary"] { background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%) !important; color: white !important; border-radius: 12px; font-weight: 900; padding: 12px 24px; border: none !important; box-shadow: 0 6px 20px rgba(59,130,246,0.3) !important; transition: all 0.3s ease; text-transform: uppercase; }
    .stButton>button[kind="primary"]:hover { transform: translateY(-3px); box-shadow: 0 8px 25px rgba(59,130,246,0.4) !important; }
    
    .pill-header { color: white; padding: 8px 20px; border-radius: 50px; font-size: 14px; font-weight: 800; margin-bottom: 15px; margin-top: 10px; text-transform: uppercase; display: inline-block; }
    .bg-blue { background: linear-gradient(135deg, #3b82f6, #1d4ed8); }
    .bg-purple { background: linear-gradient(135deg, #a855f7, #6d28d9); }
    .bg-green { background: linear-gradient(135deg, #10b981, #047857); }

    .logo-container { display: flex; justify-content: center; align-items: center; width: 100%; margin-bottom: 15px; }
    .logo-container img { width: 100px; height: 100px; border-radius: 30%; object-fit: cover; box-shadow: 0 8px 20px rgba(59, 130, 246, 0.2); }
    .alt-logo { width: 100px; height: 100px; border-radius: 30%; background: linear-gradient(135deg, #4f46e5, #3b82f6); color: white; display: flex; justify-content: center; align-items: center; font-weight: 800; font-size: 14px; text-align: center; box-shadow: 0 8px 20px rgba(59, 130, 246, 0.2); }

    .floating-container { position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 15px; z-index: 999999; }
    .float-btn { width: 50px; height: 50px; border-radius: 50%; box-shadow: 0 10px 25px rgba(0,0,0,0.15); display: flex; justify-content: center; align-items: center; background: white; transition: 0.3s; border: 2px solid #e2e8f0; }
    .float-btn:hover { transform: translateY(-5px); border-color: #3b82f6; }
    
    div[data-testid="stMetric"] { padding: 15px 20px; text-align: center; }
    div[data-testid="stMetricValue"] { color: #1e40af !important; font-weight: 900 !important; font-size: 26px !important; }
    div[data-testid="stMetricLabel"] { font-size: 13px !important; color: #64748b !important; font-weight: 700 !important; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# Khởi tạo trạng thái Session
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "otp_verified" not in st.session_state: st.session_state["otp_verified"] = False
if "show_deposit_form" not in st.session_state: st.session_state["show_deposit_form"] = False
if "show_qr" not in st.session_state: st.session_state["show_qr"] = False
if "deposit_amount" not in st.session_state: st.session_state["deposit_amount"] = 100000
if "qr_expire_time" not in st.session_state: st.session_state["qr_expire_time"] = 0
if "previous_balance" not in st.session_state: st.session_state["previous_balance"] = None 

if "s_name" not in st.session_state: st.session_state["s_name"] = "Trường Sơn Marketing"
if "s_email" not in st.session_state: st.session_state["s_email"] = ""
if "s_pwd" not in st.session_state: st.session_state["s_pwd"] = ""
if "s_sign" not in st.session_state: st.session_state["s_sign"] = "Trân trọng,\nTrường Sơn Marketing"

LOGO_URL = "logo_moi.png"

# ==========================================
# 1. HỆ THỐNG ĐĂNG NHẬP (Giữ nguyên)
# ==========================================
if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div class="glass-box" style="padding: 35px;">', unsafe_allow_html=True)
        logo_b64 = get_image_base64(LOGO_URL)
        if logo_b64: st.markdown(f'<div class="logo-container"><img src="data:image/png;base64,{logo_b64}"></div>', unsafe_allow_html=True)
        else: st.markdown('<div class="logo-container"><div class="alt-logo">TRƯỜNG SƠN<br>MARKETING</div></div>', unsafe_allow_html=True)
            
        st.markdown('<h2 style="text-align:center; color:#0f172a; font-weight:900; margin-bottom:5px; font-size:28px;">BULKMAIL PRO</h2>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; color:#64748b; margin-bottom:20px; font-size:14px;">Đăng nhập để bắt đầu chiến dịch</p>', unsafe_allow_html=True)
        
        tab_login, tab_reg, tab_forgot = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký", "🔑 Quên MK"])
        all_data = load_users()
        users_db = all_data.get("users", all_data) 

        with tab_login:
            log_user = st.text_input("Tên đăng nhập", key="login_u")
            log_pwd = st.text_input("Mật khẩu", type="password", key="login_p")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("ĐĂNG NHẬP HỆ THỐNG", type="primary", use_container_width=True):
                if log_user in users_db and users_db[log_user].get("password") == hash_password(log_pwd):
                    st.session_state["current_user"] = log_user; st.session_state["logged_in"] = True; st.rerun()
                else: 
                    st.toast("Thông tin đăng nhập chưa chính xác!", icon="❌")
                    st.error("❌ Thông tin đăng nhập chưa chính xác!")

        with tab_reg:
            reg_user = st.text_input("Tên đăng nhập mới", key="reg_u")
            reg_email = st.text_input("Email khôi phục", key="reg_e")
            reg_pwd = st.text_input("Mật khẩu", type="password", key="reg_p")
            reg_pwd_confirm = st.text_input("Xác nhận mật khẩu", type="password", key="reg_pc")
            if st.button("TẠO TÀI KHOẢN", type="primary", use_container_width=True):
                if not reg_user or not reg_email or not reg_pwd: st.warning("⚠️ Điền đủ thông tin!")
                elif reg_user in users_db: st.error("❌ Username đã tồn tại!")
                elif reg_pwd != reg_pwd_confirm: st.error("❌ Mật khẩu không khớp!")
                else:
                    save_user_api(reg_user, hash_password(reg_pwd), reg_email)
                    st.toast("Đăng ký thành công! Vui lòng đăng nhập.", icon="🎉")
                    st.success("✅ Đăng ký thành công!")

        with tab_forgot:
            # Code quên MK giữ nguyên...
            st.info("Vui lòng liên hệ Admin qua Zalo ở góc màn hình để được cấp lại mật khẩu.")
            
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 2. DASHBOARD CHÍNH (SIDEBAR LAYOUT)
# ==========================================
else:
    all_data = load_users()
    users_db = all_data.get("users", all_data)
    logs_db = all_data.get("logs", [])
    current_user_data = users_db.get(st.session_state["current_user"], {})
    
    balance = int(float(current_user_data.get("balance", 0)))
    
    # 🌟 CẤP BẬC VIP TỰ ĐỘNG
    if balance < 100000: vip_class = "badge-dong"; vip_text = "🥉 Đồng"
    elif balance < 500000: vip_class = "badge-bac"; vip_text = "🥈 Bạc"
    elif balance < 2000000: vip_class = "badge-vang"; vip_text = "🥇 Vàng"
    else: vip_class = "badge-kimcuong"; vip_text = "💎 Kim Cương"

    # ÂM THANH & PHÁO HOA KHI CỘNG TIỀN
    if st.session_state["previous_balance"] is None: st.session_state["previous_balance"] = balance
    elif balance > st.session_state["previous_balance"]:
        play_success_sound(); st.balloons()
        st.toast(f"🎉 Đã cộng {balance - st.session_state['previous_balance']:,} VNĐ vào tài khoản!", icon="💰")
        st.session_state["previous_balance"] = balance
        st.session_state["show_deposit_form"] = False; st.session_state["show_qr"] = False

    # ========================================================
    # MENU BÊN TRÁI (SIDEBAR)
    # ========================================================
    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        logo_b64 = get_image_base64(LOGO_URL)
        if logo_b64: st.markdown(f'<div class="logo-container"><img src="data:image/png;base64,{logo_b64}" width="90"></div>', unsafe_allow_html=True)
        else: st.markdown('<h3 style="text-align:center; color:#1e40af; font-weight:900;">BULKMAIL</h3>', unsafe_allow_html=True)
        
        st.markdown(f"<div style='text-align:center; margin-bottom:20px;'><b>Xin chào, {st.session_state['current_user']}</b><br><span style='color:#047857; font-weight:800;'>Số dư: {balance:,}đ</span></div>", unsafe_allow_html=True)
        
        st.markdown("<p style='font-size:12px; font-weight:700; color:#94a3b8; text-transform:uppercase; margin-bottom:5px; margin-left:10px;'>Main Menu</p>", unsafe_allow_html=True)
        menu = st.radio("", ["🏠 Bảng Điều Khiển", "✉️ Chiến Dịch Email", "📊 Lịch Sử Nạp", "⚙️ Cài Đặt Hệ Thống"], label_visibility="collapsed")
        
        st.markdown("<div style='margin-top: 100px;'></div>", unsafe_allow_html=True)
        if st.button("🚪 Đăng xuất tài khoản", use_container_width=True):
            st.session_state["logged_in"] = False; st.rerun()

    # ========================================================
    # NỘI DUNG CHÍNH DỰA VÀO MENU ĐÃ CHỌN
    # ========================================================

    # 1. BẢNG ĐIỀU KHIỂN & NẠP TIỀN
    if menu == "🏠 Bảng Điều Khiển":
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 20px;">
            <div><div class="gradient-text" style="font-size: 32px;">Trang Chủ & Dịch Vụ</div><span style="color:#64748b;">Tổng quan hệ thống của bạn</span></div>
            <div><span class="vip-badge {vip_class}">{vip_text}</span></div>
        </div>
        """, unsafe_allow_html=True)

        col_main, col_right = st.columns([7, 3], gap="large")
        
        with col_main:
            # Thống kê
            m1, m2, m3 = st.columns(3)
            my_logs = [l for l in logs_db if st.session_state['current_user'].upper() in str(l.get('raw_data','')).upper() and "Thành công" in str(l.get('status',''))]
            m1.metric(label="Tổng số lần nạp", value=f"{len(my_logs)} Lần")
            m2.metric(label="Cấp bậc hiện tại", value=vip_text.split(" ")[1])
            m3.metric(label="Hạn mức Mail", value="Vô hạn")
            st.markdown("<br>", unsafe_allow_html=True)

            # Nạp tiền
            st.markdown('<div class="pill-header bg-blue">💳 NẠP TIỀN TỰ ĐỘNG 24/7</div>', unsafe_allow_html=True)
            if not st.session_state.get("show_deposit_form") and not st.session_state.get("show_qr"):
                st.info("Hệ thống tự động cộng tiền trong 1-3 phút. Bấm nút bên dưới để lấy QR code thanh toán.")
                if st.button("TẠO HOÁ ĐƠN NẠP TIỀN", type="primary"): 
                    st.session_state["show_deposit_form"] = True; st.rerun()

            if st.session_state.get("show_deposit_form"):
                st.markdown('<div class="glass-box" style="padding:25px;">', unsafe_allow_html=True)
                amount_input = st.number_input("Nhập số tiền cần nạp (VNĐ)", value=st.session_state.get("deposit_amount", 100000), step=10000, min_value=0)
                st.markdown("<br>", unsafe_allow_html=True)
                bc1, bc2 = st.columns(2)
                if bc1.button("Hủy bỏ", use_container_width=True): 
                    st.session_state["show_deposit_form"] = False; st.rerun()
                if bc2.button("Lấy mã QR thanh toán", type="primary", use_container_width=True):
                    if amount_input < 10000: st.toast("Tối thiểu 10.000 VNĐ", icon="⚠️")
                    else:
                        st.session_state["deposit_amount"] = amount_input
                        st.session_state["show_qr"] = True; st.session_state["qr_expire_time"] = time.time() + 600
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

            if st.session_state.get("show_qr"):
                time_left = int(st.session_state["qr_expire_time"] - time.time())
                if time_left <= 0: st.warning("⏳ Mã QR hết hạn."); st.session_state["show_qr"] = False
                else:
                    st.markdown("<div class='glass-box' style='padding:25px; border-color:#fca5a5;'>", unsafe_allow_html=True)
                    cq, ci = st.columns([1, 1.2], gap="large")
                    
                    SEPAY_ACC = "VQRQAHQHF1360"; SEPAY_BANK = "MBBank"; MY_NAME = "PHAN DUC TRUONG SON"
                    amt = st.session_state["deposit_amount"]; cont = f"NAP {st.session_state['current_user']}"
                    qr_url = f"https://qr.sepay.vn/img?acc={SEPAY_ACC}&bank={SEPAY_BANK}&amount={amt}&des={cont.replace(' ', '%20')}"
                    
                    with cq:
                        st.image(qr_url, width=220)
                        components.html(f"<div style='text-align:center; color:red; font-weight:bold; padding:5px; background:#fee2e2; border-radius:8px;'>⏳ Còn lại: <span id='t'></span></div><script>var l={time_left};setInterval(function(){{if(l<=0)document.getElementById('t').innerHTML='HẾT HẠN';else{{var m=Math.floor(l/60),s=l%60;document.getElementById('t').innerHTML=m+':'+(s<10?'0':'')+s;l--;}}}},1000);</script>", height=40)
                    with ci:
                        st.markdown(f"**🏦 Ngân hàng:** {SEPAY_BANK}<br>**👤 Chủ TK:** {MY_NAME}<br>**💳 Số tài khoản:** `{SEPAY_ACC}`<br>**💰 Số tiền:** <b style='color:green; font-size:18px;'>{amt:,} VNĐ</b>", unsafe_allow_html=True)
                        st.markdown("**Nội dung (Bấm 📋 Copy):**"); st.code(cont, language="text")
                        if st.button("🔄 LÀM MỚI SỐ DƯ ĐỂ XÁC NHẬN", type="primary", use_container_width=True): st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

        with col_right:
            # BẢNG TIN (CẬP NHẬT MỚI) Y HỆT ẢNH MẪU
            st.markdown("""
            <div class="news-panel">
                <h4 style="margin-top:0; color:#0f172a; display:flex; align-items:center; gap:8px;">🔔 Cập Nhật Mới</h4>
                <hr style="margin: 10px 0;">
                
                <div class="news-item">
                    <div class="news-date">⏳ Hôm nay</div>
                    <div class="news-title">🚀 Cập nhật giao diện Dashboard SaaS chuẩn Quốc tế. Thêm Huy hiệu VIP tự động.</div>
                </div>
                
                <div class="news-item">
                    <div class="news-date">⏳ Hôm qua</div>
                    <div class="news-title">🛠 Tối ưu thuật toán lách firewall Gmail 5.7.0. Đảm bảo tỷ lệ Inbox 99%.</div>
                </div>
                
                <div class="news-item">
                    <div class="news-date">⏳ Tuần trước</div>
                    <div class="news-title">✅ Tích hợp API SePay nạp tiền tự động bằng QR Code siêu tốc độ.</div>
                </div>
                
                <div style="text-align:center; margin-top: 20px;">
                    <a href="#" style="font-size:13px; color:#3b82f6; font-weight:600; text-decoration:none;">Xem tất cả</a>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # 2. CHIẾN DỊCH GỬI EMAIL
    elif menu == "✉️ Chiến Dịch Email":
        st.markdown('<div class="gradient-text" style="font-size: 32px;">Thiết lập Chiến dịch</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        col_data, col_content = st.columns([1, 1.2], gap="large")
        with col_data:
            st.markdown('<div class="pill-header bg-purple">📁 DỮ LIỆU KHÁCH HÀNG</div>', unsafe_allow_html=True)
            up = st.file_uploader("Tải tệp (.xlsx, .csv)", type=["csv", "xlsx"])
            df = pd.read_excel(up) if up and up.name.endswith("xlsx") else (pd.read_csv(up) if up else None)
            if df is not None: st.toast(f"Đã nhận {len(df)} địa chỉ email.", icon="✅")
                
            attachments = st.file_uploader("📎 Tệp đính kèm (Tối đa 5MB)", accept_multiple_files=True)
            
            delay = st.number_input("⏳ Khoảng nghỉ giữa mỗi Mail (Giây):", value=15, min_value=5)
            if df is not None:
                mins, secs = divmod(len(df) * delay, 60)
                st.info(f"⚡ **Dự kiến hoàn thành:** {mins} phút {secs} giây")

        with col_content:
            st.markdown('<div class="pill-header bg-green">✍️ SOẠN THÔNG ĐIỆP</div>', unsafe_allow_html=True)
            subject = st.text_input("Tiêu đề Email:")
            
            # Thư viện mẫu
            templates = {
                "📝 Tự soạn mới": "",
                "🎁 Báo Khuyến Mãi": f"Kính chào {{{{name}}}},<br><br>Chúng tôi dành tặng bạn voucher giảm giá đặc biệt. Xem ngay bên dưới.",
                "🤝 Thư Cảm Ơn": f"Chào {{{{name}}}},<br><br>Cảm ơn bạn đã đồng hành cùng dịch vụ của chúng tôi thời gian qua."
            }
            selected_temp = st.selectbox("📚 Chọn mẫu nội dung nhanh:", list(templates.keys()))
            
            raw_body = st_quill(value=templates[selected_temp], placeholder="Soạn nội dung hoặc dán từ web vào đây...", html=True)
            if not raw_body: raw_body = ""

        sign_html = st.session_state["s_sign"].replace("\n", "<br>")
        full_email_content = f"<div style='font-family:Arial; line-height:1.8; color:#333;'>{raw_body}<br><br><div style='color:#666; border-top:1px solid #eee; padding-top:10px;'>{sign_html}</div></div>"
        
        st.markdown("<hr style='margin: 30px 0;'>", unsafe_allow_html=True)
        if st.button("🚀 BẮT ĐẦU CHIẾN DỊCH GỬI MAIL", type="primary", use_container_width=True):
            if df is None or not subject: st.error("⚠️ Vui lòng điền đủ thông tin!")
            elif not SYS_EMAIL or not SYS_PWD: st.error("⚠️ Chưa có Email hệ thống ở mục Cài Đặt!")
            else:
                progress = st.progress(0); log = st.expander("📋 Trình giám sát hệ thống (Live)", expanded=True)
                
                # --- THUẬT TOÁN TỐI ƯU CỐT LÕI 5.7.0 ---
                soup = BeautifulSoup(full_email_content, "html.parser")
                for tag in soup(["script", "style", "meta", "noscript", "iframe"]): tag.decompose()
                inline_images = []; img_counter = 0
                
                for img in soup.find_all("img"):
                    src = img.get("src", "")
                    if src.startswith("http"):
                        img.attrs = {"src": src, "style": "max-width: 100%; display: block;"}
                    elif src.startswith("data:image") and img_counter < 2:
                        try:
                            h, e = src.split(",", 1); img_data = base64.b64decode(e); img_counter += 1
                            cid = f"img_inline_{img_counter}"; inline_images.append({"cid": cid, "data": img_data, "type": "png"})
                            img.attrs = {"src": f"cid:{cid}", "style": "max-width: 100%; display: block;"}
                        except: img.decompose()
                    else: img.decompose()

                prepared_html_template = str(soup) 
                run_tk = current_user_data.get("tele_token", ""); run_id = current_user_data.get("tele_chat_id", "")
                send_tele_msg(run_tk, run_id, f"🚀 <b>BẮT ĐẦU CHIẾN DỊCH</b>\n👤 User: {st.session_state['current_user']}")
                
                success_list, error_list = [], []

                for index, row in df.iterrows():
                    try:
                        target_email = str(row.get(next((c for c in df.columns if c.lower() in ["email", "mail"]), None), row.iloc[0])).strip()
                        target_name = str(row.get(next((c for c in df.columns if c.lower() in ["name", "tên"]), None), "Quý khách"))
                        
                        msg_root = MIMEMultipart("mixed") 
                        msg_root["From"] = f"{st.session_state['s_name']} <{SYS_EMAIL}>"
                        msg_root["To"] = target_email; msg_root["Subject"] = subject
                        
                        msg_related = MIMEMultipart("related"); msg_root.attach(msg_related)
                        msg_related.attach(MIMEText(prepared_html_template.replace("{{name}}", target_name), "html", "utf-8"))
                        
                        for i in inline_images:
                            ip = MIMEImage(i["data"], _subtype=i["type"]); ip.add_header("Content-ID", f"<{i['cid']}>"); msg_related.attach(ip)
                        if attachments:
                            for f in attachments:
                                p = MIMEBase("application", "octet-stream"); p.set_payload(f.read())
                                encoders.encode_base64(p); p.add_header("Content-Disposition", f"attachment; filename={f.name}")
                                msg_root.attach(p); f.seek(0)
                                
                        with smtplib.SMTP("smtp.gmail.com", 587) as server:
                            server.starttls(); server.login(SYS_EMAIL, SYS_PWD); server.send_message(msg_root)
                            
                        success_list.append(target_email); log.write(f"✅ Đã gửi: {target_email}")
                        st.toast(f"Đã gửi thành công cho {target_name}", icon="✉️")
                    except Exception as e:
                        error_list.append(target_email); log.write(f"❌ Lỗi: {target_email} ({e})")
                        
                    progress.progress((index + 1) / len(df)); time.sleep(delay)
                    
                play_success_sound()
                st.success("🎉 Chiến dịch hoàn tất!")
                
                csv_buf = io.BytesIO()
                pd.DataFrame({"Email": success_list + error_list, "Kết quả": ["Thành công"] * len(success_list) + ["Lỗi"] * len(error_list)}).to_csv(csv_buf, index=False, encoding="utf-8-sig")
                send_tele_msg(run_tk, run_id, f"📊 <b>TỔNG KẾT</b>\n✅ Thành công: {len(success_list)}\n❌ Lỗi: {len(error_list)}")
                send_tele_file(run_tk, run_id, csv_buf.getvalue(), "ket_qua.csv")
                st.download_button("📥 TẢI BÁO CÁO (.CSV)", data=csv_buf.getvalue(), file_name="ket_qua.csv", use_container_width=True)

    # 3. LỊCH SỬ NẠP TIỀN
    elif menu == "📊 Lịch Sử Nạp":
        st.markdown('<div class="gradient-text" style="font-size: 32px;">Lịch sử Giao dịch</div><br>', unsafe_allow_html=True)
        h_list = []; chart_data = []; cur_u = st.session_state['current_user'].upper()
        
        for l in logs_db:
            if cur_u in str(l.get('raw_data','')).upper():
                try:
                    pld = json.loads(l.get('raw_data','{}'))
                    val_int = int(pld.get('transferAmount', 0))
                    amt = f"{val_int:,} VNĐ"
                except: val_int = 0; amt = "---"
                
                status = str(l.get('status', ''))
                if "Thành công" in status: 
                    status = "✅ Thành công"
                    if val_int > 0: chart_data.append({"Ngày": l.get('time', '').split(" ")[0], "Số tiền (VNĐ)": val_int})
                elif "Lỗi" in status: status = "❌ " + status
                h_list.append({"Ngày giờ": l.get('time', ''), "Số tiền": amt, "Trạng thái": status})

        if not h_list: 
            st.markdown("""
            <div style='text-align:center; padding: 50px; background: rgba(255,255,255,0.5); border-radius: 16px; border: 2px dashed #cbd5e1;'>
                <h1 style='font-size: 80px; margin: 0; filter: grayscale(50%);'>🪹</h1>
                <h3 style='color:#475569; margin-top: 15px;'>Chưa có giao dịch nào</h3>
                <p style='color:#64748b; font-size: 15px;'>Bạn chưa thực hiện khoản nạp nào. Quay lại Trang chủ để nạp tiền nhé!</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            if chart_data:
                st.markdown("<b style='color:#1e40af;'>📈 Biểu đồ lưu lượng nạp tiền</b>", unsafe_allow_html=True)
                df_chart = pd.DataFrame(chart_data).groupby("Ngày").sum()
                st.bar_chart(df_chart, color="#3b82f6")
                st.markdown("<hr style='margin: 20px 0;'>", unsafe_allow_html=True)

            st.dataframe(pd.DataFrame(h_list), use_container_width=True)

    # 4. CÀI ĐẶT HỆ THỐNG
    elif menu == "⚙️ Cài Đặt Hệ Thống":
        st.markdown('<div class="gradient-text" style="font-size: 32px;">Cấu hình Máy chủ</div><br>', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown("<b style='color:#1e40af;'>📧 Máy chủ gửi Email</b>", unsafe_allow_html=True)
            st.session_state["s_name"] = st.text_input("Tên hiển thị khi gửi thư:", value=st.session_state["s_name"])
            st.info(f"Hệ thống đang sử dụng hòm thư Admin: **{SYS_EMAIL}**")
            
            with st.popover("❓ Bấm vào đây để xem cách lấy Mật khẩu ứng dụng Gmail"):
                st.markdown("""
                <div style="font-size: 14px; color: #334155; line-height: 1.6;">
                    <b>Làm theo 4 bước sau:</b><br>
                    <b>1.</b> Truy cập link này: <a href="https://myaccount.google.com/security" target="_blank"><b>Bảo mật Google</b></a>.<br>
                    <b>2.</b> Bật <b>Xác minh 2 bước</b>.<br>
                    <b>3.</b> Tìm ô <b>Tìm kiếm</b> ➔ Gõ chữ <b>Mật khẩu ứng dụng</b> ➔ Chọn kết quả.<br>
                    <b>4.</b> Gõ tên <i>BulkMail</i> ➔ Bấm <b>Tạo</b> để lấy 16 chữ cái.
                </div>
                """, unsafe_allow_html=True)
                
        with c2:
            st.markdown("<b style='color:#1e40af;'>🔔 Báo cáo Telegram & Chữ ký</b>", unsafe_allow_html=True)
            tk = st.text_input("Bot Token Telegram:", value=current_user_data.get("tele_token", ""), type="password")
            cid = st.text_input("Chat ID Telegram:", value=current_user_data.get("tele_chat_id", ""))
            st.session_state["s_sign"] = st.text_area("Chữ ký cuối thư:", value=st.session_state["s_sign"])
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("💾 LƯU CẤU HÌNH NGAY", type="primary", use_container_width=True):
                if save_config_api(st.session_state["current_user"], tk, cid): 
                    st.toast("Đã lưu cấu hình thành công!", icon="✅")

# NÚT LIÊN HỆ NỔI (Zalo & Telegram)
st.markdown("""<div class="floating-container"><a href="https://zalo.me/0935748199" target="_blank" class="float-btn"><img src="https://upload.wikimedia.org/wikipedia/commons/9/91/Icon_of_Zalo.svg" width="30"></a><a href="https://t.me/BulkMail_Pro" target="_blank" class="float-btn"><img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg" width="30"></a></div>""", unsafe_allow_html=True)
