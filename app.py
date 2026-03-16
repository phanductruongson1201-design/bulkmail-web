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
        body = f"<h3>Chào {username},</h3><p>Mã OTP: <b style='font-size: 20px;'>{otp_code}</b></p>"
        msg.attach(MIMEText(body, "html"))
        s = smtplib.SMTP("smtp.gmail.com", 587); s.starttls(); s.login(SYS_EMAIL, SYS_PWD); s.send_message(msg); s.quit()
        return True
    except: return False

def send_tele_msg(token, chat_id, message):
    if token and chat_id:
        try: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=5)
        except: pass

def get_image_base64(path):
    try:
        with open(path, "rb") as img_file: return base64.b64encode(img_file.read()).decode("utf-8")
    except: return None

def play_success_sound():
    components.html("""<audio autoplay><source src="https://actions.google.com/sounds/v1/cartoon/magic_chime.ogg" type="audio/mpeg"></audio>""", height=0)

# ==========================================
# GIAO DIỆN CSS & HIỆU ỨNG
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif !important; }
    #MainMenu, footer, header, .stDeployButton, [data-testid="viewerBadge"] {display: none !important;}
    .block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; }
    .stApp { background-color: #f8fafc; }
    .gradient-text { background: linear-gradient(90deg, #2563eb 0%, #7c3aed 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; font-size: 46px; margin-bottom: 5px; letter-spacing: -1px; }

    /* CSS cho Huy hiệu VIP lấp lánh */
    .vip-badge {
        display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 800;
        color: white; margin-left: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.15);
        animation: shine 2s infinite; text-transform: uppercase; letter-spacing: 1px;
    }
    .badge-dong { background: linear-gradient(135deg, #cd7f32, #8b5a2b); }
    .badge-bac { background: linear-gradient(135deg, #c0c0c0, #808080); color: #333; }
    .badge-vang { background: linear-gradient(135deg, #FFD700, #FFA500); color: #8B4500; }
    .badge-kimcuong { background: linear-gradient(135deg, #00f2fe, #4facfe); }
    @keyframes shine { 0% { opacity: 0.8; transform: scale(1); } 50% { opacity: 1; transform: scale(1.05); box-shadow: 0 0 15px rgba(255,255,255,0.5); } 100% { opacity: 0.8; transform: scale(1); } }

    div[data-baseweb="tab-list"] { background-color: #f1f5f9 !important; border-radius: 12px !important; padding: 4px !important; gap: 4px !important; border-bottom: none !important; margin-bottom: 20px !important; }
    div[data-baseweb="tab"] { background-color: transparent !important; border-radius: 8px !important; border: none !important; color: #64748b !important; font-weight: 600 !important; font-size: 14px !important; padding: 8px 12px !important; margin: 0 !important; height: auto !important; }
    div[data-baseweb="tab"][aria-selected="true"] { background-color: #ffffff !important; color: #1e40af !important; box-shadow: 0 2px 6px rgba(0,0,0,0.08) !important; }
    div[data-baseweb="tab-highlight"] { display: none !important; }

    .stButton>button[kind="primary"] { background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%) !important; color: white !important; border-radius: 16px; font-weight: 900; font-size: 16px !important; padding: 12px 24px; border: none !important; box-shadow: 0 6px 20px rgba(59,130,246,0.35) !important; transition: all 0.3s ease; text-transform: uppercase; }
    .stButton>button[kind="primary"]:hover { transform: translateY(-4px); box-shadow: 0 8px 25px rgba(59,130,246,0.5) !important; }
    
    .pill-header { color: white; padding: 10px 24px; border-radius: 50px; font-size: 15px; font-weight: 800; margin-bottom: 20px; margin-top: 15px; text-transform: uppercase; letter-spacing: 1px; display: inline-block; text-shadow: 0 2px 4px rgba(0,0,0,0.2); }
    .bg-blue { background: linear-gradient(135deg, #3b82f6, #1d4ed8); }
    .bg-purple { background: linear-gradient(135deg, #a855f7, #6d28d9); }
    .bg-green { background: linear-gradient(135deg, #10b981, #047857); }
    .bg-orange { background: linear-gradient(135deg, #f59e0b, #d97706); }

    .deposit-box { background: white; padding: 25px; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1); margin-bottom: 25px; }
    
    /* Giao diện Metric xịn sò */
    div[data-testid="stMetric"] { background: white; padding: 15px 20px; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); border: 1px solid #f1f5f9; text-align: center; }
    div[data-testid="stMetricValue"] { color: #1e40af !important; font-weight: 900 !important; font-size: 28px !important; }
    div[data-testid="stMetricLabel"] { font-size: 14px !important; color: #64748b !important; font-weight: 700 !important; text-transform: uppercase; }

    .floating-container { position: fixed; bottom: 30px; right: 30px; display: flex; flex-direction: column; gap: 15px; z-index: 999999; }
    .float-btn { width: 55px; height: 55px; border-radius: 50%; box-shadow: 0 10px 25px rgba(0,0,0,0.15); display: flex; justify-content: center; align-items: center; background: white; transition: 0.3s; border: 2px solid #e2e8f0; }
    .float-btn:hover { transform: translateY(-5px); border-color: #3b82f6; }
</style>
""", unsafe_allow_html=True)

# Khởi tạo trạng thái
if "logged_in" not in st.session_state: st.session_state["logged_in"] = False
if "otp_verified" not in st.session_state: st.session_state["otp_verified"] = False
if "show_deposit_form" not in st.session_state: st.session_state["show_deposit_form"] = False
if "show_qr" not in st.session_state: st.session_state["show_qr"] = False
if "deposit_amount" not in st.session_state: st.session_state["deposit_amount"] = 100000
if "qr_expire_time" not in st.session_state: st.session_state["qr_expire_time"] = 0
if "previous_balance" not in st.session_state: st.session_state["previous_balance"] = None 
if "s_name" not in st.session_state: st.session_state["s_name"] = "Trường Sơn Marketing"
if "s_sign" not in st.session_state: st.session_state["s_sign"] = "Trân trọng,\nTrường Sơn Marketing"

LOGO_URL = "logo_moi.png"

# ==========================================
# 1. HỆ THỐNG ĐĂNG NHẬP
# ==========================================
if not st.session_state["logged_in"]:
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown('<div style="max-width:440px; margin:10px auto; padding:35px; background:white; border-radius:24px; box-shadow:0 20px 40px -15px rgba(0,0,0,0.1); border:1px solid #eee;">', unsafe_allow_html=True)
        logo_b64 = get_image_base64(LOGO_URL)
        if logo_b64: st.markdown(f'<div style="display:flex;justify-content:center;margin-bottom:20px;"><img src="data:image/png;base64,{logo_b64}" width="120" style="border-radius:35%;box-shadow:0 10px 25px rgba(59,130,246,0.2);"></div>', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align:center; color:#0f172a; font-weight:900; margin-bottom:5px;">BULKMAIL PRO</h2>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center; color:#64748b; margin-bottom:20px;">Đăng nhập để bắt đầu chiến dịch</p>', unsafe_allow_html=True)
        
        tab_login, tab_reg, tab_forgot = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký", "🔑 Quên MK"])
        all_data = load_data(); users_db = all_data["users"]

        with tab_login:
            log_user = st.text_input("Tên đăng nhập", key="login_u")
            log_pwd = st.text_input("Mật khẩu", type="password", key="login_p")
            if st.button("ĐĂNG NHẬP HỆ THỐNG", type="primary", use_container_width=True):
                if log_user in users_db and users_db[log_user].get("password") == hash_password(log_pwd):
                    st.session_state["current_user"] = log_user; st.session_state["logged_in"] = True; st.rerun()
                else: st.error("❌ Thông tin đăng nhập chưa chính xác!")
        
        with tab_reg:
            reg_user = st.text_input("Tên đăng nhập mới"); reg_email = st.text_input("Email khôi phục"); reg_pwd = st.text_input("Mật khẩu", type="password")
            if st.button("TẠO TÀI KHOẢN", type="primary", use_container_width=True):
                if not reg_user or not reg_pwd: st.warning("⚠️ Điền đủ thông tin!")
                elif reg_user in users_db: st.error("❌ Username đã tồn tại!")
                else: save_user_api(reg_user, hash_password(reg_pwd), reg_email); st.success("✅ Đăng ký thành công!")

        with tab_forgot:
            if not st.session_state["otp_verified"]:
                fu = st.text_input("Username"); fe = st.text_input("Email")
                if st.button("GỬI OTP", use_container_width=True):
                    if fu in users_db and users_db[fu].get("email") == fe:
                        otp = generate_otp()
                        if reset_password_api(fu, fe, hash_password(otp), True) and send_otp_email(fe, fu, otp):
                            st.session_state["otp_sent"] = True; st.success(f"✅ OTP đã gửi tới {fe}")
                    else: st.error("❌ Sai thông tin!")
                if st.session_state.get("otp_sent"):
                    io_otp = st.text_input("Mã OTP 6 số:")
                    if st.button("XÁC THỰC", type="primary", use_container_width=True):
                        if users_db[fu].get("password") == hash_password(io_otp):
                            st.session_state["otp_verified"] = True; st.session_state["target_user"] = fu; st.rerun()
                        else: st.error("❌ OTP sai!")
            else:
                np = st.text_input("Mật khẩu mới", type="password")
                if st.button("ĐỔI MẬT KHẨU", type="primary", use_container_width=True):
                    if reset_password_api(st.session_state["target_user"], users_db[st.session_state["target_user"]]["email"], hash_password(np), False):
                        st.session_state["otp_verified"] = False; st.success("✅ Thành công!")
        st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 2. DASHBOARD CHÍNH
# ==========================================
else:
    all_data = load_data()
    users_db = all_data["users"]
    logs_db = all_data["logs"]
    current_user_data = users_db.get(st.session_state["current_user"], {})
    
    balance = int(float(current_user_data.get("balance", 0)))
    
    # 🌟 CẤP BẬC VIP TỰ ĐỘNG
    if balance < 100000:
        vip_class = "badge-dong"; vip_text = "🥉 Đồng"
    elif balance < 500000:
        vip_class = "badge-bac"; vip_text = "🥈 Bạc"
    elif balance < 2000000:
        vip_class = "badge-vang"; vip_text = "🥇 Vàng"
    else:
        vip_class = "badge-kimcuong"; vip_text = "💎 Kim Cương"

    # ÂM THANH & TỰ ĐỘNG ẨN FORM KHI CỘNG TIỀN
    if st.session_state["previous_balance"] is None:
        st.session_state["previous_balance"] = balance
    elif balance > st.session_state["previous_balance"]:
        play_success_sound()
        st.balloons()
        st.success(f"🎉 THANH TOÁN THÀNH CÔNG! Cộng thêm {balance - st.session_state['previous_balance']:,} VNĐ.")
        st.session_state["previous_balance"] = balance
        st.session_state["show_deposit_form"] = False
        st.session_state["show_qr"] = False

    # HEADER
    head_col1, head_col2 = st.columns([5, 2.5])
    with head_col1:
        st.markdown('<div class="gradient-text">BulkMail Pro</div>', unsafe_allow_html=True)
    with head_col2:
        st.markdown(f"""
        <div style='text-align: right; padding-top: 5px;'>
            <div style='font-weight: 800; color: #0f172a; font-size: 16px;'>👤 {st.session_state['current_user']} <span class="vip-badge {vip_class}">{vip_text}</span></div>
            <div style='color: #047857; font-weight: 900; font-size: 16px; margin: 5px 0;'>💰 Số dư: {balance:,} VNĐ</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state["logged_in"] = False; st.rerun()

    # 🌟 DASHBOARD THỐNG KÊ (Visual Analytics)
    st.markdown("<br>", unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    # Lọc số giao dịch thành công
    my_logs = [l for l in logs_db if st.session_state['current_user'].upper() in str(l.get('raw_data','')).upper() and "Thành công" in str(l.get('status',''))]
    m1.metric(label="Tổng số lần nạp", value=f"{len(my_logs)} Lần", delta="Trạng thái Tốt")
    m2.metric(label="Cấp bậc hiện tại", value=vip_text.split(" ")[1], delta="Tự động gia hạn")
    m3.metric(label="Hạn mức gửi", value="Vô hạn", delta="Hệ thống Pro")
    st.markdown("<br>", unsafe_allow_html=True)

    # TABS
    tab_send, tab_history, tab_config = st.tabs(["✉️ Gửi Email", "📊 Lịch sử nạp", "⚙️ Cài đặt"])

    with tab_send:
        # ========================================================
        # KHỐI GIAO DIỆN NẠP TIỀN
        # ========================================================
        btn_col1, btn_col2 = st.columns([6, 2])
        with btn_col2:
            if st.button("💳 NẠP TIỀN VÀO TÀI KHOẢN", type="primary", use_container_width=True):
                st.session_state["show_deposit_form"] = True
                st.session_state["show_qr"] = False
                
        if st.session_state.get("show_deposit_form"):
            st.markdown('<div class="deposit-box">', unsafe_allow_html=True)
            st.markdown("<h3 style='margin-top:0;'>Nhập số tiền cần nạp</h3><hr style='margin:10px 0;'>", unsafe_allow_html=True)
            
            amount_input = st.number_input("Nhập số tiền (VNĐ)", value=st.session_state.get("deposit_amount", 100000), step=10000, min_value=0)
            
            c_p, c_r = st.columns(2)
            c_p.markdown(f"**Cần thanh toán**<br><h3 style='color:#2563eb; margin:0;'>{amount_input:,}</h3>", unsafe_allow_html=True)
            c_r.markdown(f"**Nhận được**<br><h3 style='color:#ef4444; margin:0;'>{amount_input:,}</h3>", unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            bc1, bc2, bc3 = st.columns([6, 2, 2.5])
            if bc2.button("Hủy bỏ", use_container_width=True): 
                st.session_state["show_deposit_form"] = False; st.rerun()
            if bc3.button("Tiếp tục", type="primary", use_container_width=True):
                if amount_input < 10000: st.error("⚠️ Tối thiểu 10.000 VNĐ")
                else:
                    st.session_state["deposit_amount"] = amount_input
                    st.session_state["show_qr"] = True
                    st.session_state["qr_expire_time"] = time.time() + 600
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.get("show_qr"):
            time_left = int(st.session_state["qr_expire_time"] - time.time())
            if time_left <= 0:
                st.warning("⏳ Mã QR đã hết hạn."); st.session_state["show_qr"] = False
            else:
                st.markdown("<div style='background-color: #fffbeb; border: 1px dashed #fca5a5; border-radius: 12px; padding: 20px; margin-bottom: 25px;'>", unsafe_allow_html=True)
                col_qr, col_info = st.columns([1, 1.5], gap="large")
                
                # THÔNG TIN TÀI KHOẢN NGÂN HÀNG CỦA BẠN (SEPAY)
                SEPAY_ACC = "VQRQAHQHF1360"; SEPAY_BANK = "MBBank"; MY_ACCOUNT_NAME = "PHAN DUC TRUONG SON"
                
                amount = st.session_state["deposit_amount"]
                transfer_content = f"NAP {st.session_state['current_user']}"
                
                qr_url = f"https://qr.sepay.vn/img?acc={SEPAY_ACC}&bank={SEPAY_BANK}&amount={amount}&des={transfer_content.replace(' ', '%20')}"
                
                with col_qr:
                    st.image(qr_url, width=240, caption="Mở App ngân hàng quét mã")
                    components.html(f"""
                        <div style="text-align: center; color: #ef4444; font-weight: 800; font-size: 15px; padding: 8px; background: #fee2e2; border-radius: 8px;">
                            ⏳ Hết hạn sau: <span id="time">10:00</span>
                        </div>
                        <script>
                            var timeLeft = {time_left};
                            var timerId = setInterval(function() {{
                                if (timeLeft <= 0) {{ clearInterval(timerId); document.getElementById("time").innerHTML = "ĐÃ HẾT HẠN"; }} 
                                else {{
                                    var m = Math.floor(timeLeft / 60); var s = timeLeft % 60;
                                    document.getElementById("time").innerHTML = m + ":" + (s < 10 ? "0" : "") + s;
                                    timeLeft--;
                                }}
                            }}, 1000);
                        </script>
                    """, height=50)
                    
                with col_info:
                    st.markdown(f"<h3 style='color: #1e40af; margin-top:0;'>Thông tin chuyển khoản</h3>", unsafe_allow_html=True)
                    st.markdown(f"**🏦 Ngân hàng:** {SEPAY_BANK}<br>**👤 Chủ tài khoản:** {MY_ACCOUNT_NAME}<br>**💰 Số tiền nạp:** <b style='color:#047857; font-size: 18px;'>{amount:,} VNĐ</b>", unsafe_allow_html=True)
                    st.markdown("**📝 Nội dung (Bấm 📋 ở góc phải để Copy):**")
                    st.code(transfer_content, language="text")
                    st.info("💡 Trạng thái: Đang chờ thanh toán. Sau khi chuyển xong, hệ thống sẽ tự động đối soát và báo thành công.")
                    if st.button("🔄 LÀM MỚI SỐ DƯ ĐỂ XÁC NHẬN", type="primary", use_container_width=True): st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        # ========================================================
        # KHỐI GỬI EMAIL 
        # ========================================================
        st.markdown('<div class="pill-header bg-purple">📁 DỮ LIỆU KHÁCH HÀNG</div>', unsafe_allow_html=True)
        col_data, col_content = st.columns([1, 1.2], gap="large")
        
        with col_data:
            up = st.file_uploader("Tải tệp (.xlsx, .csv)", type=["csv", "xlsx"])
            df = pd.read_excel(up) if up and up.name.endswith("xlsx") else (pd.read_csv(up) if up else None)
            attachments = st.file_uploader("📎 Tệp đính kèm", accept_multiple_files=True)
            
            # 🌟 DỰ BÁO ETA BÊN DƯỚI FILE UPLOAD
            delay = st.number_input("⏳ Khoảng nghỉ giữa mỗi Mail (Giây):", value=15, min_value=5)
            if df is not None:
                eta_secs = len(df) * delay
                mins, secs = divmod(eta_secs, 60)
                st.info(f"⚡ **Dự kiến hoàn thành:** {mins} phút {secs} giây")

        with col_content:
            st.markdown('<div class="pill-header bg-green">✍️ SOẠN THÔNG ĐIỆP</div>', unsafe_allow_html=True)
            subject = st.text_input("Tiêu đề Email:")
            
            # 🌟 THƯ VIỆN MẪU (TEMPLATES)
            email_templates = {
                "📝 Tự soạn mới": "",
                "🎁 Thông báo Khuyến Mãi": f"Kính chào Anh/Chị {{{{name}}}},<br><br>Nhân dịp tháng mới, chúng tôi dành tặng Anh/Chị voucher giảm giá đặc biệt...",
                "🤝 Thư Cảm Ơn Khách Hàng": f"Chào {{{{name}}}},<br><br>Cảm ơn bạn đã tin tưởng và đồng hành cùng dịch vụ của chúng tôi thời gian qua...",
                "💼 Giới thiệu Dịch Vụ Mới": f"Kính gửi {{{{name}}}},<br><br>Chúng tôi vừa ra mắt một giải pháp hoàn toàn mới giúp bạn tiết kiệm 50% chi phí..."
            }
            selected_temp = st.selectbox("📚 Chọn mẫu nội dung có sẵn:", list(email_templates.keys()))
            
            st.markdown("<p style='font-size:13px; color:#b91c1c;'>⚠️ LƯU Ý: Vui lòng cuộn chuột trên Web cho ảnh tải hết rồi mới Copy Paste vào đây để tránh lỗi.</p>", unsafe_allow_html=True)
            
            # Truyền giá trị mẫu vào Quill
            raw_body = st_quill(value=email_templates[selected_temp], placeholder="Soạn nội dung hoặc dán từ web vào đây...", html=True, key="quill_editor")
            if not raw_body: raw_body = ""

        sign_html = st.session_state["s_sign"].replace("\n", "<br>")
        full_email_content = f"<div style='font-family:Arial; line-height:1.8; color:#333;'>{raw_body}<br><br><div style='color:#666; border-top:1px solid #eee; padding-top:10px;'>{sign_html}</div></div>"
        
        with st.expander("👁️ Xem trước giao diện thực tế", expanded=False):
            example_name = str(df.iloc[0]["name"]) if df is not None and not df.empty and "name" in df.columns else "Quý khách"
            st.markdown(f"<div style='padding:20px; background:white; border-radius: 8px; border: 1px solid #e2e8f0;'>{full_email_content.replace('{{name}}', f'<b style=\"color:#3b82f6;\">{example_name}</b>')}</div>", unsafe_allow_html=True)

        st.markdown("<hr style='margin: 30px 0;'>", unsafe_allow_html=True)

        # NÚT BẮT ĐẦU GỬI & LÁCH LỖI 5.7.0
        col_action1, col_action2 = st.columns([1.5, 1])
        with col_action1:
            st.markdown("""
            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                <h4 style="margin-top:0; color:#0f172a; font-size:16px;">🛡️ Mức an toàn khuyến nghị</h4>
                <table style="width:100%; border-collapse: collapse; font-size: 14px;">
                    <tr style="border-bottom: 1px solid #e2e8f0;"><td style="padding: 10px 0;">Gmail mới</td><td style="padding: 10px 0; color:#f59e0b; font-weight:700;">20 - 50 mail/ngày</td></tr>
                    <tr><td style="padding: 10px 0;">Gmail cũ / Workspace</td><td style="padding: 10px 0; color:#10b981; font-weight:700;">300 - 1000 mail/ngày</td></tr>
                </table>
            </div>
            """, unsafe_allow_html=True)

        with col_action2:
            st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
            if st.button("🚀 BẮT ĐẦU CHIẾN DỊCH GỬI MAIL", type="primary", use_container_width=True):
                if df is None: st.error("⚠️ Vui lòng tải lên danh sách Khách hàng!")
                elif not subject: st.error("⚠️ Tiêu đề thư không được bỏ trống!")
                elif not SYS_EMAIL or not SYS_PWD: st.error("⚠️ Chưa có Email hệ thống!")
                else:
                    progress = st.progress(0); log = st.expander("📋 Trình giám sát hệ thống (Live)", expanded=True)
                    
                    # THUẬT TOÁN TỐI ƯU CỰC ĐỘ
                    soup = BeautifulSoup(full_email_content, "html.parser")
                    for tag in soup(["script", "style", "meta", "iframe"]): tag.decompose()
                        
                    inline_images = []; img_counter = 0
                    for img in soup.find_all("img"):
                        src = img.get("src", "")
                        if src.startswith("http"): 
                            img.attrs = {"src": src, "style": "max-width: 100%; height: auto; display: block;"}
                        elif src.startswith("data:image"):
                            if img_counter < 2:  # CHỈ CHO PHÉP TỐI ĐA 2 ẢNH ĐÍNH KÈM TỪ MÁY TÍNH
                                try:
                                    header, encoded = src.split(",", 1); img_data = base64.b64decode(encoded)
                                    img_counter += 1; cid = f"img_{img_counter}"
                                    inline_images.append({"cid": cid, "data": img_data, "type": "png"})
                                    img.attrs = {"src": f"cid:{cid}", "style": "max-width: 100%;"}
                                except: img.decompose()
                            else: img.decompose()
                        else: img.decompose()

                    prepared_html_template = str(soup) 
                    log.write("✅ Đã xử lý ảnh & tệp tin rác bảo vệ uy tín Email.")

                    run_tk = current_user_data.get("tele_token", "")
                    run_id = current_user_data.get("tele_chat_id", "")
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
                            
                            for img_dict in inline_images:
                                img_part = MIMEImage(img_dict["data"], _subtype=img_dict["type"])
                                img_part.add_header("Content-ID", f"<{img_dict['cid']}>")
                                img_part.add_header("Content-Disposition", "inline", filename=f"image_{img_dict['cid']}.png")
                                msg_related.attach(img_part)
                            
                            if attachments:
                                for f in attachments:
                                    p = MIMEBase("application", "octet-stream"); p.set_payload(f.read())
                                    encoders.encode_base64(p); p.add_header("Content-Disposition", f"attachment; filename={f.name}")
                                    msg_root.attach(p); f.seek(0)
                                    
                            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                                server.starttls(); server.login(SYS_EMAIL, SYS_PWD); server.send_message(msg_root)
                                
                            success_list.append(target_email); log.write(f"✅ Đã gửi: {target_email}")
                        except Exception as e:
                            error_list.append(target_email); log.write(f"❌ Lỗi: {target_email} ({e})")
                            
                        progress.progress((index + 1) / len(df)); time.sleep(delay)
                        
                    # Hoàn thành chiến dịch: Phát âm thanh và báo cáo
                    play_success_sound()
                    st.success("🎉 Chiến dịch hoàn tất!")
                    
                    csv_buf = io.BytesIO()
                    pd.DataFrame({"Email": success_list + error_list, "Kết quả": ["Thành công"] * len(success_list) + ["Lỗi"] * len(error_list)}).to_csv(csv_buf, index=False, encoding="utf-8-sig")
                    
                    send_tele_msg(run_tk, run_id, f"📊 <b>TỔNG KẾT</b>\n✅ Thành công: {len(success_list)}\n❌ Lỗi: {len(error_list)}")
                    send_tele_file(run_tk, run_id, csv_buf.getvalue(), "ket_qua.csv")
                    st.download_button("📥 TẢI BÁO CÁO (.CSV)", data=csv_buf.getvalue(), file_name="ket_qua.csv", use_container_width=True)

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
                    status = str(l.get('status', ''))
                    # Chỉnh màu trạng thái cho đẹp
                    if "Thành công" in status: status = "✅ Thành công"
                    elif "Lỗi" in status: status = "❌ " + status
                    h_list.append({"Ngày nạp": l.get('time', ''), "Số tiền": amt, "Trạng thái": status})
            
            if h_list: st.dataframe(pd.DataFrame(h_list), use_container_width=True)
            else: st.write("Không tìm thấy giao dịch của bạn.")

    with tab_config:
        st.markdown('<div class="pill-header bg-blue">⚙️ CÀI ĐẶT HỆ THỐNG</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.session_state["s_name"] = st.text_input("Tên hiển thị khi gửi thư:", value=st.session_state["s_name"])
            st.info(f"Lưu ý: Hệ thống đang dùng Gmail chung: {SYS_EMAIL} để gửi.")
        with c2:
            tk = st.text_input("Bot Token Telegram:", value=current_user_data.get("tele_token", ""), type="password")
            cid = st.text_input("Chat ID Telegram:", value=current_user_data.get("tele_chat_id", ""))
            st.session_state["s_sign"] = st.text_area("Chữ ký cuối thư:", value=st.session_state["s_sign"])
            if st.button("💾 Lưu cấu hình"):
                if save_config_api(st.session_state["current_user"], tk, cid): st.success("Đã lưu!")

# NÚT LIÊN HỆ NỔI
st.markdown("""<div class="floating-container"><a href="https://zalo.me/0935748199" target="_blank" class="float-btn"><img src="https://upload.wikimedia.org/wikipedia/commons/9/91/Icon_of_Zalo.svg" width="35"></a><a href="https://t.me/BulkMail_Pro" target="_blank" class="float-btn"><img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg" width="35"></a></div>""", unsafe_allow_html=True)
