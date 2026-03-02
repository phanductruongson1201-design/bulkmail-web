import pandas as pd

# D? li?u m?u
data = {
    "name": ["Nguy?n Van A", "Tr?n Th? B", "Lê Van C"],
    "email": ["email_thu_1@gmail.com", "email_thu_2@gmail.com", "email_thu_3@gmail.com"],
    "company": ["Công ty ABC", "T?p doàn XYZ", "Startup 123"],
    "danh_xung": ["Anh", "Ch?", "Anh"]
}

# T?o file Excel
df = pd.DataFrame(data)
df.to_excel("danh_sach_mau.xlsx", index=False)

print("? Ðã t?o thành công file 'danh_sach_mau.xlsx' trong thu m?c hi?n t?i!")
