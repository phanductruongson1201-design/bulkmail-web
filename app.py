import streamlit as st
import pandas as pd
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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

def reset_password_api(username, email, new_password_hash, is_reset_status):
    if not DB_URL: return False
    try:
        res = requests.post(DB_URL, json={
            "action": "reset", 
            "username": username, 
            "email": email, 
            "new_password": new_password_hash, 
            "is_reset": is_reset_status
        }).json()
        return res.get("status") == "success"
    except: return False

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Hàm tạo mã OTP 6 số ngắn gọn
def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

def send_otp_email(to_email, username, otp_code):
    if not SYS_EMAIL or not SYS_PWD: return False
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Hệ thống BulkMail <{SYS_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = f"{otp_code} là mã xác nhận khôi phục mật khẩu của bạn"
        body = f"""
        <h3>Chào {username},</h3>
        <p>Bạn đã yêu cầu khôi phục mật khẩu. Vui lòng nhập mã xác nhận dưới đây vào ứng dụng:</p>
        <h2 style='color:#1e3a8a; letter-spacing: 5px;'>{otp_code}</h2>
        <p>Mã này dùng để xác thực và giúp bạn tạo mật khẩu mới ngay lập tức.</p>
        """
        msg.attach(MIMEText(body, 'html'))
        s = smtplib.SMTP("smtp.gmail.com", 587); s.starttls()
        s.login(SYS_EMAIL, SYS_PWD); s.send_message(msg); s.quit()
        return True
    except: return False

# ==========================================
# GIAO DIỆN CSS & TRẠNG THÁI
# ==========================================
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%); }
    .auth-box { max-width: 450px; margin: auto; padding: 40px; background: white; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
    .floating-container { position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 15px; z-index: 999999; }
    .float-btn { width: 55px; height: 55px; border-radius: 50%; box-shadow: 0 4px 12px rgba(0,0,0,0.3); display: flex; justify-content: center; align-items: center; background: white; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'otp_verified' not in st.session_state: st.session_state['otp_verified'] = False

LOGO_URL = "https://storage.googleapis.com/smart-home-v3-files/media-files/z7587176856031_f586c2b79f66ddf86eae7cb7405fc298.jpg"

# ==========================================
# LUỒNG XỬ LÝ QUÊN MẬT KHẨU MỚI
# ==========================================

if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        st.image(LOGO_URL, width=250)
        tab_login, tab_forgot = st.tabs(["🔐 Đăng nhập", "🔑 Quên mật khẩu"])
        users_db = load_users()

        with tab_login:
            log_user = st.text_input("Tên đăng nhập")
            log_pwd = st.text_input("Mật khẩu", type="password")
            if st.button("Đăng nhập", type="primary", use_container_width=True):
                user_data = users_db.get(log_user)
                if user_data and user_data.get("password") == hash_password(log_pwd):
                    st.session_state['current_user'] = log_user
                    st.session_state['logged_in'] = True
                    st.rerun()
                else: st.error("❌ Sai tài khoản hoặc mật khẩu!")

        with tab_forgot:
            if not st.session_state['otp_verified']:
                fg_user = st.text_input("Tên đăng nhập của bạn")
                fg_email = st.text_input("Email đã đăng ký")
                
                # Nút yêu cầu gửi mã
                if st.button("Gửi mã xác nhận", type="primary", use_container_width=True):
                    if fg_user in users_db and users_db[fg_user].get("email") == fg_email:
                        otp_code = generate_otp()
                        # Lưu mã OTP vào cột Password tạm thời và đánh dấu is_reset = True
                        if reset_password_api(fg_user, fg_email, hash_password(otp_code), True):
                            if send_otp_email(fg_email, fg_user, otp_code):
                                st.success(f"✅ Mã xác nhận đã được gửi tới {fg_email}!")
                    else: st.error("❌ Thông tin không chính xác!")

                st.markdown("---")
                # Ô nhập mã OTP để xác thực
                input_otp = st.text_input("Nhập mã 6 số từ Email:", max_chars=6)
                if st.button("Xác thực mã", use_container_width=True):
                    user_info = users_db.get(fg_user)
                    if user_info and user_info.get("password") == hash_password(input_otp):
                        st.session_state['otp_verified'] = True
                        st.session_state['current_user'] = fg_user
                        st.rerun()
                    else: st.error("❌ Mã xác nhận không đúng!")
            
            # Nếu đã xác thực mã xong, hiện ngay màn hình đổi mật khẩu
            else:
                st.subheader("🔑 Tạo mật khẩu mới")
                new_p = st.text_input("Mật khẩu mới", type="password")
                conf_p = st.text_input("Xác nhận mật khẩu", type="password")
                if st.button("Cập nhật & Đăng nhập", type="primary", use_container_width=True):
                    if new_p == conf_p and len(new_p) >= 6:
                        u_db = load_users()
                        if reset_password_api(st.session_state['current_user'], u_db[st.session_state['current_user']]['email'], hash_password(new_p), False):
                            st.session_state['otp_verified'] = False
                            st.session_state['logged_in'] = True
                            st.success("✅ Đã đổi mật khẩu! Đang vào Dashboard...")
                            time.sleep(1); st.rerun()
                    else: st.error("❌ Mật khẩu không khớp hoặc quá ngắn!")
        st.markdown('</div>', unsafe_allow_html=True)

# GIAO DIỆN CHÍNH
else:
    st.title(f"Chào mừng {st.session_state['current_user']} đến với BulkMail Pro")
    if st.button("Đăng xuất"):
        st.session_state['logged_in'] = False
        st.rerun()

# NÚT LIÊN HỆ NỔI
st.markdown("""
<div class="floating-container">
    <a href="https://zalo.me/0935748199" target="_blank" class="float-btn"><img src="https://cdn.haitrieu.com/wp-content/uploads/2022/01/Logo-Zalo-Arc.png"></a>
    <a href="https://t.me/BulkMail_Pro" target="_blank" class="float-btn"><img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg"></a>
</div>
""", unsafe_allow_html=True)
