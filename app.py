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
import base64
import os

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
# GIAO DIỆN CSS: "VIÊN NANG ĐA SẮC NỔI BẬT"
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif !important; }
    
    #MainMenu, footer, header, .stDeployButton, [data-testid="manage-app-button"], [data-testid="viewerBadge"], iframe[title="Streamlit Toolbar"], iframe[src*="badge"] {display: none !important; visibility: hidden !important;}

    /* Nền ứng dụng */
    .stApp { background-color: #f8fafc; }
    
    /* Chữ Gradient cực ngầu cho Tiêu đề */
    .gradient-text {
        background: linear-gradient(90deg, #2563eb 0%, #7c3aed 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 900;
        font-size: 46px;
        margin-bottom: 5px;
        letter-spacing: -1px;
    }

    /* KHUNG TIÊU ĐỀ NỔI BẬT 3D (PILL DESIGN) */
    .pill-header {
        color: white;
        padding: 10px 24px;
        border-radius: 50px; /* Bo cong viên thuốc */
        font-size: 15px;
        font-weight: 800;
        margin-bottom: 20px;
        margin-top: 15px;
        text-transform: uppercase;
        letter-spacing: 1px;
        display: inline-block; /* Ôm sát chữ */
        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    /* Các màu riêng biệt cho từng bước */
    .bg-gradient-blue { background: linear-gradient(135deg, #3b82f6, #1d4ed8); box-shadow: 0 6px 15px rgba(59, 130, 246, 0.4); border: 2px solid #93c5fd; }
    .bg-gradient-purple { background: linear-gradient(135deg, #a855f7, #6d28d9); box-shadow: 0 6px 15px rgba(168, 85, 247, 0.4); border: 2px solid #d8b4fe; }
    .bg-gradient-pink { background: linear-gradient(135deg, #ec4899, #be185d); box-shadow: 0 6px 15px rgba(236, 72, 153, 0.4); border: 2px solid #fbcfe8; }
    .bg-gradient-green { background: linear-gradient(135deg, #10b981, #047857); box-shadow: 0 6px 15px rgba(16, 185, 129, 0.4); border: 2px solid #6ee7b7; }
    .bg-gradient-orange { background: linear-gradient(135deg, #f59e0b, #b45309); box-shadow: 0 6px 15px rgba(245, 158, 11, 0.4); border: 2px solid #fcd34d; }

    /* Khối Đăng nhập - Kính mờ */
    .auth-box { 
        max-width: 420px; margin: 60px auto; padding: 40px; 
        background: rgba(255, 255, 255, 0.95); 
        border-radius: 24px; 
        box-shadow: 0 20px 40px -15px rgba(0,0,0,0.1); 
        border: 1px solid rgba(255,255,255,0.5);
        backdrop-filter: blur(10px);
    }
    
    /* Auto-Card: Tự động bo góc các khối chức năng của Streamlit */
    div[data-testid="stFileUploader"], div[data-testid="stExpander"], div[data-testid="stMetric"] {
        background-color: white;
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        border: 1px solid #e2e8f0;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }

    /* NÚT BẤM CHÍNH (Glow Effect) */
    .stButton>button[kind="primary"] { 
        background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%) !important; 
        color: white !important; 
        border-radius: 12px; 
        font-weight: 800; 
        font-size: 16px;
        padding: 12px 24px; 
        border: none; 
        box-shadow: 0 6px 20px rgba(79, 70, 229, 0.35);
        transition: all 0.3s ease; 
        letter-spacing: 0.5px;
    }
    .stButton>button[kind="primary"]:hover { 
        transform: translateY(-3px); 
        box-shadow: 0 8px 25px rgba(79, 70, 229, 0.5); 
    }
    
    /* ===== NÚT PHỤ (ĐĂNG XUẤT, LƯU CẤU HÌNH, TẢI FILE) ===== */
    .stButton>button[kind="secondary"], div[data-testid="stDownloadButton"]>button {
        border-radius: 12px; 
        border: 1.5px solid #cbd5e1; 
        color: #475569 !important; 
        font-weight: 700;
        background-color: white !important;
        transition: all 0.3s ease;
    }
    .stButton>button[kind="secondary"]:hover, div[data-testid="stDownloadButton"]>button:hover {
        border-color: #3b82f6 !important; 
        color: #3b82f6 !important; 
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(59, 130, 246, 0.15);
    }
    /* ======================================================== */
    
    /* Logo Login */
    .logo-container { display: flex; justify-content: center; align-items: center; width: 100%; margin-bottom: 30px; }
    .logo-container img { width: 130px; height: 130px; border-radius: 35%; object-fit: cover; box-shadow: 0 10px 25px rgba(59, 130, 246, 0.2); border: 4px solid white;}
    .alt-logo { width: 130px; height: 130px; border-radius: 35%; background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%); color: white; display: flex; justify-content: center; align-items: center; font-weight: 800; font-size: 16px; text-align: center; border: 4px solid white; box-shadow: 0 10px 25px rgba(59, 130, 246, 0.2); }

    /* Nút liên hệ nổi */
    .floating-container { position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 15px; z-index: 999999; }
    .float-btn { width: 55px; height: 55px; border-radius: 50%; box-shadow: 0 10px 25px rgba(0,0,0,0.15); display: flex; justify-content: center; align-items: center; background: white; transition: 0.3s; border: 2px solid #e2e8f0; }
    .float-btn:hover { transform: translateY(-5px); border-color: #3b82f6; }
    .float-btn img { width: 65%; height: 65%; object-fit: contain; }
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

LOGO_URL = "logo_moi.png"

# ==========================================
# 1. HỆ THỐNG ĐĂNG NHẬP
# ==========================================
if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        
        logo_b64 = get_image_base64(LOGO_URL)
        if logo_b64:
            st.markdown(f'<div class="logo-container"><img src="data:image/png;base64,{logo_b64}"></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="logo-container"><div class="alt-logo">TRƯỜNG SƠN<br>MARKETING</div></div>', unsafe_allow_html=True)
            
        st.markdown('<h2 style="text-align:center; color:#0f172a; font-weight:900; margin-bottom:5px;">BULKMAIL PRO</h2>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; color:#64748b; margin-bottom:25px;">Đăng nhập để bắt đầu chiến dịch</p>', unsafe_allow_html=True)
        
        tab_login, tab_reg, tab_forgot = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký", "🔑 Quên MK"])
        users_db = load_users()

        with tab_login:
            log_user = st.text_input("Tên đăng nhập", key="login_u")
            log_pwd = st.text_input("Mật khẩu", type="password", key="login_p")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("ĐĂNG NHẬP HỆ THỐNG", type="primary", use_container_width=True):
                u_data = users_db.get(log_user)
                if u_data and u_data.get("password") == hash_password(log_pwd):
                    st.session_state["current_user"] = log_user
                    st.session_state["logged_in"] = True
                    st.rerun()
                else: st.error("❌ Thông tin đăng nhập chưa chính xác!")

        with tab_reg:
            reg_user = st.text_input("Tên đăng nhập mới", key="reg_u")
            reg_email = st.text_input("Email khôi phục", key="reg_e")
            reg_pwd = st.text_input("Mật khẩu", type="password", key="reg_p")
            reg_pwd_confirm = st.text_input("Xác nhận mật khẩu", type="password", key="reg_pc")
            if st.button("TẠO TÀI KHOẢN", type="primary", use_container_width=True):
                if not reg_user or not reg_email or not reg_pwd:
                    st.warning("⚠️ Điền đủ thông tin!")
                elif reg_user in users_db:
                    st.error("❌ Username đã tồn tại!")
                elif reg_pwd != reg_pwd_confirm:
                    st.error("❌ Mật khẩu không khớp!")
                else:
                    save_user_api(reg_user, hash_password(reg_pwd), reg_email)
                    st.success("✅ Đăng ký thành công!")

        with tab_forgot:
            if not st.session_state["otp_verified"]:
                fg_user = st.text_input("Nhập Username", key="fg_u")
                fg_email = st.text_input("Nhập Email đã đăng ký", key="fg_e")
                if st.button("GỬI MÃ OTP", use_container_width=True):
                    if fg_user in users_db and users_db[fg_user].get("email") == fg_email:
                        otp = generate_otp()
                        if reset_password_api(fg_user, fg_email, hash_password(otp), True):
                            if send_otp_email(fg_email, fg_user, otp):
                                st.session_state["otp_sent"] = True
                                st.success(f"✅ OTP đã gửi tới {fg_email}")
                    else: st.error("❌ Thông tin không khớp!")
                
                if st.session_state["otp_sent"]:
                    input_otp = st.text_input("Mã OTP 6 số:", max_chars=6, key="otp_i")
                    if st.button("XÁC THỰC OTP", type="primary", use_container_width=True):
                        u_info = load_users().get(fg_user)
                        if u_info and u_info.get("password") == hash_password(input_otp):
                            st.session_state["otp_verified"] = True
                            st.session_state["target_user"] = fg_user
                            st.rerun()
                        else: st.error("❌ OTP không đúng!")
            else:
                new_p = st.text_input("Mật khẩu mới", type="password", key="new_p")
                if st.button("ĐỔI MẬT KHẨU", type="primary", use_container_width=True):
                    u_db = load_users()
                    target = st.session_state["target_user"]
                    if reset_password_api(target, u_db[target]["email"], hash_password(new_p), False):
                        st.session_state["otp_verified"] = False
                        st.session_state["otp_sent"] = False
                        st.success("✅ Đổi mật khẩu thành công!")
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 2. DASHBOARD CHÍNH
# ==========================================
else:
    # --- HEADER ---
    head_col1, head_col2 = st.columns([5, 1])
    with head_col1:
        st.markdown('<div class="gradient-text">BulkMail</div>', unsafe_allow_html=True)
        st.markdown('<p style="color:#64748b; font-size: 16px; margin-bottom: 20px;">Hệ thống Marketing Tự động thông minh.</p>', unsafe_allow_html=True)
    with head_col2:
        st.markdown(f"<div style='text-align: right; padding-top: 10px; font-weight: bold; color: #1e40af;'>👤 {st.session_state['current_user']}</div>", unsafe_allow_html=True)
        # Nút đăng xuất (Giờ đã có hiệu ứng Hover xịn xò)
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state["logged_in"] = False
            st.rerun()

    # --- BƯỚC 1: CẤU HÌNH (THẺ XANH DƯƠNG) ---
    st.markdown('<div class="pill-header bg-gradient-blue">⚙️ BƯỚC 1: CẤU HÌNH MÁY CHỦ & BÁO CÁO</div>', unsafe_allow_html=True)
    
    with st.container():
        st.info("💡 Điền thông tin một lần, hệ thống sẽ tự động lưu lại cho các chiến dịch sau.")
        cfg_col1, cfg_col2 = st.columns(2, gap="large")
        
        with cfg_col1:
            st.markdown("<b style='color:#0f172a;'>📧 Thông tin Gửi thư (Gmail)</b>", unsafe_allow_html=True)
            st.session_state["s_name"] = st.text_input("Tên người gửi (Ví dụ: Trường Sơn Marketing):", value=st.session_state["s_name"])
            st.session_state["s_email"] = st.text_input("Địa chỉ Gmail của bạn:", value=st.session_state["s_email"])
            st.session_state["s_pwd"] = st.text_input("Mật khẩu ứng dụng (16 ký tự):", type="password", value=st.session_state["s_pwd"])
            
            with st.expander("❓ Bấm vào đây để xem Hướng dẫn lấy Mật khẩu ứng dụng (Rất dễ)"):
                st.markdown("""
                <div style="font-size: 14.5px; color: #334155; line-height: 1.6;">
                    <b>Làm theo 4 bước sau (chỉ mất 1 phút):</b><br>
                    <b>1.</b> Mở tab mới, truy cập link này: <a href="https://myaccount.google.com/security" target="_blank" style="color:#3b82f6; text-decoration:none;"><b>Bảo mật Tài khoản Google</b></a>.<br>
                    <b>2.</b> Đảm bảo tính năng <b>Xác minh 2 bước</b> đã được <b>BẬT</b>.<br>
                    <b>3.</b> Kéo lên trên cùng, tìm ô <b>Tìm kiếm</b> (biểu tượng kính lúp) ➔ Gõ chữ <b>"Mật khẩu ứng dụng"</b> (hoặc App Passwords) ➔ Bấm chọn kết quả hiện ra.<br>
                    <b>4.</b> Gõ tên ứng dụng là <i>"BulkMail"</i> ➔ Bấm <b>Tạo</b>. Google sẽ cấp cho bạn một dải gồm <b>16 chữ cái</b>. Hãy copy và dán vào ô bên trên (cứ dán nguyên, không cần xóa khoảng trắng).
                </div>
                """, unsafe_allow_html=True)
            
        with cfg_col2:
            st.markdown("<b style='color:#0f172a;'>🔔 Báo cáo Telegram & Chữ ký</b>", unsafe_allow_html=True)
            u_data = load_users().get(st.session_state["current_user"], {})
            new_tk = st.text_input("Bot Token Telegram (Tùy chọn):", value=u_data.get("tele_token", ""), type="password")
            new_id = st.text_input("Chat ID Telegram (Tùy chọn):", value=u_data.get("tele_chat_id", ""))
            
            st.session_state["s_sign"] = st.text_area("Chữ ký mặc định cuối thư:", value=st.session_state["s_sign"], height=68)
            
            # Nút Lưu cấu hình (Giờ đã có hiệu ứng Hover xịn xò)
            if st.button("💾 Lưu cấu hình Telegram"):
                if save_config_api(st.session_state["current_user"], new_tk, new_id):
                    st.success("✅ Đã lưu cấu hình!")

    st.markdown("<hr style='margin: 30px 0;'>", unsafe_allow_html=True)

    # --- KHỐI DỮ LIỆU & NỘI DUNG (CHIA 2 CỘT) ---
    col_data, col_content = st.columns([1, 1.2], gap="large")
    
    # Góc Trái: Data Khách hàng
    with col_data:
        # BƯỚC 2 (THẺ TÍM)
        st.markdown('<div class="pill-header bg-gradient-purple">📁 BƯỚC 2: DỮ LIỆU KHÁCH HÀNG</div>', unsafe_allow_html=True)
        
        sample_df = pd.DataFrame({"email": ["khachhang@gmail.com", "vidu@gmail.com"]})
        try:
            excel_buf = io.BytesIO()
            with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
                sample_df.to_excel(writer, index=False, sheet_name="Danh_sach")
            dl_data = excel_buf.getvalue()
        except:
            dl_data = sample_df.to_csv(index=False).encode("utf-8-sig")
            
        st.download_button("📥 Tải File Mẫu (Excel)", data=dl_data, file_name="danh_sach_mau.xlsx", use_container_width=True)
        
        up = st.file_uploader("Tải tệp danh sách (.csv, .xlsx)", type=["csv", "xlsx"])
        df = None
        if up:
            df = pd.read_excel(up) if up.name.endswith("xlsx") else pd.read_csv(up)
            st.success(f"✅ Hợp lệ! Đã nhận {len(df)} địa chỉ email.")
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # ĐÍNH KÈM (THẺ HỒNG)
        st.markdown('<div class="pill-header bg-gradient-pink">📎 TỆP ĐÍNH KÈM (TÙY CHỌN)</div>', unsafe_allow_html=True)
        attachments = st.file_uploader("Kéo thả tài liệu vào đây", accept_multiple_files=True)

    # Góc Phải: Nội dung & Soạn thảo
    with col_content:
        # BƯỚC 3 (THẺ XANH LÁ)
        st.markdown('<div class="pill-header bg-gradient-green">✍️ BƯỚC 3: SOẠN THÔNG ĐIỆP</div>', unsafe_allow_html=True)
        
        subject = st.text_input("Tiêu đề Email:")
        raw_body = st.text_area("Nội dung (Gọi tên bằng biến {{name}}):", height=230, value="Kính chào Anh/Chị {{name}},\n\nNhập nội dung thư tại đây...")
        
        col_delay, col_blank = st.columns([1, 1])
        with col_delay:
            delay = st.number_input("⏳ Khoảng nghỉ/Mail (Giây):", value=15, min_value=5, help="Thời gian nghỉ giữa mỗi mail. Đề xuất: 15-30s.")

        # Xem trước Real-time
        body_html = raw_body.replace("\n", "<br>")
        sign_html = st.session_state["s_sign"].replace("\n", "<br>")
        full_email_content = f"<div style='font-family:Arial; line-height:1.8; color:#333;'>{body_html}<br><br><div style='color:#666; border-top:1px solid #eee; padding-top:10px;'>{sign_html}</div></div>"
        
        with st.expander("👁️ Mở rộng Xem trước giao diện thực tế", expanded=False):
            example_name = str(df.iloc[0]["name"]) if df is not None and not df.empty and "name" in df.columns else "Quý khách"
            st.markdown(f"<div style='padding:20px; background:white; border-radius: 8px; border: 1px solid #e2e8f0;'>{full_email_content.replace('{{name}}', f'<b style=\"color:#3b82f6;\">{example_name}</b>')}</div>", unsafe_allow_html=True)

    st.markdown("<hr style='margin: 30px 0;'>", unsafe_allow_html=True)

    # --- KHỐI BẢNG LƯU Ý & NÚT GỬI ---
    col_action1, col_action2 = st.columns([1.5, 1])
    
    with col_action1:
        # BẢNG LƯU Ý (THẺ CAM)
        st.markdown('<div class="pill-header bg-gradient-orange">🛡️ BẢNG TIÊU CHUẨN AN TOÀN</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="background-color: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); margin-top: -10px;">
            <table style="width:100%; border-collapse: collapse; font-size: 15px; text-align: left;">
                <tr style="border-bottom: 2px solid #e2e8f0; color:#64748b;">
                    <th style="padding: 10px 0;">Loại tài khoản</th>
                    <th style="padding: 10px 0;">Số lượng an toàn / Ngày</th>
                </tr>
                <tr style="border-bottom: 1px solid #f1f5f9;">
                    <td style="padding: 12px 0; font-weight: 600;">Gmail mới tạo</td>
                    <td style="padding: 12px 0; color: #f59e0b; font-weight: 700;">20 - 50 mail</td>
                </tr>
                <tr style="border-bottom: 1px solid #f1f5f9;">
                    <td style="padding: 12px 0; font-weight: 600;">Gmail dùng lâu</td>
                    <td style="padding: 12px 0; color: #10b981; font-weight: 700;">200 - 300 mail</td>
                </tr>
                <tr>
                    <td style="padding: 12px 0; font-weight: 600;">Google Workspace</td>
                    <td style="padding: 12px 0; color: #3b82f6; font-weight: 700;">500 - 1000 mail</td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)

    with col_action2:
        st.markdown("<div style='margin-top: 55px;'></div>", unsafe_allow_html=True)
        if st.button("🚀 BẮT ĐẦU CHIẾN DỊCH GỬI MAIL", type="primary", use_container_width=True):
            if df is None:
                st.error("⚠️ Vui lòng tải lên danh sách Khách hàng!")
            elif not subject:
                st.error("⚠️ Tiêu đề thư không được bỏ trống!")
            elif not st.session_state["s_email"] or not st.session_state["s_pwd"]:
                st.error("⚠️ Lỗi: Bạn chưa điền Email hoặc Mật khẩu ở Bước 1!")
            else:
                progress = st.progress(0)
                log = st.expander("📋 Trình giám sát hệ thống (Live)", expanded=True)
                
                # Biến đếm kết quả
                success_list = []
                error_list = []
                
                u_data_run = load_users().get(st.session_state["current_user"], {})
                run_tk = u_data_run.get("tele_token", "")
                run_id = u_data_run.get("tele_chat_id", "")
                send_tele_msg(run_tk, run_id, f"🚀 <b>BẮT ĐẦU CHIẾN DỊCH</b>\n👤 User: {st.session_state['current_user']}")
                
                for index, row in df.iterrows():
                    try:
                        e_col = next((c for c in df.columns if c.lower() in ["email", "mail"]), None)
                        target_email = str(row.get(e_col, row.iloc[0])).strip()
                        n_col = next((c for c in df.columns if c.lower() in ["name", "tên"]), None)
                        target_name = str(row.get(n_col, "Khách hàng")) if n_col else "Khách hàng"
                        
                        msg = MIMEMultipart()
                        msg["From"] = f"{st.session_state['s_name']} <{st.session_state['s_email']}>"
                        msg["To"] = target_email
                        msg["Subject"] = subject
                        msg.attach(MIMEText(full_email_content.replace("{{name}}", target_name), "html"))
                        
                        if attachments:
                            for f in attachments:
                                part = MIMEBase("application", "octet-stream")
                                part.set_payload(f.read())
                                encoders.encode_base64(part)
                                part.add_header("Content-Disposition", f"attachment; filename={f.name}")
                                msg.attach(part)
                                f.seek(0)
                                
                        with smtplib.SMTP("smtp.gmail.com", 587) as server:
                            server.starttls()
                            server.login(st.session_state["s_email"], st.session_state["s_pwd"])
                            server.send_message(msg)
                            
                        success_list.append(target_email)
                        log.write(f"✅ Đã gửi: {target_email}")
                    except Exception as e:
                        error_list.append(target_email)
                        log.write(f"❌ Lỗi: {target_email} ({e})")
                        
                    progress.progress((index + 1) / len(df))
                    time.sleep(delay)
                    
                st.success("🎉 Chiến dịch hoàn tất!")
                
                csv_buf = io.BytesIO()
                pd.DataFrame({
                    "Email": success_list + error_list, 
                    "Kết quả": ["Thành công"] * len(success_list) + ["Lỗi"] * len(error_list)
                }).to_csv(csv_buf, index=False, encoding="utf-8-sig")
                
                send_tele_msg(run_tk, run_id, f"📊 <b>TỔNG KẾT</b>\n✅ Thành công: {len(success_list)}\n❌ Lỗi: {len(error_list)}")
                send_tele_file(run_tk, run_id, csv_buf.getvalue(), "ket_qua.csv")
                
                st.download_button("📥 TẢI BÁO CÁO (.CSV)", data=csv_buf.getvalue(), file_name="ket_qua.csv", use_container_width=True)

    # ==========================================
    # CHÂN TRANG: LOGO VÀ GIỚI THIỆU
    # ==========================================
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    logo_footer_b64 = get_image_base64(LOGO_URL)
    if logo_footer_b64:
        st.markdown(f"""<div style="display: flex; justify-content: center; padding-top: 20px;"><img src="data:image/png;base64,{logo_footer_b64}" style="width: 150px; height: 150px; border-radius: 35%; object-fit: cover; border: 4px solid white; box-shadow: 0 10px 25px rgba(59, 130, 246, 0.15);"></div>""", unsafe_allow_html=True)

    st.markdown(
        """
        <div style="display: flex; justify-content: center; padding: 25px 0 50px 0;">
            <div style="max-width: 800px; text-align: center; color: #475569; font-family: 'Plus Jakarta Sans', sans-serif; 
                        padding: 30px; border-radius: 24px; border: 1px solid #e2e8f0; background: white; 
                        box-shadow: 0 10px 25px rgba(0,0,0,0.03);">
                <p style="font-size: 15px; line-height: 1.8; margin: 0;">
                    <b style="background: linear-gradient(90deg, #3b82f6, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 22px; font-weight: 900;">BulkMail Pro</b><br><br> 
                    Là công cụ gửi thư tự động được phát triển bởi <b>Trường Sơn Marketing</b>. 
                    Chúng tôi mang đến giải pháp giúp bạn kết nối với hàng ngàn khách hàng chỉ trong tích tắc, 
                    giúp tiết kiệm thời gian và tăng hiệu quả bán hàng. <br>Với tiêu chí: <b>Dễ dùng - An toàn - Hiệu quả</b>.
                </p>
            </div>
        </div>
        """, 
        unsafe_allow_html=True
    )

# NÚT LIÊN HỆ NỔI
st.markdown("""<div class="floating-container"><a href="https://zalo.me/0935748199" target="_blank" class="float-btn"><img src="https://upload.wikimedia.org/wikipedia/commons/9/91/Icon_of_Zalo.svg"></a><a href="https://t.me/BulkMail_Pro" target="_blank" class="float-btn"><img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg"></a></div>""", unsafe_allow_html=True)
