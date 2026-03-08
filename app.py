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
# GIAO DIỆN CSS MÀU GỐC & CẢI TIẾN TAB
# ==========================================
st.markdown("""
<style>
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header {visibility: hidden !important;}
    .stDeployButton {display: none !important;}
    [data-testid="manage-app-button"] {display: none !important; visibility: hidden !important;}
    [data-testid="viewerBadge"] {display: none !important; visibility: hidden !important;}
    iframe[title="Streamlit Toolbar"] {display: none !important; visibility: hidden !important;}

    /* Nền xám trắng nhạt như cũ */
    .stApp { background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%); }
    
    .auth-box { max-width: 480px; margin: auto; padding: 30px; background: white; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
    
    /* Nút bấm xanh đậm như cũ */
    .stButton>button { background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%) !important; color: white !important; border-radius: 8px; font-weight: 600; padding: 10px 24px; transition: all 0.3s ease; border: none; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 8px 15px rgba(59, 130, 246, 0.3); }

    .logo-container { display: flex; justify-content: center; align-items: center; width: 100%; margin-bottom: 25px; }
    .logo-container img { width: 160px; height: 160px; border-radius: 50%; object-fit: cover; border: 4px solid #1e3a8a; box-shadow: 0 4px 15px rgba(0,0,0,0.2); display: block; }
    .alt-logo { width: 160px; height: 160px; border-radius: 50%; background-color: #1e3a8a; color: white; display: flex; justify-content: center; align-items: center; font-weight: 800; font-size: 18px; text-align: center; border: 4px solid white; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }

    .hero-banner { background: linear-gradient(rgba(30, 58, 138, 0.85), rgba(30, 58, 138, 0.85)), url('https://images.unsplash.com/photo-1557683316-973673baf926?auto=format&fit=crop&w=1350&q=80'); background-size: cover; padding: 40px; border-radius: 15px; color: white; text-align: center; margin-bottom: 25px; }
    .hero-banner h1 { font-size: 32px !important; font-weight: 800 !important; color: white !important; letter-spacing: 1px; }

    .welcome-text { text-align: center; color: #1e3a8a; font-weight: 800; margin-bottom: 20px; font-size: 28px; text-transform: uppercase; }
    .section-header { color: #1e3a8a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin-top: 20px; font-size: 20px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
    
    /* Thiết kế lại Tab hiện đại hơn */
    .stTabs [data-baseweb="tab-list"] { gap: 24px; border-bottom: 2px solid #e2e8f0; padding-bottom: 5px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-weight: 600; font-size: 16px; color: #64748b; }
    .stTabs [aria-selected="true"] { color: #1e3a8a !important; border-bottom: 3px solid #1e3a8a !important; }

    .floating-container { position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 12px; z-index: 999999; }
    .float-btn { width: 52px; height: 52px; border-radius: 50%; box-shadow: 0 4px 12px rgba(0,0,0,0.2); display: flex; justify-content: center; align-items: center; background: white; transition: 0.3s; }
    .float-btn:hover { transform: scale(1.1); }
    .float-btn img { width: 75%; height: 75%; object-fit: contain; }
    
    .help-box { background-color: #f0f9ff; padding: 15px; border-left: 4px solid #0ea5e9; border-radius: 5px; font-size: 14px; color: #334155; margin-bottom: 15px; }
    .alert-box { background-color: #fffbeb; padding: 15px; border: 1px solid #bae6fd; border-radius: 8px; font-size: 14px; color: #0369a1; margin-top: 15px; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# Khởi tạo session state
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "otp_verified" not in st.session_state: st.session_state["otp_verified"] = False
if "otp_sent" not in st.session_state: st.session_state["otp_sent"] = False

# Khởi tạo biến lưu cấu hình để dùng chung giữa các tab
if "s_name" not in st.session_state: st.session_state["s_name"] = "Trường Sơn Marketing"
if "s_email" not in st.session_state: st.session_state["s_email"] = ""
if "s_pwd" not in st.session_state: st.session_state["s_pwd"] = ""
if "s_sign" not in st.session_state: st.session_state["s_sign"] = "Trân trọng,\nTrường Sơn Marketing"

LOGO_URL = "logo_moi.png"

# ==========================================
# 1. HỆ THỐNG ĐĂNG NHẬP
# ==========================================
if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        st.markdown('<p class="welcome-text">BULKMAIL PRO</p>', unsafe_allow_html=True)
        
        logo_b64 = get_image_base64(LOGO_URL)
        if logo_b64:
            st.markdown(f'<div class="logo-container"><img src="data:image/png;base64,{logo_b64}"></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="logo-container"><div class="alt-logo">TRƯỜNG SƠN<br>MARKETING</div></div>', unsafe_allow_html=True)
        
        tab_login, tab_reg, tab_forgot = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký", "🔑 Quên MK"])
        users_db = load_users()

        with tab_login:
            log_user = st.text_input("Username", key="login_u")
            log_pwd = st.text_input("Mật khẩu", type="password", key="login_p")
            if st.button("ĐĂNG NHẬP", use_container_width=True):
                u_data = users_db.get(log_user)
                if u_data and u_data.get("password") == hash_password(log_pwd):
                    st.session_state["current_user"] = log_user
                    st.session_state["logged_in"] = True
                    st.rerun()
                else: st.error("❌ Tài khoản hoặc mật khẩu không đúng!")

        with tab_reg:
            reg_user = st.text_input("Tên đăng nhập mới", key="reg_u")
            reg_email = st.text_input("Email khôi phục", key="reg_e")
            reg_pwd = st.text_input("Mật khẩu", type="password", key="reg_p")
            reg_pwd_confirm = st.text_input("Xác nhận mật khẩu", type="password", key="reg_pc")
            if st.button("TẠO TÀI KHOẢN", use_container_width=True):
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
                    if st.button("XÁC THỰC OTP", use_container_width=True):
                        u_info = load_users().get(fg_user)
                        if u_info and u_info.get("password") == hash_password(input_otp):
                            st.session_state["otp_verified"] = True
                            st.session_state["target_user"] = fg_user
                            st.rerun()
                        else: st.error("❌ OTP không đúng!")
            else:
                new_p = st.text_input("Mật khẩu mới", type="password", key="new_p")
                if st.button("ĐỔI MẬT KHẨU", use_container_width=True):
                    u_db = load_users()
                    target = st.session_state["target_user"]
                    if reset_password_api(target, u_db[target]["email"], hash_password(new_p), False):
                        st.session_state["otp_verified"] = False
                        st.session_state["otp_sent"] = False
                        st.success("✅ Thành công! Hãy đăng nhập.")
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 2. DASHBOARD CHÍNH (BỐ CỤC SAAS THÔNG MINH)
# ==========================================
else:
    # Header: Banner & Thông tin User
    col_banner, col_user = st.columns([5, 1])
    with col_banner:
        st.markdown("""
        <div class="hero-banner" style="padding: 20px; text-align: left; margin-bottom: 10px;">
            <h1 style="margin: 0; font-size: 28px !important;">BULKMAIL PRO</h1>
            <p style="margin: 0; opacity: 0.9;">Giải pháp Marketing Tự động chuyên nghiệp</p>
        </div>
        """, unsafe_allow_html=True)
    with col_user:
        st.markdown(f"<div style='text-align: right; padding-top: 15px; font-weight: bold; color: #1e3a8a;'>👋 Xin chào, {st.session_state['current_user']}</div>", unsafe_allow_html=True)
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state["logged_in"] = False
            st.rerun()

    # --- CHIA TABS THÔNG MINH ---
    tab_campaign, tab_config, tab_guide = st.tabs([
        "🚀 1. CHIẾN DỊCH GỬI MAIL", 
        "⚙️ 2. CÀI ĐẶT HỆ THỐNG", 
        "🛡️ 3. HƯỚNG DẪN BẢO MẬT"
    ])

    # ==========================================
    # TAB 2: CÀI ĐẶT HỆ THỐNG (Đưa ra sau vì chỉ set 1 lần)
    # ==========================================
    with tab_config:
        st.info("💡 Thiết lập cấu hình máy chủ SMTP và báo cáo tại đây. Thông tin sẽ được tự động áp dụng vào Chiến dịch của bạn.")
        cfg_col1, cfg_col2 = st.columns(2)
        
        with cfg_col1:
            st.markdown('<div class="section-header">Tài khoản gửi (Gmail)</div>', unsafe_allow_html=True)
            st.session_state["s_name"] = st.text_input("Tên hiển thị người gửi:", value=st.session_state["s_name"])
            st.session_state["s_email"] = st.text_input("Email gửi (Gmail):", value=st.session_state["s_email"])
            st.session_state["s_pwd"] = st.text_input("App Password (16 ký tự):", type="password", value=st.session_state["s_pwd"])
            
            with st.expander("❓ Hướng dẫn lấy App Password"):
                st.markdown("""
                <div class="help-box">
                    1. Truy cập <b>Cài đặt Bảo mật Google</b>.<br>
                    2. Bật <b>Xác minh 2 bước</b>.<br>
                    3. Gõ tìm kiếm <b>Mật khẩu ứng dụng</b>. Tạo ứng dụng tên "BulkMail" và dán 16 chữ cái vào ô bên trên.
                </div>
                """, unsafe_allow_html=True)

        with cfg_col2:
            st.markdown('<div class="section-header">Chữ ký Email mặc định</div>', unsafe_allow_html=True)
            st.session_state["s_sign"] = st.text_area("Nội dung đính kèm cuối mọi thư:", value=st.session_state["s_sign"], height=130)
            
            st.markdown('<div class="section-header">Báo cáo tự động (Telegram)</div>', unsafe_allow_html=True)
            u_data = load_users().get(st.session_state["current_user"], {})
            t_tk = u_data.get("tele_token", "")
            t_id = u_data.get("tele_chat_id", "")
            new_tk = st.text_input("Bot Token:", value=t_tk, type="password")
            new_id = st.text_input("Chat ID:", value=t_id)
            if st.button("💾 Lưu cấu hình Telegram"):
                if save_config_api(st.session_state["current_user"], new_tk, new_id):
                    st.success("✅ Đã lưu cấu hình báo cáo Telegram!")

    # ==========================================
    # TAB 1: CHIẾN DỊCH GỬI MAIL (Trọng tâm)
    # ==========================================
    with tab_campaign:
        if not st.session_state["s_email"] or not st.session_state["s_pwd"]:
            st.warning("⚠️ Nhắc nhở: Bạn chưa cấu hình tài khoản gửi thư. Hãy chuyển sang Tab **[⚙️ CÀI ĐẶT HỆ THỐNG]** để thiết lập trước khi chạy chiến dịch.")
            
        camp_col1, camp_col2 = st.columns([1, 1.2])
        
        # Cột Trái: Dữ liệu
        with camp_col1:
            st.markdown('<div class="section-header">1. Tải Dữ liệu Khách hàng</div>', unsafe_allow_html=True)
            
            sample_df = pd.DataFrame({"email": ["khachhang@gmail.com", "vidu@gmail.com"]})
            try:
                excel_buf = io.BytesIO()
                with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
                    sample_df.to_excel(writer, index=False, sheet_name="Danh_sach")
                dl_data = excel_buf.getvalue()
                dl_name = "danh_sach_mau.xlsx"
                dl_mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            except:
                dl_data = sample_df.to_csv(index=False).encode("utf-8-sig")
                dl_name = "danh_sach_mau.csv"
                dl_mime = "text/csv"

            st.download_button("📥 Tải File Mẫu Excel", data=dl_data, file_name=dl_name, mime=dl_mime)

            up = st.file_uploader("Kéo thả danh sách (.csv, .xlsx) vào đây", type=["csv", "xlsx"])
            df = None
            if up:
                df = pd.read_excel(up) if up.name.endswith("xlsx") else pd.read_csv(up)
                st.success(f"✅ Hệ thống đã tiếp nhận {len(df)} địa chỉ liên hệ.")
            
            st.markdown('<div class="section-header" style="margin-top: 10px;">Tệp đính kèm (Tuỳ chọn)</div>', unsafe_allow_html=True)
            attachments = st.file_uploader("Gửi kèm Báo giá, Hợp đồng, v.v...", accept_multiple_files=True)

        # Cột Phải: Nội dung & Delay
        with camp_col2:
            st.markdown('<div class="section-header">2. Nội dung Thư Truyền thông</div>', unsafe_allow_html=True)
            subject = st.text_input("Tiêu đề chiến dịch (Subject):")
            raw_body = st.text_area("Thông điệp (Dùng {{name}} để cá nhân hóa tên khách hàng):", height=200, value="Kính chào Anh/Chị {{name}},\n\nNhập nội dung thông điệp tại đây...")
            
            delay = st.number_input("Khoảng nghỉ an toàn (giây):", value=15, min_value=1, help="Giả lập thao tác người thật. Khuyên dùng: 15-30s.")
            
            # Khối Preview
            body_html = raw_body.replace("\n", "<br>")
            sign_html = st.session_state["s_sign"].replace("\n", "<br>")
            full_email_content = f"<div style='font-family:Arial; line-height:1.8; color:#333;'>{body_html}<br><br><div style='color:#666; border-top:1px solid #eee; padding-top:10px;'>{sign_html}</div></div>"
            
            with st.expander("👁️ Bấm để Xem trước giao diện thư khách hàng sẽ nhận", expanded=False):
                example_name = str(df.iloc[0]["name"]) if df is not None and not df.empty and "name" in df.columns else "Quý khách"
                st.markdown(f"<div style='padding:15px; border:1px solid #ddd; border-radius:8px; background:white;'>{full_email_content.replace('{{name}}', f'<b style=\"color:#1e3a8a;\">{example_name}</b>')}</div>", unsafe_allow_html=True)

        st.markdown("---")
        
        # Bảng cảnh báo ghim tĩnh (Yêu cầu của bạn)
        st.markdown("""
        <div class="alert-box">
            <b>🛡️ CẢNH BÁO AN TOÀN TÀI KHOẢN (QUAN TRỌNG):</b> Để giữ tỷ lệ vào Inbox cao và tránh bị khóa SMTP, tuyệt đối tuân thủ giới hạn:<br>
            • Tài khoản mới: <b>20 - 50 mail/ngày</b> | Tài khoản lâu năm: <b>200 - 300 mail/ngày</b> | Tốc độ nghỉ: <b>15 giây/mail</b>.
        </div>
        """, unsafe_allow_html=True)

        if st.button("▶ KÍCH HOẠT CHIẾN DỊCH HÀNG LOẠT", type="primary", use_container_width=True):
            if df is not None and st.session_state["s_email"] and st.session_state["s_pwd"]:
                progress = st.progress(0)
                log = st.expander("📋 Nhật ký vận hành (Live)", expanded=True)
                
                success_list = []
                error_list = []
                
                # Biến gửi Telegram (Load trực tiếp từ DB)
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
                        log.write(f"✅ [{index+1}/{len(df)}] Đã gửi thành công: {target_email}")
                    except Exception as e:
                        error_list.append(target_email)
                        log.write(f"❌ [{index+1}/{len(df)}] Lỗi {target_email}: {e}")
                        
                    progress.progress((index + 1) / len(df))
                    time.sleep(delay)
                    
                st.success("🎉 Chiến dịch hoàn tất! Vui lòng tải báo cáo bên dưới.")
                
                csv_buf = io.BytesIO()
                pd.DataFrame({
                    "Email": success_list + error_list, 
                    "Kết quả": ["Thành công"] * len(success_list) + ["Lỗi"] * len(error_list)
                }).to_csv(csv_buf, index=False, encoding="utf-8-sig")
                
                send_tele_msg(run_tk, run_id, f"📊 <b>TỔNG KẾT</b>\n✅ Thành công: {len(success_list)}\n❌ Lỗi: {len(error_list)}")
                send_tele_file(run_tk, run_id, csv_buf.getvalue(), "ket_qua.csv")
                
                st.download_button("📥 TẢI BÁO CÁO CHI TIẾT (.CSV)", data=csv_buf.getvalue(), file_name="ket_qua_chien_dich.csv")
                
            else:
                st.error("⚠️ Lỗi: Thiếu danh sách khách hàng hoặc chưa cấu hình Email gửi trong Tab [⚙️ Cài Đặt Hệ Thống]!")

    # ==========================================
    # TAB 3: HƯỚNG DẪN BẢO MẬT (Trình bày dạng bảng chi tiết)
    # ==========================================
    with tab_guide:
        st.markdown("### Tiêu chuẩn vận hành Email Marketing")
        st.markdown("""
        Việc gửi thư hàng loạt qua giao thức SMTP bị các nhà cung cấp (Google) giám sát rất chặt chẽ. Để tài khoản không bị đánh dấu Spam, vui lòng tuân thủ:
        
        | Tình trạng Tài khoản | Giới hạn Số lượng (Khuyên dùng) | Chiến lược Gửi chuẩn |
        | :--- | :--- | :--- |
        | **Mới tạo (Dưới 3 tháng)** | `20 - 50 mail / ngày` | "Nuôi" mail bằng cách gửi/nhận thủ công với bạn bè trong 2 tuần đầu. |
        | **Đã dùng lâu (Cá nhân)** | `100 - 300 mail / ngày` | Chia nhỏ tệp data. Không gửi dồn dập 300 mail cùng 1 lúc. |
        | **Tài khoản Google Workspace**| `500 - 1000 mail / ngày` | Giữ tốc độ nghỉ (Delay) ở mức 15 - 30 giây giữa mỗi thư. |
        
        *Lưu ý: Nếu danh sách của bạn có chứa quá nhiều Email ảo (Email không tồn tại), Google sẽ khóa tính năng gửi thư của bạn vĩnh viễn (Bounce Rate cao).*
        """)

    # ==========================================
    # PHẦN GIỚI THIỆU GỐC & LOGO NỔI CHÂN TRANG
    # ==========================================
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("---")
    
    logo_footer_b64 = get_image_base64(LOGO_URL)
    if logo_footer_b64:
        st.markdown(f"""<div style="display: flex; justify-content: center; padding-top: 20px;"><img src="data:image/png;base64,{logo_footer_b64}" style="width: 170px; height: 170px; border-radius: 50%; object-fit: cover; border: 4px solid #1e3a8a; box-shadow: 0 4px 15px rgba(0,0,0,0.2);"></div>""", unsafe_allow_html=True)

    st.markdown(
        """
        <div style="display: flex; justify-content: center; padding: 20px 0 50px 0;">
            <div style="max-width: 850px; text-align: center; color: #333; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                        padding: 20px; border-radius: 10px; border: 1px solid #ddd; background: white; 
                        box-shadow: 0 10px 30px rgba(0,0,0,0.1);">
                <p style="font-size: 16px; line-height: 1.6; margin: 0;">
                    <b style="color: #1e3a8a; font-size: 18px;">BulkMail Pro</b> là công cụ gửi thư tự động được phát triển bởi <b>Trường Sơn Marketing</b>. 
                    Chúng tôi mang đến giải pháp giúp bạn kết nối với hàng ngàn khách hàng chỉ trong tích tắc, 
                    giúp tiết kiệm thời gian và tăng hiệu quả bán hàng. Với tiêu chí: Dễ dùng - An toàn - Hiệu quả, 
                    Trường Sơn Marketing cam kết luôn đồng hành và hỗ trợ bạn trong mọi chiến dịch kinh doanh.
                </p>
            </div>
        </div>
        """, 
        unsafe_allow_html=True
    )

# NÚT LIÊN HỆ NỔI
st.markdown("""<div class="floating-container"><a href="https://zalo.me/0935748199" target="_blank" class="float-btn" style="border: 2px solid #0068ff;"><img src="https://upload.wikimedia.org/wikipedia/commons/9/91/Icon_of_Zalo.svg"></a><a href="https://t.me/BulkMail_Pro" target="_blank" class="float-btn" style="border: 2px solid #229ED9;"><img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg"></a></div>""", unsafe_allow_html=True)
