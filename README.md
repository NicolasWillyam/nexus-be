Dưới đây là file Markdown (`README.md` hoặc phần **Hướng dẫn khởi chạy**) được chuẩn hóa, trình bày chuyên nghiệp, tích hợp chính xác toàn bộ các câu lệnh bạn đã cung cấp.

Bạn có thể copy trực tiếp đoạn bên dưới vào dự án Backend của mình:

````markdown
## 🛠️ Hướng Dẫn Cài Đặt & Chạy Môi Trường Local

### 1. Khởi Tạo & Kích Hoạt Môi Trường Ảo (Virtual Environment)

Tùy thuộc vào hệ điều hành bạn đang sử dụng, hãy chạy các câu lệnh tương ứng dưới đây để tạo và kích hoạt môi trường ảo `venv`:

- **Trên macOS / Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
````

- **Trên Windows (CMD / PowerShell):**

```cmd
python -m venv venv
venv\Scripts\activate

```

---

### 2. Cài Đặt Các Thư Thư Viện Phụ Thuộc (Dependencies)

Sau khi đã kích hoạt môi trường ảo, tiến hành cài đặt các thư viện cần thiết:

```bash
pip install -r requirements.txt

```

---

### 3. Khởi Tạo Dữ Liệu Ban Đầu & Đồng Bộ (Database Setup & Jobs)

Trước khi khởi chạy ứng dụng lần đầu, hãy chạy các script để nạp dữ liệu mẫu (Seed Data) và tiến hành đồng bộ dữ liệu thị trường:

#### a. Nạp dữ liệu cơ sở ban đầu (Seed Data):

```bash
python -m app.seed_data

```

#### b. Chạy các Cron Jobs đồng bộ dữ liệu:

- **Đồng bộ dữ liệu cuối ngày (Daily Sync):**

```bash
python -m app.jobs.daily_sync

```

- **Đồng bộ dữ liệu trong ngày (Intraday Sync - Realtime):**

```bash
python -m app.jobs.intraday_sync

```

---

### 4. Khởi Chạy Server API (FastAPI)

Chạy ứng dụng ở chế độ Development với tính năng Auto-Reload:

```bash
uvicorn app.main:app --reload

```

- **API Base URL:** `http://127.0.0.1:8000`
- **Tài liệu Swagger UI:** `http://127.0.0.1:8000/docs`
- **Tài liệu ReDoc:** `http://127.0.0.1:8000/redoc`

```

```
