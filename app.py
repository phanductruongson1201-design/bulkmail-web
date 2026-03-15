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
import re
import urllib.request
 
# ── Thư viện paste ảnh từ clipboard ──────────────────────────
# Cài đặt: pip install streamlit-paste-button
try:
    from streamlit_paste_button import paste_image_button
    PASTE_AVAILABLE = True
except ImportError:
    PASTE_AVAILABLE = False
 
# 1. Cấu hình trang
st.set_page_config(page_title="BulkMail Pro - Trường Sơn", page_icon="🚀", layout="wide")
 
# ==========================================
# API & HỆ THỐNG
# ==========================================
DB_URL    = st.secrets.get("DB_URL", "")
SYS_EMAIL = st.secrets.get("SENDER_EMAIL", "")
SYS_PWD   = st.secrets.get("APP_PASSWORD", "")
 
def load_users():
    if not DB_URL: return {}
    try: return requests.get(DB_URL).json()
    except: return {}
 
def save_user_api(username, password_hash, email):
    if not DB_URL: return
    try: requests.post(DB_URL, json={"action":"register","username":username,"password":password_hash,"email":email})
    except: pass
 
def reset_password_api(username, email, new_password_hash, is_reset_status):
    if not DB_URL: return False
    try:
        res = requests.post(DB_URL, json={"action":"reset","username":username,"email":email,
                            "new_password":new_password_hash,"is_reset":is_reset_status}).json()
        return res.get("status") == "success"
    except: return False
 
def save_config_api(username, tele_token, tele_chat_id):
    if not DB_URL: return False
    try:
        res = requests.post(DB_URL, json={"action":"update_config","username":username,
                            "tele_token":tele_token,"tele_chat_id":tele_chat_id}).json()
        return res.get("status") == "success"
    except: return False
 
def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()
def generate_otp(n=6): return "".join(random.choices(string.digits, k=n))
 
def send_otp_email(to_email, username, otp_code):
    if not SYS_EMAIL or not SYS_PWD: return False
    try:
        msg = MIMEMultipart()
        msg["From"] = f"Hệ thống xác thực <{SYS_EMAIL}>"
        msg["To"]   = to_email
        msg["Subject"] = f"{otp_code} là mã xác thực của bạn"
        msg.attach(MIMEText(f"<h3>Chào {username},</h3><p>Mã OTP: <b style='font-size:20px;'>{otp_code}</b></p>","html"))
        s = smtplib.SMTP("smtp.gmail.com",587); s.starttls(); s.login(SYS_EMAIL,SYS_PWD); s.send_message(msg); s.quit()
        return True
    except: return False
 
def send_tele_msg(token, chat_id, message):
    if token and chat_id:
        try: requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                           data={"chat_id":chat_id,"text":message,"parse_mode":"HTML"},timeout=5)
        except: pass
 
def send_tele_file(token, chat_id, file_content, file_name):
    if token and chat_id:
        try: requests.post(f"https://api.telegram.org/bot{token}/sendDocument",
                           data={"chat_id":chat_id},files={"document":(file_name,file_content)},timeout=10)
        except: pass
 
def get_image_base64(path):
    try:
        with open(path,"rb") as f: return base64.b64encode(f.read()).decode("utf-8")
    except: return None
 
# ==========================================
# ✅ HÀM XỬ LÝ ẢNH
# ==========================================
 
def file_to_base64_tag(uploaded_file):
    """File upload → thẻ <img> Base64."""
    try:
        img_bytes = uploaded_file.read(); uploaded_file.seek(0)
        ext = uploaded_file.name.split(".")[-1].lower()
        mime = {"jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png",
                "gif":"image/gif","webp":"image/webp","bmp":"image/bmp"}.get(ext,"image/jpeg")
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        return (f'<img src="data:{mime};base64,{b64}" alt="{uploaded_file.name}" '
                f'style="max-width:100%;height:auto;display:block;margin:10px 0;">')
    except: return ""
 
def pil_to_base64_tag(pil_image, label="pasted"):
    """PIL Image (từ paste) → thẻ <img> Base64."""
    try:
        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return (f'<img src="data:image/png;base64,{b64}" alt="{label}" '
                f'style="max-width:100%;height:auto;display:block;margin:10px 0;">')
    except: return ""
 
