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
    try:
        res = requests.get(DB_URL)
        return res.json()
    except:
        return {}

def save_user_api(username, password_hash, email):
    if not DB_URL: return
    try:
        requests.post(DB_URL, json={"action": "register", "username": username, "password": password_hash, "email": email})
    except:
        pass

def reset_password_api(username, email, new_password_hash, is_reset_status):
    if not DB_URL: return False
    try:
        res = requests.post(DB_URL, json={
            "action": "reset", "username": username, "email": email, 
            "new_password": new_password_hash, "is_reset": is_reset_status
        }).json()
        return res.get("status") == "success"
    except:
        return False

def save_config_api(username, tele_token, tele_chat_id):
    if not DB_URL: return False
    try:
        res = requests.post(DB_URL, json={"action": "update_config", "username": username, "tele_token": tele_token, "tele_chat_id": tele_chat_id}).json()
        return res.get("status") == "success"
    except:
        return False

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

def send_otp_email(to_email, username, otp_code):
    if not SYS_EMAIL or not SYS_PWD: return False
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Hệ thống xác thực <{SYS_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = f"{otp_code} là mã xác thực của bạn"
        body = f"<h3>Chào {username},</h3><p>Mã OTP để khôi phục mật khẩu của bạn là: <b style='font-size: 20px;'>{otp_code}</b></p>"
        msg.attach(MIMEText(body, 'html'))
        # Sử dụng SSL cổng 465 để ổn định hơn
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as s:
            s.login(SYS_EMAIL, SYS_PWD)
            s.send_message(msg)
        return True
    except:
        return False

def send_tele_msg(token, chat_id, message):
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, data={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=5)
        except:
            pass

def send_tele_file(token, chat_id, file_content, file_name):
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendDocument"
            files = {'document': (file_name, file_content)}
            requests.post(url, data={'chat_id': chat_id}, files=files, timeout=10)
        except:
            pass

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
    .logo-container img { width: 160px; height: 160px; border-radius: 50%; object-fit: cover; border: 4px solid #1e3a8a; box-shadow: 0 4px 15px rgba(0,0,0,0.2); display: block; }
    .alt-logo { width: 160px; height: 160px; border-radius: 50%; background-color: #1e3a8a; color: white; display: flex; justify-content: center; align-items: center; font-weight: 800; font-size: 18px; text-align: center; border: 4px solid white; }

    .hero-banner { background: linear-gradient(rgba(30, 58, 138, 0.85), rgba(30, 58, 138, 0.85)), url('https://images.unsplash.com/photo-1557683316-973673baf926?auto=format&fit=crop&w=1350&q=80'); padding: 40px; border-radius: 15px; color: white; text-align: center; margin-bottom: 25px; }
    .hero-banner h1 { font-size: 32px !important; font-weight: 800 !important; color: white !important; }

    .section-header { color: #1e3a8a; border-bottom: 2px solid #1e3a8a; padding-bottom: 5px; margin-top: 20px; font-size: 20px; font-weight: 700; }
    .help-box { background-color: #f0f7ff; padding: 15px; border-left: 4px solid #3b82f6; border-radius: 5px; font-size: 14px; color: #333; margin-top: 5px; }

    .floating-container { position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 15px; z-index: 999999; }
    .float-btn { width: 55px; height: 55px; border-radius: 50%; box-shadow: 0 4px 15px rgba(0,0,0,0.2); display: flex; justify-content: center; align-items: center; background: white; transition: all 0.3s; border: 2.5px solid #eee; }
    .float-btn img { width: 35px; height: 35px; }
</style>
""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'otp_verified' not in st.session_state: st.session_state['otp_verified'] = False
if 'otp_sent' not in st.session_state: st.session_state['otp_sent'] = False

LOGO_URL = "logo_moi.png"

# ==========================================
# 1. HỆ THỐNG ĐĂNG NHẬP
# ==========================================
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; color:#1e3a8a; font-weight:800; font-size:28px;">BULKMAIL PRO</p>', unsafe_allow_html=True)
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
                    st.session_state['current_user'] = log_user
                    st.session_state['logged_in'] = True
                    st.rerun()
                else: st.error("❌ Sai tài khoản hoặc mật khẩu!")

        with tab_reg:
            reg_user = st.text_input("Tên đăng nhập mới", key="reg_u")
            reg_email = st.text_input("Email khôi phục", key="reg_e")
            reg_pwd = st.text_input("Mật khẩu", type="password", key="reg_p")
            if st.button("TẠO TÀI KHOẢN", use_container_width=True):
                if not reg_user or not reg_email or not reg_pwd:
                    st.warning("⚠️ Điền đủ thông tin!")
                elif reg_user in users_db:
                    st.error("❌ Username đã tồn tại!")
                else:
                    save_user_api(reg_user, hash_password(reg_pwd), reg_email)
                    st.success("✅ Đăng ký thành công!")

        with tab_forgot:
            if not st.session_state['otp_verified']:
                fg_user = st.text_input("Nhập Username", key="fg_u")
                fg_email = st.text_input("Nhập Email đăng ký", key="fg_e")
                if st.button("GỬI MÃ OTP", use_container_width=True):
                    if fg_user in users_db and users_db[fg_user].get("email") == fg_email:
                        otp = generate_otp()
                        if reset_password_api(fg_user, fg_email, hash_password(otp), True):
                            if send_otp_email(fg_email, fg_user, otp):
                                st.session_state['otp_sent'] = True
                                st.success(f"✅ Đã gửi OTP tới {fg_email}")
                if st.session_state['otp_sent']:
                    input_otp = st.text_input("Nhập mã OTP 6 số:", max_chars=6)
                    if st.button("XÁC THỰC MÃ"):
                        u_info = load_users().get(fg_user)
                        if u_info and u_info.get("password") == hash_password(input_otp):
                            st.session_state['otp_verified'] = True
                            st.session_state['target_user'] = fg_user
                            st.rerun()
            else:
                new_p = st.text_input("Mật khẩu mới", type="password")
                if st.button("ĐỔI MẬT KHẨU"):
                    u_db = load_users()
                    target = st.session_state['target_user']
                    if reset_password_api(target, u_db[target]['email'], hash_password(new_p), False):
                        st.session_state['otp_verified'] = False
                        st.success("✅ Thành công! Hãy đăng nhập.")
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 2. DASHBOARD CHÍNH
# ==========================================
else:
    head_col1, head_col2 = st.columns([6, 1])
    head_col1.markdown(f"### 👋 Xin chào, **{st.session_state['current_user']}**")
    if head_col2.button("🚪 Đăng xuất", use_container_width=True):
        st.session_state['logged_in'] = False; st.rerun()

    st.markdown('<div class="hero-banner"><h1>BULKMAIL PRO</h1><p>Giải pháp Email Marketing chuyên nghiệp</p></div>', unsafe_allow_html=True)

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown('<div class="section-header">1. Cấu hình Tài khoản</div>', unsafe_allow_html=True)
        s_name = st.text_input("Tên hiển thị:", value=st.session_state.get('s_name', ""))
        s_mail = st.text_input("Email gửi (Gmail):", value=st.session_state.get('s_email', ""))
        raw_pass = st.text_input("App Password (16 ký tự):", type="password", value=st.session_state.get('s_pwd', ""))
        s_pass = raw_pass.replace(" ", "").strip()
        
        with st.expander("❓ Hướng dẫn lấy mật khẩu ứng dụng"):
            st.markdown("""<div class="help-box">1. Vào Bảo mật Google > Bật Xác minh 2 bước.<br>2. Tìm 'Mật khẩu ứng dụng', tạo mã cho 'BulkMail' và copy 16 ký tự.</div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-header">2. Danh sách khách hàng</div>', unsafe_allow_html=True)
        up = st.file_uploader("Tải file .xlsx hoặc .csv", type=["csv", "xlsx"])
        df = None
        if up:
            df = pd.read_excel(up) if up.name.endswith('xlsx') else pd.read_csv(up)
            st.success(f"✅ Đã nhận {len(df)} khách hàng")
        attachments = st.file_uploader("Đính kèm file", accept_multiple_files=True)

    with col_right:
        st.markdown('<div class="section-header">3. Nội dung Email</div>', unsafe_allow_html=True)
        subject = st.text_input("Tiêu đề thư:")
        content = st.text_area("Nội dung (dùng {{name}}):", height=230, value="Chào {{name}},")
        
        with st.expander("👁️ Xem trước"):
            # Tìm cột tên khách linh hoạt
            n_col = next((c for c in df.columns if c.lower() in ['name', 'tên', 'khách hàng']), None) if df is not None else None
            ex_name = str(df.iloc[0][n_col]) if n_col and not df.empty else "Quý khách"
            st.markdown(f"<div style='padding:15px; border:1px solid #ddd; background:white;'>{content.replace('{{name}}', ex_name).replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
        
        delay = st.number_input("Khoảng nghỉ (giây):", value=5, min_value=1)

    st.markdown("---")
    u_data = load_users().get(st.session_state['current_user'], {})
    new_tk = st.sidebar.text_input("Telegram Token:", value=u_data.get("tele_token", ""), type="password")
    new_id = st.sidebar.text_input("Telegram Chat ID:", value=u_data.get("tele_chat_id", ""))
    if st.sidebar.button("💾 Lưu Telegram"):
        save_config_api(st.session_state['current_user'], new_tk, new_id)
        st.sidebar.success("✅ Đã lưu!")

    st.warning("⚠️ **Lưu ý:** Chỉ nên gửi từ **200 - 300 email mỗi ngày** để an toàn cho tài khoản.")

    if st.button("▶ BẮT ĐẦU CHIẾN DỊCH", type="primary", use_container_width=True):
        if df is not None and s_mail and s_pass:
            e_col = next((c for c in df.columns if c.lower() in ['email', 'mail']), None)
            if not e_col: st.error("❌ File thiếu cột Email!")
            else:
                progress = st.progress(0); log = st.expander("📋 Nhật ký", expanded=True)
                send_tele_msg(new_tk, new_id, f"🚀 Bắt đầu chiến dịch: {st.session_state['current_user']}")
                success_list = []; error_list = []
                
                for index, row in df.iterrows():
                    target_email = str(row.get(e_col, "")).strip()
                    n_col = next((c for c in df.columns if c.lower() in ['name', 'tên', 'khách hàng']), None)
                    target_name = str(row.get(n_col, "Quý khách")) if n_col else "Quý khách"
                    
                    try:
                        msg = MIMEMultipart()
                        msg['From'] = f"{s_name} <{s_mail}>"; msg['To'] = target_email; msg['Subject'] = subject
                        msg.attach(MIMEText(content.replace("{{name}}", target_name).replace("\n", "<br>"), 'html'))
                        if attachments:
                            for f in attachments:
                                part = MIMEBase('application', "octet-stream")
                                part.set_payload(f.read()); encoders.encode_base64(part)
                                part.add_header('Content-Disposition', f'attachment; filename={f.name}')
                                msg.attach(part); f.seek(0)
                        
                        # Sử dụng SSL cổng 465 để vượt chặn
                        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=15) as server:
                            server.login(s_mail, s_pass)
                            server.send_message(msg)
                        success_list.append(target_email); log.write(f"✅ Thành công: {target_email}")
                    except Exception as e:
                        error_list.append(target_email); log.write(f"❌ Lỗi {target_email}: {e}")
                    progress.progress((index + 1) / len(df)); time.sleep(delay)
                
                # Gửi báo cáo Telegram
                csv_buf = io.BytesIO()
                pd.DataFrame({"Email": success_list + error_list, "Kết quả": ["Thành công"]*len(success_list) + ["Lỗi"]*len(error_list)}).to_csv(csv_buf, index=False, encoding='utf-8-sig')
                send_tele_msg(new_tk, new_id, f"📊 Tổng kết: {len(success_list)} thành công, {len(error_list)} lỗi.")
                send_tele_file(new_tk, new_id, csv_buf.getvalue(), "bao_cao.csv")
                st.success("🎉 Hoàn tất chiến dịch!"); st.download_button("📥 Tải báo cáo", data=csv_buf.getvalue(), file_name="bao_cao.csv")
        else: st.error("⚠️ Điền đủ thông tin!")

# NÚT LIÊN HỆ
st.markdown("""
<div class="floating-container">
    <a href="https://zalo.me/0935748199" target="_blank" class="float-btn" style="border: 2.5px solid #0068ff;"><img src="https://upload.wikimedia.org/wikipedia/commons/9/91/Icon_of_Zalo.svg"></a>
    <a href="https://t.me/BulkMail_Pro" target="_blank" class="float-btn" style="border: 2.5px solid #229ED9;"><img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg"></a>
</div>
""", unsafe_allow_html=True)
