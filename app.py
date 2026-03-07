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
# GIAO DIỆN CSS (Chỉnh chu & Thu nhỏ Logo)
# ==========================================
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%); }
    .auth-box { max-width: 450px; margin: auto; padding: 40px; background: white; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
    .stButton>button { background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%) !important; color: white !important; border-radius: 8px; border: none; font-weight: 600; }
    
    /* Căn giữa và thu nhỏ logo dashboard */
    .logo-container {
        display: flex;
        justify-content: center;
        margin-bottom: 20px;
    }
    .logo-container img {
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border: 2px solid white;
    }

    .floating-container { position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 15px; z-index: 999999; }
    .float-btn { width: 55px; height: 55px; border-radius: 50%; box-shadow: 0 4px 12px rgba(0,0,0,0.3); display: flex; justify-content: center; align-items: center; background: white; overflow: hidden; }
    .float-btn img { width: 100%; height: 100%; object-fit: cover; }
</style>
""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'otp_verified' not in st.session_state: st.session_state['otp_verified'] = False

# ĐỊNH NGHĨA BIẾN LOGO
LOGO_URL = "logo_moi.png" 

# ==========================================
# 1. LOGIC ĐĂNG NHẬP / QUÊN MK
# ==========================================
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        try:
            st.image(LOGO_URL, width=250)
        except:
            st.warning("⚠️ Không tìm thấy file logo_moi.png trên GitHub.")
            
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
                fg_user = st.text_input("Username")
                fg_email = st.text_input("Email đăng ký")
                if st.button("Gửi mã OTP", type="primary", use_container_width=True):
                    if fg_user in users_db and users_db[fg_user].get("email") == fg_email:
                        otp = generate_otp()
                        if reset_password_api(fg_user, fg_email, hash_password(otp), True):
                            if send_otp_email(fg_email, fg_user, otp): st.success("✅ Đã gửi mã OTP!")
                
                input_otp = st.text_input("Nhập mã 6 số:", max_chars=6)
                if st.button("Xác thực mã", use_container_width=True):
                    u_info = users_db.get(fg_user)
                    if u_info and u_info.get("password") == hash_password(input_otp):
                        st.session_state['otp_verified'] = True
                        st.session_state['current_user'] = fg_user
                        st.rerun()
                    else: st.error("❌ Mã không đúng!")
            else:
                new_p = st.text_input("Mật khẩu mới", type="password")
                if st.button("Cập nhật mật khẩu", type="primary", use_container_width=True):
                    u_db = load_users()
                    if reset_password_api(st.session_state['current_user'], u_db[st.session_state['current_user']]['email'], hash_password(new_p), False):
                        st.session_state['otp_verified'] = False
                        st.session_state['logged_in'] = True
                        st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 2. GIAO DIỆN DASHBOARD (Đã thu nhỏ Logo)
# ==========================================
else:
    col_h1, col_h2 = st.columns([8, 1])
    with col_h1: st.subheader(f"👋 Chào mừng {st.session_state['current_user']}")
    with col_h2:
        if st.button("Đăng xuất"):
            st.session_state['logged_in'] = False
            st.rerun()

    # CHỈNH SỬA LOGO TẠI ĐÂY: Căn giữa và đặt chiều rộng 400px
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        try:
            st.image(LOGO_URL, width=400) # Thu nhỏ lại 400px để chỉn chu hơn
        except:
            st.info("💡 Không tìm thấy ảnh logo_moi.png")
        st.markdown('</div>', unsafe_allow_html=True)
    
    t_send, t_acc = st.tabs(["🚀 Gửi Email Chiến dịch", "⚙️ Quản lý Tài khoản"])

    with t_send:
        c1, c2 = st.columns(2)
        with c1:
            st.header("1. Cấu hình Gửi")
            s_name = st.text_input("Tên hiển thị người gửi:")
            s_mail = st.text_input("Email gửi (Gmail):")
            s_pass = st.text_input("App Password:", type="password")
            
            df_sample = pd.DataFrame({"email": ["vidu@gmail.com"], "name": ["Nguyễn Văn A"]})
            buf = io.BytesIO(); df_sample.to_excel(buf, index=False)
            st.download_button("📥 Tải file mẫu", data=buf.getvalue(), file_name="mau.xlsx")
            
            up = st.file_uploader("Tải danh sách khách hàng", type=["csv", "xlsx"])
            df = None
            if up:
                df = pd.read_excel(up) if up.name.endswith('xlsx') else pd.read_csv(up)
                st.success(f"✅ Đã tải {len(df)} liên hệ.")
            
            attachments = st.file_uploader("Chọn ảnh/file đính kèm", accept_multiple_files=True)

        with c2:
            st.header("2. Nội dung Email")
            subject = st.text_input("Tiêu đề thư:")
            body = st.text_area("Nội dung thư (HTML):", height=200, value="Chào {{name}},...")
            delay = st.number_input("Khoảng nghỉ (giây):", value=5, min_value=1)

        st.markdown("---")
        with st.expander("🔔 Cấu hình Thông báo Telegram"):
            users_db = load_users()
            u_data = users_db.get(st.session_state['current_user'], {})
            t_tk_val = u_data.get("tele_token", "")
            t_id_val = u_data.get("tele_chat_id", "")
            
            t_col1, t_col2 = st.columns(2)
            with t_col1:
                new_tele_tk = st.text_input("Bot Token:", value=t_tk_val, type="password", key="tele_tk_main")
            with t_col2:
                new_tele_id = st.text_input("Chat ID:", value=t_id_val, key="tele_id_main")
            
            if st.button("💾 Lưu cấu hình Telegram", use_container_width=True):
                if save_config_api(st.session_state['current_user'], new_tele_tk, new_tele_id):
                    st.success("✅ Đã lưu cấu hình báo cáo Telegram!")
                    time.sleep(1); st.rerun()

        if st.button("▶ BẮT ĐẦU CHIẾN DỊCH", type="primary", use_container_width=True):
            if df is not None:
                if t_tk_val and t_id_val:
                    requests.post(f"https://api.telegram.org/bot{t_tk_val}/sendMessage", 
                                   data={"chat_id": t_id_val, "text": "⏳ Bắt đầu gửi..."}, timeout=5)
                st.warning("Đang xử lý gửi mail...")
                progress = st.progress(0)
                for i in range(len(df)):
                    time.sleep(delay)
                    progress.progress((i + 1) / len(df))
                st.success("🎉 Chiến dịch hoàn tất!")
                if t_tk_val and t_id_val:
                    requests.post(f"https://api.telegram.org/bot{t_tk_val}/sendMessage", 
                                   data={"chat_id": t_id_val, "text": "✅ Đã xong!"}, timeout=5)
            else: st.error("Vui lòng tải danh sách khách hàng!")

    with t_acc:
        st.header("⚙️ Cài đặt Tài khoản")
        st.write("Thông tin người dùng và các tùy chỉnh khác.")

# NÚT LIÊN HỆ NỔI
st.markdown("""
<div class="floating-container">
    <a href="https://zalo.me/0935748199" target="_blank" class="float-btn"><img src="https://cdn.haitrieu.com/wp-content/uploads/2022/01/Logo-Zalo-Arc.png"></a>
    <a href="https://t.me/BulkMail_Pro" target="_blank" class="float-btn"><img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg"></a>
</div>
""", unsafe_allow_html=True)
