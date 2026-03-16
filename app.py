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
st.set_page_config(page_title="BulkMail Pro - Trường Sơn", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# API CƠ SỞ DỮ LIỆU & HỆ THỐNG
# ==========================================
DB_URL = st.secrets.get("DB_URL", "")
SYS_EMAIL = st.secrets.get("SENDER_EMAIL", "")
SYS_PWD = st.secrets.get("APP_PASSWORD", "")

def load_users():
    if not DB_URL: return {"users": {}, "logs": []}
    try: 
        res = requests.get(DB_URL).json()
        if isinstance(res, dict) and "users" in res: return res
        return {"users": res, "logs": []}
    except: return {"users": {}, "logs": []}

def save_user_api(username, password_hash, email):
    if not DB_URL: return
    try: requests.post(DB_URL, json={"action": "register", "username": username, "password": password_hash, "email": email})
    except: pass

def reset_password_api(username, email, new_password_hash, is_reset_status):
    if not DB_URL: return False
    try:
        res = requests.post(DB_URL, json={"action": "reset", "username": username, "email": email, "new_password": new_password_hash, "is_reset": is_reset_status}).json()
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
        msg["To"] = to_email; msg["Subject"] = f"{otp_code} là mã xác thực của bạn"
        body = f"<h3>Chào {username},</h3><p>Mã OTP: <b style='font-size: 20px; color:#2563eb;'>{otp_code}</b></p>"
        msg.attach(MIMEText(body, "html"))
        s = smtplib.SMTP("smtp.gmail.com", 587); s.starttls(); s.login(SYS_EMAIL, SYS_PWD); s.send_message(msg); s.quit()
        return True
    except: return False

def send_tele_msg(token, chat_id, message):
    if token and chat_id:
        try: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=5)
        except: pass

def send_tele_file(token, chat_id, file_content, file_name):
    if token and chat_id:
        try:
            files = {"document": (file_name, file_content)}
            requests.post(f"https://api.telegram.org/bot{token}/sendDocument", data={"chat_id": chat_id}, files=files, timeout=10)
        except: pass

def get_image_base64(path):
    try:
        with open(path, "rb") as img_file: return base64.b64encode(img_file.read()).decode("utf-8")
    except: return None

def play_success_sound():
    components.html("""<audio autoplay><source src="https://actions.google.com/sounds/v1/cartoon/magic_chime.ogg" type="audio/ogg"></audio>""", height=0)

