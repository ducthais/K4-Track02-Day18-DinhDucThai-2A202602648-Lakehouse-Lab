# Reflection: Anti-pattern trong AI Lakehouse

**Anti-pattern: Stale Vector Index Synchronization during Lifecycle Erasure**

Trong kiến trúc AI Lakehouse kết hợp RAG, anti-pattern nguy hiểm là xóa bản ghi trong bảng lưu trữ (Delta/Iceberg) nhưng quên xóa vector trong external index.

Hệ thống RAG dễ gặp lỗi này do vector database là thành phần tách rời, thường chỉ nhận embeddings qua batch push ban đầu. Khi người dùng thực thi quyền xóa dữ liệu (Right to Erasure theo Nghị định 13/2023/NĐ-CP), lệnh `DELETE` trên bảng Delta chỉ commit tombstone mới; external vector index vẫn giữ vector cũ và tiếp tục trả về dữ liệu đã xóa khi tìm kiếm ngữ nghĩa, gây rò rỉ thông tin cá nhân.

**Cách phòng tránh:**
1. Bật Delta Change Data Feed (`enableChangeDataFeed=true`) để bắt trọn mọi biến động dữ liệu.
2. Xây dựng CDC consumer tiêu thụ CDF stream, lọc sự kiện `_change_type='delete'` để xóa ngay vector trong external index.
3. Chạy job đối soát định kỳ qua DuckDB nhằm quét sạch vector mồ côi.

*AI Usage:* Hỗ trợ rà soát rubric (chi tiết tại [AI_USAGE.md](AI_USAGE.md)).
