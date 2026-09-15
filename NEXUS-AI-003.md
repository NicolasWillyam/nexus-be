# NEXUS-[TASK 16] – kiểm thử AI
 1. Thông tin
Họ tên:Nguyễn Gia Phương 
Nhóm: 3
Task: AI Testing
Ngày thực hiện:8/9/2026 -> 
 2. Chức năng này dùng để làm gì?
Mô tả đơn giản chức năng :
Chức năng này dùng để kiểm tra và đánh giá chất lượng các bài giải thích phân bổ danh mục đầu tư do AI sinh ra, đảm bảo tính chính xác, không bịa đặt số liệu và dễ hiểu cho người dùng.
 3. Nghiệp vụ
 3.1 Người dùng muốn làm gì?: Xem báo cáo phân tích chi tiết bằng văn bản giải thích lý do phân bổ tiền vào các mã cổ phiếu.
 3.2 Tại sao Nexus cần chức năng này?: Giúp tự động hóa việc tư vấn và giúp người dùng hiểu rõ căn cứ định lượng đằng sau các quyết định đầu tư.
 3.3 Người dùng sử dụng như thế nào?: Gửi yêu cầu phân bổ danh mục qua giao diện AI sau đó  Hệ thống gọi AI phân tích  từ đó trả về báo cáo dạng Markdown đã qua kiểm duyệt Guardrails cho người dùng qua giao diện web hoặc ứng dụng tương lai được phát triển.
 4. API sử dụng
API thứ nhất :GET /api/v1/data-pipeline/portfolio-inputs
 Chức năng: Thực hiện tiền xử lý dữ liệu lịch sử giá của một nhóm mã cổ phiếu để cung cấp các đầu vào toán học cốt lõi cho thuật toán tối ưu hóa danh mục đầu tư.
 Đặc điểm & Dữ liệu trả về:
      Nhận danh sách các mã cổ phiếu (symbols) và số ngày giao dịch chuẩn hóa trong năm (trading_days, mặc định 252 ngày).
          Tính toán và trả về Expected Returns (Lợi nhuận kỳ vọng quy đổi theo năm cho từng mã) và Covariance Matrix (Ma trận hiệp phương sai / rủi ro chéo giữa các mã cổ phiếu).
API thứ hai :GET /api/v1/portfolio/optimize-with-ai
 Chức năng: Nhận các thông tin định lượng về danh mục (điểm số cổ phiếu, tỷ trọng phân bổ, số tiền đầu tư) để yêu cầu mô hình AI sinh bài viết giải thích, đồng thời chạy qua tầng kiểm duyệt (Guardrails) nhằm đảm bảo tính chính xác.
 Đặc điểm & Dữ liệu trả về:
       Nhận payload đầu vào chứa cấu hình phân bổ vốn và các mã cổ phiếu.
       Tầng kiểm định (Guardrails) sẽ tự động kiểm tra xem AI có bịa đặt mã cổ phiếu lạ (hallucination) hay bị lệch số liệu tiền đầu tư hay không.
       Trả về kết quả gồm nội dung bài giải thích dạng Markdown (explanation_markdown) cùng trạng thái kiểm duyệt (guardrail_passed).
 5. Input
Các mã cổ phiếu mà khác hàng quan tâm và số tiền muốn đầu tư 
6. Output
Phản hồi trả về từ hệ thống sau khi hoàn tất quá trình xử lý và thông qua lớp kiểm duyệt an toàn (Guardrails Validator) bao gồm một cấu trúc JSON hoàn chỉnh chứa cả dữ liệu định lượng và báo cáo phân tích định tính bằng văn bản Markdown
7. Cách tôi thực hiện
Mô tả các bước thực hiện.
Liệt kê các bước bạn đã làm:
Tìm hiểu các tiêu chí kiểm thử AI (tính chính xác, chống bịa đặt, kiểm soát diễn giải).
Thiết lập bộ 10 test case dựa trên các nhóm chiến lược rủi ro và mã cổ phiếu đại diện.
Chạy kiểm thử
Clone code cài đặt môi trường 
Chạy file tạo cài dữ liệu database trên Pgadmin 
Thêm các mã key của bản thân vào file mới .evn trong mã nguồn gốc 
Chạy code nexus-be
Chạy API liên quan đến đánh giá từ AI về điểm của các mã cổ phiếu 
Nhận thấy AI không hoạt đông do tính năng giải thích của AI không hoạt động hoặc báo lỗi do sử dụng phiên bản thư viện client cũ hoặc các phương thức gọi API/định dạng tham số của LLM đã bị thay đổi/deprecated ở phiên bản hiện tại, ví dụ như cách khởi tạo OpenAI hay cú pháp truyền tham số messages/model
kiểm tra lại log lỗi, cập nhật cú pháp
chạy lại các API 
ghi nhận kết quả và đánh giá
 8. Code chính
