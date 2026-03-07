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
# GIAO DIỆN CSS (CHỈN CHU & NỔI BẬT)
# ==========================================
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%); }
    .auth-box { max-width: 480px; margin: auto; padding: 30px; background: white; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
    .stButton>button { background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%) !important; color: white !important; border-radius: 8px; font-weight: 600; }
    
    .welcome-text { 
        text-align: center; color: #1e3a8a; font-weight: 800; margin-bottom: 20px; font-size: 32px; 
        text-transform: uppercase; letter-spacing: 1px; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
    }

    .logo-container { display: flex; justify-content: center; margin-bottom: 20px; }
    .logo-container img { border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border: 2px solid #fff; }
    .preview-box { padding: 25px; background: #ffffff; border: 1px solid #e0e0e0; border-radius: 10px; margin-top: 10px; line-height: 1.8; }
    
    .dashboard-title { color: #1e3a8a; font-size: 32px; font-weight: 800; margin-bottom: 5px; }
    .section-header { color: #1e3a8a; border-bottom: 2px solid #1e3a8a; padding-bottom: 5px; margin-top: 20px; font-size: 20px; font-weight: 700; }
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
        try: st.image(LOGO_URL, width=320)
        except: st.info("🎯 TRƯỜNG SƠN - DỊCH VỤ HỖ TRỢ MXH")
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

        with tab_reg:
            reg_user = st.text_input("Username mới", key="reg_u")
            reg_email = st.text_input("Email khôi phục", key="reg_e")
            reg_pwd = st.text_input("Mật khẩu", type="password", key="reg_p")
            if st.button("ĐĂNG KÝ NGAY", use_container_width=True):
                if reg_user in users_db: st.error("Tên này đã tồn tại!")
                else:
                    save_user_api(reg_user, hash_password(reg_pwd), reg_email)
                    st.success("✅ Đã tạo tài khoản thành công!")

        with tab_forgot:
            if not st.session_state['otp_verified']:
                fg_user = st.text_input("Username", key="fg_u")
                fg_email = st.text_input("Email đăng ký", key="fg_e")
                if st.button("GỬI MÃ OTP", use_container_width=True):
                    if fg_user in users_db and users_db[fg_user].get("email") == fg_email:
                        otp = generate_otp()
                        if reset_password_api(fg_user, fg_email, hash_password(otp), True):
                            if send_otp_email(fg_email, fg_user, otp): st.success("✅ Mã OTP đã gửi!")
                input_otp = st.text_input("Nhập mã OTP:", max_chars=6, key="otp_i")
                if st.button("XÁC THỰC", use_container_width=True):
                    u_info = users_db.get(fg_user)
                    if u_info and u_info.get("password") == hash_password(input_otp):
                        st.session_state['otp_verified'] = True
                        st.session_state['current_user'] = fg_user
                        st.rerun()
            else:
                new_p = st.text_input("Mật khẩu mới", type="password", key="new_p")
                if st.button("ĐỔI MẬT KHẨU", use_container_width=True):
                    u_db = load_users()
                    if reset_password_api(st.session_state['current_user'], u_db[st.session_state['current_user']]['email'], hash_password(new_p), False):
                        st.session_state['otp_verified'] = False
                        st.session_state['logged_in'] = True
                        st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 2. DASHBOARD CHÍNH (GIAO DIỆN 5 BƯỚC)
# ==========================================
else:
    head_col1, head_col2 = st.columns([6, 1])
    with head_col1:
        st.markdown(f"### 👋 Xin chào, **{st.session_state['current_user']}**")
    with head_col2:
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state['logged_in'] = False
            st.rerun()

    c_l1, c_l2, c_l3 = st.columns([1, 1.8, 1])
    with c_l2:
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        try: st.image(LOGO_URL, width=400)
        except: st.info("BulkMail Pro")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="dashboard-title">🔵 BulkMail Pro – Trình Quản Lý Email Marketing</div>', unsafe_allow_html=True)
    st.info("💡 Hệ thống gửi email hàng loạt cá nhân hóa. Vui lòng sử dụng cho danh sách liên hệ hợp pháp.")

    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown('<div class="section-header">1. Cấu hình Máy chủ & Tài khoản</div>', unsafe_allow_html=True)
        s_name = st.text_input("Tên hiển thị người gửi (VD: Công ty ABC):", value=st.session_state.get('s_name', ""))
        s_mail = st.text_input("Email Gmail dùng để gửi:", value=st.session_state.get('s_email', ""))
        s_pass = st.text_input("Mật khẩu ứng dụng (App Password):", type="password", value=st.session_state.get('s_pwd', ""))
        
        st.markdown('<div class="section-header">2. Chữ ký Email (Cuối thư)</div>', unsafe_allow_html=True)
        s_sign = st.text_area("Thông tin liên hệ, SĐT, Zalo...:", value=st.session_state.get('s_sign', "Trân trọng,\nĐội ngũ hỗ trợ Trường Sơn"), height=100)
        
        st.session_state['s_name'], st.session_state['s_email'], st.session_state['s_pwd'], st.session_state['s_sign'] = s_name, s_mail, s_pass, s_sign
        
        st.markdown('<div class="section-header">3. Dữ liệu Khách hàng</div>', unsafe_allow_html=True)
        up = st.file_uploader("Tải file danh sách (.csv, .xlsx)", type=["csv", "xlsx"])
        df = None
        if up:
            df = pd.read_excel(up) if up.name.endswith('xlsx') else pd.read_csv(up)
            st.success(f"✅ Đã nhận {len(df)} khách hàng.")
        attachments = st.file_uploader("Đính kèm file hoặc ảnh vào thư", accept_multiple_files=True)

    with col_right:
        st.markdown('<div class="section-header">4. Biên soạn Nội dung Email</div>', unsafe_allow_html=True)
        subject = st.text_input("Tiêu đề thư (Subject):", placeholder="Ví dụ: Thư ngỏ hợp tác từ Trường Sơn Marketing")
        raw_body = st.text_area(
            "Nội dung chính:", 
            height=250, 
            placeholder="Mẹo: Dùng {{name}} để hệ thống tự gọi tên khách hàng.",
            value="Kính chào Anh/Chị {{name}},\n\n(Ví dụ: Hệ thống sẽ tự đổi {{name}} thành tên thật của khách như Nguyễn Văn A...)\n\nNhập nội dung thư của bạn tại đây..."
        )
        
        body_html = raw_body.replace("\n", "<br>")
        sign_html = s_sign.replace("\n", "<br>")
        full_email_content = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.8; color: #333;">
            {body_html}
            <br><br>
            <div style="color: #666; border-top: 1px solid #eee; padding-top: 10px; font-size: 14px;">
                {sign_html}
            </div>
        </div>
        """
        with st.expander("👁️ Xem trước thực tế (Live Preview)", expanded=True):
            p_text = full_email_content
            example_name = "Nguyễn Văn A"
            if df is not None and not df.empty and "name" in df.columns:
                example_name = str(df.iloc[0]["name"])
            p_text = p_text.replace("{{name}}", f"<b style='color:#1e3a8a;'>{example_name}</b>")
            st.markdown(p_text, unsafe_allow_html=True)
        
        st.markdown('<div class="section-header">5. Thiết lập Gửi & Kiểm tra</div>', unsafe_allow_html=True)
        delay = st.number_input("Khoảng nghỉ giữa 2 email (giây):", value=5, min_value=1)

    st.markdown("---")
    users_db = load_users(); u_data = users_db.get(st.session_state['current_user'], {})
    t_tk = u_data.get("tele_token", ""); t_id = u_data.get("tele_chat_id", "")
    with st.expander("🔔 Nhận báo cáo kết quả qua Telegram"):
        new_tk = st.text_input("Bot Token:", value=t_tk, type="password", key="t_tk")
        new_id = st.text_input("Chat ID:", value=t_id, key="t_id")
        if st.button("💾 Lưu cấu hình Telegram"):
            if save_config_api(st.session_state['current_user'], new_tk, new_id):
                st.success("✅ Đã lưu cấu hình báo cáo Telegram!"); time.sleep(1); st.rerun()

    if st.button("▶ BẮT ĐẦU GỬI CHIẾN DỊCH", type="primary", use_container_width=True):
        if df is not None and s_mail and s_pass:
            progress_bar = st.progress(0); log_ex = st.expander("📋 Nhật ký chi tiết", expanded=True)
            send_tele_msg(t_tk, t_id, f"🚀 <b>CHIẾN DỊCH BẮT ĐẦU</b>\n👤 User: {st.session_state['current_user']}\n📧 Số lượng: {len(df)}")
            success_list = []; error_list = []
            for index, row in df.iterrows():
                try:
                    target_email = row.get('email'); target_name = row.get('name', 'Khách hàng')
                    msg = MIMEMultipart()
                    msg['From'] = f"{s_name} <{s_mail}>"; msg['To'] = target_email; msg['Subject'] = subject
                    msg.attach(MIMEText(full_email_content.replace("{{name}}", str(target_name)), 'html'))
                    if attachments:
                        for f in attachments:
                            part = MIMEBase('application', "octet-stream")
                            part.set_payload(f.read()); encoders.encode_base64(part)
                            part.add_header('Content-Disposition', f'attachment; filename={f.name}')
                            msg.attach(part); f.seek(0)
                    server = smtplib.SMTP("smtp.gmail.com", 587); server.starttls()
                    server.login(s_mail, s_pass); server.send_message(msg); server.quit()
                    success_list.append(target_email); log_ex.write(f"✅ Gửi thành công: {target_email}")
                except Exception as e:
                    error_list.append(f"{target_email}"); log_ex.write(f"❌ Lỗi gửi {target_email}: {str(e)}")
                progress_bar.progress((index + 1) / len(df)); time.sleep(delay)
            csv_buf = io.BytesIO(); pd.DataFrame({"Email": success_list + error_list, "Kết quả": ["Thành công"]*len(success_list) + ["Lỗi"]*len(error_list)}).to_csv(csv_buf, index=False, encoding='utf-8-sig')
            send_tele_msg(t_tk, t_id, f"📊 <b>TỔNG KẾT</b>\n✅ Thành công: {len(success_list)}\n❌ Lỗi: {len(error_list)}"); send_tele_file(t_tk, t_id, csv_buf.getvalue(), "bao_cao.csv")
            st.success("🎉 Chiến dịch hoàn tất!"); st.download_button("📥 Tải báo cáo", data=csv_buf.getvalue(), file_name="ket_qua.csv")
        else: st.error("⚠️ Vui lòng cung cấp đầy đủ thông tin!")

# NÚT ZALO
st.markdown('<div style="position:fixed;bottom:20px;right:20px;z-index:99"><a href="https://zalo.me/0935748199"><img src="https://cdn.haitrieu.com/wp-content/uploads/2022/01/Logo-Zalo-Arc.png" width="50"></a></div>', unsafe_allow_html=True)
