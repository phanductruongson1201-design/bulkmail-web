import streamlit as st
import pandas as pd
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import time
import requests
import hashlib
import string
import random

# 1. Cấu hình trang Web
st.set_page_config(page_title="BulkMail Pro - Trường Sơn", page_icon="🔵", layout="wide")

# ==========================================
# API CƠ SỞ DỮ LIỆU & HỆ THỐNG
# ==========================================
DB_URL = st.secrets.get("DB_URL", "")
SYS_EMAIL = st.secrets.get("SENDER_EMAIL", "")
SYS_PWD = st.secrets.get("APP_PASSWORD", "")

def load_users():
    if not DB_URL: return {}
    try: return requests.get(DB_URL).json()
    except: return {}

def save_user_api(username, password_hash, email):
    if not DB_URL: return
    try: requests.post(DB_URL, json={"action": "register", "username": username, "password": password_hash, "email": email})
    except: pass

def reset_password_api(username, email, new_password_hash, is_reset_status):
    if not DB_URL: return False
    try:
        res = requests.post(DB_URL, json={
            "action": "reset", "username": username, "email": email, 
            "new_password": new_password_hash, "is_reset": is_reset_status
        }).json()
        return res.get("status") == "success"
    except: return False

def save_config_api(username, tele_token, tele_chat_id):
    if not DB_URL: return False
    try:
        res = requests.post(DB_URL, json={"action": "update_config", "username": username, "tele_token": tele_token, "tele_chat_id": tele_chat_id}).json()
        return res.get("status") == "success"
    except: return False

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

