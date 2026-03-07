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

def send_tele_msg(token, chat_id, message):
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, data={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=5)
        except: pass

def send_tele_file(token, chat_id, file_content, file_name):
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendDocument"
            files = {'document': (file_name, file_content)}
            requests.post(url, data={'chat_id': chat_id}, files=files, timeout=10)
        except: pass

# ==========================================
# GIAO DIỆN CSS (LOGO TRÒN & CĂN GIỮA)
# ==========================================
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%); }
    .auth-box { max-width: 480px; margin: auto; padding: 30px; background: white; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
    .stButton>button { background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%) !important; color: white !important; border-radius: 8px; font-weight: 600; }
    
    .logo-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-bottom: 25px;
        width: 100%;
    }
    .logo-container img {
        border-radius: 50% !important;
        width: 180px !important;
        height: 180px !important;
        object-fit: cover !important;
        border: 4px solid white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }

    .hero-banner {
        background: linear-gradient(rgba(30, 58, 138, 0.85), rgba(30, 58, 138, 0.85)), url('https://images.unsplash.com/photo-1557683316-973673baf926?auto=format&fit=crop&w=1350&q=80');
        background-size: cover;
        padding: 40px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin-bottom: 25px;
    }
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

LOGO_URL = "logo_moi.png"

# ==========================================
# 1. HỆ THỐNG ĐĂNG NHẬP
# ==========================================
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        st.markdown('<p class="welcome-text">CHÀO MỪNG BẠN ĐẾN VỚI BULKMAIL PRO</p>', unsafe_allow_html=True)
        
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        try: st.image(LOGO_URL, width=180)
        except: st.info("🎯 TRƯỜNG SƠN MARKETING")
        st.markdown('</div>', unsafe_allow_html=True)
        
        tab_login, tab_reg, tab_forgot = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký", "🔑 Quên MK"])
        users_db = load_users()

        with tab_login:
            log_user = st.text_input("Tên đăng nhập", key="login_u")
            log_pwd = st.text_input("Mật khẩu", type="password", key="login_p")
            if st.button("ĐĂNG NHẬP HỆ THỐNG", use_container_width=True):
                u_data = users_db.get(log_user)
                if u_data and u_data.get("password") == hash_password(log_pwd):
                    st.session_state['current_user'] = log_user
                    st.session_state['logged_in'] = True
                    st.rerun()
                else: st.error("❌ Tài khoản hoặc mật khẩu không đúng!")
        
        # (Phần logic đăng ký và quên mật khẩu giữ nguyên...)
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 2. DASHBOARD CHÍNH
# ==========================================
else:
    head_col1, head_col2 = st.columns([6, 1])
    with head_col1:
        st.markdown(f"### 👋 Xin chào, **{st.session_state['current_user']}**")
    with head_col2:
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state['logged_in'] = False
            st.rerun()

    st.markdown('<div class="logo-container">', unsafe_allow_html=True)
    try: st.image(LOGO_URL, width=180)
    except: st.info("Dashboard")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="hero-banner">
        <h1>BULKMAIL PRO – GIẢI PHÁP EMAIL MARKETING HÀNG LOẠT</h1>
        <p>Gửi hàng ngàn email cá nhân hóa chuyên nghiệp chỉ với một cú nhấp chuột.</p>
    </div>
    """, unsafe_allow_html=True)

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown('<div class="section-header">1. Cấu hình Máy chủ & Tài khoản</div>', unsafe_allow_html=True)
        s_name = st.text_input("Tên hiển thị người gửi:", value=st.session_state.get('s_name', ""))
        s_mail = st.text_input("Email gửi (Gmail):", value=st.session_state.get('s_email', ""))
        s_pass = st.text_input("App Password (16 ký tự):", type="password", value=st.session_state.get('s_pwd', ""))
        
        st.markdown('<div class="section-header">2. Chữ ký Email</div>', unsafe_allow_html=True)
        s_sign = st.text_area("Thông tin liên hệ cuối thư:", value=st.session_state.get('s_sign', "Trân trọng,\nĐội ngũ hỗ trợ Trường Sơn"), height=100)
        st.session_state['s_name'], st.session_state['s_email'], st.session_state['s_pwd'], st.session_state['s_sign'] = s_name, s_mail, s_pass, s_sign
        
        st.markdown('<div class="section-header">3. Dữ liệu Khách hàng</div>', unsafe_allow_html=True)
        up = st.file_uploader("Tải danh sách (.csv, .xlsx)", type=["csv", "xlsx"])
        df = None
        if up:
            df = pd.read_excel(up) if up.name.endswith('xlsx') else pd.read_csv(up)
            st.success(f"✅ Đã nhận {len(df)} khách hàng.")
        attachments = st.file_uploader("Đính kèm file", accept_multiple_files=True)

    with col_right:
        st.markdown('<div class="section-header">4. Biên soạn Nội dung Email</div>', unsafe_allow_html=True)
        subject = st.text_input("Tiêu đề thư (Subject):")
        raw_body = st.text_area("Nội dung chính:", height=250, 
                                 value="Kính chào Anh/Chị {{name}},\n\nNhập nội dung thư tại đây...")
        
        body_html = raw_body.replace("\n", "<br>")
        sign_html = s_sign.replace("\n", "<br>")
        full_email_content = f"<div style='font-family:Arial; line-height:1.8; color:#333;'>{body_html}<br><br><div style='color:#666; border-top:1px solid #eee; padding-top:10px;'>{sign_html}</div></div>"
        
        with st.expander("👁️ Xem trước thực tế", expanded=True):
            p_text = full_email_content
            example_name = str(df.iloc[0]["name"]) if df is not None and not df.empty else "Nguyễn Văn A"
            st.markdown(p_text.replace("{{name}}", f"<b style='color:#1e3a8a;'>{example_name}</b>"), unsafe_allow_html=True)
        
        st.markdown('<div class="section-header">5. Thiết lập Gửi</div>', unsafe_allow_html=True)
        delay = st.number_input("Khoảng nghỉ (giây):", value=5, min_value=1)

    # --- PHỤC HỒI NÚT LƯU TELEGRAM NHƯ CŨ ---
    st.markdown("---")
    u_data = load_users().get(st.session_state['current_user'], {})
    t_tk = u_data.get("tele_token", ""); t_id = u_data.get("tele_chat_id", "")
    with st.expander("🔔 Nhận báo cáo kết quả qua Telegram"):
        new_tk = st.text_input("Bot Token:", value=t_tk, type="password", key="new_t_tk")
        new_id = st.text_input("Chat ID:", value=t_id, key="new_t_id")
        if st.button("💾 Lưu cấu hình báo cáo"):
            if save_config_api(st.session_state['current_user'], new_tk, new_id):
                st.success("✅ Đã lưu cấu hình báo cáo!")
                time.sleep(1); st.rerun()

    if st.button("▶ BẮT ĐẦU CHIẾN DỊCH", type="primary", use_container_width=True):
        if df is not None and s_mail and s_pass:
            progress_bar = st.progress(0); log_ex = st.expander("📋 Nhật ký chi tiết", expanded=True)
            # Lấy token từ input mới để gửi báo cáo tức thời
            send_tele_msg(new_tk, new_id, f"🚀 <b>BẮT ĐẦU</b>\n👤 User: {st.session_state['current_user']}")
            # (Phần logic gửi thư giữ nguyên...)
            st.success("🎉 Hoàn tất!")
        else: st.error("⚠️ Thiếu cấu hình!")

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