def embed_url_images(html_content):
    """Tải ảnh từ URL trong HTML → nhúng Base64."""
    def replace_src(match):
        full_tag, src = match.group(0), match.group(1)
        if src.startswith("data:") or not src.startswith("http"): return full_tag
        try:
            req = urllib.request.Request(src, headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                img_bytes = resp.read()
                mime = resp.headers.get("Content-Type","image/jpeg").split(";")[0].strip()
                if not mime.startswith("image/"): mime = "image/jpeg"
            b64 = base64.b64encode(img_bytes).decode("utf-8")
            return full_tag.replace(src, f"data:{mime};base64,{b64}", 1)
        except: return full_tag
    return re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE).sub(replace_src, html_content)
 
def build_email_html(raw_text, image_tags_dict):
    """
    Text → HTML email.
    Hỗ trợ biến:
      {{name}}  → tên khách hàng
      {{anh1}}  → ảnh 1 (upload hoặc paste)
      {{anh2}}  → ảnh 2 ...
    Link ảnh URL đứng 1 dòng riêng → <img>
    URL thường → <a href>
    """
    url_img_re = re.compile(r'^(https?://\S+\.(?:jpg|jpeg|png|gif|webp|bmp|svg))(\?.*)?$', re.IGNORECASE)
    url_re     = re.compile(r'(https?://\S+)', re.IGNORECASE)
    html_lines = []
    for line in raw_text.split("\n"):
        stripped = line.strip()
        replaced = stripped
        for var, tag in image_tags_dict.items():
            replaced = replaced.replace(var, tag)
        if replaced != stripped:
            html_lines.append(replaced)
        elif url_img_re.match(stripped):
            html_lines.append(f'<img src="{stripped}" alt="image" style="max-width:100%;height:auto;display:block;margin:10px 0;">')
        elif stripped == "":
            html_lines.append("<br>")
        else:
            html_lines.append(url_re.sub(r'<a href="\1" target="_blank" style="color:#3b82f6;">\1</a>', line))
    return embed_url_images("<br>".join(html_lines))
 