def send_otp_email(to_email, username, otp_code):
    if not SYS_EMAIL or not SYS_PWD: return False
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Hệ thống BulkMail <{SYS_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = f"{otp_code} là mã xác nhận của bạn"
        body = f"<h3>Chào {username},</h3><p>Mã xác nhận khôi phục mật khẩu: <b>{otp_code}</b></p>"
        msg.attach(MIMEText(body, 'html'))
        s = smtplib.SMTP("smtp.gmail.com", 587); s.starttls()
        s.login(SYS_EMAIL, SYS_PWD); s.send_message(msg); s.quit()
        return True
    except: return False

# ==========================================
# GIAO DIỆN CSS
# ==========================================
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%); }
    .auth-box { max-width: 480px; margin: auto; padding: 30px; background: white; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
    .stButton>button { background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%) !important; color: white !important; border-radius: 8px; font-weight: 600; }
    
    .logo-container { display: flex; justify-content: center; align-items: center; margin-bottom: 25px; width: 100%; }
    .logo-container img { border-radius: 50% !important; width: 180px !important; height: 180px !important; object-fit: cover !important; border: 4px solid white; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }

    .hero-banner { background: linear-gradient(rgba(30, 58, 138, 0.85), rgba(30, 58, 138, 0.85)), url('https://images.unsplash.com/photo-1557683316-973673baf926?auto=format&fit=crop&w=1350&q=80'); background-size: cover; padding: 40px; border-radius: 15px; color: white; text-align: center; margin-bottom: 25px; }
    .hero-banner h1 { font-size: 32px !important; font-weight: 800 !important; color: white !important; }

    .welcome-text { text-align: center; color: #1e3a8a; font-weight: 800; margin-bottom: 20px; font-size: 28px; text-transform: uppercase; }
    .section-header { color: #1e3a8a; border-bottom: 2px solid #1e3a8a; padding-bottom: 5px; margin-top: 20px; font-size: 20px; font-weight: 700; }
    .stTabs [data-baseweb="tab-list"] { justify-content: center !important; }

    .floating-container { position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 12px; z-index: 999999; }
    .float-btn { width: 52px; height: 52px; border-radius: 50%; box-shadow: 0 4px 12px rgba(0,0,0,0.2); display: flex; justify-content: center; align-items: center; background: white; }
    .float-btn img { width: 75%; height: 75%; object-fit: contain; }
</style>
""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'otp_verified' not in st.session_state: st.session_state['otp_verified'] = False
if 'otp_sent' not in st.session_state: st.session_state['otp_sent'] = False

LOGO_URL = "logo_moi.png"

# ==========================================
# 1. HỆ THỐNG ĐĂNG NHẬP / ĐĂNG KÝ / QUÊN MK
# ==========================================
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        st.markdown('<p class="welcome-text">BULKMAIL PRO</p>', unsafe_allow_html=True)
        
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        try: st.image(LOGO_URL, width=180)
        except: st.info("🎯 TRƯỜNG SƠN MARKETING")
        st.markdown('</div>', unsafe_allow_html=True)
        
        tab_login, tab_reg, tab_forgot = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký", "🔑 Quên MK"])
        users_db = load_users()

        with tab_login:
            log_user = st.text_input("Tên đăng nhập", key="login_u")
            log_pwd = st.text_input("Mật khẩu", type="password", key="login_p")
            if st.button("ĐĂNG NHẬP", use_container_width=True):
                u_data = users_db.get(log_user)
                if u_data and u_data.get("password") == hash_password(log_pwd):
                    st.session_state['current_user'] = log_user
                    st.session_state['logged_in'] = True
                    st.rerun()
                else: st.error("❌ Sai tài khoản hoặc mật khẩu!")

        with tab_reg:
            reg_user = st.text_input("Tên đăng nhập mới", key="reg_u")
            reg_email = st.text_input("Email (để khôi phục mật khẩu)", key="reg_e")
            reg_pwd = st.text_input("Mật khẩu", type="password", key="reg_p")
            reg_pwd_confirm = st.text_input("Xác nhận mật khẩu", type="password", key="reg_pc")
            
            if st.button("TẠO TÀI KHOẢN", use_container_width=True):
                if not reg_user or not reg_email or not reg_pwd:
                    st.warning("⚠️ Vui lòng điền đủ thông tin!")
                elif reg_user in users_db:
                    st.error("❌ Tên đăng nhập đã tồn tại!")
                elif reg_pwd != reg_pwd_confirm:
                    st.error("❌ Mật khẩu xác nhận không khớp!")
                else:
                    save_user_api(reg_user, hash_password(reg_pwd), reg_email)
                    st.success("✅ Đăng ký thành công! Hãy chuyển sang tab Đăng nhập.")

        with tab_forgot:
            if not st.session_state['otp_verified']:
                fg_user = st.text_input("Nhập tên đăng nhập", key="fg_u")
                fg_email = st.text_input("Nhập email đã đăng ký", key="fg_e")
                
                if st.button("GỬI MÃ XÁC THỰC (OTP)", use_container_width=True):
                    if fg_user in users_db and users_db[fg_user].get("email") == fg_email:
                        otp = generate_otp()
                        # Lưu OTP tạm thời vào DB dưới dạng password để xác thực
                        if reset_password_api(fg_user, fg_email, hash_password(otp), True):
                            if send_otp_email(fg_email, fg_user, otp):
                                st.session_state['otp_sent'] = True
                                st.success(f"✅ Mã OTP đã được gửi tới {fg_email}")
                    else:
                        st.error("❌ Thông tin tài khoản hoặc email không chính xác!")
                
                if st.session_state['otp_sent']:
                    input_otp = st.text_input("Nhập mã OTP 6 số:", max_chars=6, key="otp_i")
                    if st.button("XÁC THỰC OTP", use_container_width=True):
                        u_info = load_users().get(fg_user)
                        if u_info and u_info.get("password") == hash_password(input_otp):
                            st.session_state['otp_verified'] = True
                            st.session_state['target_user'] = fg_user
                            st.rerun()
                        else:
                            st.error("❌ Mã OTP không đúng hoặc đã hết hạn!")
            else:
                st.info(f"Đang đặt lại mật khẩu cho: **{st.session_state['target_user']}**")
                new_p = st.text_input("Mật khẩu mới", type="password", key="new_p")
                new_p_c = st.text_input("Xác nhận mật khẩu mới", type="password", key="new_pc")
                
                if st.button("CẬP NHẬT MẬT KHẨU", use_container_width=True):
                    if new_p == new_p_c and len(new_p) >= 6:
                        u_db = load_users()
                        target = st.session_state['target_user']
                        if reset_password_api(target, u_db[target]['email'], hash_password(new_p), False):
                            st.session_state['otp_verified'] = False
                            st.session_state['otp_sent'] = False
                            st.success("✅ Đổi mật khẩu thành công! Hãy đăng nhập lại.")
                    else:
                        st.error("❌ Mật khẩu không khớp hoặc quá ngắn!")
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 2. DASHBOARD CHÍNH (LOẠI BỎ LOGO)
# ==========================================
else:
    head_col1, head_col2 = st.columns([6, 1])
    head_col1.markdown(f"### 👋 Xin chào, **{st.session_state['current_user']}**")
    if head_col2.button("🚪 Đăng xuất", use_container_width=True):
        st.session_state['logged_in'] = False
        st.rerun()

    st.markdown("""
    <div class="hero-banner">
        <h1>BULKMAIL PRO – GIẢI PHÁP EMAIL MARKETING HÀNG LOẠT</h1>
        <p>Gửi hàng ngàn email cá nhân hóa chuyên nghiệp chỉ với một cú nhấp chuột.</p>
    </div>
    """, unsafe_allow_html=True)

    # ... (Các phần cấu hình 1-5 giữ nguyên như bản trước) ...
    st.info("💡 Hệ thống gửi email hàng loạt cá nhân hóa. Vui lòng sử dụng danh sách liên hệ hợp pháp.")
    # (Dán tiếp phần Dashboard của bạn vào đây)

# NÚT LIÊN HỆ NỔI
st.markdown("""
<div class="floating-container">
    <a href="https://zalo.me/0935748199" target="_blank" class="float-btn" style="border: 2px solid #0068ff;">
        <img src="https://cdn.haitrieu.com/wp-content/uploads/2022/01/Logo-Zalo-Arc.png">
    </a>
    <a href="https://t.me/BulkMail_Pro" target="_blank" class="float-btn" style="border: 2px solid #229ED9;">
        <img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg">
    </a>
</div>
""", unsafe_allow_html=True)
