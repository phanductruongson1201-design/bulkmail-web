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

# 1. Cấu hình trang Web
st.set_page_config(page_title="BulkMail Pro - Professional", page_icon="🔵", layout="wide")

# Khởi tạo biến lưu trạng thái báo cáo (Sửa lỗi mất nút tải)
if 'log_data' not in st.session_state:
    st.session_state.log_data = None

# ==========================================
# GIAO DIỆN CSS: TONE XANH NƯỚC BIỂN
# ==========================================
st.markdown("""
<style>
    .stApp { background-color: #F0F4F8; }
    h1, h2, h3 { color: #003366 !important; font-family: 'Segoe UI', Tahoma, sans-serif; }
    .stButton>button {
        background-color: #0056b3 !important; color: white !important;
        border-radius: 6px; border: none; padding: 10px 24px; font-weight: 600;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); transition: all 0.3s ease;
    }
    .stButton>button:hover { background-color: #003366 !important; box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15); transform: translateY(-1px); }
    .stDropzone { border: 2px dashed #0056b3 !important; background-color: #E6F0FA !important; }
    div[data-testid="stAlert"] { background-color: #E6F0FA; color: #003366; border-left: 5px solid #0056b3; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# NỘI DUNG CHÍNH CỦA APP
# ==========================================

st.title("🔵 BulkMail Pro – Trình Quản Lý Email Marketing")
st.info("💡 Hệ thống gửi email hàng loạt cá nhân hóa. Vui lòng sử dụng cho danh sách liên hệ hợp pháp.")

col1, col2 = st.columns([1, 1])

with col1:
    st.header("1. Cấu hình Máy chủ & Tài khoản")
    
    sender_name = st.text_input("Tên hiển thị người gửi (VD: Công ty ABC):")
    sender_email = st.text_input("Email gửi:")
    app_password = st.text_input("App Password:", type="password", help="Mật khẩu ứng dụng 16 ký tự của Gmail")
    
    c1, c2 = st.columns(2)
    with c1:
        smtp_server = st.text_input("SMTP Server:", value="smtp.gmail.com")
    with c2:
        smtp_port = st.text_input("Port:", value="587")

    st.header("2. Dữ liệu Khách hàng (.csv, .xlsx)")
    uploaded_file = st.file_uploader("Kéo thả file danh sách email vào đây", type=["csv", "xlsx"])
    
    df = None
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            df.columns = df.columns.str.strip().str.lower()
            if 'email' not in df.columns:
                st.error("Lỗi: File tải lên bắt buộc phải có cột tên là 'email'.")
                df = None
            else:
                df = df.dropna(subset=['email'])
                st.success(f"✅ Đã tải {len(df)} liên hệ. Các trường dữ liệu: {', '.join(df.columns)}")
                st.dataframe(df.head(3), use_container_width=True)
        except Exception as e:
            st.error(f"Lỗi đọc file: {e}")

    st.header("3. Đính kèm Tài liệu (Tùy chọn)")
    uploaded_attachments = st.file_uploader("Chọn file đính kèm (cho phép nhiều file)", accept_multiple_files=True)

with col2:
    st.header("4. Biên soạn Nội dung")
    subject = st.text_input("Tiêu đề (Subject):")
    body = st.text_area("Nội dung (Hỗ trợ định dạng HTML) - Cú pháp biến: {{tên_cột}}", height=200, 
                        value="Kính chào {{name}},<br><br>Nhập nội dung email của bạn tại đây...")

    with st.expander("👁️ Xem trước hiển thị Email (Live Preview)", expanded=False):
        st.markdown("*Minh họa bố cục email (các biến sẽ được thay thế khi gửi thực tế):*")
        components.html(body, height=250, scrolling=True)

    st.header("5. Thiết lập Gửi & Kiểm tra")
    delay = st.number_input("Khoảng nghỉ giữa 2 email (giây):", min_value=1, max_value=60, value=5)
    
    st.markdown("---")
    test_email = st.text_input("Địa chỉ Email nhận Test:")
    if st.button("Thử nghiệm (Gửi Test)"):
        if not sender_email or not app_password or not test_email:
            st.warning("Vui lòng điền đủ Email gửi, App Password và Email nhận test.")
        else:
            try:
                # Kiểm tra port
                port_num = int(smtp_port.strip())
                
                smtp = smtplib.SMTP(smtp_server, port_num)
                smtp.starttls()
                smtp.login(sender_email, app_password)
                
                msg = MIMEMultipart()
                msg['From'] = f"{sender_name} <{sender_email}>" if sender_name else sender_email
                msg['To'] = test_email
                msg['Subject'] = "[TEST] " + subject
                msg.attach(MIMEText(body, 'html'))
                
                if uploaded_attachments:
                    for file in uploaded_attachments:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(file.getvalue())
                        encoders.encode_base64(part)
                        part.add_header("Content-Disposition", "attachment", filename=file.name)
                        msg.attach(part)

                smtp.send_message(msg)
                smtp.quit()
                st.success("✅ Đã gửi email test thành công! Vui lòng kiểm tra hộp thư của bạn.")
            except ValueError:
                st.error("❌ Lỗi: Port phải là một con số (VD: 587)")
            except Exception as e:
                st.error(f"❌ Lỗi gửi test: {e}")

# 3. Khu vực thực thi gửi hàng loạt
st.markdown("---")
st.header("🚀 6. Kích hoạt Chiến dịch")

if st.button("▶ BẮT ĐẦU GỬI HÀNG LOẠT", type="primary", use_container_width=True):
    if df is None or len(df) == 0:
        st.error("Vui lòng tải lên danh sách email hợp lệ trước!")
    elif not sender_email or not app_password or not subject or not body:
        st.error("Vui lòng điền đầy đủ thông tin SMTP, tiêu đề và nội dung Email!")
    else:
        st.session_state.log_data = None # Reset log cũ
        progress_bar = st.progress(0)
        status_text = st.empty()
        log_area = st.empty()
        
        sent_count = 0
        error_count = 0
        batch_count = 0
        total_emails = len(df)
        log_messages = []

        attachments_data = []
        if uploaded_attachments:
            for file in uploaded_attachments:
                attachments_data.append({
                    "name": file.name,
                    "data": file.getvalue()
                })

        try:
            port_num = int(smtp_port.strip())
            
            def connect_smtp():
                s = smtplib.SMTP(smtp_server, port_num)
                s.starttls()
                s.login(sender_email, app_password)
                return s

            smtp = connect_smtp()
            
            for index, row in df.iterrows():
                recipient_email = str(row['email']).strip()
                if not recipient_email or recipient_email.lower() == 'nan':
                    # Bỏ qua dòng trống nhưng vẫn cập nhật thanh tiến trình
                    total_emails -= 1 
                    continue

                p_subject = subject
                p_body = body
                for col in df.columns:
                    val = str(row[col]) if pd.notna(row[col]) else ""
                    p_subject = p_subject.replace(f"{{{{{col}}}}}", val)
                    p_body = p_body.replace(f"{{{{{col}}}}}", val)

                msg = MIMEMultipart()
                msg['From'] = f"{sender_name} <{sender_email}>" if sender_name else sender_email
                msg['To'] = recipient_email
                msg['Subject'] = p_subject
                msg.attach(MIMEText(p_body, 'html'))

                for att in attachments_data:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(att["data"])
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", "attachment", filename=att['name'])
                    msg.attach(part)

                try:
                    smtp.send_message(msg)
                    sent_count += 1
                    batch_count += 1
                    log_messages.append(f"✅ Thành công: {recipient_email}")
                except Exception as e:
                    error_count += 1
                    log_messages.append(f"❌ Lỗi ({recipient_email}): {str(e)}")

                if total_emails > 0:
                    progress = (sent_count + error_count) / total_emails
                    progress_bar.progress(min(progress, 1.0))
                
                status_text.write(f"**Tiến độ:** Đã gửi: {sent_count} | Lỗi: {error_count} | Tổng số: {total_emails}")
                log_area.text("\n".join(log_messages[-5:]))

                if batch_count >= 50:
                    try:
                        smtp.quit()
                        status_text.write(f"Đang làm mới phiên kết nối SMTP để đảm bảo an toàn...")
                        time.sleep(5)
                        smtp = connect_smtp()
                        batch_count = 0
                    except Exception as e:
                        log_messages.append(f"⚠️ Lỗi kết nối lại: {e}")

                if index < total_emails - 1:
                    time.sleep(delay)

            try:
                smtp.quit()
            except: pass

            st.success(f"🎉 CHIẾN DỊCH HOÀN TẤT! Đã gửi thành công {sent_count}/{total_emails} email.")
            
            # Lưu log vào session_state để không bị mất nút tải
            log_df = pd.DataFrame({"Thời gian": [datetime.now().strftime('%Y-%m-%d %H:%M:%S')] * len(log_messages), 
                                   "Kết quả": log_messages})
            st.session_state.log_data = log_df.to_csv(index=False).encode('utf-8-sig')

        except ValueError:
            st.error("❌ Lỗi cấu hình: Port phải là một con số (VD: 587)")
        except Exception as e:
            st.error(f"❌ Lỗi SMTP hệ thống: Xin kiểm tra lại Email và App Password. Chi tiết: {e}")

# Hiển thị nút tải file Log bên ngoài vòng lặp (Dựa vào session state)
if st.session_state.log_data is not None:
    st.download_button(
        label="📥 TẢI XUỐNG BÁO CÁO (CSV)",
        data=st.session_state.log_data,
        file_name=f"BulkMail_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
