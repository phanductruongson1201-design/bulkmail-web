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
 
# ── Paste clipboard ───────────────────────────────────────────
try:
    from streamlit_paste_button import paste_image_button
    PASTE_AVAILABLE = True
except ImportError:
    PASTE_AVAILABLE = False
 
# ─────────────────────────────────────────────────────────────
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
 
def reset_password_api(username, email, new_pw_hash, is_reset):
    if not DB_URL: return False
    try:
        r = requests.post(DB_URL, json={"action":"reset","username":username,"email":email,
                          "new_password":new_pw_hash,"is_reset":is_reset}).json()
        return r.get("status") == "success"
    except: return False
 
def save_config_api(username, tele_token, tele_chat_id):
    if not DB_URL: return False
    try:
        r = requests.post(DB_URL, json={"action":"update_config","username":username,
                          "tele_token":tele_token,"tele_chat_id":tele_chat_id}).json()
        return r.get("status") == "success"
    except: return False
 
def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()
def generate_otp(n=6): return "".join(random.choices(string.digits, k=n))
 
def send_otp_email(to_email, username, otp_code):
    if not SYS_EMAIL or not SYS_PWD: return False
    try:
        msg = MIMEMultipart()
        msg["From"]    = f"Hệ thống xác thực <{SYS_EMAIL}>"
        msg["To"]      = to_email
        msg["Subject"] = f"{otp_code} là mã xác thực của bạn"
        msg.attach(MIMEText(f"<h3>Chào {username},</h3><p>Mã OTP: <b style='font-size:20px;'>{otp_code}</b></p>","html"))
        s = smtplib.SMTP("smtp.gmail.com",587); s.starttls()
        s.login(SYS_EMAIL, SYS_PWD); s.send_message(msg); s.quit()
        return True
    except: return False
 
def send_tele_msg(token, chat_id, msg):
    if token and chat_id:
        try: requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                data={"chat_id":chat_id,"text":msg,"parse_mode":"HTML"}, timeout=5)
        except: pass
 
def send_tele_file(token, chat_id, content, name):
    if token and chat_id:
        try: requests.post(f"https://api.telegram.org/bot{token}/sendDocument",
                data={"chat_id":chat_id}, files={"document":(name,content)}, timeout=10)
        except: pass
 
def get_image_base64(path):
    try:
        with open(path,"rb") as f: return base64.b64encode(f.read()).decode()
    except: return None
 
# ==========================================
# ✅ XỬ LÝ ẢNH
# ==========================================
 
def file_to_base64_tag(uploaded_file):
    """UploadedFile → <img> Base64."""
    try:
        data = uploaded_file.read(); uploaded_file.seek(0)
        ext  = uploaded_file.name.rsplit(".",1)[-1].lower()
        mime = {"jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png",
                "gif":"image/gif","webp":"image/webp","bmp":"image/bmp"}.get(ext,"image/jpeg")
        b64  = base64.b64encode(data).decode()
        return (f'<img src="data:{mime};base64,{b64}" alt="{uploaded_file.name}" '
                f'style="max-width:100%;height:auto;display:block;margin:10px 0;">')
    except: return ""
 
def pil_to_base64_tag(pil_image, label="pasted"):
    """PIL Image → <img> Base64 PNG."""
    try:
        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return (f'<img src="data:image/png;base64,{b64}" alt="{label}" '
                f'style="max-width:100%;height:auto;display:block;margin:10px 0;">')
    except: return ""
 
def embed_url_images(html):
    """Nhúng ảnh URL thành Base64."""
    def _replace(m):
        tag, src = m.group(0), m.group(1)
        if src.startswith("data:") or not src.startswith("http"): return tag
        try:
            req = urllib.request.Request(src, headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                data = r.read()
                mime = r.headers.get("Content-Type","image/jpeg").split(";")[0].strip()
                if not mime.startswith("image/"): mime = "image/jpeg"
            return tag.replace(src, f"data:{mime};base64,{base64.b64encode(data).decode()}", 1)
        except: return tag
    return re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.I).sub(_replace, html)
 
