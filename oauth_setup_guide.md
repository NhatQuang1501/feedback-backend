# Hướng dẫn cấu hình OAuth cho hệ thống Feedback

## Cấu hình Google OAuth

1. Truy cập [Google Cloud Console](https://console.cloud.google.com/)
2. Tạo một dự án mới
3. Vào "APIs & Services" > "Credentials"
4. Chọn "Create Credentials" > "OAuth client ID"
5. Chọn "Web application"
6. Đặt tên cho OAuth client
7. Thêm các Authorized JavaScript origins:
   - http://localhost:3000 (cho frontend)
   - http://127.0.0.1:8000 (cho backend)
8. Thêm các Authorized redirect URIs:
   - http://localhost:3000/auth/google/callback
   - http://127.0.0.1:8000/api/auth/login/google/
9. Lưu và sao chép Client ID và Client Secret vào file .env

## Cấu hình Frontend

Trong frontend, cài đặt thư viện OAuth:
- React: `react-oauth/google` cho Google