# ==========================================
# GIAO DIỆN CSS MỚI - CHUẨN UI/UX HIỆN ĐẠI
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; color: #334155; }
    .stApp { background-color: #f8fafc; } 
    #MainMenu, footer, header, .stDeployButton, [data-testid="viewerBadge"], iframe[title="Streamlit Toolbar"] {display: none !important; visibility: hidden !important;}
    .block-container { padding-top: 2rem !important; padding-bottom: 3rem !important; max-width: 95% !important;}
    
    .gradient-text { background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; font-size: 36px; margin-bottom: 8px; letter-spacing: -0.5px; }
    h1, h2, h3, h4 { color: #0f172a; font-weight: 700; }

    .modern-card { background: #ffffff; border-radius: 16px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03); border: 1px solid #f1f5f9; transition: all 0.3s ease-in-out; margin-bottom: 20px; }
    .modern-card:hover { transform: translateY(-4px); box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.1), 0 8px 10px -6px rgba(59, 130, 246, 0.1); border-color: #e2e8f0; }

    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; box-shadow: 4px 0 15px rgba(0,0,0,0.03); }
    div[role="radiogroup"] > label { padding: 14px 16px; border-radius: 12px; margin-bottom: 8px; transition: all 0.2s ease; border: 1px solid transparent; cursor: pointer; }
    div[role="radiogroup"] > label:hover { background-color: #f8fafc; border-color: #e2e8f0; transform: translateX(4px); }
    div[role="radiogroup"] > label[data-checked="true"] { background: #eff6ff; border-left: 4px solid #2563eb; border-radius: 4px 12px 12px 4px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02); }
    div[role="radiogroup"] > label > div:first-child { display: none; } 
    div[role="radiogroup"] > label p { font-weight: 600 !important; color: #475569 !important; font-size: 15px !important; margin: 0 !important; }
    div[role="radiogroup"] > label[data-checked="true"] p { color: #1d4ed8 !important; font-weight: 700 !important; }

    .stButton>button[kind="primary"] { background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important; color: white !important; border-radius: 12px; font-weight: 700; font-size: 15px !important; padding: 12px 24px; border: none !important; box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3) !important; transition: all 0.2s ease; letter-spacing: 0.5px; }
    .stButton>button[kind="primary"]:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4) !important; background: linear-gradient(135deg, #1d4ed8 0%, #1e3a8a 100%) !important; }
    .stButton>button[kind="primary"]:active { transform: translateY(0); }
    
    .stButton>button[kind="secondary"], div[data-testid="stDownloadButton"]>button { background: #ffffff !important; border-radius: 12px; border: 1px solid #cbd5e1 !important; color: #475569 !important; font-weight: 600; transition: all 0.2s ease; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    .stButton>button[kind="secondary"]:hover, div[data-testid="stDownloadButton"]>button:hover { border-color: #94a3b8 !important; color: #0f172a !important; background: #f8fafc !important; transform: translateY(-1px); box-shadow: 0 4px 6px rgba(0,0,0,0.05); }

    div[data-testid="stMetric"] { background: #ffffff; padding: 20px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #f1f5f9; text-align: center; transition: transform 0.3s ease; }
    div[data-testid="stMetric"]:hover { transform: translateY(-3px); border-color: #bfdbfe; box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.1); }
    div[data-testid="stMetricValue"] { color: #1e40af !important; font-weight: 800 !important; font-size: 32px !important; margin-bottom: 4px;}
    div[data-testid="stMetricLabel"] { font-size: 13px !important; color: #64748b !important; font-weight: 600 !important; text-transform: uppercase; letter-spacing: 0.5px; }

    div[data-baseweb="tab-list"] { background: #f1f5f9 !important; border-radius: 12px !important; padding: 4px !important; gap: 4px !important; border-bottom: none !important; margin-bottom: 24px !important; }
    div[data-baseweb="tab"] { background-color: transparent !important; border-radius: 8px !important; border: none !important; color: #64748b !important; font-weight: 500 !important; font-size: 14px !important; padding: 10px 16px !important; margin: 0 !important; }
    div[data-baseweb="tab"][aria-selected="true"] { background-color: #ffffff !important; color: #2563eb !important; box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important; font-weight: 600 !important;}
    div[data-baseweb="tab-highlight"] { display: none !important; }

    .vip-badge { display: inline-flex; align-items: center; justify-content: center; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; color: white; margin-left: 8px; text-transform: uppercase; letter-spacing: 0.5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
    .badge-dong { background: #b45309; }
    .badge-bac { background: #94a3b8; }
    .badge-vang { background: #eab308; color: #422006; }
    .badge-kimcuong { background: linear-gradient(135deg, #0ea5e9, #2563eb); animation: pulse-blue 2s infinite; }
    @keyframes pulse-blue { 0% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.4); } 70% { box-shadow: 0 0 0 6px rgba(37, 99, 235, 0); } 100% { box-shadow: 0 0 0 0 rgba(37, 99, 235, 0); } }

    .pill-header { display: inline-block; padding: 8px 16px; border-radius: 8px; font-size: 14px; font-weight: 700; margin-bottom: 16px; text-transform: uppercase; letter-spacing: 0.5px; border-left: 4px solid; background: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.02); color: #1e293b; }
    .bh-blue { border-color: #3b82f6; }
    .bh-purple { border-color: #8b5cf6; }
    .bh-green { border-color: #10b981; }

    div[data-testid="stFileUploader"] { background: #ffffff !important; border: 2px dashed #cbd5e1 !important; border-radius: 12px; padding: 24px; transition: all 0.3s; }
    div[data-testid="stFileUploader"]:hover { border-color: #3b82f6 !important; background: #f8fafc !important; }
    div[data-testid="stExpander"] { background: #ffffff !important; border: 1px solid #e2e8f0 !important; border-radius: 12px; box-shadow: 0 2px 5px rgba(0,0,0,0.02); }

    .logo-container { display: flex; justify-content: center; align-items: center; margin-bottom: 24px; }
    .logo-container img { width: 90px; height: 90px; border-radius: 24px; object-fit: cover; box-shadow: 0 10px 20px rgba(0,0,0,0.08); border: 2px solid #ffffff; }
    .alt-logo { width: 90px; height: 90px; border-radius: 24px; background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white; display: flex; justify-content: center; align-items: center; font-weight: 800; font-size: 12px; text-align: center; box-shadow: 0 10px 20px rgba(37,99,235,0.2); border: 2px solid #ffffff; }

    .floating-container { position: fixed; bottom: 24px; right: 24px; display: flex; flex-direction: column; gap: 12px; z-index: 99; }
    .float-btn { width: 48px; height: 48px; border-radius: 50%; box-shadow: 0 4px 15px rgba(0,0,0,0.1); display: flex; justify-content: center; align-items: center; background: white; transition: transform 0.2s; border: 1px solid #e2e8f0; }
    .float-btn:hover { transform: scale(1.1); border-color: #3b82f6; }
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
        st.markdown('<div class="modern-card" style="margin-top: 40px; padding: 40px;">', unsafe_allow_html=True)
        logo_b64 = get_image_base64(LOGO_URL)
        if logo_b64: st.markdown(f'<div class="logo-container"><img src="data:image/png;base64,{logo_b64}"></div>', unsafe_allow_html=True)
        else: st.markdown('<div class="logo-container"><div class="alt-logo">TRƯỜNG SƠN<br>MARKETING</div></div>', unsafe_allow_html=True)
            
        st.markdown('<h2 style="text-align:center; color:#0f172a; margin-bottom:8px; font-size:26px;">Đăng nhập hệ thống</h2>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; color:#64748b; margin-bottom:24px; font-size:14px;">Quản lý chiến dịch email marketing của bạn</p>', unsafe_allow_html=True)
        
        tab_login, tab_reg, tab_forgot = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký", "🔑 Quên MK"])
        all_data = load_users()
        users_db = all_data.get("users", all_data) 

        with tab_login:
            log_user = st.text_input("Tên đăng nhập", key="login_u")
            log_pwd = st.text_input("Mật khẩu", type="password", key="login_p")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Truy cập hệ thống", type="primary", use_container_width=True):
                u_data = users_db.get(log_user)
                if u_data and u_data.get("password") == hash_password(log_pwd):
                    st.session_state["current_user"] = log_user; st.session_state["logged_in"] = True; st.rerun()
                else: 
                    st.toast("Thông tin đăng nhập không hợp lệ", icon="⚠️")
                    st.error("Thông tin đăng nhập chưa chính xác!")

        with tab_reg:
            reg_user = st.text_input("Tên đăng nhập mới", key="reg_u")
            reg_email = st.text_input("Email khôi phục", key="reg_e")
            reg_pwd = st.text_input("Mật khẩu", type="password", key="reg_p")
            reg_pwd_confirm = st.text_input("Xác nhận mật khẩu", type="password", key="reg_pc")
            if st.button("Tạo tài khoản", type="primary", use_container_width=True):
                if not reg_user or not reg_email or not reg_pwd: st.warning("Vui lòng điền đủ thông tin")
                elif reg_user in users_db: st.error("Username đã tồn tại")
                elif reg_pwd != reg_pwd_confirm: st.error("Mật khẩu không khớp")
                else:
                    save_user_api(reg_user, hash_password(reg_pwd), reg_email)
                    st.toast("Đăng ký thành công!", icon="🎉"); st.success("Đăng ký thành công! Vui lòng đăng nhập.")

        with tab_forgot:
            st.info("Vui lòng liên hệ Quản trị viên qua Zalo ở góc màn hình để được cấp lại mật khẩu.")
            
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 2. DASHBOARD CHÍNH
# ==========================================
else:
    all_data = load_users()
    users_db = all_data.get("users", all_data)
    logs_db = all_data.get("logs", [])
    current_user_data = users_db.get(st.session_state["current_user"], {})
    
    balance = int(float(current_user_data.get("balance", 0)))
    
    if balance < 100000: vip_class = "badge-dong"; vip_text = "Thành viên Đồng"
    elif balance < 500000: vip_class = "badge-bac"; vip_text = "Thành viên Bạc"
    elif balance < 2000000: vip_class = "badge-vang"; vip_text = "Thành viên Vàng"
    else: vip_class = "badge-kimcuong"; vip_text = "Đối tác Kim Cương"

    if st.session_state["previous_balance"] is None: st.session_state["previous_balance"] = balance
    elif balance > st.session_state["previous_balance"]:
        play_success_sound(); st.balloons()
        st.toast(f"Cộng thành công {balance - st.session_state['previous_balance']:,} VNĐ!", icon="💳")
        st.session_state["previous_balance"] = balance
        st.session_state["show_deposit_form"] = False; st.session_state["show_qr"] = False

    # ========================================================
    # MENU BÊN TRÁI (SIDEBAR)
    # ========================================================
    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        logo_b64 = get_image_base64(LOGO_URL)
        if logo_b64: st.markdown(f'<div class="logo-container"><img src="data:image/png;base64,{logo_b64}" width="80"></div>', unsafe_allow_html=True)
        else: st.markdown('<h3 style="text-align:center; color:#1e40af; font-weight:800; font-size:20px;">BULKMAIL PRO</h3>', unsafe_allow_html=True)
        
        st.markdown(f"<div style='text-align:center; margin-bottom:24px;'><div style='font-size:16px; font-weight:700; color:#0f172a;'>{st.session_state['current_user']}</div><div style='color:#2563eb; font-weight:700; font-size:14px; margin-top:4px;'>Số dư: {balance:,}đ</div></div>", unsafe_allow_html=True)
        
        st.markdown("<p style='font-size:11px; font-weight:600; color:#94a3b8; text-transform:uppercase; margin-bottom:8px; margin-left:12px; letter-spacing:1px;'>Menu Điều Hướng</p>", unsafe_allow_html=True)
        menu = st.radio("", ["🏠 Tổng Quan", "✉️ Tạo Chiến Dịch", "📊 Quản Lý Giao Dịch", "⚙️ Cài Đặt Hệ Thống"], label_visibility="collapsed")
        
        st.markdown("<div style='margin-top: 80px;'></div>", unsafe_allow_html=True)
        if st.button("Đăng xuất", use_container_width=True):
            st.session_state["logged_in"] = False; st.rerun()

    # ========================================================
    # NỘI DUNG CHÍNH
    # ========================================================

    # 1. TỔNG QUAN & NẠP TIỀN
    if menu == "🏠 Tổng Quan":
        # KHÔNG THỤT LỀ HTML MARKDOWN Ở ĐÂY
        st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 24px;">
    <div>
        <div class="gradient-text" style="font-size: 28px;">Bảng Điều Khiển</div>
        <div style="color:#64748b; font-size: 14px;">Theo dõi hoạt động và nạp quỹ tài khoản</div>
    </div>
    <div><span class="vip-badge {vip_class}">{vip_text}</span></div>
</div>
""", unsafe_allow_html=True)

        col_main, col_right = st.columns([7, 3], gap="large")
        
        with col_main:
            m1, m2, m3 = st.columns(3)
            my_logs = [l for l in logs_db if st.session_state['current_user'].upper() in str(l.get('raw_data','')).upper() and "Thành công" in str(l.get('status',''))]
            m1.metric(label="Tổng số lần nạp", value=f"{len(my_logs)}")
            m2.metric(label="Hạng thẻ", value=vip_text.split(" ")[-1])
            m3.metric(label="Trạng thái", value="Hoạt động")

            st.markdown('<div class="modern-card" style="margin-top: 24px;">', unsafe_allow_html=True)
            st.markdown('<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 16px;"><h3 style="margin:0; font-size: 18px; color:#0f172a;">💳 Cổng nạp tiền tự động 24/7</h3></div>', unsafe_allow_html=True)
            
            if not st.session_state.get("show_deposit_form") and not st.session_state.get("show_qr"):
                st.markdown("<p style='color:#64748b; font-size:14px; margin-bottom: 20px;'>Nạp tiền thông qua quét mã QR Code. Hệ thống tự động đối soát và cộng tiền trong 1-3 phút.</p>", unsafe_allow_html=True)
                if st.button("Tạo hóa đơn nạp tiền", type="primary"): 
                    st.session_state["show_deposit_form"] = True; st.rerun()

            if st.session_state.get("show_deposit_form"):
                amount_input = st.number_input("Nhập số tiền cần nạp (VNĐ)", value=st.session_state.get("deposit_amount", 100000), step=10000, min_value=0)
                st.markdown("<br>", unsafe_allow_html=True)
                bc1, bc2 = st.columns(2)
                if bc1.button("Hủy bỏ", use_container_width=True): 
                    st.session_state["show_deposit_form"] = False; st.rerun()
                if bc2.button("Tạo mã QR", type="primary", use_container_width=True):
                    if amount_input < 10000: st.toast("Tối thiểu nạp 10.000 VNĐ", icon="⚠️")
                    else:
                        st.session_state["deposit_amount"] = amount_input
                        st.session_state["show_qr"] = True; st.session_state["qr_expire_time"] = time.time() + 600
                        st.rerun()

            if st.session_state.get("show_qr"):
                time_left = int(st.session_state["qr_expire_time"] - time.time())
                if time_left <= 0: st.warning("Mã QR đã hết hạn."); st.session_state["show_qr"] = False
                else:
                    st.markdown("<div style='background:#f8fafc; border-radius:12px; padding:20px; border: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
                    cq, ci = st.columns([1, 1.2], gap="large")
                    
                    SEPAY_ACC = "VQRQAHQHF1360"; SEPAY_BANK = "MBBank"; MY_NAME = "PHAN DUC TRUONG SON"
                    amt = st.session_state["deposit_amount"]; cont = f"NAP {st.session_state['current_user']}"
                    qr_url = f"https://qr.sepay.vn/img?acc={SEPAY_ACC}&bank={SEPAY_BANK}&amount={amt}&des={cont.replace(' ', '%20')}"
                    
                    with cq:
                        st.image(qr_url, use_column_width=True)
                        components.html(f"<div style='text-align:center; color:#b91c1c; font-weight:600; font-size:14px;'>Hết hạn sau: <span id='t'></span></div><script>var l={time_left};setInterval(function(){{if(l<=0)document.getElementById('t').innerHTML='00:00';else{{var m=Math.floor(l/60),s=l%60;document.getElementById('t').innerHTML=m+':'+(s<10?'0':'')+s;l--;}}}},1000);</script>", height=30)
                    with ci:
                        st.markdown(f"<div style='font-size:14px; color:#475569; margin-bottom:8px;'>Ngân hàng: <b>{SEPAY_BANK}</b></div>", unsafe_allow_html=True)
                        st.markdown(f"<div style='font-size:14px; color:#475569; margin-bottom:8px;'>Chủ tài khoản: <b>{MY_NAME}</b></div>", unsafe_allow_html=True)
                        st.markdown(f"<div style='font-size:14px; color:#475569; margin-bottom:8px;'>Số tài khoản: <b>{SEPAY_ACC}</b></div>", unsafe_allow_html=True)
                        st.markdown(f"<div style='font-size:14px; color:#475569; margin-bottom:16px;'>Số tiền: <b style='color:#2563eb; font-size:18px;'>{amt:,}đ</b></div>", unsafe_allow_html=True)
                        st.markdown("<div style='font-size:13px; color:#64748b; margin-bottom:4px;'>Nội dung chuyển khoản (bấm 📋 copy)</div>", unsafe_allow_html=True)
                        st.code(cont, language="text")
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("Xác nhận thanh toán", type="primary", use_container_width=True): st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col_right:
            # SỬA LỖI HIỂN THỊ HTML CHO CỘT BẢNG TIN BẰNG CÁCH XÓA KHOẢNG TRẮNG ĐẦU DÒNG
            st.markdown("""
<div class="modern-card">
    <h4 style="margin-top:0; color:#0f172a; font-size:16px; margin-bottom: 16px;">🔔 Bảng tin hệ thống</h4>
    
    <div style="border-left: 3px solid #3b82f6; padding-left: 12px; margin-bottom: 16px;">
        <div style="font-size: 11px; color: #94a3b8; font-weight:600; text-transform:uppercase; margin-bottom: 4px;">Phiên bản mới</div>
        <div style="font-size: 13px; color: #334155; font-weight: 500; line-height: 1.5;">Cập nhật giao diện UI/UX chuẩn SaaS. Trải nghiệm mượt mà, tối ưu trên di động.</div>
    </div>
    
    <div style="border-left: 3px solid #10b981; padding-left: 12px; margin-bottom: 16px;">
        <div style="font-size: 11px; color: #94a3b8; font-weight:600; text-transform:uppercase; margin-bottom: 4px;">Bảo mật</div>
        <div style="font-size: 13px; color: #334155; font-weight: 500; line-height: 1.5;">Nâng cấp hệ thống lách firewall Gmail 5.7.0. Đảm bảo tỷ lệ vào Inbox cao nhất.</div>
    </div>
    
    <div style="border-left: 3px solid #8b5cf6; padding-left: 12px;">
        <div style="font-size: 11px; color: #94a3b8; font-weight:600; text-transform:uppercase; margin-bottom: 4px;">Thanh toán</div>
        <div style="font-size: 13px; color: #334155; font-weight: 500; line-height: 1.5;">Hỗ trợ nạp tiền tự động qua QR Code 24/7. Tự động cấp Huy hiệu thẻ VIP.</div>
    </div>
</div>
""", unsafe_allow_html=True)

    # 2. CHIẾN DỊCH GỬI EMAIL
    elif menu == "✉️ Tạo Chiến Dịch":
        st.markdown('<div class="gradient-text" style="font-size: 28px;">Thiết Lập Chiến Dịch</div><div style="color:#64748b; font-size: 14px; margin-bottom: 24px;">Cấu hình nội dung và danh sách người nhận</div>', unsafe_allow_html=True)
        
        col_data, col_content = st.columns([1, 1.2], gap="large")
        
        with col_data:
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.markdown('<div class="pill-header bh-purple">1. Nguồn Dữ Liệu</div>', unsafe_allow_html=True)
            up = st.file_uploader("Tải lên danh sách khách hàng (.xlsx, .csv)", type=["csv", "xlsx"])
            df = pd.read_excel(up) if up and up.name.endswith("xlsx") else (pd.read_csv(up) if up else None)
            if df is not None: st.toast(f"Tải thành công {len(df)} dòng", icon="✅")
                
            st.markdown('<div style="margin-top:16px;"></div>', unsafe_allow_html=True)
            attachments = st.file_uploader("Tệp đính kèm (Catalogue, Báo giá...)", accept_multiple_files=True)
            
            st.markdown('<div style="margin-top:16px;"></div>', unsafe_allow_html=True)
            delay = st.number_input("Khoảng cách gửi giữa mỗi email (Giây)", value=15, min_value=5, help="Để an toàn cho tài khoản, nên để từ 15s trở lên.")
            if df is not None:
                mins, secs = divmod(len(df) * delay, 60)
                st.markdown(f"<div style='padding:12px; background:#eff6ff; border-radius:8px; color:#1d4ed8; font-size:13px; font-weight:500;'>⏱ Dự kiến hoàn thành trong: <b>{mins} phút {secs} giây</b></div>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col_content:
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.markdown('<div class="pill-header bh-green">2. Soạn Thông Điệp</div>', unsafe_allow_html=True)
            subject = st.text_input("Tiêu đề chiến dịch:")
            
            templates = {
                "Tự soạn mới (Trống)": "",
                "Mẫu: Chào mừng khách hàng": f"Kính chào {{{{name}}}},<br><br>Cảm ơn bạn đã quan tâm đến dịch vụ của chúng tôi. Dưới đây là thông tin chi tiết...",
                "Mẫu: Cập nhật tính năng": f"Chào {{{{name}}}},<br><br>Hệ thống vừa cập nhật một số tính năng mới rất hữu ích dành riêng cho bạn."
            }
            selected_temp = st.selectbox("Sử dụng cấu trúc thư mẫu:", list(templates.keys()))
            
            st.markdown("<p style='font-size: 13px; color: #64748b; margin-top:8px; margin-bottom:8px;'>Nội dung chi tiết (Có thể dán trực tiếp hình ảnh/text từ Website):</p>", unsafe_allow_html=True)
            raw_body = st_quill(value=templates[selected_temp], placeholder="Soạn nội dung...", html=True)
            if not raw_body: raw_body = ""
            st.markdown('</div>', unsafe_allow_html=True)

        sign_html = st.session_state["s_sign"].replace("\n", "<br>")
        full_email_content = f"<div style='font-family:Arial, sans-serif; line-height:1.6; color:#334155;'>{raw_body}<br><br><div style='color:#94a3b8; font-size:13px; border-top:1px solid #f1f5f9; padding-top:16px;'>{sign_html}</div></div>"
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # SỬA LỖI HIỂN THỊ HTML CHO BẢNG CẨM NANG AN TOÀN
        col_action1, col_action2 = st.columns([1.5, 1])
        with col_action1:
            st.markdown("""
<div style="background: rgba(255,255,255,0.7); border: 1px solid rgba(255,255,255,0.5); backdrop-filter: blur(10px); border-radius: 16px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
    <h4 style="margin-top:0; color:#0f172a; font-size:16px;">🛡️ Cẩm nang An toàn Tài khoản</h4>
    <table style="width:100%; border-collapse: collapse; font-size: 14px; text-align: left;">
        <tr style="border-bottom: 1px solid rgba(0,0,0,0.1); color:#64748b;"><th style="padding: 10px 0;">Loại tài khoản</th><th style="padding: 10px 0;">Số lượng an toàn / Ngày</th></tr>
        <tr style="border-bottom: 1px solid rgba(0,0,0,0.05);"><td style="padding: 12px 0; font-weight: 600;">Gmail mới tạo</td><td style="padding: 12px 0; color: #f59e0b; font-weight: 700;">20 - 50 mail</td></tr>
        <tr style="border-bottom: 1px solid rgba(0,0,0,0.05);"><td style="padding: 12px 0; font-weight: 600;">Gmail dùng lâu</td><td style="padding: 12px 0; color: #10b981; font-weight: 700;">200 - 300 mail</td></tr>
        <tr><td style="padding: 12px 0; font-weight: 600;">Google Workspace</td><td style="padding: 12px 0; color: #3b82f6; font-weight: 700;">500 - 1000 mail</td></tr>
    </table>
</div>
""", unsafe_allow_html=True)

        with col_action2:
            st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
            if st.button("🚀 BẮT ĐẦU CHẠY CHIẾN DỊCH NGAY", type="primary", use_container_width=True):
                if df is None or not subject: st.error("⚠️ Vui lòng cung cấp File danh sách và Tiêu đề!")
                elif not SYS_EMAIL or not SYS_PWD: st.error("⚠️ Chưa cấu hình Email gửi ở mục Cài Đặt!")
                else:
                    progress = st.progress(0); log = st.expander("📋 Nhật ký hệ thống", expanded=True)
                    
                    soup = BeautifulSoup(full_email_content, "html.parser")
                    for tag in soup(["script", "style", "meta", "noscript", "iframe"]): tag.decompose()
                    inline_images = []; img_counter = 0
                    
                    for img in soup.find_all("img"):
                        src = img.get("src", "")
                        if src.startswith("http"):
                            img.attrs = {"src": src, "style": "max-width: 100%; display: block; border-radius:8px;"}
                        elif src.startswith("data:image") and img_counter < 2:
                            try:
                                h, e = src.split(",", 1); img_data = base64.b64decode(e); img_counter += 1
                                cid = f"img_inline_{img_counter}"; inline_images.append({"cid": cid, "data": img_data, "type": "png"})
                                img.attrs = {"src": f"cid:{cid}", "style": "max-width: 100%; display: block; border-radius:8px;"}
                            except: img.decompose()
                        else: img.decompose()

                    prepared_html_template = str(soup) 
                    run_tk = current_user_data.get("tele_token", ""); run_id = current_user_data.get("tele_chat_id", "")
                    send_tele_msg(run_tk, run_id, f"🚀 <b>BẮT ĐẦU CHIẾN DỊCH</b>\n👤 User: {st.session_state['current_user']}")
                    
                    success_list, error_list = [], []

                    for index, row in df.iterrows():
                        try:
                            target_email = str(row.get(next((c for c in df.columns if c.lower() in ["email", "mail"]), None), row.iloc[0])).strip()
                            target_name = str(row.get(next((c for c in df.columns if c.lower() in ["name", "tên"]), None), "Quý khách"))
                            
                            msg_root = MIMEMultipart("mixed") 
                            msg_root["From"] = f"{st.session_state['s_name']} <{SYS_EMAIL}>"
                            msg_root["To"] = target_email; msg_root["Subject"] = subject
                            
                            msg_related = MIMEMultipart("related"); msg_root.attach(msg_related)
                            msg_related.attach(MIMEText(prepared_html_template.replace("{{name}}", target_name), "html", "utf-8"))
                            
                            for i in inline_images:
                                ip = MIMEImage(i["data"], _subtype=i["type"]); ip.add_header("Content-ID", f"<{i['cid']}>"); msg_related.attach(ip)
                            if attachments:
                                for f in attachments:
                                    p = MIMEBase("application", "octet-stream"); p.set_payload(f.read())
                                    encoders.encode_base64(p); p.add_header("Content-Disposition", f"attachment; filename={f.name}")
                                    msg_root.attach(p); f.seek(0)
                                    
                            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                                server.starttls(); server.login(SYS_EMAIL, SYS_PWD); server.send_message(msg_root)
                                
                            success_list.append(target_email); log.write(f"✅ Giao thành công: {target_email}")
                        except Exception as e:
                            error_list.append(target_email); log.write(f"❌ Thất bại: {target_email}")
                            
                        progress.progress((index + 1) / len(df)); time.sleep(delay)
                        
                    play_success_sound()
                    st.success("Tất cả email đã được xử lý!")
                    
                    csv_buf = io.BytesIO()
                    pd.DataFrame({"Email": success_list + error_list, "Kết quả": ["Thành công"] * len(success_list) + ["Lỗi"] * len(error_list)}).to_csv(csv_buf, index=False, encoding="utf-8-sig")
                    send_tele_msg(run_tk, run_id, f"📊 <b>TỔNG KẾT</b>\n✅ Thành công: {len(success_list)}\n❌ Lỗi: {len(error_list)}")
                    send_tele_file(run_tk, run_id, csv_buf.getvalue(), "ket_qua.csv")
                    st.download_button("TẢI BÁO CÁO EXCEL (.CSV)", data=csv_buf.getvalue(), file_name="ket_qua.csv")

    # 3. LỊCH SỬ NẠP TIỀN
    elif menu == "📊 Quản Lý Giao Dịch":
        st.markdown('<div class="gradient-text" style="font-size: 28px;">Lịch sử Nạp quỹ</div><div style="color:#64748b; font-size: 14px; margin-bottom: 24px;">Theo dõi các biến động số dư tài khoản của bạn</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="modern-card">', unsafe_allow_html=True)
        h_list = []; chart_data = []; cur_u = st.session_state['current_user'].upper()
        
        for l in logs_db:
            if cur_u in str(l.get('raw_data','')).upper():
                try:
                    pld = json.loads(l.get('raw_data','{}')); val_int = int(pld.get('transferAmount', 0)); amt = f"{val_int:,} VNĐ"
                except: val_int = 0; amt = "---"
                
                status = str(l.get('status', ''))
                if "Thành công" in status: 
                    status = "✅ Thành công"
                    if val_int > 0: chart_data.append({"Ngày": l.get('time', '').split(" ")[0], "VND": val_int})
                elif "Lỗi" in status: status = "❌ " + status
                h_list.append({"Thời gian": l.get('time', ''), "Số tiền": amt, "Trạng thái": status})

        if not h_list: 
            # SỬA LỖI TRẠNG THÁI RỖNG
            st.markdown("""
<div style='text-align:center; padding: 60px 20px;'>
    <div style='font-size: 60px; margin-bottom:16px;'>🪹</div>
    <div style='color:#334155; font-weight:600; font-size:18px; margin-bottom:8px;'>Chưa có dữ liệu giao dịch</div>
    <div style='color:#94a3b8; font-size: 14px;'>Hãy thực hiện khoản nạp đầu tiên để kích hoạt thẻ VIP của hệ thống.</div>
</div>
""", unsafe_allow_html=True)
        else:
            if chart_data:
                st.markdown("<p style='font-size:14px; font-weight:600; color:#334155; margin-bottom:16px;'>📈 Lưu lượng nạp tiền gần đây</p>", unsafe_allow_html=True)
                df_chart = pd.DataFrame(chart_data).groupby("Ngày").sum()
                st.bar_chart(df_chart, color="#3b82f6", use_container_width=True)
                st.markdown("<hr style='border:none; border-top:1px solid #f1f5f9; margin: 24px 0;'>", unsafe_allow_html=True)

            st.dataframe(pd.DataFrame(h_list), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # 4. CÀI ĐẶT HỆ THỐNG
    elif menu == "⚙️ Cài Đặt Hệ Thống":
        st.markdown('<div class="gradient-text" style="font-size: 28px;">Cấu Hình Nâng Cao</div><div style="color:#64748b; font-size: 14px; margin-bottom: 24px;">Quản lý kết nối API và chữ ký Email</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.markdown('<div class="pill-header bh-blue">📧 Thông tin gửi thư</div>', unsafe_allow_html=True)
            st.session_state["s_name"] = st.text_input("Tên định danh người gửi:", value=st.session_state["s_name"])
            st.markdown(f"<div style='font-size:13px; color:#64748b; padding:12px; background:#f8fafc; border-radius:8px; border:1px solid #e2e8f0; margin-top:10px;'>Hệ thống SMTP đang liên kết với hòm thư Admin: <b>{SYS_EMAIL}</b></div>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
                
        with c2:
            st.markdown('<div class="modern-card">', unsafe_allow_html=True)
            st.markdown('<div class="pill-header bh-blue">🔔 Thông báo Telegram & Chữ ký</div>', unsafe_allow_html=True)
            tk = st.text_input("Mã Bot Token:", value=current_user_data.get("tele_token", ""), type="password")
            cid = st.text_input("ID Đoạn chat (Chat ID):", value=current_user_data.get("tele_chat_id", ""))
            st.session_state["s_sign"] = st.text_area("Cấu hình chữ ký cuối Email:", value=st.session_state["s_sign"], height=100)
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Lưu thay đổi", type="primary", use_container_width=True):
                if save_config_api(st.session_state["current_user"], tk, cid): 
                    st.toast("Lưu cấu hình thành công", icon="✅")
            st.markdown('</div>', unsafe_allow_html=True)

# NÚT LIÊN HỆ NỔI (Zalo & Telegram)
st.markdown("""<div class="floating-container"><a href="https://zalo.me/0935748199" target="_blank" class="float-btn"><img src="https://upload.wikimedia.org/wikipedia/commons/9/91/Icon_of_Zalo.svg" width="28"></a><a href="https://t.me/BulkMail_Pro" target="_blank" class="float-btn"><img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg" width="28"></a></div>""", unsafe_allow_html=True)
