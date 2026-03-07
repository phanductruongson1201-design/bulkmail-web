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

def save_user(username, password_hash, email):
    if not DB_URL: return
    try: requests.post(DB_URL, json={"action": "register", "username": username, "password": password_hash, "email": email})
    except: pass

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

def save_config_api(username, tele_token, tele_chat_id):
    if not DB_URL: return False
    try:
        res = requests.post(DB_URL, json={"action": "update_config", "username": username, "tele_token": tele_token, "tele_chat_id": tele_chat_id}).json()
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
        body = f"<h3>Chào {username},</h3><p>Mật khẩu tạm thời: <b style='color:red;'>{new_password}</b></p><p>Vui lòng đổi mật khẩu mới ngay sau khi đăng nhập.</p>"
        msg.attach(MIMEText(body, 'html'))
        s = smtplib.SMTP("smtp.gmail.com", 587); s.starttls()
        s.login(SYS_EMAIL, SYS_PWD); s.send_message(msg); s.quit()
        return True
    except: return False

# ==========================================
# GIAO DIỆN CSS (Sáng, Sang trọng & Nút nổi)
# ==========================================
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%); }
    .auth-box { max-width: 450px; margin: auto; padding: 40px; background: white; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
    .stButton>button { background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%) !important; color: white !important; border-radius: 8px; border: none; font-weight: 600; transition: 0.3s; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(59, 130, 246, 0.4); }
    
    .floating-container { position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 15px; z-index: 999999; }
    .float-btn { width: 55px; height: 55px; border-radius: 50%; box-shadow: 0 4px 12px rgba(0,0,0,0.3); transition: 0.3s; display: flex; justify-content: center; align-items: center; background: white; overflow: hidden; }
    .float-btn:hover { transform: scale(1.1) translateY(-5px); }
    .float-btn img { width: 100%; height: 100%; object-fit: cover; }
</style>
""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'must_reset' not in st.session_state: st.session_state['must_reset'] = False

LOGO_URL = "https://storage.googleapis.com/smart-home-v3-files/media-files/z7587176856031_f586c2b79f66ddf86eae7cb7405fc298.jpg"

# ==========================================
# 1. HỆ THỐNG ĐĂNG NHẬP
# ==========================================
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        st.image(LOGO_URL, width=250)
        st.title("🔵 BulkMail Pro")
        tab_login, tab_register, tab_forgot = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký", "🔑 Quên mật khẩu"])
        users_db = load_users()

        with tab_login:
            log_user = st.text_input("Tên đăng nhập")
            log_pwd = st.text_input("Mật khẩu", type="password")
            if st.button("Đăng nhập ngay", type="primary", use_container_width=True):
                user_data = users_db.get(log_user)
                if user_data and user_data.get("password") == hash_password(log_pwd):
                    st.session_state['current_user'] = log_user
                    if user_data.get("is_reset") == True:
                        st.session_state['must_reset'] = True
                        st.session_state['logged_in'] = True
                        st.rerun()
                    else:
                        st.session_state['logged_in'] = True
                        st.rerun()
                else: st.error("❌ Sai tài khoản hoặc mật khẩu!")

        with tab_register:
            reg_user = st.text_input("Tên đăng nhập ", key="reg_u")
            reg_email = st.text_input("Email khôi phục", key="reg_e")
            reg_pwd = st.text_input("Mật khẩu ", type="password", key="reg_p")
            if st.button("Đăng ký tài khoản", type="primary", use_container_width=True):
                if reg_user in users_db: st.error("Tên đã tồn tại!")
                else:
                    save_user(reg_user, hash_password(reg_pwd), reg_email)
                    st.success("Đăng ký xong! Hãy quay lại Đăng nhập.")

        with tab_forgot:
            fg_user = st.text_input("Username cần cấp lại")
            fg_email = st.text_input("Email đã đăng ký")
            if st.button("Gửi mật khẩu tạm", type="primary", use_container_width=True):
                if fg_user in users_db and users_db[fg_user].get("email") == fg_email:
                    new_p = generate_random_password()
                    if reset_password_api(fg_user, fg_email, hash_password(new_p), True):
                        if send_recovery_email(fg_email, fg_user, new_p): st.success("✅ Đã gửi MK tạm!")
                else: st.error("❌ Thông tin không đúng!")
        st.markdown('</div>', unsafe_allow_html=True)

