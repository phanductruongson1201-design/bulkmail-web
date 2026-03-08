import streamlit as st
import pandas as pd
import io
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import time
import requests
import hashlib
import string
import random
import base64
import os

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

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def save_user_api(username, password_hash, email):
    if not DB_URL: return
    try: requests.post(DB_URL, json={"action": "register", "username": username, "password": password_hash, "email": email})
    except: pass

def get_image_base64(path):
    try:
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')
    except:
        return None

# ==========================================
# GIAO DIỆN CSS
# ==========================================
st.markdown("""
<style>
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header {visibility: hidden !important;}
    .stDeployButton {display: none !important;}
    [data-testid="manage-app-button"] {display: none !important;}
    [data-testid="viewerBadge"] {display: none !important;}

    .stApp { background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%); }
    .auth-box { max-width: 480px; margin: auto; padding: 30px; background: white; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
    .stButton>button { background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%) !important; color: white !important; border-radius: 8px; font-weight: 600; }
    
    .logo-container { display: flex; justify-content: center; align-items: center; width: 100%; margin-bottom: 25px; }
    .logo-container img { width: 160px; height: 160px; border-radius: 50%; object-fit: cover; border: 4px solid #1e3a8a; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }

    .hero-banner { background: linear-gradient(rgba(30, 58, 138, 0.85), rgba(30, 58, 138, 0.85)), url('https://images.unsplash.com/photo-1557683316-973673baf926?auto=format&fit=crop&w=1350&q=80'); background-size: cover; padding: 40px; border-radius: 15px; color: white; text-align: center; margin-bottom: 25px; }
    .hero-banner h1 { font-size: 32px !important; font-weight: 800 !important; color: white !important; }

    .section-header { color: #1e3a8a; border-bottom: 2px solid #1e3a8a; padding-bottom: 5px; margin-top: 20px; font-size: 20px; font-weight: 700; }
    .help-box { background-color: #f0f7ff; padding: 15px; border-left: 4px solid #3b82f6; border-radius: 5px; font-size: 14px; color: #333; margin-top: 5px; }
</style>
""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

# ==========================================
# 1. ĐĂNG NHẬP
# ==========================================
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; color:#1e3a8a; font-weight:800; font-size:28px;">BULKMAIL PRO</p>', unsafe_allow_html=True)
        logo_b64 = get_image_base64("logo_moi.png")
        if logo_b64:
            st.markdown(f'<div class="logo-container"><img src="data:image/png;base64,{logo_b64}"></div>', unsafe_allow_html=True)
        
        tab_login, tab_reg = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký"])
        users_db = load_users()
        with tab_login:
            log_user = st.text_input("Username", key="login_u")
            log_pwd = st.text_input("Mật khẩu", type="password", key="login_p")
            if st.button("ĐĂNG NHẬP", use_container_width=True):
                u_data = users_db.get(log_user)
                if u_data and u_data.get("password") == hash_password(log_pwd):
                    st.session_state['current_user'] = log_user
                    st.session_state['logged_in'] = True
                    st.rerun()
                else: st.error("❌ Sai tài khoản/mật khẩu!")
        with tab_reg:
            reg_user = st.text_input("Username mới")
            reg_email = st.text_input("Email khôi phục")
            reg_pwd = st.text_input("Mật khẩu mới", type="password")
            if st.button("TẠO TÀI KHOẢN", use_container_width=True):
                save_user_api(reg_user, hash_password(reg_pwd), reg_email)
                st.success("✅ Thành công!")
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 2. DASHBOARD
# ==========================================
else:
    head_col1, head_col2 = st.columns([6, 1])
    head_col1.markdown(f"### 👋 Xin chào, **{st.session_state['current_user']}**")
    if head_col2.button("🚪 Thoát", use_container_width=True):
        st.session_state['logged_in'] = False; st.rerun()

    st.markdown('<div class="hero-banner"><h1>BULKMAIL PRO</h1><p>Giải pháp Email Marketing chuyên nghiệp</p></div>', unsafe_allow_html=True)

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown('<div class="section-header">1. Cấu hình Tài khoản</div>', unsafe_allow_html=True)
        s_name = st.text_input("Tên hiển thị:", value="Trường Sơn Marketing")
        s_mail = st.text_input("Email gửi (Gmail):")
        raw_pass = st.text_input("App Password (16 ký tự):", type="password")
        s_pass = raw_pass.replace(" ", "").strip()
        
        # --- KHÔI PHỤC PHẦN GỢI Ý LẤY APP PASS ---
        with st.expander("❓ Hướng dẫn lấy App Password nhanh"):
            st.markdown("""
            <div class="help-box">
                <b>Cần dùng Mật khẩu ứng dụng thay vì mật khẩu Gmail thường:</b><br>
                1. Truy cập <a href="https://myaccount.google.com/security" target="_blank">Bảo mật Google</a>.<br>
                2. Bật <b>Xác minh 2 bước</b>.<br>
                3. Tìm mục <b>Mật khẩu ứng dụng</b>, tạo một mã mới tên 'BulkMail' và copy 16 ký tự dán vào ô trên.
            </div>
            """, unsafe_allow_html=True)

        st.markdown('<div class="section-header">2. Danh sách khách hàng</div>', unsafe_allow_html=True)
        up = st.file_uploader("Tải file .xlsx hoặc .csv", type=["csv", "xlsx"])
        df = None
        if up:
            df = pd.read_excel(up) if up.name.endswith('xlsx') else pd.read_csv(up)
            st.success(f"✅ Đã nhận {len(df)} khách hàng")

    with col_right:
        st.markdown('<div class="section-header">3. Nội dung Email</div>', unsafe_allow_html=True)
        subject = st.text_input("Tiêu đề thư:")
        content = st.text_area("Nội dung (dùng {{name}}):", height=200, value="Chào {{name}},")
        
        with st.expander("👁️ Xem trước"):
            n_col = next((c for c in df.columns if c.lower() in ['name', 'tên']), None) if df is not None else None
            ex_name = str(df.iloc[0][n_col]) if n_col else "Quý khách"
            st.markdown(f"<div style='padding:10px; border:1px solid #ddd;'>{content.replace('{{name}}', ex_name)}</div>", unsafe_allow_html=True)

    st.markdown("---")
    
    # --- CẢNH BÁO AN TOÀN ---
    st.warning("⚠️ **CẢNH BÁO:** Mỗi tài khoản Gmail chỉ nên gửi an toàn **200 - 300 mail/ngày** để tránh bị đánh dấu Spam.")

    if st.button("▶ BẮT ĐẦU GỬI", type="primary", use_container_width=True):
        if df is not None and s_mail and s_pass:
            e_col = next((c for c in df.columns if c.lower() in ['email', 'mail']), None)
            if not e_col: st.error("❌ File thiếu cột Email!")
            else:
                progress = st.progress(0); log = st.expander("📋 Nhật ký", expanded=True)
                for index, row in df.iterrows():
                    target_email = str(row.get(e_col, "")).strip()
                    n_col = next((c for c in df.columns if c.lower() in ['name', 'tên']), None)
                    target_name = str(row.get(n_col, "Quý khách")) if n_col else "Quý khách"
                    
                    try:
                        msg = MIMEMultipart()
                        msg['From'] = f"{s_name} <{s_mail}>"; msg['To'] = target_email; msg['Subject'] = subject
                        msg.attach(MIMEText(content.replace("{{name}}", target_name), 'html'))
                        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as server:
                            server.login(s_mail, s_pass); server.send_message(msg)
                        log.write(f"✅ Đã gửi: {target_email}")
                    except Exception as e: log.write(f"❌ Lỗi {target_email}: {e}")
                    progress.progress((index + 1) / len(df)); time.sleep(2)
                st.success("🎉 Hoàn tất!")
        else: st.error("⚠️ Điền đủ thông tin!")
