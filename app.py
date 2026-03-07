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

def save_config_api(username, tele_token, tele_chat_id):
    if not DB_URL: return False
    try:
        res = requests.post(DB_URL, json={"action": "update_config", "username": username, "tele_token": tele_token, "tele_chat_id": tele_chat_id}).json()
        return res.get("status") == "success"
    except: return False

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def send_tele_msg(token, chat_id, message):
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, data={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=5)
        except: pass

# ==========================================
# GIAO DIỆN CSS
# ==========================================
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%); }
    .auth-box { max-width: 450px; margin: auto; padding: 40px; background: white; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
    .stButton>button { background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%) !important; color: white !important; border-radius: 8px; border: none; font-weight: 600; }
    .logo-container { display: flex; justify-content: center; margin-bottom: 20px; }
    .logo-container img { border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border: 2px solid white; }
    .preview-box { padding: 15px; background: #f8f9fa; border-left: 5px solid #1e3a8a; border-radius: 5px; color: #333; margin-top: 10px; }
</style>
""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

LOGO_URL = "logo_moi.png"

# ==========================================
# 1. LOGIC ĐĂNG NHẬP
# ==========================================
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        try: st.image(LOGO_URL, width=250)
        except: st.warning("⚠️ Logo lỗi.")
        
        log_user = st.text_input("Username")
        log_pwd = st.text_input("Password", type="password")
        if st.button("ĐĂNG NHẬP", use_container_width=True):
            users_db = load_users()
            user_data = users_db.get(log_user)
            if user_data and user_data.get("password") == hash_password(log_pwd):
                st.session_state['current_user'] = log_user
                st.session_state['logged_in'] = True
                st.rerun()
            else: st.error("❌ Sai tài khoản!")
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 2. GIAO DIỆN CHÍNH
# ==========================================
else:
    # Header & Logo
    c_h1, c_h2 = st.columns([8, 1])
    with c_h2: 
        if st.button("Thoát"): 
            st.session_state['logged_in'] = False
            st.rerun()

    c_l1, c_l2, c_l3 = st.columns([1, 2, 1])
    with c_l2:
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        try: st.image(LOGO_URL, width=400)
        except: st.info("BulkMail Pro")
        st.markdown('</div>', unsafe_allow_html=True)

    col_left, col_right = st.columns(2)
    
    with col_left:
        st.header("1. Cấu hình Gửi")
        s_name = st.text_input("Tên hiển thị:", value=st.session_state.get('s_name', ""))
        s_mail = st.text_input("Email Gmail:", value=st.session_state.get('s_email', ""))
        s_pass = st.text_input("App Password:", type="password", value=st.session_state.get('s_pwd', ""))
        
        # Lưu vào session
        st.session_state['s_name'], st.session_state['s_email'], st.session_state['s_pwd'] = s_name, s_mail, s_pass

        up = st.file_uploader("Danh sách Excel", type=["csv", "xlsx"])
        df = None
        if up:
            df = pd.read_excel(up) if up.name.endswith('xlsx') else pd.read_csv(up)
            st.success(f"✅ {len(df)} liên hệ.")
        attachments = st.file_uploader("File đính kèm", accept_multiple_files=True)

    with col_right:
        st.header("2. Nội dung")
        subject = st.text_input("Tiêu đề:")
        body = st.text_area("Nội dung (HTML):", height=150, value="Chào {{name}},...")
        with st.expander("🔍 Xem trước"):
            p_text = body
            if df is not None and not df.empty and "name" in df.columns:
                p_text = p_text.replace("{{name}}", str(df.iloc[0]["name"]))
            st.markdown(f'<div class="preview-box">{p_text}</div>', unsafe_allow_html=True)
        delay = st.number_input("Nghỉ (giây):", value=5, min_value=1)

    # TELEGRAM CONFIG
    st.markdown("---")
    users_db = load_users()
    u_data = users_db.get(st.session_state['current_user'], {})
    with st.expander("🔔 Cấu hình Telegram"):
        t_tk = st.text_input("Bot Token:", value=u_data.get("tele_token", ""), type="password")
        t_id = st.text_input("Chat ID:", value=u_data.get("tele_chat_id", ""))
        if st.button("💾 Lưu Tele"):
            if save_config_api(st.session_state['current_user'], t_tk, t_id):
                st.success("✅ Đã lưu!"); time.sleep(1); st.rerun()

    # ==========================================
    # GỬI MAIL & BÁO CÁO TELEGRAM
    # ==========================================
    if st.button("▶ BẮT ĐẦU CHIẾN DỊCH", type="primary", use_container_width=True):
        if df is not None and s_mail and s_pass:
            progress_bar = st.progress(0)
            log_container = st.expander("📋 Nhật ký chi tiết", expanded=True)
            
            # Gửi thông báo bắt đầu lên Tele
            start_msg = f"🚀 <b>CHIẾN DỊCH MỚI</b>\n👤 User: {st.session_state['current_user']}\n📧 Số lượng: {len(df)} mail\n⏰ Bắt đầu lúc: {time.strftime('%H:%M:%S')}"
            send_tele_msg(t_tk, t_id, start_msg)

            success_list = []
            error_list = []

            for index, row in df.iterrows():
                target_email = row.get('email')
                target_name = row.get('name', 'Khách hàng')
                
                try:
                    msg = MIMEMultipart()
                    msg['From'] = f"{s_name} <{s_mail}>"; msg['To'] = target_email; msg['Subject'] = subject
                    msg.attach(MIMEText(body.replace("{{name}}", str(target_name)), 'html'))
                    
                    if attachments:
                        for f in attachments:
                            part = MIMEBase('application', "octet-stream")
                            part.set_payload(f.read()); encoders.encode_base64(part)
                            part.add_header('Content-Disposition', f'attachment; filename={f.name}')
                            msg.attach(part); f.seek(0)

                    server = smtplib.SMTP("smtp.gmail.com", 587); server.starttls()
                    server.login(s_mail, s_pass); server.send_message(msg); server.quit()
                    
                    success_list.append(target_email)
                    with log_container: st.write(f"✅ {target_email}: Xong")
                except Exception as e:
                    error_list.append(f"{target_email} ({str(e)})")
                    with log_container: st.write(f"❌ {target_email}: Lỗi")

                progress_bar.progress((index + 1) / len(df))
                time.sleep(delay)

            # --- GỬI TỔNG KẾT CHI TIẾT VỀ TELEGRAM ---
            report_msg = f"📊 <b>KẾT QUẢ CHIẾN DỊCH</b>\n"
            report_msg += f"✅ Thành công: {len(success_list)}\n"
            report_msg += f"❌ Thất bại: {len(error_list)}\n\n"
            
            if error_list:
                report_msg += "⚠️ <b>Danh sách lỗi:</b>\n"
                report_msg += "\n".join([f"- {err}" for err in error_list[:10]]) # Gửi tối đa 10 lỗi đầu tiên
                if len(error_list) > 10: report_msg += "\n..."

            send_tele_msg(t_tk, t_id, report_msg)
            
            st.success(f"🎉 Hoàn tất! Đã báo cáo kết quả về Telegram của bạn.")
            # Hiển thị bảng kết quả cho phép tải về
            final_df = pd.DataFrame({"Email": success_list + [e.split()[0] for e in error_list], 
                                    "Kết quả": ["Thành công ✅"]*len(success_list) + ["Lỗi ❌"]*len(error_list)})
            st.download_button("📥 Tải báo cáo Excel", data=final_df.to_csv(index=False).encode('utf-8-sig'), file_name="report.csv")
            
        else: st.error("Thiếu thông tin cấu hình!")

# NÚT ZALO
st.markdown('<div style="position:fixed;bottom:20px;right:20px;z-index:99"><a href="https://zalo.me/0935748199"><img src="https://cdn.haitrieu.com/wp-content/uploads/2022/01/Logo-Zalo-Arc.png" width="50"></a></div>', unsafe_allow_html=True)
