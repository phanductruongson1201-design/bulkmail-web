import streamlit as st
import pandas as pd
import io
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage # Thêm để xử lý ảnh
from email import encoders
import time
import requests
import hashlib
import string
import random
import base64
import os
import re # Thêm để tìm mã ảnh
from bs4 import BeautifulSoup # Thêm để xử lý HTML ảnh
from streamlit_quill import st_quill # Thêm ô soạn thảo dán ảnh

# 1. Cấu hình trang Web (Giao diện rộng)
st.set_page_config(page_title="BulkMail Pro - Trường Sơn", page_icon="🚀", layout="wide")

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
    return "".join(random.choices(string.digits, k=length))

def send_otp_email(to_email, username, otp_code):
    if not SYS_EMAIL or not SYS_PWD: return False
    try:
        msg = MIMEMultipart()
        msg["From"] = f"Hệ thống xác thực <{SYS_EMAIL}>"
        msg["To"] = to_email
        msg["Subject"] = f"{otp_code} là mã xác thực của bạn"
        body = f"<h3>Chào {username},</h3><p>Mã OTP để khôi phục mật khẩu của bạn là: <b style='font-size: 20px;'>{otp_code}</b></p>"
        msg.attach(MIMEText(body, "html"))
        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.starttls()
        s.login(SYS_EMAIL, SYS_PWD)
        s.send_message(msg)
        s.quit()
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
            files = {"document": (file_name, file_content)}
            requests.post(url, data={"chat_id": chat_id}, files=files, timeout=10)
        except: pass

