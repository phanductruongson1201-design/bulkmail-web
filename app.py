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

def generate_random_password(length=8):
    chars = string.ascii_letters + string.digits + "@#$"
    return ''.join(random.choice(chars) for _ in range(length))

def send_recovery_email(to_email, username, new_password):
    if not SYS_EMAIL or not SYS_PWD: return False
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Hệ thống BulkMail <{SYS_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = "Mật khẩu tạm thời của bạn"
        body = f"<h3>Chào {username},</h3><p>Mật khẩu tạm thời: <b style='color:red;'>{new_password}</b></p><p>Hệ thống yêu cầu bạn đổi mật khẩu mới ngay khi đăng nhập.</p>"
        msg.attach(MIMEText(body, 'html'))
        s = smtplib.SMTP("smtp.gmail.com", 587); s.starttls()
        s.login(SYS_EMAIL, SYS_PWD); s.send_message(msg); s.quit()
        return True
    except: return False

# ==========================================
# GIAO DIỆN CSS & NÚT NỔI
# ==========================================
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%); }
    .auth-box { max-width: 450px; margin: auto; padding: 40px; background: white; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
    .stButton>button { background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%) !important; color: white !important; border-radius: 8px; font-weight: 600; }
    
    .floating-container { position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 15px; z-index: 999999; }
    .float-btn { width: 55px; height: 55px; border-radius: 50%; box-shadow: 0 4px 12px rgba(0,0,0,0.3); transition: 0.3s; display: flex; justify-content: center; align-items: center; background: white; overflow: hidden; }
    .float-btn:hover { transform: scale(1.1); }
    .float-btn img { width: 100%; height: 100%; object-fit: cover; }
</style>
""", unsafe_allow_html=True)

# Khởi tạo trạng thái phiên
if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'must_reset' not in st.session_state: st.session_state['must_reset'] = False

LOGO_URL = "https://storage.googleapis.com/smart-home-v3-files/media-files/z7587176856031_f586c2b79f66ddf86eae7cb7405fc298.jpg"

# ==========================================
# LUỒNG XỬ LÝ: ĐĂNG NHẬP -> ÉP ĐỔI MẬT KHẨU
# ==========================================

# TRƯỜNG HỢP 1: CHƯA ĐĂNG NHẬP
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
                    # Kiểm tra xem có đang bị đánh dấu Reset không
                    if user_data.get("is_reset") == True:
                        st.session_state['must_reset'] = True
                        st.session_state['logged_in'] = True
                        st.rerun()
                    else:
                        st.session_state['logged_in'] = True
                        st.rerun()
                else: st.error("❌ Sai tài khoản hoặc mật khẩu!")

        with tab_forgot:
            fg_user = st.text_input("Username")
            fg_email = st.text_input("Email đăng ký")
            if st.button("Cấp lại mật khẩu tạm", type="primary", use_container_width=True):
                if fg_user in users_db and users_db[fg_user].get("email") == fg_email:
                    temp_p = generate_random_password()
                    if reset_password_api(fg_user, fg_email, hash_password(temp_p), True):
                        if send_recovery_email(fg_email, fg_user, temp_p):
                            st.success("✅ Đã gửi MK tạm vào Email của bạn!")
                else: st.error("❌ Thông tin không khớp!")
        st.markdown('</div>', unsafe_allow_html=True)

# TRƯỜNG HỢP 2: ĐÃ ĐĂNG NHẬP NHƯNG ĐANG DÙNG MK TẠM (BẮT ĐỔI NGAY)
elif st.session_state['must_reset']:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        st.header("🔑 Tạo mật khẩu mới")
        st.info("Vì lý do bảo mật, bạn cần tạo mật khẩu riêng thay cho mật khẩu tạm thời.")
        new_p = st.text_input("Mật khẩu mới", type="password")
        conf_p = st.text_input("Xác nhận mật khẩu", type="password")
        if st.button("Lưu & Vào hệ thống", type="primary", use_container_width=True):
            if new_p == conf_p and len(new_p) >= 6:
                u_db = load_users()
                # Ghi đè MK mới và gỡ bỏ cờ is_reset (is_reset=False)
                if reset_password_api(st.session_state['current_user'], u_db[st.session_state['current_user']]['email'], hash_password(new_p), False):
                    st.session_state['must_reset'] = False
                    st.success("✅ Đã cập nhật mật khẩu thành công!")
                    time.sleep(1); st.rerun()
            else: st.error("❌ Mật khẩu không khớp hoặc quá ngắn!")
        st.markdown('</div>', unsafe_allow_html=True)

# TRƯỜNG HỢP 3: GIAO DIỆN CHÍNH
else:
    # (Phần Dashboard của bạn - Gửi Email, Cài đặt...)
    st.title("BulkMail Pro Dashboard")
    if st.button("Thoát"):
        st.session_state['logged_in'] = False
        st.rerun()

# ==========================================
# NÚT LIÊN HỆ NỔI (ZALO & TELEGRAM)
# ==========================================
st.markdown(f"""
<div class="floating-container">
    <a href="https://zalo.me/0935748199" target="_blank" class="float-btn">
        <img src="https://cdn.haitrieu.com/wp-content/uploads/2022/01/Logo-Zalo-Arc.png">
    </a>
    <a href="https://t.me/BulkMail_Pro" target="_blank" class="float-btn">
        <img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg">
    </a>
</div>
""", unsafe_allow_html=True)
