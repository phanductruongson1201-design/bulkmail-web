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

# 1. Cấu hình trang Web
st.set_page_config(page_title="BulkMail Pro - Trường Sơn", page_icon="🔵", layout="wide")

# ==========================================
# API CƠ SỞ DỮ LIỆU & HỆ THỐNG
# ==========================================
DB_URL = st.secrets.get("DB_URL", "")

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

def send_tele_file(token, chat_id, file_content, file_name):
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendDocument"
            files = {'document': (file_name, file_content)}
            requests.post(url, data={'chat_id': chat_id}, files=files, timeout=10)
        except: pass

# ==========================================
# GIAO DIỆN CSS (Tối ưu hóa Header)
# ==========================================
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%); }
    .auth-box { max-width: 450px; margin: auto; padding: 40px; background: white; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
    .stButton>button { background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%) !important; color: white !important; border-radius: 8px; font-weight: 600; }
    
    /* Header chào mừng và đăng xuất */
    .user-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 20px;
        background: rgba(255, 255, 255, 0.6);
        border-radius: 10px;
        margin-bottom: 20px;
        border: 1px solid #ddd;
    }
    
    .logo-container { display: flex; justify-content: center; margin-bottom: 20px; }
    .logo-container img { border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border: 2px solid white; }
    .preview-box { padding: 15px; background: #ffffff; border: 1px solid #ddd; border-radius: 8px; margin-top: 10px; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False

LOGO_URL = "logo_moi.png"

# ==========================================
# 1. ĐĂNG NHẬP
# ==========================================
if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        try: st.image(LOGO_URL, width=250)
        except: st.info("BulkMail Pro")
        log_user = st.text_input("Username")
        log_pwd = st.text_input("Password", type="password")
        if st.button("ĐĂNG NHẬP", use_container_width=True):
            users_db = load_users()
            u_data = users_db.get(log_user)
            if u_data and u_data.get("password") == hash_password(log_pwd):
                st.session_state['current_user'] = log_user
                st.session_state['logged_in'] = True
                st.rerun()
            else: st.error("❌ Thông tin sai!")
        st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 2. DASHBOARD CHÍNH
# ==========================================
else:
    # --- HEADER CHÀO MỪNG VÀ NÚT ĐĂNG XUẤT ---
    head_col1, head_col2 = st.columns([6, 1])
    with head_col1:
        st.markdown(f"### 👋 Xin chào, **{st.session_state['current_user']}**")
    with head_col2:
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state['logged_in'] = False
            st.rerun()

    # LOGO CĂN GIỮA
    c_l1, c_l2, c_l3 = st.columns([1, 2, 1])
    with c_l2:
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        try: st.image(LOGO_URL, width=400)
        except: st.info("Dashboard")
        st.markdown('</div>', unsafe_allow_html=True)

    col_left, col_right = st.columns(2)
    
    with col_left:
        st.header("1. Cấu hình Gửi")
        s_name = st.text_input("Tên hiển thị:", value=st.session_state.get('s_name', ""))
        s_mail = st.text_input("Email Gmail:", value=st.session_state.get('s_email', ""))
        s_pass = st.text_input("App Password:", type="password", value=st.session_state.get('s_pwd', ""))
        st.session_state['s_name'], st.session_state['s_email'], st.session_state['s_pwd'] = s_name, s_mail, s_pass

        up = st.file_uploader("Danh sách Excel", type=["csv", "xlsx"])
        df = None
        if up:
            df = pd.read_excel(up) if up.name.endswith('xlsx') else pd.read_csv(up)
            st.success(f"✅ {len(df)} liên hệ.")
        attachments = st.file_uploader("File đính kèm thư", accept_multiple_files=True)

    with col_right:
        st.header("2. Nội dung thư")
        subject = st.text_input("Tiêu đề:")
        raw_body = st.text_area("Nội dung (Gõ xuống dòng bình thường):", height=200, value="Chào {{name}},\n\nĐây là nội dung thư mẫu.\nChúc bạn một ngày tốt lành!")
        
        # Chuyển đổi dấu xuống dòng (\n) thành thẻ HTML (<br>)
        body = raw_body.replace("\n", "<br>")
        
        with st.expander("🔍 Xem trước thực tế", expanded=True):
            p_text = body
            if df is not None and not df.empty and "name" in df.columns:
                p_text = p_text.replace("{{name}}", str(df.iloc[0]["name"]))
            st.markdown(f"**Tiêu đề:** {subject}")
            st.markdown(f'<div class="preview-box">{p_text}</div>', unsafe_allow_html=True)
        
        delay = st.number_input("Nghỉ (giây):", value=5, min_value=1)

    # TELEGRAM CONFIG
    st.markdown("---")
    users_db = load_users()
    u_data = users_db.get(st.session_state['current_user'], {})
    t_tk = u_data.get("tele_token", ""); t_id = u_data.get("tele_chat_id", "")
    with st.expander("🔔 Gửi thông báo về telegram ( có thể thêm hoặc không)"):
        new_tk = st.text_input("Bot Token:", value=t_tk, type="password")
        new_id = st.text_input("Chat ID:", value=t_id)
        if st.button("💾 Lưu cấu hình"):
            if save_config_api(st.session_state['current_user'], new_tk, new_id):
                st.success("✅ Đã lưu!"); time.sleep(1); st.rerun()

    # ==========================================
    # TIẾN TRÌNH GỬI
    # ==========================================
    if st.button("▶ BẮT ĐẦU CHIẾN DỊCH", type="primary", use_container_width=True):
        if df is not None and s_mail and s_pass:
            progress_bar = st.progress(0)
            log_expander = st.expander("📋 Nhật ký trực tiếp", expanded=True)
            
            start_msg = f"🚀 <b>CHIẾN DỊCH BẮT ĐẦU</b>\n👤 User: {st.session_state['current_user']}\n📧 Quy mô: {len(df)} mail"
            send_tele_msg(t_tk, t_id, start_msg)

            success_list = []; error_list = []

            for index, row in df.iterrows():
                target_email = row.get('email')
                target_name = row.get('name', 'Khách hàng')
                
                try:
                    msg = MIMEMultipart()
                    msg['From'] = f"{s_name} <{s_mail}>"; msg['To'] = target_email; msg['Subject'] = subject
                    
                    final_html = f"""
                    <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                        {body.replace("{{name}}", str(target_name))}
                    </div>
                    """
                    msg.attach(MIMEText(final_html, 'html'))
                    
                    if attachments:
                        for f in attachments:
                            part = MIMEBase('application', "octet-stream")
                            part.set_payload(f.read()); encoders.encode_base64(part)
                            part.add_header('Content-Disposition', f'attachment; filename={f.name}')
                            msg.attach(part); f.seek(0)

                    server = smtplib.SMTP("smtp.gmail.com", 587); server.starttls()
                    server.login(s_mail, s_pass); server.send_message(msg); server.quit()
                    
                    success_list.append(target_email)
                    with log_expander: st.write(f"✅ {target_email}")
                except Exception as e:
                    error_list.append(f"{target_email} ({str(e)})")
                    with log_expander: st.write(f"❌ {target_email}: {str(e)}")

                progress_bar.progress((index + 1) / len(df))
                time.sleep(delay)

            # Tổng kết và Gửi Telegram
            final_df = pd.DataFrame({"Email": success_list + [e.split()[0] for e in error_list], "Trạng thái": ["Thành công"]*len(success_list) + ["Lỗi"]*len(error_list)})
            csv_buffer = io.BytesIO()
            final_df.to_csv(csv_buffer, index=False, encoding='utf-8-sig')
            
            report_msg = f"📊 <b>TỔNG KẾT</b>\n✅ Thành công: {len(success_list)}\n❌ Thất bại: {len(error_list)}"
            send_tele_msg(t_tk, t_id, report_msg)
            send_tele_file(t_tk, t_id, csv_buffer.getvalue(), f"Bao_cao_{st.session_state['current_user']}.csv")

            st.success("🎉 Hoàn tất!")
            st.download_button("📥 Tải báo cáo", data=csv_buffer.getvalue(), file_name="ket_qua.csv")
            
        else: st.error("Thiếu cấu hình!")

# NÚT ZALO
st.markdown('<div style="position:fixed;bottom:20px;right:20px;z-index:99"><a href="https://zalo.me/0935748199"><img src="https://cdn.haitrieu.com/wp-content/uploads/2022/01/Logo-Zalo-Arc.png" width="50"></a></div>', unsafe_allow_html=True)