def get_image_base64(path):
    try:
        with open(path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    except:
        return None

# ==========================================
# GIAO DIỆN CSS
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap');
    
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif !important; }
    
    #MainMenu, footer, header, .stDeployButton, [data-testid="manage-app-button"], [data-testid="viewerBadge"], iframe[title="Streamlit Toolbar"], iframe[src*="badge"] {display: none !important; visibility: hidden !important;}

    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
    }

    .stApp { background-color: #f8fafc; }
    
    .gradient-text {
        background: linear-gradient(90deg, #2563eb 0%, #7c3aed 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 900;
        font-size: 46px;
        margin-bottom: 5px;
        letter-spacing: -1px;
    }

    div[data-baseweb="tab-list"] {
        background-color: #f1f5f9 !important;
        border-radius: 12px !important;
        padding: 4px !important;
        gap: 4px !important;
        border-bottom: none !important;
        margin-bottom: 20px !important;
    }
    div[data-baseweb="tab"] {
        background-color: transparent !important;
        border-radius: 8px !important;
        border: none !important;
        color: #64748b !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 8px 12px !important;
        margin: 0 !important;
        height: auto !important;
    }
    div[data-baseweb="tab"][aria-selected="true"] {
        background-color: #ffffff !important;
        color: #1e40af !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08) !important;
    }
    div[data-baseweb="tab"][aria-selected="true"] p {
        color: #1e40af !important;
        font-weight: 800 !important;
    }
    div[data-baseweb="tab-highlight"] {
        display: none !important;
    }
       
    div[data-testid="stExpander"] {
        background-color: #eff6ff !important;
        border: 2px solid #bfdbfe !important;
        border-radius: 16px;
        box-shadow: 0 4px 10px rgba(59, 130, 246, 0.08);
    }
    div[data-testid="stExpander"] summary {
        background-color: transparent !important; 
    }

    div[data-testid="stFileUploader"] {
        background-color: #faf5ff !important;
        border: 2px solid #e9d5ff !important;
        border-radius: 16px;
        box-shadow: 0 4px 10px rgba(168, 85, 247, 0.08);
        padding: 20px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stFileUploader"]:hover { transform: translateY(-2px); box-shadow: 0 8px 15px rgba(168, 85, 247, 0.15); }

    .stButton>button[kind="primary"] { 
        background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%) !important; 
        color: white !important; 
        border-radius: 16px; 
        font-weight: 900; 
        font-size: 18px !important;
        padding: 15px 24px; 
        border: none !important; 
        box-shadow: 0 6px 20px rgba(59, 130, 246, 0.35) !important;
        transition: all 0.3s ease; 
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .stButton>button[kind="primary"]:hover { 
        transform: translateY(-4px); 
        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.5) !important; 
    }
    
    .auth-box .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
        box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4) !important;
        font-size: 16px !important;
        padding: 10px 20px;
    }
    
    .stButton>button[kind="secondary"], div[data-testid="stDownloadButton"]>button {
        border-radius: 12px; 
        border: 2px solid #cbd5e1 !important; 
        color: #475569 !important; 
        font-weight: 700;
        background-color: white !important;
        transition: all 0.3s ease;
    }

    .pill-header {
        color: white;
        padding: 10px 24px;
        border-radius: 50px; 
        font-size: 15px;
        font-weight: 800;
        margin-bottom: 20px;
        margin-top: 15px;
        text-transform: uppercase;
        letter-spacing: 1px;
        display: inline-block; 
        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    .bg-blue { background: linear-gradient(135deg, #3b82f6, #1d4ed8); box-shadow: 0 6px 15px rgba(59, 130, 246, 0.4); border: 2px solid #93c5fd; }
    .bg-purple { background: linear-gradient(135deg, #a855f7, #6d28d9); box-shadow: 0 6px 15px rgba(168, 85, 247, 0.4); border: 2px solid #d8b4fe; }
    .bg-green { background: linear-gradient(135deg, #10b981, #047857); box-shadow: 0 6px 15px rgba(16, 185, 129, 0.4); border: 2px solid #6ee7b7; }

    .auth-box { 
        max-width: 440px; margin: 10px auto; padding: 35px; 
        background: rgba(255, 255, 255, 0.95); 
        border-radius: 24px; 
        box-shadow: 0 20px 40px -15px rgba(0,0,0,0.1); 
        border: 1px solid rgba(255,255,255,0.5);
        backdrop-filter: blur(10px);
    }
    
    .logo-container { display: flex; justify-content: center; align-items: center; width: 100%; margin-bottom: 20px; }
    .logo-container img { width: 120px; height: 120px; border-radius: 35%; object-fit: cover; border: 4px solid white; box-shadow: 0 10px 25px rgba(59, 130, 246, 0.2); }

    .floating-container { position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 15px; z-index: 999999; }
    .float-btn { width: 55px; height: 55px; border-radius: 50%; box-shadow: 0 10px 25px rgba(0,0,0,0.15); display: flex; justify-content: center; align-items: center; background: white; transition: 0.3s; border: 2px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)

if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "otp_verified" not in st.session_state: st.session_state["otp_verified"] = False
if "otp_sent" not in st.session_state: st.session_state["otp_sent"] = False

if "s_name" not in st.session_state: st.session_state["s_name"] = "Trường Sơn Marketing"
if "s_email" not in st.session_state: st.session_state["s_email"] = ""
if "s_pwd" not in st.session_state: st.session_state["s_pwd"] = ""
if "s_sign" not in st.session_state: st.session_state["s_sign"] = "Trân trọng,<br>Trường Sơn Marketing"

LOGO_URL = "logo_moi.png"

# ==========================================
# 1. HỆ THỐNG ĐĂNG NHẬP
# ==========================================
if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        logo_b64 = get_image_base64(LOGO_URL)
        if logo_b64: st.markdown(f'<div class="logo-container"><img src="data:image/png;base64,{logo_b64}"></div>', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align:center; color:#0f172a; font-weight:900; margin-bottom:5px; font-size:28px;">BULKMAIL PRO</h2>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; color:#64748b; margin-bottom:20px; font-size:14px;">Đăng nhập để bắt đầu chiến dịch</p>', unsafe_allow_html=True)
        tab_login, tab_reg, tab_forgot = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký", "🔑 Quên MK"])
        users_db = load_users()

        with tab_login:
            log_user = st.text_input("Tên đăng nhập", key="login_u")
            log_pwd = st.text_input("Mật khẩu", type="password", key="login_p")
            if st.button("ĐĂNG NHẬP HỆ THỐNG", type="primary", use_container_width=True):
                u_data = users_db.get(log_user)
                if u_data and u_data.get("password") == hash_password(log_pwd):
                    st.session_state["current_user"] = log_user
                    st.session_state["logged_in"] = True; st.rerun()
                else: st.error("❌ Thông tin đăng nhập chưa chính xác!")
        # (Giữ nguyên tab Đăng ký và Quên mật khẩu từ code của bạn...)
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 2. DASHBOARD CHÍNH
# ==========================================
else:
    head_col1, head_col2 = st.columns([5, 1])
    with head_col1:
        st.markdown('<div class="gradient-text">BulkMail</div>', unsafe_allow_html=True)
    with head_col2:
        if st.button("🚪 Đăng xuất", use_container_width=True): st.session_state["logged_in"] = False; st.rerun()

    st.markdown('<div class="pill-header bg-blue">⚙️ BƯỚC 1: CẤU HÌNH MÁY CHỦ & BÁO CÁO</div>', unsafe_allow_html=True)
    with st.expander("Bấm để mở rộng Cài đặt Máy chủ", expanded=True):
        cfg_col1, cfg_col2 = st.columns(2, gap="large")
        with cfg_col1:
            st.markdown("<b style='color:#1e40af;'>📧 Thông tin Gửi thư (Gmail)</b>", unsafe_allow_html=True)
            st.session_state["s_name"] = st.text_input("Tên người gửi:", value=st.session_state["s_name"])
            st.session_state["s_email"] = st.text_input("Địa chỉ Gmail:", value=st.session_state["s_email"])
            st.session_state["s_pwd"] = st.text_input("Mật khẩu ứng dụng (16 ký tự):", type="password", value=st.session_state["s_pwd"])
        with cfg_col2:
            st.markdown("<b style='color:#1e40af;'>🔔 Báo cáo Telegram & Chữ ký</b>", unsafe_allow_html=True)
            u_data = load_users().get(st.session_state["current_user"], {})
            tele_tk = st.text_input("Bot Token:", value=u_data.get("tele_token", ""), type="password")
            tele_id = st.text_input("Chat ID:", value=u_data.get("tele_chat_id", ""))
            st.session_state["s_sign"] = st.text_area("Chữ ký mặc định cuối thư:", value=st.session_state["s_sign"])

    st.markdown("<hr>", unsafe_allow_html=True)

    col_data, col_content = st.columns([1, 1.2], gap="large")
    with col_data:
        st.markdown('<div class="pill-header bg-purple">📁 BƯỚC 2: DỮ LIỆU KHÁCH HÀNG</div>', unsafe_allow_html=True)
        up = st.file_uploader("Tải Excel/CSV", type=["csv", "xlsx"])
        df = pd.read_excel(up) if up and up.name.endswith("xlsx") else (pd.read_csv(up) if up else None)
        if df is not None: st.success(f"✅ Đã nhận {len(df)} địa chỉ email.")
        st.markdown('<div class="pill-header bg-purple" style="font-size: 13px;">📎 TỆP ĐÍNH KÈM (TÙY CHỌN)</div>', unsafe_allow_html=True)
        attachments = st.file_uploader("Kéo thả tài liệu vào đây", accept_multiple_files=True)

    with col_content:
        st.markdown('<div class="pill-header bg-green">✍️ BƯỚC 3: SOẠN THÔNG ĐIỆP</div>', unsafe_allow_html=True)
        subject = st.text_input("Tiêu đề Email:")
        
        # SỬA: Thay text_area bằng Quill Editor để DÁN ẢNH ĐƯỢC
        raw_body = st_quill(placeholder="Bôi đen chữ và ảnh bên web khác rồi Paste vào đây...", html=True, key="quill_editor")
        delay = st.number_input("⏳ Khoảng nghỉ (Giây):", value=15, min_value=5)

    if st.button("🚀 BẮT ĐẦU CHIẾN DỊCH GỬI MAIL", type="primary", use_container_width=True):
        if df is None or not subject or not st.session_state["s_email"]: st.error("⚠️ Thiếu thông tin gửi!")
        else:
            progress = st.progress(0); log = st.expander("📋 Trình giám sát hệ thống", expanded=True); success, fail = 0, 0
            
            for index, row in df.iterrows():
                try:
                    target_email = str(row.get("email", row.iloc[0])).strip()
                    target_name = str(row.get("name", "Quý khách"))
                    
                    # SỬA: Xử lý nhúng ảnh CID để người nhận thấy được ảnh
                    msg = MIMEMultipart("related")
                    msg["From"] = f"{st.session_state['s_name']} <{st.session_state['s_email']}>"
                    msg["To"] = target_email; msg["Subject"] = subject
                    
                    soup = BeautifulSoup(raw_body.replace("{{name}}", target_name), "html.parser")
                    img_counter = 0
                    for img in soup.find_all("img"):
                        src = img.get("src", "")
                        if src.startswith("data:image"):
                            img_counter += 1; cid = f"img_{img_counter}"
                            header, encoded = src.split(",", 1); img_data = base64.b64decode(encoded)
                            img_type = re.search(r"image/(.*?);", header).group(1)
                            img_part = MIMEImage(img_data, _subtype=img_type)
                            img_part.add_header("Content-ID", f"<{cid}>")
                            msg.attach(img_part); img["src"] = f"cid:{cid}"
                    
                    final_html = f"<html><body>{str(soup)}<br><br>{st.session_state['s_sign']}</body></html>"
                    msg.attach(MIMEText(final_html, "html"))
                    
                    if attachments:
                        for f in attachments:
                            part = MIMEBase("application", "octet-stream"); part.set_payload(f.read())
                            encoders.encode_base64(part); part.add_header("Content-Disposition", f"attachment; filename={f.name}"); msg.attach(part); f.seek(0)

                    with smtplib.SMTP("smtp.gmail.com", 587) as server:
                        server.starttls(); server.login(st.session_state["s_email"], st.session_state["s_pwd"]); server.send_message(msg)
                    success += 1; log.write(f"✅ Đã gửi: {target_email}")
                except Exception as e: fail += 1; log.write(f"❌ Lỗi {target_email}: {e}")
                progress.progress((index + 1) / len(df)); time.sleep(delay)
            st.success(f"🎉 Hoàn tất! Thành công: {success}, Lỗi: {fail}")

# CHÂN TRANG VÀ NÚT LIÊN HỆ (GIỮ NGUYÊN)
st.markdown("""<div class="floating-container"><a href="https://zalo.me/0935748199" target="_blank" class="float-btn"><img src="https://upload.wikimedia.org/wikipedia/commons/9/91/Icon_of_Zalo.svg"></a><a href="https://t.me/BulkMail_Pro" target="_blank" class="float-btn"><img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg"></a></div>""", unsafe_allow_html=True)
