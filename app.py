import streamlit as st
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
from bs4 import BeautifulSoup
from streamlit_quill import st_quill

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

def hash_password(password): return hashlib.sha256(password.encode()).hexdigest()
def generate_otp(length=6): return "".join(random.choices(string.digits, k=length))

def send_otp_email(to_email, username, otp_code):
    if not SYS_EMAIL or not SYS_PWD: return False
    try:
        msg = MIMEMultipart()
        msg["From"] = f"Hệ thống xác thực <{SYS_EMAIL}>"
        msg["To"] = to_email
        msg["Subject"] = f"{otp_code} là mã xác thực của bạn"
        body = f"<h3>Chào {username},</h3><p>Mã OTP là: <b>{otp_code}</b></p>"
        msg.attach(MIMEText(body, "html"))
        s = smtplib.SMTP("smtp.gmail.com", 587); s.starttls(); s.login(SYS_EMAIL, SYS_PWD); s.send_message(msg); s.quit()
        return True
    except: return False

def send_tele_msg(token, chat_id, message):
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, data={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=5)
        except: pass

def get_image_base64(path):
    try:
        with open(path, "rb") as img_file: return base64.b64encode(img_file.read()).decode("utf-8")
    except: return None

# ==========================================
# GIAO DIỆN CSS CHUYÊN NGHIỆP
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif !important; }
    #MainMenu, footer, header, .stDeployButton, [data-testid="manage-app-button"] {display: none !important;}
    .block-container { padding-top: 1.5rem !important; }
    .stApp { background-color: #f8fafc; }
    .gradient-text { background: linear-gradient(90deg, #2563eb 0%, #7c3aed 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; font-size: 46px; margin-bottom: 5px; letter-spacing: -1px; }
    div[data-baseweb="tab-list"] { background-color: #f1f5f9 !important; border-radius: 12px !important; padding: 4px !important; gap: 4px !important; border-bottom: none !important; }
    div[data-baseweb="tab"] { background-color: transparent !important; border-radius: 8px !important; color: #64748b !important; font-weight: 600 !important; }
    div[data-baseweb="tab"][aria-selected="true"] { background-color: #ffffff !important; color: #1e40af !important; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08) !important; }
    div[data-testid="stExpander"] { background-color: #eff6ff !important; border: 2px solid #bfdbfe !important; border-radius: 16px; }
    div[data-testid="stFileUploader"] { background-color: #faf5ff !important; border: 2px solid #e9d5ff !important; border-radius: 16px; padding: 20px; }
    .stButton>button[kind="primary"] { background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%) !important; color: white !important; border-radius: 16px; font-weight: 900; font-size: 18px !important; padding: 15px 24px; border: none !important; box-shadow: 0 6px 20px rgba(59, 130, 246, 0.35) !important; }
    .pill-header { color: white; padding: 10px 24px; border-radius: 50px; font-size: 15px; font-weight: 800; margin-bottom: 20px; text-transform: uppercase; display: inline-block; text-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .bg-blue { background: linear-gradient(135deg, #3b82f6, #1d4ed8); }
    .bg-purple { background: linear-gradient(135deg, #a855f7, #6d28d9); }
    .bg-green { background: linear-gradient(135deg, #10b981, #047857); }
    .auth-box { max-width: 440px; margin: 0 auto 20px auto; padding: 35px; background: white; border-radius: 24px; box-shadow: 0 20px 40px -15px rgba(0,0,0,0.1); }
    .logo-container img { width: 120px; height: 120px; border-radius: 35%; object-fit: cover; border: 4px solid white; box-shadow: 0 10px 25px rgba(59, 130, 246, 0.2); }
    .floating-container { position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 15px; z-index: 9999; }
    .float-btn { width: 55px; height: 55px; border-radius: 50%; box-shadow: 0 10px 25px rgba(0,0,0,0.15); display: flex; justify-content: center; align-items: center; background: white; border: 2px solid #e2e8f0; }
</style>
""", unsafe_allow_html=True)

# Khởi tạo trạng thái
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "otp_verified" not in st.session_state: st.session_state["otp_verified"] = False
if "otp_sent" not in st.session_state: st.session_state["otp_sent"] = False

if "s_name" not in st.session_state: st.session_state["s_name"] = "Trường Sơn Marketing"
if "s_email" not in st.session_state: st.session_state["s_email"] = ""
if "s_pwd" not in st.session_state: st.session_state["s_pwd"] = ""
if "s_sign" not in st.session_state: st.session_state["s_sign"] = "Trân trọng,\nTrường Sơn Marketing"

# ==========================================
# 1. HỆ THỐNG ĐĂNG NHẬP
# ==========================================
if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div style="text-align: center; margin-top: -10px; margin-bottom: 10px;"><h1 class="gradient-text" style="font-size: 50px;">Bulkmail Pro</h1></div>', unsafe_allow_html=True)
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        logo_b64 = get_image_base64("logo_moi.png")
        if logo_b64: st.markdown(f'<div style="display:flex;justify-content:center;margin-bottom:20px;"><div class="logo-container"><img src="data:image/png;base64,{logo_b64}"></div></div>', unsafe_allow_html=True)
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
                    st.session_state["logged_in"] = True
                    st.rerun()
                else: st.error("❌ Thông tin không chính xác!")

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
                    st.success("✅ Đăng ký thành công!")

        with tab_forgot:
            if not st.session_state["otp_verified"]:
                fg_user = st.text_input("Username", key="fg_u")
                fg_email = st.text_input("Email", key="fg_e")
                if st.button("GỬI OTP", use_container_width=True):
                    if fg_user in users_db and users_db[fg_user].get("email") == fg_email:
                        otp = generate_otp()
                        if reset_password_api(fg_user, fg_email, hash_password(otp), True):
                            if send_otp_email(fg_email, fg_user, otp):
                                st.session_state["otp_sent"] = True
                                st.success("✅ OTP đã gửi!")
                if st.session_state["otp_sent"]:
                    input_otp = st.text_input("Mã OTP:", key="otp_i")
                    if st.button("XÁC THỰC", type="primary", use_container_width=True):
                        u_info = load_users().get(fg_user)
                        if u_info and u_info.get("password") == hash_password(input_otp):
                            st.session_state["otp_verified"] = True
                            st.session_state["target_user"] = fg_user
                            st.rerun()
            else:
                new_p = st.text_input("Mật khẩu mới", type="password", key="new_p")
                if st.button("ĐỔI MẬT KHẨU", type="primary", use_container_width=True):
                    u_db = load_users(); target = st.session_state["target_user"]
                    if reset_password_api(target, u_db[target]["email"], hash_password(new_p), False):
                        st.session_state["otp_verified"] = False; st.session_state["otp_sent"] = False
                        st.success("✅ Thành công!")
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 2. DASHBOARD CHÍNH
# ==========================================
else:
    head_col1, head_col2 = st.columns([5, 1])
    with head_col1: st.markdown('<div class="gradient-text">BulkMail</div>', unsafe_allow_html=True)
    with head_col2:
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state["logged_in"] = False; st.rerun()

    st.markdown('<div class="pill-header bg-blue">⚙️ BƯỚC 1: CẤU HÌNH MÁY CHỦ</div>', unsafe_allow_html=True)
    with st.expander("Cài đặt Gmail & Telegram", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            st.session_state["s_name"] = st.text_input("Tên người gửi:", value=st.session_state["s_name"])
            st.session_state["s_email"] = st.text_input("Gmail gửi:", value=st.session_state["s_email"])
            st.session_state["s_pwd"] = st.text_input("Mật khẩu ứng dụng (16 ký tự):", type="password", value=st.session_state["s_pwd"])
        with c2:
            u_data = load_users().get(st.session_state["current_user"], {})
            tele_tk = st.text_input("Bot Token:", value=u_data.get("tele_token", ""), type="password")
            tele_id = st.text_input("Chat ID:", value=u_data.get("tele_chat_id", ""))
            st.session_state["s_sign"] = st.text_area("Chữ ký cuối thư:", value=st.session_state["s_sign"])
            if st.button("💾 Lưu cấu hình Telegram"):
                if save_config_api(st.session_state["current_user"], tele_tk, tele_id): st.success("✅ Đã lưu!")

    st.markdown("<hr>", unsafe_allow_html=True)

    col_data, col_content = st.columns([1, 1.2], gap="large")
    with col_data:
        st.markdown('<div class="pill-header bg-purple">📁 BƯỚC 2: KHÁCH HÀNG</div>', unsafe_allow_html=True)
        up = st.file_uploader("Tải Excel/CSV", type=["csv", "xlsx"])
        df = pd.read_excel(up) if up and up.name.endswith("xlsx") else (pd.read_csv(up) if up else None)
        if df is not None: st.success(f"Đã nhận {len(df)} khách hàng")
        st.markdown('<div class="pill-header bg-purple" style="font-size:12px;">📎 TỆP ĐÍNH KÈM THÊM</div>', unsafe_allow_html=True)
        files = st.file_uploader("Kéo thả file", accept_multiple_files=True)

    with col_content:
        st.markdown('<div class="pill-header bg-green">✍️ BƯỚC 3: SOẠN THƯ</div>', unsafe_allow_html=True)
        subject = st.text_input("Tiêu đề email:")
        # NÂNG CẤP Ô SOẠN THẢO COPY ẢNH
        raw_body = st_quill(placeholder="Dán nội dung và ảnh vào đây...", html=True, key="editor")
        delay = st.number_input("⏳ Nghỉ giữa các mail (giây):", value=15, min_value=5)

    if st.button("🚀 BẮT ĐẦU GỬI MAIL", type="primary", use_container_width=True):
        if df is None or not subject or not st.session_state["s_email"]: st.error("Thiếu thông tin gửi!")
        else:
            progress = st.progress(0); log = st.expander("📋 Nhật ký", expanded=True); success, fail = 0, 0
            u_run = load_users().get(st.session_state["current_user"], {})
            send_tele_msg(u_run.get("tele_token"), u_run.get("tele_chat_id"), "🚀 Bắt đầu chiến dịch")
            
            for idx, row in df.iterrows():
                try:
                    target_email = str(row.get("email", row.iloc[0])).strip()
                    target_name = str(row.get("name", "Quý khách"))
                    msg = MIMEMultipart("related")
                    msg["From"] = f"{st.session_state['s_name']} <{st.session_state['s_email']}>"
                    msg["To"] = target_email; msg["Subject"] = subject
                    
                    # XỬ LÝ ẢNH DÁN VÀO (FIX LỖI HIỂN THỊ GMAIL)
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
                    
                    final_html = f"<html><body>{str(soup)}<br><br>{st.session_state['s_sign'].replace('\\n', '<br>')}</body></html>"
                    msg.attach(MIMEText(final_html, "html"))
                    
                    if files:
                        for f in files:
                            part = MIMEBase("application", "octet-stream"); part.set_payload(f.read())
                            encoders.encode_base64(part); part.add_header("Content-Disposition", f"attachment; filename={f.name}")
                            msg.attach(part); f.seek(0)

                    with smtplib.SMTP("smtp.gmail.com", 587) as server:
                        server.starttls(); server.login(st.session_state["s_email"], st.session_state["s_pwd"])
                        server.send_message(msg)
                    success += 1; log.write(f"✅ {target_email}: OK")
                except Exception as e: fail += 1; log.write(f"❌ {target_email}: {e}")
                progress.progress((idx + 1) / len(df)); time.sleep(delay)
            
            st.success(f"Hoàn tất! Thành công: {success}, Lỗi: {fail}")

# CHÂN TRANG & NÚT NỔI
st.markdown("""<div style="background-color: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-top:30px;">
<h4 style="margin-top:0; color:#0f172a; font-size:16px;">🛡️ Cẩm nang An toàn Tài khoản</h4>
<table style="width:100%; border-collapse: collapse; font-size: 14px; text-align: left;">
<tr style="border-bottom: 1px solid #e2e8f0; color:#64748b;"><th style="padding: 10px 0;">Loại tài khoản</th><th style="padding: 10px 0;">Số lượng an toàn / Ngày</th></tr>
<tr style="border-bottom: 1px solid #f1f5f9;"><td style="padding: 12px 0; font-weight: 600;">Gmail mới tạo</td><td style="padding: 12px 0; color: #f59e0b; font-weight: 700;">20 - 50 mail</td></tr>
<tr style="border-bottom: 1px solid #f1f5f9;"><td style="padding: 12px 0; font-weight: 600;">Gmail dùng lâu</td><td style="padding: 12px 0; color: #10b981; font-weight: 700;">200 - 300 mail</td></tr>
<tr><td style="padding: 12px 0; font-weight: 600;">Google Workspace</td><td style="padding: 12px 0; color: #3b82f6; font-weight: 700;">500 - 1000 mail</td></tr>
</table></div>""", unsafe_allow_html=True)

logo_footer = get_image_base64("logo_moi.png")
if logo_footer: st.markdown(f'<div style="display: flex; justify-content: center; padding-top: 20px;"><img src="data:image/png;base64,{logo_footer}" style="width: 150px; height: 150px; border-radius: 35%; border: 4px solid white; box-shadow: 0 10px 25px rgba(59, 130, 246, 0.15);"></div>', unsafe_allow_html=True)
st.markdown('<div style="display: flex; justify-content: center; padding: 25px 0 50px 0;"><div style="max-width: 800px; text-align: center; color: #475569; padding: 30px; border-radius: 24px; border: 1px solid #e2e8f0; background: white;"><p style="font-size: 15px; line-height: 1.8; margin: 0;"><b style="background: linear-gradient(90deg, #3b82f6, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 22px; font-weight: 900;">BulkMail Pro</b><br><br>Giải pháp Marketing chuyên nghiệp bởi <b>Trường Sơn Marketing</b>.</p></div></div>', unsafe_allow_html=True)
st.markdown("""<div class="floating-container"><a href="https://zalo.me/0935748199" target="_blank" class="float-btn"><img src="https://upload.wikimedia.org/wikipedia/commons/9/91/Icon_of_Zalo.svg" width="35"></a><a href="https://t.me/BulkMail_Pro" target="_blank" class="float-btn"><img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg" width="35"></a></div>""", unsafe_allow_html=True)
