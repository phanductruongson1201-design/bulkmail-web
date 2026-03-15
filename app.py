import streamlit as st
import streamlit.components.v1 as components
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
import json
from bs4 import BeautifulSoup 
from streamlit_quill import st_quill 

# 1. Cấu hình trang Web
st.set_page_config(page_title="BulkMail Pro - Trường Sơn", page_icon="🚀", layout="wide")

# ==========================================
# API CƠ SỞ DỮ LIỆU & HỆ THỐNG
# ==========================================
DB_URL = st.secrets.get("DB_URL", "")
SYS_EMAIL = st.secrets.get("SENDER_EMAIL", "")
SYS_PWD = st.secrets.get("APP_PASSWORD", "")

def load_data():
    if not DB_URL: return {"users": {}, "logs": []}
    try: 
        res = requests.get(DB_URL).json()
        # Xử lý linh hoạt nếu API trả về bản cũ (chỉ users) hoặc bản mới (users + logs)
        if isinstance(res, dict) and "users" in res:
            return res
        return {"users": res, "logs": []}
    except: return {"users": {}, "logs": []}

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
# GIAO DIỆN CSS (Giữ nguyên phong cách của Ngân)
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif !important; }
    #MainMenu, footer, header, .stDeployButton, [data-testid="manage-app-button"], [data-testid="viewerBadge"], iframe[title="Streamlit Toolbar"], iframe[src*="badge"] {display: none !important; visibility: hidden !important;}
    .block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; }
    .stApp { background-color: #f8fafc; }
    .gradient-text { background: linear-gradient(90deg, #2563eb 0%, #7c3aed 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; font-size: 46px; margin-bottom: 5px; letter-spacing: -1px; }

    div[data-baseweb="tab-list"] { background-color: #f1f5f9 !important; border-radius: 12px !important; padding: 4px !important; gap: 4px !important; border-bottom: none !important; margin-bottom: 20px !important; }
    div[data-baseweb="tab"] { background-color: transparent !important; border-radius: 8px !important; border: none !important; color: #64748b !important; font-weight: 600 !important; font-size: 14px !important; padding: 8px 12px !important; margin: 0 !important; height: auto !important; }
    div[data-baseweb="tab"][aria-selected="true"] { background-color: #ffffff !important; color: #1e40af !important; box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08) !important; }
    div[data-baseweb="tab"][aria-selected="true"] p { color: #1e40af !important; font-weight: 800 !important; }
    div[data-baseweb="tab-highlight"] { display: none !important; }
       
    div[data-testid="stExpander"] { background-color: #eff6ff !important; border: 2px solid #bfdbfe !important; border-radius: 16px; box-shadow: 0 4px 10px rgba(59, 130, 246, 0.08); }
    div[data-testid="stExpander"] summary { background-color: transparent !important; }

    div[data-testid="stFileUploader"] { background-color: #faf5ff !important; border: 2px solid #e9d5ff !important; border-radius: 16px; box-shadow: 0 4px 10px rgba(168, 85, 247, 0.08); padding: 20px; transition: transform 0.2s ease, box-shadow 0.2s ease; }
    div[data-testid="stFileUploader"]:hover { transform: translateY(-2px); box-shadow: 0 8px 15px rgba(168, 85, 247, 0.15); }

    .stButton>button[kind="primary"] { background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%) !important; color: white !important; border-radius: 16px; font-weight: 900; font-size: 18px !important; padding: 15px 24px; border: none !important; box-shadow: 0 6px 20px rgba(59, 130, 246, 0.35) !important; transition: all 0.3s ease; text-transform: uppercase; letter-spacing: 1px; }
    .stButton>button[kind="primary"]:hover { transform: translateY(-4px); box-shadow: 0 8px 25px rgba(59, 130, 246, 0.5) !important; }
    
    .auth-box .stButton>button[kind="primary"] { background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important; box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4) !important; font-size: 16px !important; padding: 10px 20px; }
    
    .stButton>button[kind="secondary"], div[data-testid="stDownloadButton"]>button { border-radius: 12px; border: 2px solid #cbd5e1 !important; color: #475569 !important; font-weight: 700; background-color: white !important; transition: all 0.3s ease; }
    .stButton>button[kind="secondary"]:hover, div[data-testid="stDownloadButton"]>button:hover { border-color: #3b82f6 !important; color: #3b82f6 !important; transform: translateY(-2px); box-shadow: 0 6px 15px rgba(59, 130, 246, 0.15); }

    .pill-header { color: white; padding: 10px 24px; border-radius: 50px; font-size: 15px; font-weight: 800; margin-bottom: 20px; margin-top: 15px; text-transform: uppercase; letter-spacing: 1px; display: inline-block; text-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .bg-blue { background: linear-gradient(135deg, #3b82f6, #1d4ed8); box-shadow: 0 6px 15px rgba(59, 130, 246, 0.4); border: 2px solid #93c5fd; }
    .bg-purple { background: linear-gradient(135deg, #a855f7, #6d28d9); box-shadow: 0 6px 15px rgba(168, 85, 247, 0.4); border: 2px solid #d8b4fe; }
    .bg-green { background: linear-gradient(135deg, #10b981, #047857); box-shadow: 0 6px 15px rgba(16, 185, 129, 0.4); border: 2px solid #6ee7b7; }
    .bg-orange { background: linear-gradient(135deg, #f59e0b, #d97706); box-shadow: 0 6px 15px rgba(245, 158, 11, 0.4); border: 2px solid #fcd34d; }

    .auth-box { max-width: 440px; margin: 10px auto; padding: 35px; background: rgba(255, 255, 255, 0.95); border-radius: 24px; box-shadow: 0 20px 40px -15px rgba(0,0,0,0.1); border: 1px solid rgba(255,255,255,0.5); backdrop-filter: blur(10px); }
    
    .logo-container { display: flex; justify-content: center; align-items: center; width: 100%; margin-bottom: 20px; }
    .logo-container img { width: 120px; height: 120px; border-radius: 35%; object-fit: cover; box-shadow: 0 10px 25px rgba(59, 130, 246, 0.2); border: 4px solid white;}
    .alt-logo { width: 120px; height: 120px; border-radius: 35%; background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%); color: white; display: flex; justify-content: center; align-items: center; font-weight: 800; font-size: 16px; text-align: center; border: 4px solid white; box-shadow: 0 10px 25px rgba(59, 130, 246, 0.2); }

    .floating-container { position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 15px; z-index: 999999; }
    .float-btn { width: 55px; height: 55px; border-radius: 50%; box-shadow: 0 10px 25px rgba(0,0,0,0.15); display: flex; justify-content: center; align-items: center; background: white; transition: 0.3s; border: 2px solid #e2e8f0; }
    .float-btn:hover { transform: translateY(-5px); border-color: #3b82f6; }
    .float-btn img { width: 65%; height: 65%; object-fit: contain; }
    
    .deposit-box { background: white; padding: 25px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); margin-bottom: 25px; }
</style>
""", unsafe_allow_html=True)

# Khởi tạo trạng thái Session
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "otp_verified" not in st.session_state: st.session_state["otp_verified"] = False
if "otp_sent" not in st.session_state: st.session_state["otp_sent"] = False

if "show_deposit_form" not in st.session_state: st.session_state["show_deposit_form"] = False
if "show_qr" not in st.session_state: st.session_state["show_qr"] = False
if "deposit_amount" not in st.session_state: st.session_state["deposit_amount"] = 100000
if "qr_expire_time" not in st.session_state: st.session_state["qr_expire_time"] = 0
if "previous_balance" not in st.session_state: st.session_state["previous_balance"] = None 

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
            
        st.markdown('<h2 style="text-align:center; color:#0f172a; font-weight:900; margin-bottom:5px; font-size:28px;">BULKMAIL PRO</h2>', unsafe_allow_html=True)
        tab_login, tab_reg, tab_forgot = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký", "🔑 Quên MK"])
        all_data = load_data()
        users_db = all_data["users"]

        with tab_login:
            log_user = st.text_input("Tên đăng nhập", key="login_u")
            log_pwd = st.text_input("Mật khẩu", type="password", key="login_p")
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
            if st.button("TẠO TÀI KHOẢN", type="primary", use_container_width=True):
                if not reg_user or not reg_email or not reg_pwd: st.warning("⚠️ Điền đủ thông tin!")
                elif reg_user in users_db: st.error("❌ Username đã tồn tại!")
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
                
                if st.session_state.get("otp_sent"):
                    input_otp = st.text_input("Mã OTP 6 số:", max_chars=6)
                    if st.button("XÁC THỰC OTP", type="primary", use_container_width=True):
                        u_info = load_data()["users"].get(fg_user)
                        if u_info and u_info.get("password") == hash_password(input_otp):
                            st.session_state["otp_verified"] = True
                            st.session_state["target_user"] = fg_user
                            st.rerun()
                        else: st.error("❌ OTP không đúng!")
            else:
                new_p = st.text_input("Mật khẩu mới", type="password")
                if st.button("ĐỔI MẬT KHẨU", type="primary", use_container_width=True):
                    target = st.session_state["target_user"]
                    if reset_password_api(target, users_db[target]["email"], hash_password(new_p), False):
                        st.session_state["otp_verified"] = False
                        st.success("✅ Đổi mật khẩu thành công!")
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 2. DASHBOARD CHÍNH (Sau đăng nhập)
# ==========================================
else:
    all_data = load_data()
    users_db = all_data["users"]
    logs_db = all_data["logs"]
    current_user_data = users_db.get(st.session_state["current_user"], {})
    
    balance = int(float(current_user_data.get("balance", 0)))

    # Pháo hoa mừng cộng tiền thành công
    if st.session_state["previous_balance"] is None:
        st.session_state["previous_balance"] = balance
    elif balance > st.session_state["previous_balance"]:
        st.balloons()
        st.success(f"🎉 THANH TOÁN THÀNH CÔNG! Tài khoản của bạn vừa được cộng thêm {balance - st.session_state['previous_balance']:,} VNĐ.")
        st.session_state["previous_balance"] = balance
        st.session_state["show_deposit_form"] = False
        st.session_state["show_qr"] = False

    # Header Dashboard
    head_col1, head_col2 = st.columns([5, 1.5])
    with head_col1:
        st.markdown('<div class="gradient-text">BulkMail</div>', unsafe_allow_html=True)
    with head_col2:
        st.markdown(f"""
        <div style='text-align: right; padding-top: 5px;'>
            <div style='font-weight: bold; color: #1e40af; font-size: 15px;'>👤 {st.session_state['current_user']}</div>
            <div style='color: #047857; font-weight: 800; font-size: 14px;'>💰 Số dư: {balance:,} VNĐ</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state["logged_in"] = False
            st.rerun()

    # TỔ HỢP TABS
    tab_send, tab_history, tab_config = st.tabs(["✉️ Gửi Email", "📊 Lịch sử nạp", "⚙️ Cài đặt"])

    with tab_send:
        # NẠP TIỀN POPUP (Giữ nguyên giao diện mockup của Ngân)
        if st.button("💳 NẠP TIỀN TỰ ĐỘNG", type="primary"):
            st.session_state["show_deposit_form"] = True
            st.session_state["show_qr"] = False
            
        if st.session_state.get("show_deposit_form"):
            st.markdown('<div class="deposit-box">', unsafe_allow_html=True)
            st.markdown("### Nhập số tiền cần nạp")
            st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
            amount_input = st.number_input("Nhập số tiền VNĐ", value=st.session_state["deposit_amount"], step=10000, min_value=0)
            
            c_p, c_r = st.columns(2)
            c_p.markdown(f"**Cần thanh toán**<br><h3 style='color:#2563eb; margin:0;'>{amount_input:,}</h3>", unsafe_allow_html=True)
            c_r.markdown(f"**Nhận được**<br><h3 style='color:#ef4444; margin:0;'>{amount_input:,}</h3>", unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            bc1, bc2, bc3 = st.columns([6, 2, 2.5])
            if bc2.button("Đóng"): 
                st.session_state["show_deposit_form"] = False; st.rerun()
            if bc3.button("Tạo hoá đơn", type="primary"):
                if amount_input < 10000: st.error("Tối thiểu 10.000đ")
                else:
                    st.session_state["deposit_amount"] = amount_input
                    st.session_state["show_qr"] = True
                    st.session_state["qr_expire_time"] = time.time() + 600
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.get("show_qr"):
            time_left = int(st.session_state["qr_expire_time"] - time.time())
            if time_left <= 0:
                st.warning("⏳ Mã QR hết hạn."); st.session_state["show_qr"] = False
            else:
                st.markdown("<div style='background:#fffbeb; border:1px dashed orange; border-radius:12px; padding:20px; margin-bottom:20px;'>", unsafe_allow_html=True)
                col_qr, col_info = st.columns([1, 1.5])
                acc = "VQRQAHQHF1360"; bank = "MBBank"; name = "PHAN DUC TRUONG SON"
                amt = st.session_state["deposit_amount"]
                cont = f"NAP {st.session_state['current_user']}"
                qr_url = f"https://qr.sepay.vn/img?acc={acc}&bank={bank}&amount={amt}&des={cont.replace(' ','%20')}"
                
                with col_qr:
                    st.image(qr_url, width=240)
                    components.html(f"<div style='text-align:center;color:red;font-weight:bold;'>⏳ Hết hạn: <span id='t'>10:00</span></div><script>var l={time_left};setInterval(function(){{if(l<=0)document.getElementById('t').innerHTML='HẾT HẠN';else{{var m=Math.floor(l/60),s=l%60;document.getElementById('t').innerHTML=m+':'+(s<10?'0':'')+s;l--;}}}},1000);</script>", height=30)
                
                with col_info:
                    st.markdown(f"**🏦 Ngân hàng:** {bank}<br>**👤 Chủ TK:** {name}<br>**💰 Số tiền:** <b style='color:green;'>{amt:,} VNĐ</b>", unsafe_allow_html=True)
                    st.markdown("**Nội dung (Bấm 📋 Copy):**")
                    st.code(cont, language="text")
                    if st.button("🔄 LÀM MỚI SỐ DƯ ĐỂ XÁC NHẬN", use_container_width=True): st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        # PHẦN GỬI MAIL (Giữ nguyên toàn bộ logic chống lỗi 5.7.0)
        st.markdown('<div class="pill-header bg-purple">📁 DỮ LIỆU KHÁCH HÀNG</div>', unsafe_allow_html=True)
        col_data, col_content = st.columns([1, 1.2], gap="large")
        with col_data:
            up = st.file_uploader("Tải tệp (.xlsx, .csv)", type=["csv", "xlsx"])
            df = pd.read_excel(up) if up and up.name.endswith("xlsx") else (pd.read_csv(up) if up else None)
            attachments = st.file_uploader("📎 Tệp đính kèm", accept_multiple_files=True)

        with col_content:
            st.markdown('<div class="pill-header bg-green">✍️ SOẠN THÔNG ĐIỆP</div>', unsafe_allow_html=True)
            subject = st.text_input("Tiêu đề Email:")
            raw_body = st_quill(placeholder="Dán nội dung từ web vào đây...", html=True)
            delay = st.number_input("⏳ Nghỉ/Mail (s):", value=15, min_value=5)

        if st.button("🚀 BẮT ĐẦU CHIẾN DỊCH GỬI MAIL", type="primary", use_container_width=True):
            if df is None or not subject: st.error("⚠️ Thiếu danh sách hoặc tiêu đề!")
            else:
                progress = st.progress(0); log = st.expander("Live Log", expanded=True)
                soup = BeautifulSoup(raw_body or "", "html.parser")
                for tag in soup(["script", "style"]): tag.decompose()
                inline_images = []; img_counter = 0
                for img in soup.find_all("img"):
                    src = img.get("src", "")
                    if src.startswith("http"): img.attrs = {"src": src, "style": "max-width: 100%"}
                    elif src.startswith("data:image") and img_counter < 2:
                        try:
                            h, e = src.split(",", 1); img_data = base64.b64decode(e)
                            img_counter += 1; cid = f"img_{img_counter}"
                            inline_images.append({"cid": cid, "data": img_data, "type": "png"})
                            img.attrs = {"src": f"cid:{cid}", "style": "max-width: 100%"}
                        except: img.decompose()
                    else: img.decompose()
                
                full_html = str(soup) + f"<br><br>{st.session_state['s_sign'].replace('\\n','<br>')}"
                success_c = 0
                for idx, row in df.iterrows():
                    try:
                        target_email = str(row.get("email", row.iloc[0])).strip()
                        target_name = str(row.get("name", "Quý khách"))
                        msg = MIMEMultipart("related")
                        msg["From"] = f"{st.session_state['s_name']} <{SYS_EMAIL}>"
                        msg["To"] = target_email; msg["Subject"] = subject
                        msg.attach(MIMEText(full_html.replace("{{name}}", target_name), "html"))
                        for i in inline_images:
                            part = MIMEImage(i["data"], _subtype=i["type"])
                            part.add_header("Content-ID", f"<{i['cid']}>"); msg.attach(part)
                        if attachments:
                            for f in attachments:
                                p = MIMEBase("application", "octet-stream"); p.set_payload(f.read())
                                encoders.encode_base64(p); p.add_header("Content-Disposition", f"attachment; filename={f.name}")
                                msg.attach(p); f.seek(0)
                        
                        with smtplib.SMTP("smtp.gmail.com", 587) as s:
                            s.starttls(); s.login(SYS_EMAIL, SYS_PWD); s.send_message(msg)
                        success_c += 1; log.write(f"✅ {target_email}")
                    except Exception as e: log.write(f"❌ {target_email}: {e}")
                    progress.progress((idx+1)/len(df)); time.sleep(delay)
                st.success(f"Chiến dịch hoàn tất! Đã gửi {success_c} mail.")

    with tab_history:
        st.markdown('<div class="pill-header bg-blue">📜 NHẬT KÝ GIAO DỊCH</div>', unsafe_allow_html=True)
        if not logs_db: st.info("Chưa có lịch sử giao dịch.")
        else:
            h_list = []; cur_u = st.session_state['current_user'].upper()
            for l in logs_db:
                if cur_u in str(l.get('raw_data','')).upper():
                    try:
                        pld = json.loads(l.get('raw_data','{}'))
                        amt = f"{pld.get('transferAmount', 0):,} VNĐ"
                    except: amt = "---"
                    h_list.append({"Ngày nạp": l['time'], "Số tiền": amt, "Trạng thái": l['status']})
            if h_list: st.table(pd.DataFrame(h_list))
            else: st.write("Không tìm thấy giao dịch của bạn.")

    with tab_config:
        st.markdown('<div class="pill-header bg-blue">⚙️ CÀI ĐẶT HỆ THỐNG</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.session_state["s_name"] = st.text_input("Tên hiển thị:", value=st.session_state["s_name"])
            st.info(f"Hệ thống gửi từ: {SYS_EMAIL}")
        with c2:
            tk = st.text_input("Bot Token Telegram:", value=current_user_data.get("tele_token", ""), type="password")
            cid = st.text_input("Chat ID Telegram:", value=current_user_data.get("tele_chat_id", ""))
            st.session_state["s_sign"] = st.text_area("Chữ ký cuối thư:", value=st.session_state["s_sign"])
            if st.button("💾 Lưu cấu hình"):
                if save_config_api(st.session_state["current_user"], tk, cid): st.success("Đã lưu!")

# NÚT LIÊN HỆ NỔI
st.markdown("""<div class="floating-container"><a href="https://zalo.me/0935748199" target="_blank" class="float-btn"><img src="https://upload.wikimedia.org/wikipedia/commons/9/91/Icon_of_Zalo.svg" width="35"></a><a href="https://t.me/BulkMail_Pro" target="_blank" class="float-btn"><img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg" width="35"></a></div>""", unsafe_allow_html=True)