# ==========================================
# CSS
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap');
    html,body,[class*="css"]{font-family:'Plus Jakarta Sans',sans-serif!important;}
    #MainMenu,footer,header,.stDeployButton,[data-testid="manage-app-button"],[data-testid="viewerBadge"],
    iframe[title="Streamlit Toolbar"],iframe[src*="badge"]{display:none!important;visibility:hidden!important;}
    .block-container{padding-top:1.5rem!important;padding-bottom:2rem!important;}
    .stApp{background-color:#f8fafc;}
    .gradient-text{background:linear-gradient(90deg,#2563eb 0%,#7c3aed 100%);-webkit-background-clip:text;
        -webkit-text-fill-color:transparent;font-weight:900;font-size:46px;margin-bottom:5px;letter-spacing:-1px;}
    div[data-baseweb="tab-list"]{background-color:#f1f5f9!important;border-radius:12px!important;
        padding:4px!important;gap:4px!important;border-bottom:none!important;margin-bottom:20px!important;}
    div[data-baseweb="tab"]{background-color:transparent!important;border-radius:8px!important;
        border:none!important;color:#64748b!important;font-weight:600!important;font-size:14px!important;
        padding:8px 12px!important;margin:0!important;height:auto!important;}
    div[data-baseweb="tab"][aria-selected="true"]{background-color:#fff!important;color:#1e40af!important;
        box-shadow:0 2px 6px rgba(0,0,0,0.08)!important;}
    div[data-baseweb="tab"][aria-selected="true"] p{color:#1e40af!important;font-weight:800!important;}
    div[data-baseweb="tab-highlight"]{display:none!important;}
    div[data-testid="stExpander"]{background-color:#eff6ff!important;border:2px solid #bfdbfe!important;
        border-radius:16px;box-shadow:0 4px 10px rgba(59,130,246,0.08);}
    div[data-testid="stExpander"] summary{background-color:transparent!important;}
    div[data-testid="stFileUploader"]{background-color:#faf5ff!important;border:2px solid #e9d5ff!important;
        border-radius:16px;box-shadow:0 4px 10px rgba(168,85,247,0.08);padding:20px;
        transition:transform 0.2s,box-shadow 0.2s;}
    div[data-testid="stFileUploader"]:hover{transform:translateY(-2px);box-shadow:0 8px 15px rgba(168,85,247,0.15);}
    .stButton>button[kind="primary"]{background:linear-gradient(135deg,#1e40af 0%,#3b82f6 100%)!important;
        color:white!important;border-radius:16px;font-weight:900;font-size:18px!important;padding:15px 24px;
        border:none!important;box-shadow:0 6px 20px rgba(59,130,246,0.35)!important;
        transition:all 0.3s;text-transform:uppercase;letter-spacing:1px;}
    .stButton>button[kind="primary"]:hover{transform:translateY(-4px);box-shadow:0 8px 25px rgba(59,130,246,0.5)!important;}
    .auth-box .stButton>button[kind="primary"]{background:linear-gradient(135deg,#3b82f6 0%,#2563eb 100%)!important;
        font-size:16px!important;padding:10px 20px;}
    .stButton>button[kind="secondary"],div[data-testid="stDownloadButton"]>button{border-radius:12px;
        border:2px solid #cbd5e1!important;color:#475569!important;font-weight:700;
        background-color:white!important;transition:all 0.3s;}
    .stButton>button[kind="secondary"]:hover,div[data-testid="stDownloadButton"]>button:hover{
        border-color:#3b82f6!important;color:#3b82f6!important;transform:translateY(-2px);}
    .pill-header{color:white;padding:10px 24px;border-radius:50px;font-size:15px;font-weight:800;
        margin-bottom:20px;margin-top:15px;text-transform:uppercase;letter-spacing:1px;
        display:inline-block;text-shadow:0 2px 4px rgba(0,0,0,0.2);}
    .bg-blue  {background:linear-gradient(135deg,#3b82f6,#1d4ed8);box-shadow:0 6px 15px rgba(59,130,246,0.4);border:2px solid #93c5fd;}
    .bg-purple{background:linear-gradient(135deg,#a855f7,#6d28d9);box-shadow:0 6px 15px rgba(168,85,247,0.4);border:2px solid #d8b4fe;}
    .bg-green {background:linear-gradient(135deg,#10b981,#047857);box-shadow:0 6px 15px rgba(16,185,129,0.4);border:2px solid #6ee7b7;}
    .bg-orange{background:linear-gradient(135deg,#f59e0b,#d97706);box-shadow:0 6px 15px rgba(245,158,11,0.4);border:2px solid #fcd34d;}
    .auth-box{max-width:440px;margin:10px auto;padding:35px;background:rgba(255,255,255,0.95);
        border-radius:24px;box-shadow:0 20px 40px -15px rgba(0,0,0,0.1);
        border:1px solid rgba(255,255,255,0.5);backdrop-filter:blur(10px);}
    .logo-container{display:flex;justify-content:center;align-items:center;width:100%;margin-bottom:20px;}
    .logo-container img{width:120px;height:120px;border-radius:35%;object-fit:cover;
        box-shadow:0 10px 25px rgba(59,130,246,0.2);border:4px solid white;}
    .alt-logo{width:120px;height:120px;border-radius:35%;background:linear-gradient(135deg,#4f46e5 0%,#3b82f6 100%);
        color:white;display:flex;justify-content:center;align-items:center;font-weight:800;
        font-size:16px;text-align:center;border:4px solid white;box-shadow:0 10px 25px rgba(59,130,246,0.2);}
 
    /* Card ảnh */
    .img-card{background:white;border:2px solid #e0f2fe;border-radius:14px;padding:10px;
        text-align:center;margin-bottom:8px;box-shadow:0 2px 8px rgba(59,130,246,0.08);}
    .img-card img{max-height:80px;border-radius:8px;object-fit:cover;}
    .var-badge{display:inline-block;background:#dbeafe;color:#1d4ed8;border-radius:20px;
        padding:2px 12px;font-size:13px;font-weight:800;margin-top:5px;}
    .source-badge{display:inline-block;font-size:11px;color:#94a3b8;margin-top:3px;}
 
    /* Khu vực paste */
    .paste-zone{background:#f0fdf4;border:2px dashed #86efac;border-radius:16px;
        padding:18px;text-align:center;margin-bottom:12px;}
 
    .floating-container{position:fixed;bottom:30px;right:30px;display:flex;flex-direction:column;gap:15px;z-index:999999;}
    .float-btn{width:55px;height:55px;border-radius:50%;box-shadow:0 10px 25px rgba(0,0,0,0.15);
        display:flex;justify-content:center;align-items:center;background:white;transition:0.3s;border:2px solid #e2e8f0;}
    .float-btn:hover{transform:translateY(-5px);border-color:#3b82f6;}
    .float-btn img{width:65%;height:65%;object-fit:contain;}
</style>
""", unsafe_allow_html=True)
 
# Session state
for key, val in {
    "logged_in": False, "otp_verified": False, "otp_sent": False,
    "s_name": "Trường Sơn Marketing", "s_email": "", "s_pwd": "",
    "s_sign": "Trân trọng,\nTrường Sơn Marketing",
    "all_images": [],   # list of {"tag": "<img...>", "source": "upload"|"paste", "label": "..."}
}.items():
    if key not in st.session_state:
        st.session_state[key] = val
 
LOGO_URL = "logo_moi.png"
 
# ==========================================
# 1. ĐĂNG NHẬP
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
        st.markdown('<h2 style="text-align:center;color:#0f172a;font-weight:900;margin-bottom:5px;font-size:28px;">BULKMAIL PRO</h2>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;color:#64748b;margin-bottom:20px;font-size:14px;">Đăng nhập để bắt đầu chiến dịch</p>', unsafe_allow_html=True)
 
        tab_login, tab_reg, tab_forgot = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký", "🔑 Quên MK"])
        users_db = load_users()
 
        with tab_login:
            log_user = st.text_input("Tên đăng nhập", key="login_u")
            log_pwd  = st.text_input("Mật khẩu", type="password", key="login_p")
            st.markdown("<br>", unsafe_allow_html=True)
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
            reg_pwd_confirm = st.text_input("Xác nhận mật khẩu", type="password", key="reg_pc")
            if st.button("TẠO TÀI KHOẢN", type="primary", use_container_width=True):
                if not reg_user or not reg_email or not reg_pwd: st.warning("⚠️ Điền đủ thông tin!")
                elif reg_user in users_db: st.error("❌ Username đã tồn tại!")
                elif reg_pwd != reg_pwd_confirm: st.error("❌ Mật khẩu không khớp!")
                else:
                    save_user_api(reg_user, hash_password(reg_pwd), reg_email)
                    st.success("✅ Đăng ký thành công!")
 
        with tab_forgot:
            if not st.session_state["otp_verified"]:
                fg_user  = st.text_input("Nhập Username", key="fg_u")
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
                    if st.button("XÁC THỰC OTP", type="primary", use_container_width=True):
                        u_info = load_users().get(fg_user)
                        if u_info and u_info.get("password") == hash_password(input_otp):
                            st.session_state["otp_verified"] = True
                            st.session_state["target_user"]  = fg_user
                            st.rerun()
                        else: st.error("❌ OTP không đúng!")
            else:
                new_p = st.text_input("Mật khẩu mới", type="password", key="new_p")
                if st.button("ĐỔI MẬT KHẨU", type="primary", use_container_width=True):
                    u_db = load_users(); target = st.session_state["target_user"]
                    if reset_password_api(target, u_db[target]["email"], hash_password(new_p), False):
                        st.session_state["otp_verified"] = False
                        st.session_state["otp_sent"] = False
                        st.success("✅ Đổi mật khẩu thành công!")
        st.markdown("</div>", unsafe_allow_html=True)
 
# ==========================================
# 2. DASHBOARD CHÍNH
# ==========================================
else:
    head_col1, head_col2 = st.columns([5, 1])
    with head_col1:
        st.markdown('<div class="gradient-text">BulkMail</div>', unsafe_allow_html=True)
        st.markdown('<p style="color:#64748b;font-size:16px;margin-bottom:20px;">Thiết lập và vận hành hàng ngàn email cá nhân hóa chỉ trong tích tắc.</p>', unsafe_allow_html=True)
    with head_col2:
        st.markdown(f"<div style='text-align:right;padding-top:10px;font-weight:bold;color:#1e40af;'>👤 {st.session_state['current_user']}</div>", unsafe_allow_html=True)
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state["logged_in"] = False
            st.rerun()
 
    # BƯỚC 1
    st.markdown('<div class="pill-header bg-blue">⚙️ BƯỚC 1: CẤU HÌNH MÁY CHỦ & BÁO CÁO</div>', unsafe_allow_html=True)
    with st.expander("Bấm để mở rộng Cài đặt Máy chủ", expanded=True):
        cfg_col1, cfg_col2 = st.columns(2, gap="large")
        with cfg_col1:
            st.markdown("<b style='color:#1e40af;'>📧 Thông tin Gửi thư (Gmail)</b>", unsafe_allow_html=True)
            st.session_state["s_name"]  = st.text_input("Tên người gửi:", value=st.session_state["s_name"])
            st.session_state["s_email"] = st.text_input("Địa chỉ Gmail:", value=st.session_state["s_email"])
            st.session_state["s_pwd"]   = st.text_input("Mật khẩu ứng dụng (16 ký tự):", type="password", value=st.session_state["s_pwd"])
            with st.expander("❓ Hướng dẫn lấy Mật khẩu ứng dụng"):
                st.markdown("""<div style="font-size:14.5px;color:#334155;line-height:1.6;">
                    <b>1.</b> Truy cập <a href="https://myaccount.google.com/security" target="_blank" style="color:#3b82f6;"><b>Bảo mật Google</b></a>.<br>
                    <b>2.</b> Bật <b>Xác minh 2 bước</b>.<br>
                    <b>3.</b> Tìm kiếm <b>"Mật khẩu ứng dụng"</b> → Bấm chọn.<br>
                    <b>4.</b> Đặt tên <i>"BulkMail"</i> → <b>Tạo</b> → Copy 16 ký tự vào ô trên.
                </div>""", unsafe_allow_html=True)
        with cfg_col2:
            st.markdown("<b style='color:#1e40af;'>🔔 Báo cáo Telegram & Chữ ký</b>", unsafe_allow_html=True)
            u_data = load_users().get(st.session_state["current_user"], {})
            new_tk = st.text_input("Bot Token Telegram (Tùy chọn):", value=u_data.get("tele_token",""), type="password")
            new_id = st.text_input("Chat ID Telegram (Tùy chọn):", value=u_data.get("tele_chat_id",""))
            st.session_state["s_sign"] = st.text_area("Chữ ký cuối thư:", value=st.session_state["s_sign"], height=68)
            if st.button("💾 Lưu cấu hình Telegram"):
                if save_config_api(st.session_state["current_user"], new_tk, new_id):
                    st.success("✅ Đã lưu!")
 
    st.markdown("<hr style='margin:10px 0 20px 0;'>", unsafe_allow_html=True)
 
    col_data, col_content = st.columns([1, 1.2], gap="large")
 
    # ── CỘT TRÁI ──────────────────────────────────────────────
    with col_data:
        # BƯỚC 2: Dữ liệu
        st.markdown('<div class="pill-header bg-purple">📁 BƯỚC 2: DỮ LIỆU KHÁCH HÀNG</div>', unsafe_allow_html=True)
        sample_df = pd.DataFrame({"email":["khachhang@gmail.com","vidu@gmail.com"]})
        try:
            excel_buf = io.BytesIO()
            with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
                sample_df.to_excel(writer, index=False, sheet_name="Danh_sach")
            dl_data = excel_buf.getvalue()
        except: dl_data = sample_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 Tải File Mẫu (Excel)", data=dl_data, file_name="danh_sach_mau.xlsx", use_container_width=True)
        up = st.file_uploader("Tải tệp danh sách (.csv, .xlsx)", type=["csv","xlsx"])
        df = None
        if up:
            df = pd.read_excel(up) if up.name.endswith("xlsx") else pd.read_csv(up)
            st.success(f"✅ Hợp lệ! Đã nhận {len(df)} địa chỉ email.")
 
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="pill-header bg-purple" style="font-size:13px;padding:6px 18px;margin-bottom:10px;">📎 TỆP ĐÍNH KÈM (TÙY CHỌN)</div>', unsafe_allow_html=True)
        attachments = st.file_uploader("Kéo thả tài liệu vào đây", accept_multiple_files=True)
 
        # ── ẢNH CHÈN NỘI DUNG ─────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="pill-header bg-orange" style="font-size:13px;padding:6px 18px;margin-bottom:6px;">🖼️ ẢNH CHÈN VÀO NỘI DUNG</div>', unsafe_allow_html=True)
        st.caption("Dùng **{{anh1}}**, **{{anh2}}**... trong ô soạn thảo để đặt ảnh đúng vị trí.")
 
        tab_upload, tab_paste = st.tabs(["📂 Upload từ máy", "📋 Paste từ clipboard"])
 
        # Tab 1: Upload file
        with tab_upload:
            uploaded_imgs = st.file_uploader(
                "Chọn ảnh (jpg, png, gif, webp)",
                type=["jpg","jpeg","png","gif","webp","bmp"],
                accept_multiple_files=True,
                key="upload_imgs"
            )
            if uploaded_imgs:
                # Cập nhật danh sách — giữ ảnh paste cũ, thay ảnh upload mới
                paste_imgs   = [x for x in st.session_state["all_images"] if x["source"] == "paste"]
                upload_imgs  = []
                for img_file in uploaded_imgs:
                    tag = file_to_base64_tag(img_file)
                    upload_imgs.append({"tag": tag, "source": "upload", "label": img_file.name})
                st.session_state["all_images"] = upload_imgs + paste_imgs
 
        # Tab 2: Paste từ clipboard
        with tab_paste:
            if PASTE_AVAILABLE:
                st.markdown('<div class="paste-zone">📋 Bấm nút bên dưới rồi nhấn <b>Ctrl+V</b> để dán ảnh từ clipboard</div>', unsafe_allow_html=True)
                paste_result = paste_image_button(
                    label="📋 Bấm đây rồi Ctrl+V để Paste ảnh",
                    key="paste_btn",
                    errors="raise"
                )
                if paste_result and paste_result.image_data is not None:
                    tag = pil_to_base64_tag(paste_result.image_data, label=f"paste_{len(st.session_state['all_images'])+1}")
                    # Thêm vào danh sách nếu chưa có
                    existing_tags = [x["tag"] for x in st.session_state["all_images"]]
                    if tag not in existing_tags:
                        st.session_state["all_images"].append({"tag": tag, "source": "paste", "label": f"Ảnh paste #{len(st.session_state['all_images'])+1}"})
                        st.success("✅ Đã thêm ảnh từ clipboard!")
                        st.rerun()
            else:
                st.warning("⚠️ Chưa cài thư viện paste. Chạy lệnh sau rồi khởi động lại app:")
                st.code("pip install streamlit-paste-button", language="bash")
                st.info("Sau khi cài xong, tính năng Paste clipboard sẽ tự hoạt động.")
 
        # Hiển thị tất cả ảnh đã thêm
        all_imgs = st.session_state["all_images"]
        if all_imgs:
            st.markdown(f"<br><b style='color:#1e40af;'>🗂️ Danh sách ảnh ({len(all_imgs)} ảnh)</b>", unsafe_allow_html=True)
            # Nút xóa tất cả
            if st.button("🗑️ Xóa tất cả ảnh", use_container_width=True):
                st.session_state["all_images"] = []
                st.rerun()
 
            cols_img = st.columns(min(len(all_imgs), 3))
            for i, img_info in enumerate(all_imgs):
                var_name = "{{" + f"anh{i+1}" + "}}"
                with cols_img[i % 3]:
                    # Trích base64 từ tag để preview
                    b64_match = re.search(r'base64,([^"\']+)', img_info["tag"])
                    if b64_match:
                        b64_data = b64_match.group(1)
                        src_match = re.search(r'src="([^"]+)"', img_info["tag"])
                        src = src_match.group(1) if src_match else f"data:image/png;base64,{b64_data}"
                        source_icon = "📂" if img_info["source"] == "upload" else "📋"
                        st.markdown(
                            f'<div class="img-card">'
                            f'<img src="{src}"><br>'
                            f'<span class="var-badge">{var_name}</span><br>'
                            f'<span class="source-badge">{source_icon} {img_info["label"][:20]}</span>'
                            f'</div>', unsafe_allow_html=True
                        )
 
    # ── CỘT PHẢI ──────────────────────────────────────────────
    with col_content:
        st.markdown('<div class="pill-header bg-green">✍️ BƯỚC 3: SOẠN THÔNG ĐIỆP</div>', unsafe_allow_html=True)
        subject  = st.text_input("Tiêu đề Email:")
        raw_body = st.text_area(
            "Nội dung thư:",
            height=280,
            value=(
                "Kính chào Anh/Chị {{name}},\n\n"
                "Nội dung thư của bạn ở đây...\n\n"
                "Chèn ảnh bằng cách đặt biến trên một dòng riêng:\n"
                "{{anh1}}\n\n"
                "{{anh2}}\n\n"
                "Cảm ơn bạn đã quan tâm!"
            )
        )
 
        with st.expander("📖 Hướng dẫn sử dụng biến"):
            st.markdown("""
| Biến | Tác dụng |
|------|----------|
| `{{name}}` | Tên khách hàng (cột **name/tên** trong file Excel) |
| `{{anh1}}` | Ảnh thứ 1 (upload hoặc paste) |
| `{{anh2}}` | Ảnh thứ 2 |
| `{{anh3}}` | Ảnh thứ 3... tối đa 10 ảnh |
 
**Nguồn ảnh hỗ trợ:**
- 📂 **Upload file**: Kéo thả từ máy tính
- 📋 **Paste clipboard**: Copy ảnh từ web/Word/screenshot → Ctrl+V
 
> 💡 Đặt `{{anh1}}` trên **một dòng riêng** để ảnh hiển thị đẹp.
            """)
 
        col_delay, _ = st.columns([1, 1])
        with col_delay:
            delay = st.number_input("⏳ Khoảng nghỉ/Mail (Giây):", value=15, min_value=5)
 
        # Xem trước
        sign_html = st.session_state["s_sign"].replace("\n","<br>")
        with st.expander("👁️ Xem trước email thực tế", expanded=False):
            example_name = (str(df.iloc[0]["name"]) if df is not None and not df.empty and "name" in df.columns else "Quý khách")
            all_imgs = st.session_state["all_images"]
            img_tags_dict = {"{{" + f"anh{i+1}" + "}}": img["tag"] for i, img in enumerate(all_imgs)}
            preview_body = build_email_html(
                raw_body.replace("{{name}}", f'<b style="color:#3b82f6;">{example_name}</b>'),
                img_tags_dict
            )
            st.markdown(
                f"<div style='padding:20px;background:white;border-radius:8px;border:1px solid #e2e8f0;"
                f"font-family:Arial;line-height:1.8;color:#333;'>"
                f"{preview_body}<br><br>"
                f"<div style='color:#666;border-top:1px solid #eee;padding-top:10px;'>{sign_html}</div>"
                f"</div>", unsafe_allow_html=True
            )
 
    st.markdown("<hr style='margin:30px 0;'>", unsafe_allow_html=True)
 
    # GỬI MAIL
    col_action1, col_action2 = st.columns([1.5, 1])
    with col_action1:
        st.markdown("""
        <div style="background:white;border:1px solid #e2e8f0;border-radius:16px;padding:20px;box-shadow:0 4px 6px -1px rgba(0,0,0,0.05);">
            <h4 style="margin-top:0;color:#0f172a;font-size:16px;">🛡️ Cẩm nang An toàn Tài khoản</h4>
            <table style="width:100%;border-collapse:collapse;font-size:14px;">
                <tr style="border-bottom:1px solid #e2e8f0;color:#64748b;">
                    <th style="padding:10px 0;">Loại tài khoản</th><th style="padding:10px 0;">An toàn / Ngày</th>
                </tr>
                <tr style="border-bottom:1px solid #f1f5f9;">
                    <td style="padding:12px 0;font-weight:600;">Gmail mới tạo</td>
                    <td style="padding:12px 0;color:#f59e0b;font-weight:700;">20 - 50 mail</td>
                </tr>
                <tr style="border-bottom:1px solid #f1f5f9;">
                    <td style="padding:12px 0;font-weight:600;">Gmail dùng lâu</td>
                    <td style="padding:12px 0;color:#10b981;font-weight:700;">200 - 300 mail</td>
                </tr>
                <tr>
                    <td style="padding:12px 0;font-weight:600;">Google Workspace</td>
                    <td style="padding:12px 0;color:#3b82f6;font-weight:700;">500 - 1000 mail</td>
                </tr>
            </table>
        </div>""", unsafe_allow_html=True)
 
    with col_action2:
        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
        if st.button("🚀 BẮT ĐẦU CHIẾN DỊCH GỬI MAIL", type="primary", use_container_width=True):
            if df is None: st.error("⚠️ Vui lòng tải lên danh sách Khách hàng!")
            elif not subject: st.error("⚠️ Tiêu đề thư không được bỏ trống!")
            elif not st.session_state["s_email"] or not st.session_state["s_pwd"]: st.error("⚠️ Bạn chưa điền Email hoặc Mật khẩu!")
            else:
                sign_html_send = st.session_state["s_sign"].replace("\n","<br>")
                all_imgs_send  = st.session_state["all_images"]
                img_tags_dict  = {"{{" + f"anh{i+1}" + "}}": img["tag"] for i, img in enumerate(all_imgs_send)}
 
                # ✅ Xử lý ảnh 1 LẦN trước vòng lặp
                with st.spinner("⏳ Đang xử lý và nhúng ảnh..."):
                    processed_body = build_email_html(raw_body, img_tags_dict)
 
                progress = st.progress(0)
                log = st.expander("📋 Trình giám sát (Live)", expanded=True)
                success_list, error_list = [], []
 
                u_data_run = load_users().get(st.session_state["current_user"], {})
                run_tk = u_data_run.get("tele_token",""); run_id = u_data_run.get("tele_chat_id","")
                send_tele_msg(run_tk, run_id, f"🚀 <b>BẮT ĐẦU CHIẾN DỊCH</b>\n👤 {st.session_state['current_user']}")
 
                for index, row in df.iterrows():
                    target_email = ""
                    try:
                        e_col = next((c for c in df.columns if c.lower() in ["email","mail"]), None)
                        target_email = str(row.get(e_col, row.iloc[0])).strip()
                        n_col = next((c for c in df.columns if c.lower() in ["name","tên"]), None)
                        target_name  = str(row.get(n_col,"Khách hàng")) if n_col else "Khách hàng"
 
                        personalized = processed_body.replace("{{name}}", target_name)
                        final_html = (
                            f"<div style='font-family:Arial;line-height:1.8;color:#333;'>"
                            f"{personalized}<br><br>"
                            f"<div style='color:#666;border-top:1px solid #eee;padding-top:10px;'>{sign_html_send}</div>"
                            f"</div>"
                        )
                        msg = MIMEMultipart()
                        msg["From"]    = f"{st.session_state['s_name']} <{st.session_state['s_email']}>"
                        msg["To"]      = target_email
                        msg["Subject"] = subject
                        msg.attach(MIMEText(final_html, "html"))
                        if attachments:
                            for f in attachments:
                                part = MIMEBase("application","octet-stream")
                                part.set_payload(f.read()); encoders.encode_base64(part)
                                part.add_header("Content-Disposition", f"attachment; filename={f.name}")
                                msg.attach(part); f.seek(0)
                        with smtplib.SMTP("smtp.gmail.com", 587) as server:
                            server.starttls()
                            server.login(st.session_state["s_email"], st.session_state["s_pwd"])
                            server.send_message(msg)
                        success_list.append(target_email)
                        log.write(f"✅ Đã gửi: {target_email}")
                    except Exception as e:
                        error_list.append(target_email)
                        log.write(f"❌ Lỗi: {target_email} ({e})")
                    progress.progress((index+1)/len(df))
                    time.sleep(delay)
 
                st.success("🎉 Chiến dịch hoàn tất!")
                csv_buf = io.BytesIO()
                pd.DataFrame({"Email":success_list+error_list,
                              "Kết quả":["Thành công"]*len(success_list)+["Lỗi"]*len(error_list)
                             }).to_csv(csv_buf, index=False, encoding="utf-8-sig")
                send_tele_msg(run_tk, run_id, f"📊 <b>TỔNG KẾT</b>\n✅ {len(success_list)}\n❌ {len(error_list)}")
                send_tele_file(run_tk, run_id, csv_buf.getvalue(), "ket_qua.csv")
                st.download_button("📥 TẢI BÁO CÁO (.CSV)", data=csv_buf.getvalue(), file_name="ket_qua.csv", use_container_width=True)
 
    # CHÂN TRANG
    st.markdown("<br><br>", unsafe_allow_html=True)
    logo_footer_b64 = get_image_base64(LOGO_URL)
    if logo_footer_b64:
        st.markdown(f'<div style="display:flex;justify-content:center;padding-top:20px;"><img src="data:image/png;base64,{logo_footer_b64}" style="width:150px;height:150px;border-radius:35%;object-fit:cover;border:4px solid white;box-shadow:0 10px 25px rgba(59,130,246,0.15);"></div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="display:flex;justify-content:center;padding:25px 0 50px 0;">
        <div style="max-width:800px;text-align:center;color:#475569;padding:30px;border-radius:24px;
                    border:1px solid #e2e8f0;background:white;box-shadow:0 10px 25px rgba(0,0,0,0.03);">
            <p style="font-size:15px;line-height:1.8;margin:0;">
                <b style="background:linear-gradient(90deg,#3b82f6,#8b5cf6);-webkit-background-clip:text;
                   -webkit-text-fill-color:transparent;font-size:22px;font-weight:900;">BulkMail Pro</b><br><br>
                Là công cụ gửi thư tự động được phát triển bởi <b>Trường Sơn Marketing</b>.
                Với tiêu chí: <b>Dễ dùng - An toàn - Hiệu quả</b>.
            </p>
        </div>
    </div>""", unsafe_allow_html=True)
 
st.markdown("""<div class="floating-container">
    <a href="https://zalo.me/0935748199" target="_blank" class="float-btn"><img src="https://upload.wikimedia.org/wikipedia/commons/9/91/Icon_of_Zalo.svg"></a>
    <a href="https://t.me/BulkMail_Pro" target="_blank" class="float-btn"><img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg"></a>
</div>""", unsafe_allow_html=True)
