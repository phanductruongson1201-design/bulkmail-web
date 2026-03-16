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
st.set_page_config(page_title="BulkMail Pro - Bứt Phá Doanh Thu", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

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
# GIAO DIỆN CSS MỚI ĐÃ SỬA LỖI ẨN MENU VÀ XÓA TOOLBAR
# ==========================================
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; color: #334155; }
    .stApp { background-color: #f4f7fe; } 
    
    /* 🌟 KHẮC PHỤC LỖI KHÔNG CLICK ĐƯỢC VÀ XÓA SẠCH BIỂU TƯỢNG SHARE/GITHUB */
    #MainMenu, footer, .stDeployButton, [data-testid="viewerBadge"], 
    [data-testid="stHeaderActionElements"], [data-testid="stToolbar"], [data-testid="stStatusWidget"],
    iframe[title="Streamlit Toolbar"] {
        display: none !important; 
        visibility: hidden !important;
    }
    
    [data-testid="stHeader"] {background: transparent !important; pointer-events: none;} 
    [data-testid="collapsedControl"] {pointer-events: auto; background: white; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);} 
    
    .block-container { padding-top: 1rem !important; padding-bottom: 3rem !important; max-width: 98% !important;}
    
    /* 🌟 ĐỒNG BỘ CHIỀU CAO CÁC NÚT TRÊN TOPBAR (42px) */
    .topbar-wallet { 
        border: 1px solid #3b82f6; color: #3b82f6; padding: 0 16px; border-radius: 6px; 
        font-weight: 700; font-size: 14px; display: inline-flex; align-items: center; 
        gap: 8px; background: white; cursor: pointer; transition: all 0.2s; height: 42px;
    }
    .topbar-wallet:hover { background: #eff6ff; }
    
    /* Làm đẹp Selectbox Tìm Kiếm */
    div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        border: 1px solid #f97316 !important;
        background-color: white !important;
        border-radius: 6px !important;
        min-height: 42px !important;
        cursor: pointer;
    }
    
    /* Tùy chỉnh Nút Popover (User Profile) */
    button[data-testid="baseButton-popover"] { 
        border: 1px solid #e2e8f0 !important; background: white !important; 
        color: #1e293b !important; font-weight: 600 !important; font-size: 15px !important; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important; padding: 0 16px !important; 
        height: 42px !important; border-radius: 6px !important; transition: all 0.2s;
    }
    button[data-testid="baseButton-popover"]:hover { border-color: #cbd5e1 !important; color: #2563eb !important;}
    
    /* Giao diện Dropdown Menu (Popover Body) */
    div[data-testid="stPopoverBody"] { padding: 10px 0 !important; border-radius: 8px !important; border: 1px solid #e2e8f0 !important; box-shadow: 0 10px 25px rgba(0,0,0,0.1) !important; width: 220px !important; }
    .dropdown-item { padding: 12px 20px; font-size: 15px; color: #334155; font-weight: 500; display: flex; align-items: center; gap: 12px; cursor: pointer; transition: background 0.2s; border-bottom: 1px solid #f1f5f9; }
    .dropdown-item:hover { background: #f8fafc; color: #2563eb; }
    .dropdown-item i { width: 20px; text-align: center; color: #64748b; font-size: 16px;}
    .dropdown-item:hover i { color: #2563eb; }
    
    /* CSS cho nút Logout trong Popover */
    .logout-btn-container button { width: 100% !important; background: transparent !important; border: none !important; color: #475569 !important; text-align: left !important; padding: 12px 20px !important; font-size: 15px !important; font-weight: 500 !important; justify-content: flex-start !important; box-shadow: none !important; }
    .logout-btn-container button:hover { background: #f8fafc !important; color: #e11d48 !important; }
    .logout-btn-container button p { margin: 0; display: flex; align-items: center; gap: 12px; }

    /* Layout Thẻ Sản phẩm (Store Grid) */
    .store-card { background: white; border-radius: 8px; border: 1px solid #e2e8f0; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); transition: all 0.3s ease; height: 100%; display: flex; flex-direction: column; justify-content: space-between; }
    .store-card:hover { box-shadow: 0 10px 20px rgba(0,0,0,0.06); border-color: #cbd5e1; transform: translateY(-3px); }
    .price-tag { border: 1px solid #ef4444; color: #ef4444; padding: 4px 12px; border-radius: 4px; font-weight: 700; font-size: 14px; display: inline-block; margin-top: 15px; margin-bottom: 10px; }
    .stock-tag { border: 1px solid #10b981; color: #10b981; padding: 4px 12px; border-radius: 4px; font-weight: 600; font-size: 13px; display: inline-block; }
    
    /* Nút Mua (Xanh dương) */
    .btn-buy { background: #3b82f6 !important; color: white !important; font-weight: 700 !important; border: none !important; border-radius: 4px !important; padding: 10px 20px !important; width: 100%; box-shadow: 0 4px 6px rgba(59, 130, 246, 0.2) !important; transition: all 0.2s; }
    .btn-buy:hover { background: #2563eb !important; box-shadow: 0 6px 12px rgba(59, 130, 246, 0.3) !important; }

    /* Sidebar UI/UX */
    [data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #f1f5f9; box-shadow: 4px 0 15px rgba(0,0,0,0.05); transition: width 0.3s ease-in-out !important;}
    div[role="radiogroup"] > label { padding: 12px 16px; border-radius: 8px; margin-bottom: 4px; transition: all 0.2s ease; border: 1px solid transparent; cursor: pointer; }
    div[role="radiogroup"] > label:hover { background-color: #f8fafc; }
    div[role="radiogroup"] > label[data-checked="true"] { background: #eff6ff; border-left: 4px solid #2563eb; border-radius: 4px 8px 8px 4px; }
    div[role="radiogroup"] > label > div:first-child { display: none; } 
    div[role="radiogroup"] > label p { font-weight: 600 !important; color: #475569 !important; font-size: 14px !important; margin: 0 !important; }
    div[role="radiogroup"] > label[data-checked="true"] p { color: #1d4ed8 !important; font-weight: 700 !important; }

    .logo-container { display: flex; justify-content: center; align-items: center; margin-bottom: 24px; }
    .logo-container img { width: 70px; height: 70px; border-radius: 16px; object-fit: cover; box-shadow: 0 4px 10px rgba(0,0,0,0.08); border: 2px solid #ffffff; }
    .alt-logo { width: 70px; height: 70px; border-radius: 16px; background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white; display: flex; justify-content: center; align-items: center; font-weight: 800; font-size: 12px; text-align: center; box-shadow: 0 4px 10px rgba(37,99,235,0.2); border: 2px solid #ffffff; }
</style>
""", unsafe_allow_html=True)

# Khởi tạo Session
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "otp_verified" not in st.session_state: st.session_state["otp_verified"] = False
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
# 1. ĐĂNG NHẬP
# ==========================================
if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div style="background:white; padding:40px; border-radius:16px; box-shadow:0 10px 25px rgba(0,0,0,0.05); margin-top:50px;">', unsafe_allow_html=True)
        logo_b64 = get_image_base64(LOGO_URL)
        if logo_b64: st.markdown(f'<div class="logo-container"><img src="data:image/png;base64,{logo_b64}"></div>', unsafe_allow_html=True)
        else: st.markdown('<div class="logo-container"><div class="alt-logo">TRƯỜNG SƠN<br>MARKETING</div></div>', unsafe_allow_html=True)
            
        st.markdown('<h2 style="text-align:center; color:#0f172a; margin-bottom:8px; font-size:26px;">Đăng Nhập Hệ Thống</h2>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; color:#64748b; margin-bottom:24px; font-size:14px;">Quản lý dịch vụ BulkMail Pro</p>', unsafe_allow_html=True)
        
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
                    st.error("Thông খুন tin đăng nhập chưa chính xác!")

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
                    st.success("Đăng ký thành công! Vui lòng đăng nhập.")

        with tab_forgot:
            st.info("Vui lòng liên hệ Admin qua Zalo để cấp lại mật khẩu.")
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
    
    if st.session_state["previous_balance"] is None: st.session_state["previous_balance"] = balance
    elif balance > st.session_state["previous_balance"]:
        play_success_sound(); st.balloons()
        st.toast(f"Cộng thành công {balance - st.session_state['previous_balance']:,} VNĐ!", icon="💳")
        st.session_state["previous_balance"] = balance
        st.session_state["show_deposit_form"] = False; st.session_state["show_qr"] = False

    # ========================================================
    # THANH TOPBAR ĐIỀU HƯỚNG CHUẨN ẢNH ĐÃ SỬA LỖI
    # ========================================================
    top1, top2, top3, top4 = st.columns([1.5, 4.5, 1, 2])
    
    with top1:
        st.markdown(f'<div class="topbar-wallet"><i class="fa-solid fa-wallet"></i> Ví: {balance:,}</div>', unsafe_allow_html=True)
    with top2:
        st.selectbox("Tìm kiếm", ["TÌM KIẾM NHANH SẢN PHẨM...", "🔥 Gói Nạp 100K Hệ Thống", "🔥 Gói Nạp 500K Cấp Độ Bạc", "Tùy chọn số tiền nạp"], label_visibility="collapsed")
    with top3:
        st.markdown('<div style="display:flex; gap:15px; font-size:18px; color:#64748b; height:42px; align-items:center; justify-content:flex-end;"><i class="fa-solid fa-moon cursor-pointer hover:text-blue-500"></i><i class="fa-regular fa-bell cursor-pointer hover:text-blue-500"></i></div>', unsafe_allow_html=True)
    with top4:
        with st.popover(f"👨🏻‍💼 {st.session_state['current_user']}"):
            st.markdown("""
            <div class="dropdown-item"><i class="fa-regular fa-circle-user"></i> Trang cá nhân <span style="margin-left:auto; color:#facc15;"><i class="fa-solid fa-crown"></i></span></div>
            <div class="dropdown-item"><i class="fa-solid fa-pen-to-square"></i> Thay đổi mật khẩu</div>
            <div class="dropdown-item"><i class="fa-solid fa-file-invoice"></i> Nhật ký hoạt động</div>
            <div class="dropdown-item"><i class="fa-solid fa-money-bill-transfer"></i> Biến động số dư</div>
            <div class="dropdown-item"><i class="fa-solid fa-shield-halved"></i> Bảo mật</div>
            """, unsafe_allow_html=True)
            
            st.markdown('<div class="logout-btn-container">', unsafe_allow_html=True)
            if st.button("🚪 Đăng xuất", use_container_width=True):
                st.session_state["logged_in"] = False; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<hr style="margin: 0 0 20px 0; border: none; border-bottom: 2px solid #e2e8f0;">', unsafe_allow_html=True)

    # ========================================================
    # SIDEBAR
    # ========================================================
    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        logo_b64 = get_image_base64(LOGO_URL)
        if logo_b64: st.markdown(f'<div class="logo-container"><img src="data:image/png;base64,{logo_b64}"></div>', unsafe_allow_html=True)
        else: st.markdown('<h3 style="text-align:center; color:#1e40af; font-weight:800;">BULKMAIL</h3>', unsafe_allow_html=True)
        
        st.markdown("<p style='font-size:11px; font-weight:700; color:#94a3b8; text-transform:uppercase; margin-bottom:8px; margin-left:12px;'>Quản lý</p>", unsafe_allow_html=True)
        menu = st.radio("", ["🏠 Cửa Hàng Dịch Vụ", "✉️ Gửi Mail Hàng Loạt", "📊 Lịch Sử Giao Dịch"], label_visibility="collapsed")

    # ========================================================
    # NỘI DUNG CHÍNH 
    # ========================================================

    # 1. CỬA HÀNG DỊCH VỤ (Mô phỏng ảnh Store)
    if menu == "🏠 Cửa Hàng Dịch Vụ":
        st.markdown('<div style="background:#1e3a8a; color:white; padding:15px 20px; font-size:18px; font-weight:700; border-radius:8px 8px 0 0; margin-bottom:20px;"><i class="fa-solid fa-layer-group"></i> Dịch Vụ BulkMail Hệ Thống</div>', unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3, gap="medium")
        with c1:
            st.markdown("""
            <div class="store-card">
                <div>
                    <h4 style="color:#0f172a; font-size:16px; margin:0 0 10px 0;"><span style="color:#ef4444; font-size:12px;">🔥 HOT</span> Gói Nạp 100K Hệ Thống</h4>
                    <p style="font-size:13px; color:#64748b; font-style:italic; margin:0;">- Hệ thống gửi tự động Server riêng<br>- Không giới hạn số lượng thiết bị</p>
                    <div class="price-tag">Giá: 100,000đ</div>
                    <br><div class="stock-tag">Còn lại: Không giới hạn</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🛒 NẠP NGAY 100K", key="btn1"): 
                st.session_state["deposit_amount"] = 100000; st.session_state["show_qr"] = True; st.session_state["qr_expire_time"] = time.time() + 600; st.rerun()

        with c2:
            st.markdown("""
            <div class="store-card">
                <div>
                    <h4 style="color:#0f172a; font-size:16px; margin:0 0 10px 0;"><span style="color:#ef4444; font-size:12px;">🔥 HOT</span> Gói Nạp 500K Cấp Độ Bạc</h4>
                    <p style="font-size:13px; color:#64748b; font-style:italic; margin:0;">- Tự động nâng cấp tài khoản Bạc<br>- Hỗ trợ cài đặt kỹ thuật 24/7</p>
                    <div class="price-tag">Giá: 500,000đ</div>
                    <br><div class="stock-tag">Còn lại: 15 Slots</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🛒 NẠP NGAY 500K", key="btn2"):
                st.session_state["deposit_amount"] = 500000; st.session_state["show_qr"] = True; st.session_state["qr_expire_time"] = time.time() + 600; st.rerun()

        with c3:
            st.markdown("""
            <div class="store-card">
                <div>
                    <h4 style="color:#0f172a; font-size:16px; margin:0 0 10px 0;"><span style="color:#ef4444; font-size:12px;">🔥 HOT</span> Gói Tùy Chọn Số Tiền</h4>
                    <p style="font-size:13px; color:#64748b; font-style:italic; margin:0;">- Bạn có thể nạp số tiền bất kỳ<br>- Phù hợp nhu cầu cá nhân hóa</p>
                    <div class="price-tag">Giá: Tùy Chọn</div>
                    <br><div class="stock-tag">Tối thiểu: 10.000đ</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🛒 NHẬP SỐ TIỀN KHÁC", key="btn3"):
                st.session_state["show_deposit_form"] = True; st.rerun()

        if st.session_state.get("show_deposit_form"):
            st.markdown('<hr><div style="background:white; padding:20px; border-radius:8px; border:1px solid #e2e8f0; width:50%;">', unsafe_allow_html=True)
            st.markdown('<h4 style="margin-top:0;">Nhập số tiền muốn nạp</h4>', unsafe_allow_html=True)
            amount_input = st.number_input("Số tiền (VNĐ)", value=100000, step=10000, min_value=0, label_visibility="collapsed")
            col1, col2 = st.columns(2)
            if col1.button("Hủy"): st.session_state["show_deposit_form"] = False; st.rerun()
            if col2.button("Tạo mã QR", type="primary"):
                if amount_input < 10000: st.toast("Tối thiểu 10.000đ", icon="⚠️")
                else: st.session_state["deposit_amount"] = amount_input; st.session_state["show_qr"] = True; st.session_state["show_deposit_form"] = False; st.session_state["qr_expire_time"] = time.time() + 600; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.get("show_qr"):
            time_left = int(st.session_state["qr_expire_time"] - time.time())
            if time_left <= 0: st.warning("Mã QR đã hết hạn."); st.session_state["show_qr"] = False
            else:
                st.markdown("<hr><div style='background:white; border-radius:8px; padding:20px; border: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
                cq, ci = st.columns([1, 2], gap="large")
                SEPAY_ACC = "VQRQAHQHF1360"; SEPAY_BANK = "MBBank"; MY_NAME = "PHAN DUC TRUONG SON"
                amt = st.session_state["deposit_amount"]; cont = f"NAP {st.session_state['current_user']}"
                qr_url = f"https://qr.sepay.vn/img?acc={SEPAY_ACC}&bank={SEPAY_BANK}&amount={amt}&des={cont.replace(' ', '%20')}"
                
                with cq:
                    st.image(qr_url, use_column_width=True)
                    components.html(f"<div style='text-align:center; color:#ef4444; font-weight:700; font-size:14px; background:#fee2e2; padding:6px; border-radius:4px;'>Hết hạn sau: <span id='t'></span></div><script>var l={time_left};setInterval(function(){{if(l<=0)document.getElementById('t').innerHTML='00:00';else{{var m=Math.floor(l/60),s=l%60;document.getElementById('t').innerHTML=m+':'+(s<10?'0':'')+s;l--;}}}},1000);</script>", height=40)
                with ci:
                    st.markdown(f"<h3 style='margin-top:0; color:#1e40af;'>Thanh toán quét mã QR</h3>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size:15px; color:#334155; margin-bottom:8px;'>Ngân hàng: <b>{SEPAY_BANK}</b></div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size:15px; color:#334155; margin-bottom:8px;'>Chủ tài khoản: <b>{MY_NAME}</b></div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size:15px; color:#334155; margin-bottom:8px;'>Số tài khoản: <b style='color:#ef4444'>{SEPAY_ACC}</b></div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='font-size:15px; color:#334155; margin-bottom:16px;'>Số tiền cần nạp: <b style='color:#ef4444; font-size:20px;'>{amt:,}đ</b></div>", unsafe_allow_html=True)
                    st.markdown("<div style='font-size:14px; font-weight:600;'>Nội dung chuyển khoản (bắt buộc):</div>", unsafe_allow_html=True)
                    st.code(cont, language="text")
                    if st.button("🔄 Đã chuyển khoản xong - Làm mới số dư", type="primary"): st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    # 2. GỬI MAIL 
    elif menu == "✉️ Gửi Mail Hàng Loạt":
        col_data, col_content = st.columns([1, 1.2], gap="large")
        with col_data:
            st.markdown('<div style="background:white; padding:20px; border-radius:8px; border:1px solid #e2e8f0; margin-bottom:20px;">', unsafe_allow_html=True)
            st.markdown('<h4 style="margin-top:0; border-bottom:1px solid #e2e8f0; padding-bottom:10px;"><i class="fa-solid fa-file-excel text-blue-500"></i> Dữ liệu khách hàng</h4>', unsafe_allow_html=True)
            up = st.file_uploader("Tải lên danh sách nhận (.xlsx, .csv)", type=["csv", "xlsx"])
            df = pd.read_excel(up) if up and up.name.endswith("xlsx") else (pd.read_csv(up) if up else None)
            attachments = st.file_uploader("Tệp đính kèm", accept_multiple_files=True)
            delay = st.number_input("Nghỉ/Mail (Giây)", value=15, min_value=5)
            st.markdown('</div>', unsafe_allow_html=True)

        with col_content:
            st.markdown('<div style="background:white; padding:20px; border-radius:8px; border:1px solid #e2e8f0;">', unsafe_allow_html=True)
            st.markdown('<h4 style="margin-top:0; border-bottom:1px solid #e2e8f0; padding-bottom:10px;"><i class="fa-solid fa-envelope-open-text text-green-500"></i> Soạn Thông Điệp</h4>', unsafe_allow_html=True)
            subject = st.text_input("Tiêu đề chiến dịch:")
            templates = {"Tự soạn mới": "", "Khuyến mãi Tết": f"Kính chào {{{{name}}}}, gửi bạn ưu đãi...", "Thư cảm ơn": f"Cảm ơn {{{{name}}}} đã đồng hành..."}
            selected_temp = st.selectbox("Mẫu nội dung:", list(templates.keys()))
            raw_body = st_quill(value=templates[selected_temp], placeholder="Soạn nội dung...", html=True)
            if not raw_body: raw_body = ""
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div style="background:white; padding:20px; border-radius:8px; border:1px solid #e2e8f0; margin-top:20px;">', unsafe_allow_html=True)
        st.markdown('<h4 style="margin-top:0; border-bottom:1px solid #e2e8f0; padding-bottom:10px;"><i class="fa-solid fa-gears text-purple-500"></i> Cấu Hình SMTP & Báo Cáo</h4>', unsafe_allow_html=True)
        cfg1, cfg2 = st.columns(2, gap="large")
        with cfg1:
            st.session_state["s_name"] = st.text_input("Tên người gửi:", value=st.session_state["s_name"])
            st.session_state["s_email"] = st.text_input("Tài khoản Gmail:", value=st.session_state["s_email"])
            st.session_state["s_pwd"] = st.text_input("Mật khẩu ứng dụng:", type="password", value=st.session_state["s_pwd"])
        with cfg2:
            tk_input = st.text_input("Bot Token (Telegram):", value=current_user_data.get("tele_token", ""), type="password")
            cid_input = st.text_input("Chat ID (Telegram):", value=current_user_data.get("tele_chat_id", ""))
            st.session_state["s_sign"] = st.text_area("Chữ ký cuối Email:", value=st.session_state["s_sign"])
        if st.button("Lưu cấu hình", type="secondary"):
            if save_config_api(st.session_state["current_user"], tk_input, cid_input): st.toast("Đã lưu!", icon="✅")
        st.markdown('</div>', unsafe_allow_html=True)

        sign_html = st.session_state["s_sign"].replace("\n", "<br>")
        full_email_content = f"<div style='font-family:Arial; line-height:1.6; color:#333;'>{raw_body}<br><br><div style='color:#666; font-size:13px; border-top:1px solid #eee; padding-top:10px;'>{sign_html}</div></div>"
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 CHẠY CHIẾN DỊCH", type="primary", use_container_width=True):
            if df is None or not subject: st.error("⚠️ Điền đủ File và Tiêu đề!")
            elif not st.session_state["s_email"] or not st.session_state["s_pwd"]: st.error("⚠️ Nhập Email và Mật khẩu!")
            else:
                progress = st.progress(0); log = st.expander("Nhật ký gửi", expanded=True)
                soup = BeautifulSoup(full_email_content, "html.parser")
                for tag in soup(["script", "style"]): tag.decompose()
                inline_images = []; img_counter = 0
                for img in soup.find_all("img"):
                    src = img.get("src", "")
                    if src.startswith("http"): img.attrs = {"src": src, "style": "max-width: 100%; border-radius:8px;"}
                    elif src.startswith("data:image") and img_counter < 2:
                        try:
                            h, e = src.split(",", 1); img_data = base64.b64decode(e); img_counter += 1
                            cid = f"img_inline_{img_counter}"; inline_images.append({"cid": cid, "data": img_data, "type": "png"})
                            img.attrs = {"src": f"cid:{cid}", "style": "max-width: 100%; border-radius:8px;"}
                        except: img.decompose()
                    else: img.decompose()

                prepared_html_template = str(soup) 
                send_tele_msg(tk_input, cid_input, f"🚀 <b>BẮT ĐẦU CHIẾN DỊCH</b>\n👤 User: {st.session_state['current_user']}")
                success_list, error_list = [], []

                for index, row in df.iterrows():
                    try:
                        target_email = str(row.get(next((c for c in df.columns if c.lower() in ["email", "mail"]), None), row.iloc[0])).strip()
                        target_name = str(row.get(next((c for c in df.columns if c.lower() in ["name", "tên"]), None), "Quý khách"))
                        
                        msg_root = MIMEMultipart("mixed") 
                        msg_root["From"] = f"{st.session_state['s_name']} <{st.session_state['s_email']}>"
                        msg_root["To"] = target_email; msg_root["Subject"] = subject
                        msg_related = MIMEMultipart("related"); msg_root.attach(msg_related)
                        msg_related.attach(MIMEText(prepared_html_template.replace("{{name}}", target_name), "html", "utf-8"))
                        
                        for i in inline_images:
                            ip = MIMEImage(i["data"], _subtype=i["type"]); ip.add_header("Content-ID", f"<{i['cid']}>"); msg_related.attach(ip)
                        if attachments:
                            for f in attachments:
                                p = MIMEBase("application", "octet-stream"); p.set_payload(f.read())
                                encoders.encode_base64(p); p.add_header("Content-Disposition", f"attachment; filename={f.name}"); msg_root.attach(p); f.seek(0)
                                
                        with smtplib.SMTP("smtp.gmail.com", 587) as server:
                            server.starttls(); server.login(st.session_state["s_email"], st.session_state["s_pwd"]); server.send_message(msg_root)
                        success_list.append(target_email); log.write(f"✅ Giao thành công: {target_email}")
                    except Exception as e:
                        error_list.append(target_email); log.write(f"❌ Lỗi: {target_email}")
                    progress.progress((index + 1) / len(df)); time.sleep(delay)
                    
                play_success_sound()
                st.success("Hoàn tất chiến dịch!")
                csv_buf = io.BytesIO()
                pd.DataFrame({"Email": success_list + error_list, "Kết quả": ["Thành công"] * len(success_list) + ["Lỗi"] * len(error_list)}).to_csv(csv_buf, index=False, encoding="utf-8-sig")
                send_tele_msg(tk_input, cid_input, f"📊 <b>TỔNG KẾT</b>\n✅ Thành công: {len(success_list)}\n❌ Lỗi: {len(error_list)}")
                send_tele_file(tk_input, cid_input, csv_buf.getvalue(), "ket_qua.csv")
                st.download_button("TẢI BÁO CÁO (.CSV)", data=csv_buf.getvalue(), file_name="ket_qua.csv")

    # 3. LỊCH SỬ
    elif menu == "📊 Lịch Sử Giao Dịch":
        st.markdown('<div style="background:white; padding:20px; border-radius:8px; border:1px solid #e2e8f0;">', unsafe_allow_html=True)
        st.markdown('<h3 style="margin-top:0; color:#1e40af;">Nhật ký Nạp tiền</h3>', unsafe_allow_html=True)
        h_list = []; chart_data = []; cur_u = st.session_state['current_user'].upper()
        
        for l in logs_db:
            if cur_u in str(l.get('raw_data','')).upper():
                try: pld = json.loads(l.get('raw_data','{}')); val_int = int(pld.get('transferAmount', 0)); amt = f"{val_int:,}đ"
                except: val_int = 0; amt = "---"
                status = str(l.get('status', ''))
                if "Thành công" in status: 
                    status = "✅ Thành công"
                    if val_int > 0: chart_data.append({"Ngày": l.get('time', '').split(" ")[0], "VND": val_int})
                elif "Lỗi" in status: status = "❌ " + status
                h_list.append({"Thời gian": l.get('time', ''), "Số tiền": amt, "Trạng thái": status})

        if not h_list: st.info("Bạn chưa có giao dịch nào.")
        else:
            if chart_data:
                df_chart = pd.DataFrame(chart_data).groupby("Ngày").sum()
                st.bar_chart(df_chart, color="#3b82f6", use_container_width=True)
            st.dataframe(pd.DataFrame(h_list), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