Thêm file .env 
ai_explanation.py
9. Test

STT	Test Case / Tình huống	Dữ liệu đầu vào / Mã cổ phiếu	Kết quả thực tế từ AI	Đánh giá lỗi (Thực tế kiểm thử)	Trạng thái
1	Case 1: High return + high risk	LLY (Score: 85.16, Tỷ trọng: 21.4%)	AI nhận diện đúng điểm số cao và phân bổ lớn nhất.	AI tự suy diễn nguyên nhân do MACD/Sharpe dù công thức trọng số dựa trên mô hình toán.	Lỗi suy diễn nhân quả
2	Case 2: Low return + low risk	CVX (Score: 74.72, Tỷ trọng: 18.77%)	Chỉ ra đúng mức biến động thấp nhất (23.62%).	Khớp hoàn toàn dữ liệu backend, diễn đạt an toàn, chuẩn xác.	 PASS
3	Case 3: High score + low risk	GOOGL (Score: 69.96, Tỷ trọng: 17.58%)	Phản ánh đúng hiệu suất và tỷ trọng dòng vốn tối ưu.	Dữ liệu đồng bộ tốt với hệ thống phân tích.	 PASS
4	Kiểm tra vùng biên (RSI Quá bán)	AAPL (Score: 57.72, RSI: 25.98)	AI viết: "Áp dụng chiến lược bắt đáy"	Dùng từ "bắt đáy" là Nói quá / Sai nguyên tắc tài chính (quá bán không đồng nghĩa chắc chắn là đáy).	 FAIL Cần siết Prompt
5	Kiểm tra nhóm Sharpe âm	META (Score: 43.85, Sharpe: -0.62)	Mô tả đúng trạng thái Sharpe âm và rủi ro.	Phản ánh đúng thực tế số liệu kỹ thuật, không bịa đặt.	 PASS
6	Case 1: High return + high risk (Vùng RSI Quá mua)	TSLA (Score: 33.47, RSI: 70.38)	AI viết: "Áp lực điều chỉnh ngắn hạn"	Mang tính dự đoán tương lai quá mức dựa trên chỉ báo kỹ thuật đơn lẻ.	 PASS Lỗi overstatement
7	Case 2: Low return + low risk (Trọng số thấp)	MSFT (Score: 33.11, Tỷ trọng: 8.32%)	Giải thích rõ lý do tỷ trọng thấp đi kèm cảnh báo an toàn.	Văn phong rõ ràng, logic với cấu trúc phân bổ.	 PASS
					
					
10. Screenshot

Thêm screenshot chức năng.

---

# 11. Khó khăn gặp phải

Ví dụ:

- API response khác với dự kiến.
- Chưa biết cách xử lý empty state.
- Chưa biết cách xử lý loading.

---

# 12. Tôi đã học được gì?

...

---

# 13. Git

Branch:

feature/NEXUS-STOCK-002-stock-search

Commit:

feat: add stock search

Merge Request:

[link MR]

code ban đầu gặp lỗi do API Google thay đổi cấu trúc/model. Đoạn code bạn vừa sửa được xếp vào nhóm Fix lỗi kỹ thuật tiền kiểm thử (Pre-test Bug Fixing) để đảm bảo hệ thống có thể dựng lên được môi trường chạy.
