import streamlit as st
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import time
from datetime import datetime
import streamlit.components.v1 as components
import requests
import hashlib
import random
import string

# 1. Cấu hình trang Web
st.set_page_config(page_title="BulkMail Pro - SaaS Edition", page_icon="🔵", layout="wide")

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

def reset_password_api(username, email, new_password_hash):
    if not DB_URL: return False
    try:
        res = requests.post(DB_URL, json={"action": "reset", "username": username, "email": email, "new_password": new_password_hash}).json()
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
        msg['From'] = f"BulkMail System <{SYS_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = "Mật khẩu mới của bạn - BulkMail Pro"
        
        body = f"""
        <h3>Chào {username},</h3>
        <p>Bạn vừa yêu cầu cấp lại mật khẩu cho hệ thống BulkMail Pro.</p>
        <p>Mật khẩu đăng nhập mới của bạn là: <b style="color:red; font-size:18px;">{new_password}</b></p>
        <p>Vui lòng đăng nhập và bảo mật thông tin tài khoản.</p>
        """
        msg.attach(MIMEText(body, 'html'))
        
        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.starttls()
        s.login(SYS_EMAIL, SYS_PWD)
        s.send_message(msg)
        s.quit()
        return True
    except: return False

# ==========================================
# GIAO DIỆN CSS
# ==========================================
# ==========================================
# GIAO DIỆN CSS
# ==========================================
st.markdown("""
<style>
    /* 1. Nền tổng thể: Gradient xám trắng sang trọng và sạch sẽ */
    .stApp { 
        background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%); 
    }
    
    /* 2. Font chữ tiêu đề: Chuyên nghiệp, màu xanh đen hoàng gia */
    h1, h2, h3 { 
        color: #1a365d !important; 
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-weight: 700;
    }
    
    /* 3. Nút bấm: Đổ bóng 3D, Gradient xanh và hiệu ứng nổi lên khi di chuột */
    .stButton>button { 
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%) !important; 
        color: white !important; 
        border-radius: 8px; 
        border: none; 
        padding: 10px 24px; 
        font-weight: 600; 
        box-shadow: 0 4px 6px rgba(59, 130, 246, 0.25);
        transition: all 0.3s ease;
    }
    .stButton>button:hover { 
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(59, 130, 246, 0.35);
    }
    
    /* 4. Hộp Đăng nhập/Đăng ký: Hiệu ứng kính mờ (Glassmorphism) cực kỳ hiện đại */
    .auth-box { 
        max-width: 450px; 
        margin: 50px auto; 
        padding: 40px; 
        background: rgba(255, 255, 255, 0.85); 
        border-radius: 16px; 
        box-shadow: 0 10px 30px rgba(0,0,0,0.08); 
        border: 1px solid rgba(255, 255, 255, 0.5);
        backdrop-filter: blur(10px);
    }
    
    /* 5. Bo góc nhẹ cho các ô nhập liệu (Input) */
    .stTextInput>div>div>input {
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'current_user' not in st.session_state: st.session_state['current_user'] = ""

# ==========================================
# HỆ THỐNG ĐĂNG NHẬP / ĐĂNG KÝ / QUÊN MẬT KHẨU
# ==========================================
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        st.title("🔵 BulkMail Pro")
        
        tab_login, tab_register, tab_forgot = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký", "🔑 Quên mật khẩu"])
        users_db = load_users()

        with tab_login:
            log_user = st.text_input("Tên đăng nhập", key="log_user")
            log_pwd = st.text_input("Mật khẩu", type="password", key="log_pwd")
            if st.button("Đăng nhập", type="primary", use_container_width=True):
                if log_user in users_db and users_db[log_user].get("password") == hash_password(log_pwd):
                    st.session_state['logged_in'] = True
                    st.session_state['current_user'] = log_user
                    st.rerun()
                else:
                    st.error("❌ Tài khoản hoặc mật khẩu không chính xác!")

        with tab_register:
            reg_user = st.text_input("Tên đăng nhập", key="reg_user")
            reg_email = st.text_input("Email của bạn (Để khôi phục MK)", key="reg_email")
            reg_pwd = st.text_input("Mật khẩu", type="password", key="reg_pwd")
            reg_pwd2 = st.text_input("Nhập lại mật khẩu", type="password", key="reg_pwd2")
            if st.button("Đăng ký ngay", type="primary", use_container_width=True, key="btn_reg"):
                if not reg_user or not reg_pwd or not reg_email:
                    st.warning("Vui lòng điền đủ thông tin.")
                elif reg_user in users_db:
                    st.error("⚠️ Tên đăng nhập đã tồn tại!")
                elif reg_pwd != reg_pwd2:
                    st.error("⚠️ Mật khẩu không khớp!")
                else:
                    save_user(reg_user, hash_password(reg_pwd), reg_email)
                    st.success("🎉 Đăng ký thành công! Hãy chuyển sang Đăng nhập.")

        with tab_forgot:
            st.info("Hệ thống sẽ tạo mật khẩu mới và gửi về Email bạn đã đăng ký.")
            fg_user = st.text_input("Tên đăng nhập của bạn", key="fg_user")
            fg_email = st.text_input("Email đã đăng ký", key="fg_email")
            
            if st.button("Lấy lại mật khẩu", type="primary", use_container_width=True, key="btn_fg"):
                if not fg_user or not fg_email:
                    st.warning("Vui lòng nhập Tên đăng nhập và Email.")
                elif fg_user not in users_db or users_db[fg_user].get("email") != fg_email:
                    st.error("❌ Tên đăng nhập hoặc Email không khớp với dữ liệu hệ thống!")
                else:
                    with st.spinner("Đang xử lý và gửi email..."):
                        new_pass = generate_random_password()
                        if reset_password_api(fg_user, fg_email, hash_password(new_pass)):
                            if send_recovery_email(fg_email, fg_user, new_pass):
                                st.success(f"✅ Đã gửi mật khẩu mới vào hòm thư {fg_email}. Vui lòng kiểm tra (cả hộp thư Spam).")
                            else:
                                st.error("❌ Đã đổi mật khẩu nhưng gặp lỗi khi gửi Email. Báo cho Admin!")
                        else:
                            st.error("❌ Lỗi hệ thống khi cập nhật mật khẩu.")
                            
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# GIAO DIỆN CHÍNH (SAU KHI ĐĂNG NHẬP)
# ==========================================
else:
    col_space, col_user, col_logout = st.columns([6, 2, 1])
    with col_user: st.write(f"👤 Chào mừng, **{st.session_state['current_user']}**!")
    with col_logout:
        if st.button("🚪 Đăng xuất"):
            st.session_state['logged_in'] = False
            st.session_state['current_user'] = ""
            st.rerun()

    st.title("🔵 BulkMail Pro – Trình Quản Lý Email Marketing")
    st.info("💡 Bạn đang ở giao diện gửi Email chính thức.")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("1. Cấu hình Máy chủ & Tài khoản")
        sender_name = st.text_input("Tên hiển thị người gửi:")
        sender_email = st.text_input("Email gửi của bạn:")
        app_password = st.text_input("App Password của bạn:", type="password")
        
        c1, c2 = st.columns(2)
        with c1: smtp_server = st.text_input("SMTP Server:", value="smtp.gmail.com")
        with c2: smtp_port = st.text_input("Port:", value="587")

        st.header("2. Dữ liệu Khách hàng")
        uploaded_file = st.file_uploader("Kéo thả file .csv hoặc .xlsx", type=["csv", "xlsx"])
        
        df = None
        if uploaded_file is not None:
            try:
                if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
                else: df = pd.read_excel(uploaded_file)
                df.columns = df.columns.str.strip().str.lower()
                if 'email' not in df.columns: st.error("Lỗi: File thiếu cột 'email'.")
                else:
                    df = df.dropna(subset=['email'])
                    st.success(f"✅ Đã tải {len(df)} liên hệ.")
            except Exception as e: st.error(f"Lỗi: {e}")

        uploaded_attachments = st.file_uploader("Chọn file đính kèm", accept_multiple_files=True)

    with col2:
        st.header("4. Biên soạn Nội dung")
        subject = st.text_input("Tiêu đề:")
        body = st.text_area("Nội dung (HTML) - Biến: {{tên_cột}}", height=150, value="Kính chào {{name}},<br><br>...")

        with st.expander("👁️ Xem trước hiển thị Email"):
            components.html(body, height=200, scrolling=True)

        st.header("5. Cấu hình Nâng cao & Báo cáo")
        delay = st.number_input("Khoảng nghỉ (giây):", min_value=1, max_value=60, value=5)
        
        st.markdown("---")
        with st.expander("🔔 Nhấn vào đây để nhận báo cáo qua Telegram (Tùy chọn)", expanded=False):
            st.info("Nhập API Telegram của riêng bạn để hệ thống báo cáo khi gửi xong.")
            
            # Tải cấu hình đã lưu của khách hàng
            users_db = load_users()
            current_user_data = users_db.get(st.session_state['current_user'], {})
            saved_token = current_user_data.get("tele_token", "")
            saved_chat_id = current_user_data.get("tele_chat_id", "")

            t1, t2 = st.columns(2)
            with t1:
                tele_token = st.text_input("Bot Token (Của bạn):", value=saved_token, type="password")
            with t2:
                tele_chat_id = st.text_input("Chat ID (Của bạn):", value=saved_chat_id)
            
            # Nút lưu cấu hình
            if st.button("💾 Lưu cấu hình Telegram", use_container_width=True):
                if save_config_api(st.session_state['current_user'], tele_token, tele_chat_id):
                    st.success("✅ Đã lưu cấu hình thành công! Lần đăng nhập sau sẽ được tự động điền.")
                else:
                    st.error("❌ Có lỗi xảy ra khi lưu. Vui lòng thử lại.")

    st.markdown("---")
    st.header("🚀 6. Kích hoạt Chiến dịch")

    if st.button("▶ BẮT ĐẦU GỬI", type="primary", use_container_width=True):
        if df is None or len(df) == 0:
            st.error("Vui lòng tải lên danh sách email!")
        elif not sender_email or not app_password or not subject or not body:
            st.error("Vui lòng điền đủ thông tin SMTP, tiêu đề và nội dung!")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            log_area = st.empty()
            sent_count, error_count = 0, 0
            total_emails = len(df)
            log_messages = []
            
            try:
                smtp = smtplib.SMTP(smtp_server, int(smtp_port.strip()))
                smtp.starttls()
                smtp.login(sender_email, app_password)
                
                for index, row in df.iterrows():
                    recipient = str(row['email']).strip()
                    if not recipient or recipient.lower() == 'nan':
                        total_emails -= 1
                        continue
                        
                    p_subj, p_body = subject, body
                    for col in df.columns:
                        val = str(row[col]) if pd.notna(row[col]) else ""
                        p_subj = p_subj.replace(f"{{{{{col}}}}}", val)
                        p_body = p_body.replace(f"{{{{{col}}}}}", val)
                        
                    msg = MIMEMultipart()
                    msg['From'] = f"{sender_name} <{sender_email}>" if sender_name else sender_email
                    msg['To'] = recipient
                    msg['Subject'] = p_subj
                    msg.attach(MIMEText(p_body, 'html'))
                    
                    try:
                        smtp.send_message(msg)
                        sent_count += 1
                        log_messages.append(f"✅ Gửi thành công: {recipient}")
                    except Exception as e:
                        error_count += 1
                        log_messages.append(f"❌ Lỗi ({recipient}): {str(e)}")
                        
                    progress_bar.progress(min((sent_count + error_count) / max(total_emails, 1), 1.0))
                    status_text.write(f"Đã gửi: {sent_count} | Lỗi: {error_count} | Tổng: {total_emails}")
                    log_area.text("\n".join(log_messages[-5:]))
                    time.sleep(delay)
                    
                smtp.quit()
                st.success(f"🎉 Hoàn tất! Đã gửi {sent_count}/{total_emails} email.")
                
                # Bắn Telegram cho khách hàng nếu họ có nhập
                if tele_token and tele_chat_id:
                    try:
                        st.info("Đang đẩy dữ liệu về Telegram của bạn...")
                        msg_text = f"🚀 **Chiến dịch BulkMail của {st.session_state['current_user']} đã xong!**\n\n📊 **Tổng kết:**\n- Tổng số email: `{total_emails}`\n- ✅ Thành công: `{sent_count}`\n- ❌ Thất bại: `{error_count}`"
                        requests.post(f"https://api.telegram.org/bot{tele_token}/sendMessage", data={"chat_id": tele_chat_id, "text": msg_text, "parse_mode": "Markdown"})
                        st.success("✅ Đã gửi báo cáo thành công qua Telegram của bạn!")
                    except Exception as e:
                        st.error(f"⚠️ Không thể gửi Telegram. Vui lòng kiểm tra lại Token/Chat ID. Lỗi: {e}")

            except Exception as e:
                st.error(f"❌ Lỗi SMTP: {e}")