def build_email_html(raw_text, img_dict):
    """
    Text → HTML email.
    {{name}}  → tên KH      {{anh1}} … {{anh10}} → ảnh tương ứng
    Link ảnh URL đứng 1 dòng → <img>
    URL thường → <a href>
    """
    url_img = re.compile(r'^(https?://\S+\.(?:jpg|jpeg|png|gif|webp|bmp|svg))(\?.*)?$', re.I)
    url_any = re.compile(r'(https?://\S+)', re.I)
    lines   = []
    for line in raw_text.split("\n"):
        s = line.strip()
        replaced = s
        for var, tag in img_dict.items():
            replaced = replaced.replace(var, tag)
        if replaced != s:
            lines.append(replaced)
        elif url_img.match(s):
            lines.append(f'<img src="{s}" alt="img" style="max-width:100%;height:auto;display:block;margin:10px 0;">')
        elif s == "":
            lines.append("<br>")
        else:
            lines.append(url_any.sub(r'<a href="\1" target="_blank" style="color:#3b82f6;">\1</a>', line))
    return embed_url_images("<br>".join(lines))
 
# ==========================================
# CSS
# ==========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap');
html,body,[class*="css"]{font-family:'Plus Jakarta Sans',sans-serif!important;}
#MainMenu,footer,header,.stDeployButton,[data-testid="manage-app-button"],
[data-testid="viewerBadge"],iframe[title="Streamlit Toolbar"],iframe[src*="badge"]
{display:none!important;visibility:hidden!important;}
.block-container{padding-top:1.5rem!important;padding-bottom:2rem!important;}
.stApp{background-color:#f8fafc;}
.gradient-text{background:linear-gradient(90deg,#2563eb,#7c3aed);-webkit-background-clip:text;
  -webkit-text-fill-color:transparent;font-weight:900;font-size:46px;letter-spacing:-1px;}
 
/* TABS */
div[data-baseweb="tab-list"]{background:#f1f5f9!important;border-radius:12px!important;
  padding:4px!important;gap:4px!important;border-bottom:none!important;margin-bottom:20px!important;}
div[data-baseweb="tab"]{background:transparent!important;border-radius:8px!important;border:none!important;
  color:#64748b!important;font-weight:600!important;font-size:14px!important;
  padding:8px 12px!important;margin:0!important;height:auto!important;}
div[data-baseweb="tab"][aria-selected="true"]{background:#fff!important;color:#1e40af!important;
  box-shadow:0 2px 6px rgba(0,0,0,.08)!important;}
div[data-baseweb="tab"][aria-selected="true"] p{color:#1e40af!important;font-weight:800!important;}
div[data-baseweb="tab-highlight"]{display:none!important;}
 
/* EXPANDER */
div[data-testid="stExpander"]{background:#eff6ff!important;border:2px solid #bfdbfe!important;
  border-radius:16px;box-shadow:0 4px 10px rgba(59,130,246,.08);}
div[data-testid="stExpander"] summary{background:transparent!important;}
 
/* FILE UPLOADER */
div[data-testid="stFileUploader"]{background:#faf5ff!important;border:2px solid #e9d5ff!important;
  border-radius:16px;padding:20px;transition:transform .2s,box-shadow .2s;}
div[data-testid="stFileUploader"]:hover{transform:translateY(-2px);box-shadow:0 8px 15px rgba(168,85,247,.15);}
 
/* BUTTONS */
.stButton>button[kind="primary"]{background:linear-gradient(135deg,#1e40af,#3b82f6)!important;
  color:#fff!important;border-radius:16px;font-weight:900;font-size:18px!important;padding:15px 24px;
  border:none!important;box-shadow:0 6px 20px rgba(59,130,246,.35)!important;
  transition:all .3s;text-transform:uppercase;letter-spacing:1px;}
.stButton>button[kind="primary"]:hover{transform:translateY(-4px);box-shadow:0 8px 25px rgba(59,130,246,.5)!important;}
.auth-box .stButton>button[kind="primary"]{background:linear-gradient(135deg,#3b82f6,#2563eb)!important;
  font-size:16px!important;padding:10px 20px;}
.stButton>button[kind="secondary"],div[data-testid="stDownloadButton"]>button{border-radius:12px;
  border:2px solid #cbd5e1!important;color:#475569!important;font-weight:700;
  background:#fff!important;transition:all .3s;}
.stButton>button[kind="secondary"]:hover,div[data-testid="stDownloadButton"]>button:hover{
  border-color:#3b82f6!important;color:#3b82f6!important;transform:translateY(-2px);}
 
/* PILL HEADERS */
.pill-header{color:#fff;padding:10px 24px;border-radius:50px;font-size:15px;font-weight:800;
  margin-bottom:20px;margin-top:15px;text-transform:uppercase;letter-spacing:1px;
  display:inline-block;text-shadow:0 2px 4px rgba(0,0,0,.2);}
.bg-blue  {background:linear-gradient(135deg,#3b82f6,#1d4ed8);box-shadow:0 6px 15px rgba(59,130,246,.4);border:2px solid #93c5fd;}
.bg-purple{background:linear-gradient(135deg,#a855f7,#6d28d9);box-shadow:0 6px 15px rgba(168,85,247,.4);border:2px solid #d8b4fe;}
.bg-green {background:linear-gradient(135deg,#10b981,#047857);box-shadow:0 6px 15px rgba(16,185,129,.4);border:2px solid #6ee7b7;}
.bg-orange{background:linear-gradient(135deg,#f59e0b,#d97706);box-shadow:0 6px 15px rgba(245,158,11,.4);border:2px solid #fcd34d;}
 
/* AUTH BOX */
.auth-box{max-width:440px;margin:10px auto;padding:35px;background:rgba(255,255,255,.95);
  border-radius:24px;box-shadow:0 20px 40px -15px rgba(0,0,0,.1);
  border:1px solid rgba(255,255,255,.5);backdrop-filter:blur(10px);}
.logo-container{display:flex;justify-content:center;align-items:center;width:100%;margin-bottom:20px;}
.logo-container img{width:120px;height:120px;border-radius:35%;object-fit:cover;
  box-shadow:0 10px 25px rgba(59,130,246,.2);border:4px solid #fff;}
.alt-logo{width:120px;height:120px;border-radius:35%;background:linear-gradient(135deg,#4f46e5,#3b82f6);
  color:#fff;display:flex;justify-content:center;align-items:center;font-weight:800;
  font-size:16px;text-align:center;border:4px solid #fff;box-shadow:0 10px 25px rgba(59,130,246,.2);}
 
/* ẢNH CARDS */
.img-card{background:#fff;border:2px solid #e0f2fe;border-radius:14px;padding:10px;
  text-align:center;margin-bottom:8px;box-shadow:0 2px 8px rgba(59,130,246,.08);}
.img-card img{max-height:80px;border-radius:8px;object-fit:cover;}
.var-badge{display:inline-block;background:#dbeafe;color:#1d4ed8;border-radius:20px;
  padding:2px 12px;font-size:13px;font-weight:800;margin-top:5px;}
.src-badge{display:inline-block;font-size:11px;color:#94a3b8;margin-top:3px;}
 
/* PASTE ZONE */
.paste-zone{background:#f0fdf4;border:2px dashed #86efac;border-radius:16px;
  padding:16px;text-align:center;margin-bottom:10px;font-size:14px;color:#166534;}
 
/* FLOATING */
.floating-container{position:fixed;bottom:30px;right:30px;display:flex;
  flex-direction:column;gap:15px;z-index:999999;}
.float-btn{width:55px;height:55px;border-radius:50%;box-shadow:0 10px 25px rgba(0,0,0,.15);
  display:flex;justify-content:center;align-items:center;background:#fff;
  transition:.3s;border:2px solid #e2e8f0;}
.float-btn:hover{transform:translateY(-5px);border-color:#3b82f6;}
.float-btn img{width:65%;height:65%;object-fit:contain;}
</style>
""", unsafe_allow_html=True)
 
# ── Session state defaults ────────────────────────────────────
_defaults = {
    "logged_in":False,"otp_verified":False,"otp_sent":False,
    "s_name":"Trường Sơn Marketing","s_email":"","s_pwd":"",
    "s_sign":"Trân trọng,\nTrường Sơn Marketing",
    # all_images: list of {"tag":"<img...>","source":"upload"|"paste","label":"...","preview_src":"data:..."}
    "all_images":[],
    # để tránh add trùng khi rerun
    "last_paste_tag":"",
}
for k,v in _defaults.items():
    if k not in st.session_state: st.session_state[k] = v
 
LOGO_URL = "logo_moi.png"
 
# ==========================================
# 1. ĐĂNG NHẬP
# ==========================================
if not st.session_state["logged_in"]:
    _, col2, _ = st.columns([1,1.2,1])
    with col2:
        st.markdown('<div class="auth-box">', unsafe_allow_html=True)
        logo_b64 = get_image_base64(LOGO_URL)
        if logo_b64:
            st.markdown(f'<div class="logo-container"><img src="data:image/png;base64,{logo_b64}"></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="logo-container"><div class="alt-logo">TRƯỜNG SƠN<br>MARKETING</div></div>', unsafe_allow_html=True)
        st.markdown('<h2 style="text-align:center;color:#0f172a;font-weight:900;font-size:28px;margin-bottom:5px;">BULKMAIL PRO</h2>', unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;color:#64748b;font-size:14px;margin-bottom:20px;">Đăng nhập để bắt đầu chiến dịch</p>', unsafe_allow_html=True)
 
        t_login, t_reg, t_forgot = st.tabs(["🔐 Đăng nhập","📝 Đăng ký","🔑 Quên MK"])
        users_db = load_users()
 
        with t_login:
            lu = st.text_input("Tên đăng nhập", key="login_u")
            lp = st.text_input("Mật khẩu", type="password", key="login_p")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("ĐĂNG NHẬP HỆ THỐNG", type="primary", use_container_width=True):
                ud = users_db.get(lu)
                if ud and ud.get("password") == hash_password(lp):
                    st.session_state["current_user"] = lu
                    st.session_state["logged_in"]    = True
                    st.rerun()
                else: st.error("❌ Thông tin đăng nhập chưa chính xác!")
 
        with t_reg:
            ru  = st.text_input("Tên đăng nhập mới", key="reg_u")
            re_ = st.text_input("Email khôi phục",   key="reg_e")
            rp  = st.text_input("Mật khẩu",           type="password", key="reg_p")
            rpc = st.text_input("Xác nhận mật khẩu", type="password", key="reg_pc")
            if st.button("TẠO TÀI KHOẢN", type="primary", use_container_width=True):
                if not ru or not re_ or not rp: st.warning("⚠️ Điền đủ thông tin!")
                elif ru in users_db:            st.error("❌ Username đã tồn tại!")
                elif rp != rpc:                 st.error("❌ Mật khẩu không khớp!")
                else:
                    save_user_api(ru, hash_password(rp), re_)
                    st.success("✅ Đăng ký thành công!")
 
        with t_forgot:
            if not st.session_state["otp_verified"]:
                fu = st.text_input("Nhập Username",          key="fg_u")
                fe = st.text_input("Nhập Email đã đăng ký", key="fg_e")
                if st.button("GỬI MÃ OTP", use_container_width=True):
                    if fu in users_db and users_db[fu].get("email") == fe:
                        otp = generate_otp()
                        if reset_password_api(fu, fe, hash_password(otp), True):
                            if send_otp_email(fe, fu, otp):
                                st.session_state["otp_sent"] = True
                                st.success(f"✅ OTP đã gửi tới {fe}")
                    else: st.error("❌ Thông tin không khớp!")
                if st.session_state["otp_sent"]:
                    oi = st.text_input("Mã OTP 6 số:", max_chars=6, key="otp_i")
                    if st.button("XÁC THỰC OTP", type="primary", use_container_width=True):
                        ui = load_users().get(fu)
                        if ui and ui.get("password") == hash_password(oi):
                            st.session_state["otp_verified"] = True
                            st.session_state["target_user"]  = fu
                            st.rerun()
                        else: st.error("❌ OTP không đúng!")
            else:
                np_ = st.text_input("Mật khẩu mới", type="password", key="new_p")
                if st.button("ĐỔI MẬT KHẨU", type="primary", use_container_width=True):
                    udb = load_users(); tgt = st.session_state["target_user"]
                    if reset_password_api(tgt, udb[tgt]["email"], hash_password(np_), False):
                        st.session_state["otp_verified"] = False
                        st.session_state["otp_sent"]     = False
                        st.success("✅ Đổi mật khẩu thành công!")
        st.markdown("</div>", unsafe_allow_html=True)
 
# ==========================================
# 2. DASHBOARD
# ==========================================
else:
    # HEADER
    hc1, hc2 = st.columns([5,1])
    with hc1:
        st.markdown('<div class="gradient-text">BulkMail</div>', unsafe_allow_html=True)
        st.markdown('<p style="color:#64748b;font-size:16px;margin-bottom:20px;">Thiết lập và vận hành hàng ngàn email cá nhân hóa chỉ trong tích tắc.</p>', unsafe_allow_html=True)
    with hc2:
        st.markdown(f"<div style='text-align:right;padding-top:10px;font-weight:bold;color:#1e40af;'>👤 {st.session_state['current_user']}</div>", unsafe_allow_html=True)
        if st.button("🚪 Đăng xuất", use_container_width=True):
            st.session_state["logged_in"] = False; st.rerun()
 
    # ── BƯỚC 1 ───────────────────────────────────────────────
    st.markdown('<div class="pill-header bg-blue">⚙️ BƯỚC 1: CẤU HÌNH MÁY CHỦ & BÁO CÁO</div>', unsafe_allow_html=True)
    with st.expander("Bấm để mở rộng Cài đặt Máy chủ", expanded=True):
        cc1, cc2 = st.columns(2, gap="large")
        with cc1:
            st.markdown("<b style='color:#1e40af;'>📧 Thông tin Gửi thư (Gmail)</b>", unsafe_allow_html=True)
            st.session_state["s_name"]  = st.text_input("Tên người gửi:", value=st.session_state["s_name"])
            st.session_state["s_email"] = st.text_input("Địa chỉ Gmail:", value=st.session_state["s_email"])
            st.session_state["s_pwd"]   = st.text_input("Mật khẩu ứng dụng (16 ký tự):", type="password", value=st.session_state["s_pwd"])
            with st.expander("❓ Hướng dẫn lấy Mật khẩu ứng dụng"):
                st.markdown("""<div style='font-size:14.5px;color:#334155;line-height:1.6;'>
                <b>1.</b> Truy cập <a href='https://myaccount.google.com/security' target='_blank' style='color:#3b82f6;'><b>Bảo mật Google</b></a>.<br>
                <b>2.</b> Bật <b>Xác minh 2 bước</b>.<br>
                <b>3.</b> Tìm <b>"Mật khẩu ứng dụng"</b> → Bấm chọn.<br>
                <b>4.</b> Đặt tên <i>"BulkMail"</i> → <b>Tạo</b> → Copy 16 ký tự.
                </div>""", unsafe_allow_html=True)
        with cc2:
            st.markdown("<b style='color:#1e40af;'>🔔 Báo cáo Telegram & Chữ ký</b>", unsafe_allow_html=True)
            ud = load_users().get(st.session_state["current_user"], {})
            ntk = st.text_input("Bot Token Telegram:", value=ud.get("tele_token",""), type="password")
            nid = st.text_input("Chat ID Telegram:",   value=ud.get("tele_chat_id",""))
            st.session_state["s_sign"] = st.text_area("Chữ ký cuối thư:", value=st.session_state["s_sign"], height=68)
            if st.button("💾 Lưu cấu hình Telegram"):
                if save_config_api(st.session_state["current_user"], ntk, nid):
                    st.success("✅ Đã lưu!")
 
    st.markdown("<hr style='margin:10px 0 20px 0;'>", unsafe_allow_html=True)
 
    col_data, col_content = st.columns([1,1.2], gap="large")
 
    # ── CỘT TRÁI ─────────────────────────────────────────────
    with col_data:
        # BƯỚC 2
        st.markdown('<div class="pill-header bg-purple">📁 BƯỚC 2: DỮ LIỆU KHÁCH HÀNG</div>', unsafe_allow_html=True)
        sample_df = pd.DataFrame({"email":["khachhang@gmail.com","vidu@gmail.com"]})
        try:
            xbuf = io.BytesIO()
            with pd.ExcelWriter(xbuf, engine="openpyxl") as w: sample_df.to_excel(w, index=False)
            dl_data = xbuf.getvalue()
        except: dl_data = sample_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 Tải File Mẫu (Excel)", data=dl_data, file_name="danh_sach_mau.xlsx", use_container_width=True)
        up = st.file_uploader("Tải tệp danh sách (.csv, .xlsx)", type=["csv","xlsx"])
        df = None
        if up:
            df = pd.read_excel(up) if up.name.endswith("xlsx") else pd.read_csv(up)
            st.success(f"✅ Hợp lệ! Đã nhận {len(df)} địa chỉ email.")
 
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="pill-header bg-purple" style="font-size:13px;padding:6px 18px;margin-bottom:10px;">📎 TỆP ĐÍNH KÈM (TÙY CHỌN)</div>', unsafe_allow_html=True)
        attachments = st.file_uploader("Kéo thả tài liệu", accept_multiple_files=True)
 
        # ── ẢNH INLINE ───────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="pill-header bg-orange" style="font-size:13px;padding:6px 18px;margin-bottom:6px;">🖼️ ẢNH CHÈN VÀO NỘI DUNG</div>', unsafe_allow_html=True)
        st.caption("Dùng **{{anh1}}**, **{{anh2}}**... trên một dòng riêng trong ô soạn thảo để chèn ảnh đúng vị trí.")
 
        tab_up, tab_paste = st.tabs(["📂 Upload từ máy tính","📋 Paste từ clipboard (Ctrl+V)"])
 
        # Tab Upload
        with tab_up:
            up_imgs = st.file_uploader(
                "Chọn ảnh (jpg, png, gif, webp) — có thể chọn nhiều",
                type=["jpg","jpeg","png","gif","webp","bmp"],
                accept_multiple_files=True, key="up_imgs"
            )
            if up_imgs:
                # Giữ ảnh paste cũ, cập nhật ảnh upload mới
                kept_paste = [x for x in st.session_state["all_images"] if x["source"]=="paste"]
                new_uploads = []
                for f in up_imgs:
                    tag = file_to_base64_tag(f)
                    # Lấy src để preview
                    m = re.search(r'src="([^"]+)"', tag)
                    prev = m.group(1) if m else ""
                    new_uploads.append({"tag":tag,"source":"upload","label":f.name,"preview_src":prev})
                st.session_state["all_images"] = new_uploads + kept_paste
 
        # Tab Paste
        with tab_paste:
            if PASTE_AVAILABLE:
                st.markdown(
                    '<div class="paste-zone">'
                    '📋 Nguồn hỗ trợ: <b>Web · Screenshot · Word · Excel · PowerPoint</b><br>'
                    'Bước 1: Copy ảnh (Ctrl+C hoặc PrtSc) &nbsp;→&nbsp; Bước 2: Bấm nút bên dưới &nbsp;→&nbsp; Bước 3: Ctrl+V'
                    '</div>', unsafe_allow_html=True
                )
                paste_result = paste_image_button(
                    label="📋 Bấm đây rồi nhấn Ctrl+V",
                    key="paste_btn"
                )
                if paste_result and paste_result.image_data is not None:
                    new_tag = pil_to_base64_tag(paste_result.image_data, label=f"paste_{len(st.session_state['all_images'])+1}")
                    # Chỉ thêm nếu khác lần paste trước (tránh trùng khi rerun)
                    if new_tag != st.session_state["last_paste_tag"]:
                        st.session_state["last_paste_tag"] = new_tag
                        m = re.search(r'src="([^"]+)"', new_tag)
                        prev = m.group(1) if m else ""
                        label = f"Paste #{sum(1 for x in st.session_state['all_images'] if x['source']=='paste')+1}"
                        st.session_state["all_images"].append({"tag":new_tag,"source":"paste","label":label,"preview_src":prev})
                        st.success(f"✅ Đã thêm ảnh paste ({label})!")
                        st.rerun()
            else:
                st.warning("⚠️ Chưa cài thư viện paste. Thêm dòng sau vào **requirements.txt** rồi redeploy:")
                st.code("streamlit-paste-button", language="text")
                st.info("Hoặc chạy lệnh: `pip install streamlit-paste-button` rồi restart app.")
 
        # ── Danh sách ảnh hiện tại ────────────────────────────
        all_imgs = st.session_state["all_images"]
        if all_imgs:
            st.markdown(f"<br><b style='color:#1e40af;'>🗂️ Danh sách ảnh ({len(all_imgs)} ảnh)</b>", unsafe_allow_html=True)
            dc1, dc2 = st.columns([1,1])
            with dc1:
                if st.button("🗑️ Xóa tất cả", use_container_width=True):
                    st.session_state["all_images"]    = []
                    st.session_state["last_paste_tag"] = ""
                    st.rerun()
            with dc2:
                # Xóa chỉ ảnh paste
                if any(x["source"]=="paste" for x in all_imgs):
                    if st.button("🗑️ Xóa ảnh paste", use_container_width=True):
                        st.session_state["all_images"]    = [x for x in all_imgs if x["source"]!="paste"]
                        st.session_state["last_paste_tag"] = ""
                        st.rerun()
 
            img_cols = st.columns(min(len(all_imgs), 3))
            for i, img in enumerate(all_imgs):
                var = "{{" + f"anh{i+1}" + "}}"
                icon = "📂" if img["source"]=="upload" else "📋"
                with img_cols[i % 3]:
                    st.markdown(
                        f'<div class="img-card">'
                        f'<img src="{img["preview_src"]}"><br>'
                        f'<span class="var-badge">{var}</span><br>'
                        f'<span class="src-badge">{icon} {img["label"][:18]}</span>'
                        f'</div>', unsafe_allow_html=True
                    )
 
    # ── CỘT PHẢI ─────────────────────────────────────────────
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
 
        with st.expander("📖 Hướng dẫn biến & chèn ảnh"):
            st.markdown("""
| Biến | Tác dụng |
|------|----------|
| `{{name}}` | Tên khách hàng (cột **name / tên** trong file) |
| `{{anh1}}` | Ảnh thứ 1 (upload hoặc paste) |
| `{{anh2}}` | Ảnh thứ 2 |
| `{{anh3}}` | Ảnh thứ 3... (tối đa 10) |
 
**Nguồn ảnh được hỗ trợ:**
 
| Tab | Nguồn |
|-----|-------|
| 📂 Upload | Kéo thả file từ máy tính |
| 📋 Paste | Web · Screenshot · Word · Excel · PowerPoint |
 
> 💡 Đặt biến `{{anh1}}` trên **một dòng riêng** để ảnh hiển thị đẹp nhất.
            """)
 
        col_delay, _ = st.columns([1,1])
        with col_delay:
            delay = st.number_input("⏳ Khoảng nghỉ/Mail (Giây):", value=15, min_value=5)
 
        # Xem trước
        sign_html = st.session_state["s_sign"].replace("\n","<br>")
        with st.expander("👁️ Xem trước email thực tế", expanded=False):
            ex_name = (str(df.iloc[0]["name"]) if df is not None and not df.empty and "name" in df.columns else "Quý khách")
            img_d   = {"{{" + f"anh{i+1}" + "}}": x["tag"] for i,x in enumerate(st.session_state["all_images"])}
            prev_body = build_email_html(
                raw_body.replace("{{name}}", f'<b style="color:#3b82f6;">{ex_name}</b>'), img_d
            )
            st.markdown(
                f"<div style='padding:20px;background:#fff;border-radius:8px;border:1px solid #e2e8f0;"
                f"font-family:Arial;line-height:1.8;color:#333;'>"
                f"{prev_body}<br><br>"
                f"<div style='color:#666;border-top:1px solid #eee;padding-top:10px;'>{sign_html}</div>"
                f"</div>", unsafe_allow_html=True
            )
 
    st.markdown("<hr style='margin:30px 0;'>", unsafe_allow_html=True)
 
    # ── GỬI MAIL ─────────────────────────────────────────────
    ca1, ca2 = st.columns([1.5,1])
    with ca1:
        st.markdown("""
        <div style="background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:20px;box-shadow:0 4px 6px -1px rgba(0,0,0,.05);">
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
 
    with ca2:
        st.markdown("<div style='margin-top:20px;'></div>", unsafe_allow_html=True)
        if st.button("🚀 BẮT ĐẦU CHIẾN DỊCH GỬI MAIL", type="primary", use_container_width=True):
            if df is None:
                st.error("⚠️ Vui lòng tải lên danh sách Khách hàng!")
            elif not subject:
                st.error("⚠️ Tiêu đề thư không được bỏ trống!")
            elif not st.session_state["s_email"] or not st.session_state["s_pwd"]:
                st.error("⚠️ Bạn chưa điền Email hoặc Mật khẩu ở Bước 1!")
            else:
                sign_send = st.session_state["s_sign"].replace("\n","<br>")
                img_d     = {"{{" + f"anh{i+1}" + "}}": x["tag"] for i,x in enumerate(st.session_state["all_images"])}
 
                # ✅ Nhúng ảnh 1 lần — không tải lại cho mỗi email
                with st.spinner("⏳ Đang xử lý và nhúng ảnh vào nội dung thư..."):
                    proc_body = build_email_html(raw_body, img_d)
 
                progress = st.progress(0)
                log = st.expander("📋 Trình giám sát (Live)", expanded=True)
                ok_list, err_list = [], []
 
                udr  = load_users().get(st.session_state["current_user"], {})
                r_tk = udr.get("tele_token",""); r_id = udr.get("tele_chat_id","")
                send_tele_msg(r_tk, r_id, f"🚀 <b>BẮT ĐẦU CHIẾN DỊCH</b>\n👤 {st.session_state['current_user']}")
 
                for idx, row in df.iterrows():
                    t_email = ""
                    try:
                        ec = next((c for c in df.columns if c.lower() in ["email","mail"]), None)
                        t_email = str(row.get(ec, row.iloc[0])).strip()
                        nc = next((c for c in df.columns if c.lower() in ["name","tên"]), None)
                        t_name  = str(row.get(nc,"Khách hàng")) if nc else "Khách hàng"
 
                        body = proc_body.replace("{{name}}", t_name)
                        html = (f"<div style='font-family:Arial;line-height:1.8;color:#333;'>{body}<br><br>"
                                f"<div style='color:#666;border-top:1px solid #eee;padding-top:10px;'>{sign_send}</div></div>")
 
                        msg = MIMEMultipart()
                        msg["From"]    = f"{st.session_state['s_name']} <{st.session_state['s_email']}>"
                        msg["To"]      = t_email
                        msg["Subject"] = subject
                        msg.attach(MIMEText(html,"html"))
 
                        if attachments:
                            for att in attachments:
                                p = MIMEBase("application","octet-stream")
                                p.set_payload(att.read()); encoders.encode_base64(p)
                                p.add_header("Content-Disposition",f"attachment; filename={att.name}")
                                msg.attach(p); att.seek(0)
 
                        with smtplib.SMTP("smtp.gmail.com",587) as srv:
                            srv.starttls()
                            srv.login(st.session_state["s_email"], st.session_state["s_pwd"])
                            srv.send_message(msg)
 
                        ok_list.append(t_email)
                        log.write(f"✅ Đã gửi: {t_email}")
                    except Exception as e:
                        err_list.append(t_email)
                        log.write(f"❌ Lỗi: {t_email} ({e})")
 
                    progress.progress((idx+1)/len(df))
                    time.sleep(delay)
 
                st.success("🎉 Chiến dịch hoàn tất!")
                cbuf = io.BytesIO()
                pd.DataFrame({"Email":ok_list+err_list,
                              "Kết quả":["Thành công"]*len(ok_list)+["Lỗi"]*len(err_list)
                             }).to_csv(cbuf, index=False, encoding="utf-8-sig")
                send_tele_msg(r_tk, r_id, f"📊 <b>TỔNG KẾT</b>\n✅ {len(ok_list)}\n❌ {len(err_list)}")
                send_tele_file(r_tk, r_id, cbuf.getvalue(), "ket_qua.csv")
                st.download_button("📥 TẢI BÁO CÁO (.CSV)", data=cbuf.getvalue(), file_name="ket_qua.csv", use_container_width=True)
 
    # CHÂN TRANG
    st.markdown("<br><br>", unsafe_allow_html=True)
    lf = get_image_base64(LOGO_URL)
    if lf:
        st.markdown(f'<div style="display:flex;justify-content:center;padding-top:20px;"><img src="data:image/png;base64,{lf}" style="width:150px;height:150px;border-radius:35%;object-fit:cover;border:4px solid #fff;box-shadow:0 10px 25px rgba(59,130,246,.15);"></div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="display:flex;justify-content:center;padding:25px 0 50px 0;">
      <div style="max-width:800px;text-align:center;color:#475569;padding:30px;border-radius:24px;
                  border:1px solid #e2e8f0;background:#fff;box-shadow:0 10px 25px rgba(0,0,0,.03);">
        <p style="font-size:15px;line-height:1.8;margin:0;">
          <b style="background:linear-gradient(90deg,#3b82f6,#8b5cf6);-webkit-background-clip:text;
             -webkit-text-fill-color:transparent;font-size:22px;font-weight:900;">BulkMail Pro</b><br><br>
          Là công cụ gửi thư tự động được phát triển bởi <b>Trường Sơn Marketing</b>.
          Với tiêu chí: <b>Dễ dùng - An toàn - Hiệu quả</b>.
        </p>
      </div>
    </div>""", unsafe_allow_html=True)
 
st.markdown("""<div class="floating-container">
  <a href="https://zalo.me/0935748199" target="_blank" class="float-btn">
    <img src="https://upload.wikimedia.org/wikipedia/commons/9/91/Icon_of_Zalo.svg"></a>
  <a href="https://t.me/BulkMail_Pro" target="_blank" class="float-btn">
    <img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg"></a>
</div>""", unsafe_allow_html=True)