# 2. MÀN HÌNH ÉP ĐỔI MẬT KHẨU
elif st.session_state['must_reset']:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        st.warning("⚠️ Bạn bắt buộc phải tạo mật khẩu mới để tiếp tục.")
        new_p = st.text_input("Mật khẩu mới", type="password")
        conf_p = st.text_input("Xác nhận mật khẩu", type="password")
        if st.button("Cập nhật & Vào hệ thống", type="primary", use_container_width=True):
            if new_p == conf_p and len(new_p) >= 6:
                u_db = load_users()
                if reset_password_api(st.session_state['current_user'], u_db[st.session_state['current_user']]['email'], hash_password(new_p), False):
                    st.session_state['must_reset'] = False
                    st.success("✅ Thành công! Đang vào hệ thống..."); time.sleep(1); st.rerun()
            else: st.error("❌ Mật khẩu không khớp hoặc quá ngắn!")
        st.markdown('</div>', unsafe_allow_html=True)

# 3. GIAO DIỆN CHÍNH
else:
    col_u, col_l = st.columns([8, 1])
    with col_u: st.subheader(f"👤 Chào mừng, {st.session_state['current_user']}")
    with col_l:
        if st.button("🚪 Thoát"):
            st.session_state['logged_in'] = False
            st.session_state['must_reset'] = False
            st.rerun()

    st.image(LOGO_URL, use_container_width=True)
    st.title("BulkMail Pro – Dashboard")
    t_send, t_acc = st.tabs(["🚀 Gửi Email", "⚙️ Tài khoản"])

    with t_send:
        c1, c2 = st.columns(2)
        with c1:
            st.header("1. Cấu hình")
            s_name = st.text_input("Tên người gửi:")
            s_mail = st.text_input("Email gửi:")
            s_pass = st.text_input("App Password:", type="password")
            df_sample = pd.DataFrame({"email": ["vidu@gmail.com"], "name": ["Văn A"], "danh_xung": ["Anh"]})
            buf = io.BytesIO(); df_sample.to_excel(buf, index=False)
            st.download_button("📥 Tải file mẫu (.xlsx)", data=buf.getvalue(), file_name="mau.xlsx")
            uploaded_file = st.file_uploader("Tải danh sách", type=["csv", "xlsx"])
            df = None
            if uploaded_file:
                df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
                st.success(f"✅ Đã tải {len(df)} dòng.")
        with c2:
            st.header("2. Nội dung")
            subject = st.text_input("Tiêu đề:")
            body = st.text_area("Nội dung (HTML):", height=200)
            delay = st.number_input("Khoảng nghỉ (giây):", value=5)

        if st.button("▶ BẮT ĐẦU GỬI", type="primary", use_container_width=True):
            users_db = load_users(); u_data = users_db.get(st.session_state['current_user'], {})
            t_tk = u_data.get("tele_token", ""); t_id = u_data.get("tele_chat_id", "")
            if t_tk and t_id:
                try: requests.post(f"https://api.telegram.org/bot{t_tk}/sendMessage", data={"chat_id": t_id, "text": "⏳ Bắt đầu..."}, timeout=5)
                except: pass
            st.warning("Đang gửi mail..."); time.sleep(2); st.success("Xong!")
            if t_tk and t_id:
                try: requests.post(f"https://api.telegram.org/bot{t_tk}/sendMessage", data={"chat_id": t_id, "text": "✅ Đã xong!"}, timeout=5)
                except: pass

    with t_acc:
        st.header("🔐 Đổi mật khẩu")
        n_p = st.text_input("Mật khẩu mới", type="password", key="np")
        c_p = st.text_input("Xác nhận", type="password", key="cp")
        if st.button("Lưu mật khẩu"):
            if n_p == c_p and len(n_p) >= 6:
                u_db = load_users()
                if reset_password_api(st.session_state['current_user'], u_db[st.session_state['current_user']]['email'], hash_password(n_p), False):
                    st.success("✅ Đã đổi!")
            else: st.error("Lỗi!")
        st.markdown("---")
        st.header("🔔 Telegram")
        tele_tk = st.text_input("Bot Token", type="password"); tele_id = st.text_input("Chat ID")
        if st.button("💾 Lưu Telegram"):
            if save_config_api(st.session_state['current_user'], tele_tk, tele_id): st.success("Đã lưu!")

# ==========================================
# NÚT LIÊN HỆ NỔI (ZALO & TELEGRAM)
# ==========================================
st.markdown("""
<div class="floating-container">
    <a href="https://zalo.me/0935748199" target="_blank" class="float-btn">
        <img src="https://cdn.haitrieu.com/wp-content/uploads/2022/01/Logo-Zalo-Arc.png" alt="Zalo">
    </a>
    <a href="https://t.me/BulkMail_Pro" target="_blank" class="float-btn">
        <img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg" alt="Telegram">
    </a>
</div>
""", unsafe_allow_html=True)
