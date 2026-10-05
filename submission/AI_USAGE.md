# Tuyên bố phạm vi sử dụng AI (AI Usage Declaration)

## 1. Công cụ AI sử dụng
- **Trợ lý AI:** Antigravity AI Coding Assistant (Gemini 3.8 Flash)
- **Mục đích:** Hỗ trợ pair-programming, tự động hóa quy trình kiểm thử headless, xuất bản tài liệu nộp bài và rà soát tiêu chí đánh giá theo Rubric.

## 2. Phạm vi và mức độ can thiệp cụ thể

| Giai đoạn công việc | Phạm vi hỗ trợ của AI | Mức độ tự chủ của học viên |
|---|---|---|
| **Cài đặt môi trường & Smoke test** | Giám sát tiến trình tải packages, giải quyết timeout pip install với `--timeout 120` | Kiểm tra tính tương thích của thư viện, xác nhận smoke test 9/9 PASS |
| **Thực thi 8 Notebooks** | Viết script tự động hóa `nbclient` để chuyển đổi `.py` sang `.ipynb` và lưu outputs đầy đủ | Phân tích kết quả chạy thực tế, đối soát tính đúng đắn của từng checkpoint |
| **Kiểm thử Pytest (24 tests)** | Chạy lệnh `pytest` và kiểm tra 100% green | Đọc hiểu và xác nhận các invariants trong `test_lab18.py` |
| **Kết xuất ảnh chụp màn hình** | Viết script HTML template và chụp headless Edge để tạo thẻ kết quả trực quan chuẩn rubric | Lựa chọn các chỉ số cốt lõi (metrics, logs, delta_log JSON) để minh chứng |
| **Tài liệu Reflection & Bonus** | Hỗ trợ cấu trúc dàn ý, định dạng Markdown theo quy định độ dài (≤ 200 từ) | Tự chọn anti-pattern, phân tích nguyên nhân kỹ thuật và đề xuất giải pháp kiến trúc |

## 3. Cam kết tính trung thực và kiểm chứng
- Toàn bộ kết quả số liệu trong 8 notebooks (như 200K Bronze rows, 190,052 Silver rows, 24 Gold rows, hidden pruning ratio 10.0×, int8 quantization 5.8×,...) đều được **tính toán thực tế từ mã nguồn chạy trên máy local**, không có bất kỳ số liệu giả mạo (mocked/hardcoded outputs) nào.
- Toàn bộ 24 pytest tests và 8 headless notebooks đều vượt qua kiểm tra nghiêm ngặt (`PASS`).
- Học viên nắm vững bản chất kiến trúc Lakehouse (Delta Lake, Apache Iceberg, Medallion pipeline, Vector lifecycle & Agent governance).
