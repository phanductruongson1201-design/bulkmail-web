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

# 1. Cấu hình trang Web (Bật chế độ Rộng & Mở sẵn thanh bên)
st.set_page_config(page_title="BulkMail Pro - Trường Sơn", page_icon="🔵", layout="wide", initial_sidebar_state="expanded")

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
# GIAO DIỆN CSS: CHUẨN DASHBOARD HIỆN ĐẠI
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
    
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header {visibility: hidden !important;}
    .stDeployButton {display: none !important;}
    [data-testid="manage-app-button"] {display: none !important;}
    [data-testid="viewerBadge"] {display: none !important;}
    iframe[title="Streamlit Toolbar"] {display: none !important;}

    /* Nền xám nhạt chuyên nghiệp */
    .stApp { background-color: #f8fafc; }
    
    /* Box đăng nhập */
    .auth-box { max-width: 450px; margin: 40px auto; padding: 40px; background: white; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.05); border: 1px solid #f1f5f9; }
    
    /* Nút bấm nổi bật */
    .stButton>button { background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%) !important; color: white !important; border-radius: 8px; font-weight: 600; padding: 10px 24px; transition: all 0.3s ease; border: none; letter-spacing: 0.5px;}
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 8px 15px rgba(59, 130, 246, 0.3); }

    /* Tiêu đề khối (Headers) */
    .block-header { color: #0f172a; font-size: 18px; font-weight: 700; margin-bottom: 15px; margin-top: 10px; border-left: 4px solid #3b82f6; padding-left: 10px; line-height: 1.2;}
    .sub-text { font-size: 14px; color: #64748b; margin-bottom: 15px; margin-top: -10px; }

    /* Logo Login */
    .logo-container { display: flex; justify-content: center; align-items: center; width: 100%; margin-bottom: 25px; }
    .logo-container img { width: 140px; height: 140px; border-radius: 50%; object-fit: cover; box-shadow: 0 4px 15px rgba(0,0,0,0.1); display: block; border: 3px solid white;}
    .alt-logo { width: 140px; height: 140px; border-radius: 50%; background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); color: white; display: flex; justify-content: center; align-items: center; font-weight: 800; font-size: 16px; text-align: center; border: 3px solid white; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }

    /* Alert Box Đẹp */
    .alert-pro { background-color: #eff6ff; border-left: 4px solid #3b82f6; padding: 16px; border-radius: 0 8px 8px 0; color: #1e293b; font-size: 14px; margin-bottom: 20px;}
    .alert-warn { background-color: #fffbeb; border-left: 4px solid #f59e0b; padding: 16px; border-radius: 0 8px 8px 0; color: #78350f; font-size: 14px; margin-bottom: 20px;}

    /* Metric Box Streamlit Override */
    [data-testid="stMetricValue"] { font-size: 24px !important; color: #1e40af !important; font-weight: 700 !important;}

    /* Nút liên hệ nổi */
    .floating-container { position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 12px; z-index: 999999; }
    .float-btn { width: 50px; height: 50px; border-radius: 50%; box-shadow: 0 4px 12px rgba(0,0,0,0.15); display: flex; justify-content: center; align-items: center; background: white; transition: 0.3s; }
    .float-btn:hover { transform: scale(1.1); }
    .float-btn img { width: 70%; height: 70%; object-fit: contain; }
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
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align:center; color:#1e40af; font-weight:800; margin-bottom:20px;">BULKMAIL PRO</h2>', unsafe_allow_html=True)
        
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
# 2. DASHBOARD CHÍNH (BỐ CỤC MỚI)
# ==========================================
else:
    # --- THANH BÊN (SIDEBAR): TẬP TRUNG CÀI ĐẶT ---
    with st.sidebar:
        st.markdown(f"<h3 style='color:#1e40af;'>👤 {st.session_state['current_user']}</h3>", unsafe_allow_html=True)
        st.markdown("<p style='font-size:13px; color:#64748b; margin-top:-10px;'>Trạng thái: Đang hoạt động 🟢</p>", unsafe_allow_html=True)
        if st.button("Đăng xuất", use_container_width=True):
            st.session_state["logged_in"] = False
            st.rerun()
            
        st.divider()
        st.markdown("### ⚙️ CẤU HÌNH MÁY CHỦ")
        st.session_state["s_name"] = st.text_input("Tên người gửi (Hiển thị):", value=st.session_state["s_name"])
        st.session_state["s_email"] = st.text_input("Email gửi (Gmail):", value=st.session_state["s_email"])
        st.session_state["s_pwd"] = st.text_input("App Password (16 ký tự):", type="password", value=st.session_state["s_pwd"])
        with st.expander("❓ Lấy App Password ở đâu?"):
            st.write("Vào Tài khoản Google > Bảo mật > Xác minh 2 bước > Mật khẩu ứng dụng. Tạo app tên BulkMail và copy mã 16 chữ cái dán vào trên.")

        st.divider()
        st.markdown("### 📝 CHỮ KÝ MẶC ĐỊNH")
        st.session_state["s_sign"] = st.text_area("Chữ ký tự động chèn vào cuối thư:", value=st.session_state["s_sign"], height=100)
        
        st.divider()
        st.markdown("### 🔔 BÁO CÁO TELEGRAM")
        u_data = load_users().get(st.session_state["current_user"], {})
        t_tk = u_data.get("tele_token", "")
        t_id = u_data.get("tele_chat_id", "")
        new_tk = st.text_input("Bot Token:", value=t_tk, type="password")
        new_id = st.text_input("Chat ID:", value=t_id)
        if st.button("Lưu cấu hình Telegram"):
            if save_config_api(st.session_state["current_user"], new_tk, new_id):
                st.success("Đã lưu!")
                time.sleep(1)
                st.rerun()

    # --- MÀN HÌNH LÀM VIỆC CHÍNH (MAIN WORKSPACE) ---
    st.markdown('<h1 style="color:#0f172a; margin-bottom: 0px;">Khởi tạo Chiến dịch Mới 🚀</h1>', unsafe_allow_html=True)
    st.markdown('<p style="color:#64748b; font-size: 16px; margin-bottom: 30px;">Tối ưu hóa quy trình tiếp cận khách hàng của bạn.</p>', unsafe_allow_html=True)

    # Hiển thị Metrics trực quan
    m1, m2, m3 = st.columns(3)
    m1.metric(label="Trạng thái cấu hình", value="Sẵn sàng" if st.session_state["s_email"] and st.session_state["s_pwd"] else "Chưa cấu hình")
    m2.metric(label="Khuyến nghị an toàn", value="200 - 300 Mail/Ngày")
    
    # Lấy delay vào biến để tính toán ở dòng metric 3
    delay = st.number_input("⏳ Thời gian nghỉ giữa mỗi Email (Giây):", value=15, min_value=1, help="Giả lập thao tác người thật. Càng lâu càng an toàn.")
    m3.metric(label="Khoảng nghỉ hiện tại", value=f"{delay} Giây")
    
    st.markdown("<hr style='margin: 10px 0 30px 0;'>", unsafe_allow_html=True)

    # KHỐI 1 & 2: Dữ liệu và Nội dung (Chia 2 cột)
    col_data, col_content = st.columns([1, 1.2], gap="large")
    
    with col_data:
        st.markdown('<div class="block-header">Bước 1: Nguồn Dữ liệu</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-text">Tải lên danh sách khách hàng của bạn.</div>', unsafe_allow_html=True)
        
        # File mẫu
        sample_df = pd.DataFrame({"email": ["khachhang@gmail.com", "vidu@gmail.com"]})
        try:
            excel_buf = io.BytesIO()
            with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
                sample_df.to_excel(writer, index=False, sheet_name="Danh_sach")
            dl_data = excel_buf.getvalue()
        except:
            dl_data = sample_df.to_csv(index=False).encode("utf-8-sig")
            
        st.download_button("📥 Tải File Mẫu (Excel)", data=dl_data, file_name="danh_sach_mau.xlsx")
        
        # Upload
        up = st.file_uploader("Tải tệp .csv hoặc .xlsx", type=["csv", "xlsx"])
        df = None
        if up:
            df = pd.read_excel(up) if up.name.endswith("xlsx") else pd.read_csv(up)
            st.success(f"✅ Hợp lệ! Đã nhận {len(df)} địa chỉ email.")
            
        st.markdown('<div class="block-header" style="margin-top: 30px;">Tệp đính kèm</div>', unsafe_allow_html=True)
        attachments = st.file_uploader("Gửi kèm Hợp đồng, Báo giá, Hình ảnh...", accept_multiple_files=True)

    with col_content:
        st.markdown('<div class="block-header">Bước 2: Soạn Thông điệp</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-text">Cá nhân hóa nội dung với biến {{name}}.</div>', unsafe_allow_html=True)
        
        subject = st.text_input("Tiêu đề chiến dịch:")
        raw_body = st.text_area("Nội dung văn bản:", height=250, value="Kính chào Anh/Chị {{name}},\n\nNhập nội dung thông điệp tại đây...")
        
        # Tiền xử lý nội dung
        body_html = raw_body.replace("\n", "<br>")
        sign_html = st.session_state["s_sign"].replace("\n", "<br>")
        full_email_content = f"<div style='font-family:Arial; line-height:1.8; color:#333;'>{body_html}<br><br><div style='color:#666; border-top:1px solid #eee; padding-top:10px;'>{sign_html}</div></div>"
        
        with st.expander("👁️ Mở rộng để Xem trước giao diện Email"):
            example_name = str(df.iloc[0]["name"]) if df is not None and not df.empty and "name" in df.columns else "Quý khách"
            st.markdown(f"<div style='padding:20px; border:1px solid #e2e8f0; border-radius:8px; background:white; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>{full_email_content.replace('{{name}}', f'<b style=\"color:#1e40af;\">{example_name}</b>')}</div>", unsafe_allow_html=True)

    st.markdown("<hr style='margin: 30px 0;'>", unsafe_allow_html=True)

    # KHỐI 3: VẬN HÀNH
    st.markdown('<div class="block-header">Bước 3: Vận hành Hệ thống</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="alert-warn">
        <b>🛡️ QUY TẮC BẢO VỆ TÀI KHOẢN (BẮT BUỘC):</b><br>
        • Gmail miễn phí: Chỉ nên gửi <b>20 - 50 mail/ngày</b> (với acc mới) hoặc <b>200 - 300 mail/ngày</b> (acc cũ lâu năm).<br>
        • Google Workspace: Tối đa <b>500 - 1000 mail/ngày</b>. Luôn chia nhỏ chiến dịch để gửi.
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚀 BẮT ĐẦU CHẠY CHIẾN DỊCH NGAY", type="primary", use_container_width=True):
        if not st.session_state["s_email"] or not st.session_state["s_pwd"]:
            st.error("⚠️ Bạn chưa điền Cấu hình Máy chủ (Email/Password) ở cột Menu bên trái!")
        elif df is None:
            st.error("⚠️ Bạn chưa tải lên danh sách Khách hàng!")
        elif not subject:
            st.error("⚠️ Tiêu đề thư không được để trống!")
        else:
            progress = st.progress(0)
            st.markdown("### 📋 Nhật ký tiến trình (Live)")
            log_container = st.empty()
            
            success_list = []
            error_list = []
            log_text = ""
            
            # Gửi thông báo bắt đầu qua Tele
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
                    log_text += f"✅ Đã gửi: {target_email}  \n"
                except Exception as e:
                    error_list.append(target_email)
                    log_text += f"❌ Lỗi {target_email}: {e}  \n"
                
                # Cập nhật giao diện live
                log_container.markdown(f"<div style='height: 200px; overflow-y: auto; background: white; padding: 10px; border-radius: 8px; border: 1px solid #e2e8f0;'>{log_text}</div>", unsafe_allow_html=True)
                progress.progress((index + 1) / len(df))
                time.sleep(delay)
                
            st.success("🎉 TẤT CẢ ĐÃ HOÀN TẤT!")
            
            csv_buf = io.BytesIO()
            pd.DataFrame({
                "Email": success_list + error_list, 
                "Kết quả": ["Thành công"] * len(success_list) + ["Lỗi"] * len(error_list)
            }).to_csv(csv_buf, index=False, encoding="utf-8-sig")
            
            send_tele_msg(run_tk, run_id, f"📊 <b>TỔNG KẾT</b>\n✅ Thành công: {len(success_list)}\n❌ Lỗi: {len(error_list)}")
            send_tele_file(run_tk, run_id, csv_buf.getvalue(), "ket_qua.csv")
            
            st.download_button("📥 TẢI BÁO CÁO CHI TIẾT (.CSV)", data=csv_buf.getvalue(), file_name="ket_qua_chien_dich.csv")

    # ==========================================
    # CHÂN TRANG: LOGO VÀ GIỚI THIỆU
    # ==========================================
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("---")
    
    logo_footer_b64 = get_image_base64(LOGO_URL)
    if logo_footer_b64:
        st.markdown(f"""<div style="display: flex; justify-content: center; padding-top: 20px;"><img src="data:image/png;base64,{logo_footer_b64}" style="width: 150px; height: 150px; border-radius: 50%; object-fit: cover; border: 4px solid white; box-shadow: 0 4px 15px rgba(0,0,0,0.1);"></div>""", unsafe_allow_html=True)

    st.markdown(
        """
        <div style="display: flex; justify-content: center; padding: 20px 0 50px 0;">
            <div style="max-width: 800px; text-align: center; color: #475569; font-family: 'Inter', sans-serif; 
                        padding: 25px; border-radius: 16px; border: 1px solid #f1f5f9; background: white; 
                        box-shadow: 0 10px 25px rgba(0,0,0,0.05);">
                <p style="font-size: 15px; line-height: 1.7; margin: 0;">
                    <b style="color: #1e40af; font-size: 18px;">BulkMail Pro</b> là công cụ gửi thư tự động được phát triển bởi <b>Trường Sơn Marketing</b>. 
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
