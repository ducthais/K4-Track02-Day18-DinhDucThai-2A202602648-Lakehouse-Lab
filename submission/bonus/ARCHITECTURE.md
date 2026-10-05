# Kiến trúc Lakehouse cho LLM Observability Quy mô 1 Tỷ Requests/Ngày

**Tác giả:** Đinh Đức Thái (MSSV: 2A202602648)  
**Môn học:** K4-Track02 — Day 18 Lakehouse Lab  
**Đề tài lựa chọn:** Topic A — LLM Observability ở quy mô 1B requests/ngày  

---

## 1. Problem Statement (Bài toán kỹ thuật)

Một foundation-model API platform ghi nhận nhật ký của toàn bộ lượt gọi LLM với quy mô **1 tỷ requests/ngày**. Mỗi request có payload trung bình ~5 KB (prompt, completion, model metadata, latency, user identifiers), tương đương **5 TB dữ liệu thô/ngày (uncompressed)**.

### Ràng buộc và thách thức cốt lõi:
1. **Độ trễ truy vấn (SLA):** Dashboard chi phí (token cost) và độ trễ (latency p50/p95/p99) theo từng tenant phải được cập nhật định kỳ mỗi **5 phút**; độ trễ truy vấn dashboard p95 < 2 giây.
2. **Vòng đời dữ liệu (Retention Lifecycle):** Toàn bộ prompt/response thô cần được giữ lại trong **7 ngày** để phục vụ đội ngũ kỹ thuật rà soát sự cố (incident review), sau 7 ngày tự động giải phóng; các chỉ số tổng hợp cấp Gold được lưu trữ **1 năm**.
3. **Tuân thủ bảo mật & PII:** Thông tin định danh cá nhân (PII như email, phone, API keys) phải được che giấu/token hóa trước khi bất kỳ nhân viên hoặc hệ thống phân tích nào có quyền truy cập.
4. **Hạn mức tài chính (FinOps Cap):** Tổng chi phí lưu trữ (Storage & API request cost) trên toàn bộ các tầng không được vượt quá **$5,000 USD / tháng**.

---

## 2. Kiến trúc tổng thể (Architecture Diagram)

Kiến trúc áp dụng mô hình **Medallion Pipeline (Bronze → Silver → Gold)** kết hợp giao thức **Delta Lake 1.x**, cơ chế streaming micro-batching, tokenization tại cửa ngõ ingest, và quản lý siêu dữ liệu tập trung qua **Apache Polaris REST Catalog**.

```text
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                                INGESTION & GATEWAY LAYER                               │
 │  1B req/day (~11,570 req/s avg, 30,000 peak) → API Gateways → Redpanda / Apache Kafka  │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │ Micro-batch (60s trigger, ~700K events)
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ 🥉 BRONZE LAYER — S3 Standard (Raw Append-Only, 7-Day TTL)                             │
 │ • Path: s3://lakehouse-data/bronze/llm_raw_events/                                     │
 │ • Schema: (request_id, ts, raw_json, headers, tenant_id)                               │
 │ • Day 18 Concept: ACID Streaming Append, Zero-copy Ingestion, 128MB-256MB Parquet      │
 │ • FinOps: S3 Lifecycle Rule tự động xóa đối tượng sau 7 ngày (Hard Expiry)             │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │ Structured Streaming + Vault Tokenization
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ 🥈 SILVER LAYER — S3 Standard / Infrequent Access (Cleansed, Partitioned, Z-Ordered)   │
 │ • Path: s3://lakehouse-data/silver/llm_events_cleansed/                                │
 │ • Schema: (request_id, ts, tenant_id, model, prompt_tok, comp_tok, lat_ms, pii_tokens) │
 │ • Day 18 Concepts:                                                                     │
 │   - PII Tokenization: HMAC-SHA256 Salted Hash (irreversible for analytics)             │
 │   - Partitioning: Partition theo date(ts)                                              │
 │   - Clustering: Z-ORDER BY (tenant_id, ts) giúp file-skipping ≥ 20×                   │
 │   - Change Data Feed (CDF): Ghi nhận tombstone phục vụ đồng bộ chỉ mục                 │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │ Continuous 5-min Windowed Aggregation
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │ 🥇 GOLD LAYER — S3 Standard (Aggregates, 1-Year Retention)                            │
 │ • Path: s3://lakehouse-data/gold/tenant_model_metrics_5m/                               │
 │ • Granularity: 5-minute tumbling window × tenant_id × model                            │
 │ • Metrics: p50/p95/p99 latency, sum(prompt_tokens), sum(completion_tokens), cost_usd    │
 │ • Day 18 Concepts: Dimensional Modeling, ACID MERGE upsert, Sub-second DuckDB reads   │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │ Zero-Copy Arrow Query Engine
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                                   SERVING & CONSUMPTION                                │
 │ • Realtime Dashboards: DuckDB / Trino qua Apache Polaris REST Catalog (p95 < 500ms)    │
 │ • Compliance & Audit: Read-access audit log + Key Vault unmasking cho Legal Audit      │
 └────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Năm quyết định kiến trúc chính & Các phương án bị loại bỏ

### Quyết định 1: Định dạng bảng lưu trữ (Table Storage Format)
- **Lựa chọn:** Chọn **Delta Lake 1.x**.
- **Lý do chọn:** Hỗ trợ tính năng *Change Data Feed (CDF)* xuất sắc cho streaming dedup; engine Rust native (`delta-rs`) cho phép DuckDB và Polars đọc trực tiếp không cần JVM; hỗ trợ `OPTIMIZE ... ZORDER BY` hoàn thiện giúp tối ưu hóa lọc theo `tenant_id`.
- **Phương án bị loại 1 (Apache Hudi):** Bị loại vì metadata overhead quá lớn ở quy mô hàng trăm nghìn file nhỏ; phụ thuộc nặng vào hệ sinh thái Java/Spark, không tương thích mượt mà với các engine truy vấn Python/C++ nhẹ như DuckDB.
- **Phương án bị loại 2 (Plain Parquet + Hive Metastore):** Bị loại vì thiếu đảm bảo ACID. Không thể đồng thời vừa ghi streaming vừa chạy job dọn dẹp compaction mà không gây xung đột đọc dữ liệu rách (dirty reads). Hoàn toàn không có tính năng Time Travel để phục hồi khi pipeline ghi nhầm dữ liệu lỗi.

### Quyết định 2: Chiến lược phân vùng và gom cụm (Partitioning & Clustering Strategy)
- **Lựa chọn:** Phân vùng theo **`date(ts)` (daily partition)** kết hợp gom cụm dữ liệu đa chiều **`Z-ORDER BY (tenant_id, ts)`** trong từng partition; kích thước file mục tiêu đặt ở **128 MB – 256 MB**.
- **Lý do chọn:** Với 10,000 tenants hoạt động song song, việc Z-Order giúp gom cụm các bản ghi của cùng một tenant vào một số lượng tối thiểu các file Parquet. Nhờ min/max stats trong transaction log, truy vấn lọc theo tenant có thể prune (loại bỏ) hơn 90% số file mà không cần đọc dữ liệu.
- **Phương án bị loại 1 (Phân vùng vật lý theo `tenant_id`):** Bị loại vì gây ra thảm họa phân mảnh thư mục (Small-File Explosion). 10,000 tenants × 288 chu kỳ micro-batch/ngày = 2.88 triệu thư mục/ngày, làm tê liệt S3 GET metadata và chi phí request tăng vọt.
- **Phương án bị loại 2 (Bảng phẳng không phân vùng):** Bị loại vì mọi truy vấn dashboard 5 phút đều phải quét toàn bộ bảng (full table scan), chi phí quét I/O vượt ngưỡng ngân sách và thời gian đáp ứng không thể đạt p95 < 2 giây.

### Quyết định 3: Cơ chế che giấu và bảo vệ thông tin định danh (PII Redaction/Tokenization)
- **Lựa chọn:** Thực hiện **Tokenization tại cửa ngõ chuyển giao Bronze → Silver** bằng giải pháp Salted HMAC-SHA256 với mã khóa lưu trữ trong AWS KMS / HashiCorp Vault.
- **Lý do chọn:** Dữ liệu thô chứa prompt đầy đủ chỉ tồn tại trong Bronze (truy cập giới hạn bởi IAM role đặc quyền và tự động xóa sau 7 ngày). Tầng Silver và Gold hoàn toàn không chứa PII dạng plaintext, cho phép mở rộng quyền truy cập cho toàn bộ đội ngũ BI/Data Science mà không vi phạm quy định bảo vệ dữ liệu.
- **Phương án bị loại 1 (Dynamic Masking tại thời điểm truy vấn):** Bị loại vì tiêu tốn tài nguyên CPU khổng lồ của query engine trên mỗi lần refresh dashboard; ngoài ra tiềm ẩn rủi ro rò rỉ dữ liệu khi người dùng xuất kết quả qua tầng cache bộ nhớ.
- **Phương án bị loại 2 (Redaction ngay tại Edge API Gateway):** Bị loại vì khi xảy ra sự cố an ninh nghiêm trọng cần điều tra pháp lý trong vòng 7 ngày, hệ thống hoàn toàn mất dấu vết ngữ cảnh ban đầu của prompt.

### Quyết định 4: Quản trị danh mục và siêu dữ liệu (Catalog & Governance)
- **Lựa chọn:** Triển khai **Apache Polaris (REST Catalog Spec)**.
- **Lý do chọn:** Chuẩn mở REST Catalog độc lập với nhà cung cấp đám mây (Vendor-neutral), cho phép chia sẻ metadata đồng nhất cho cả Spark (ghi streaming), Trino (phân tích ad-hoc) và DuckDB (phục vụ dashboard nhanh). Hỗ trợ kiểm soát truy cập cấp bảng và phân quyền theo vai trò (RBAC) chi tiết.
- **Phương án bị loại 1 (AWS Glue Data Catalog độc quyền):** Bị loại vì chi phí request rate limit của Glue rất đắt đỏ khi tiếp nhận hàng trăm commit mỗi giờ từ streaming engine, đồng thời tạo ra rào cản vendor lock-in nếu muốn triển khai multi-cloud.
- **Phương án bị loại 2 (Hive Metastore truyền thống chạy trên RDBMS):** Bị loại do nút thắt cổ chai về hiệu năng (single point of failure), dễ nghẽn transaction lock khi có nhiều writer và reader ghi nhật ký đồng thời.

### Quyết định 5: Chiến lược bảo trì định kỳ và FinOps (Maintenance & Storage Tiering)
- **Lựa chọn:** Thiết lập **Chu trình bảo trì 3 bước tự động**:
  1. Compaction chạy mỗi 60 phút: gộp các micro-batch nhỏ thành file 256 MB.
  2. Z-Order định kỳ 6 tiếng một lần cho phân vùng ngày hiện tại.
  3. S3 Lifecycle Rule hết hạn cứng sau 7 ngày cho Bronze + `VACUUM` với retention 168 giờ trên Silver.
- **Lý do chọn:** Đảm bảo duy trì hiệu năng query ổn định, tránh suy thoái Delta log, đồng thời chủ động giải phóng dung lượng rác và file mồ côi (orphans) để kiểm soát chặt chẽ ngân sách lưu trữ dưới $5,000/tháng.
- **Phương án bị loại 1 (Dịch vụ Auto-Compaction tự động của nhà cung cấp Cloud):** Bị loại vì tính phí theo số lượng đối tượng ($0.004 / 1,000 objects). Với dòng dữ liệu streaming 1 tỷ sự kiện/ngày, chi phí dọn dẹp tự động có thể vượt quá $1,800/tháng chỉ riêng tiền phí bảo trì.
- **Phương án bị loại 2 (Bảo trì thủ công không định kỳ):** Bị loại vì chỉ sau 48 giờ không compact, số lượng file nhỏ sẽ tích lũy vượt 50,000 file, khiến thời gian đọc metadata tăng từ vài mili-giây lên hơn 20 giây (gây gãy SLA dashboard 5 phút).

---

## 4. Kịch bản sự cố lúc 3 giờ sáng (Failure Modes & Rollback Runbooks)

### Sự cố 1: Lỗi xoay khóa KMS làm gãy pipeline Tokenization tại tầng Silver
- **Hiện tượng (3:00 AM):** Dịch vụ AWS KMS tự động xoay key nhưng service account của pipeline Silver chưa được cấp quyền decrypt key mới. Dữ liệu ghi vào Silver bị null toàn bộ cột `tenant_token` hoặc ghi đè chuỗi lỗi.
- **Cơ chế phát hiện:** Job kiểm tra chất lượng dữ liệu (Data Quality Gate) tại Silver phát hiện tỷ lệ `null_rate(tenant_token) > 0.1%`, kích hoạt PagerDuty mức Severity-1 và tạm dừng streaming checkpoint.
- **Quy trình Rollback (Áp dụng khái niệm Day 18 — Time Travel & RESTORE):**
  1. Sửa quyền truy cập IAM role cho KMS key.
  2. Sử dụng Delta Time Travel khôi phục bảng Silver về phiên bản trước khi xảy ra sự cố:
     ```python
     from deltalake import DeltaTable
     dt = DeltaTable("s3://lakehouse-data/silver/llm_events_cleansed")
     dt.restore(v_safe_checkpoint)
     ```
  3. Thiết lập lại `startingTimestamp` của Spark Structured Streaming về mốc thời gian an toàn của Bronze để replay lại quá trình parse và tokenization mà không làm mất bất kỳ request nào.

### Sự cố 2: Đột biến tải đột ngột (Traffic Surge) gây thảm họa Small-File Pathology
- **Hiện tượng (3:30 AM):** Một khách hàng lớn chạy batch test tải 50,000 req/s trong 45 phút. Bộ đệm streaming buộc phải flush liên tục mỗi 2 giây, sinh ra hơn 10,000 file kích thước chỉ ~80 KB tại phân vùng ngày hôm đó. Thời gian phản hồi của dashboard 5 phút nhảy vọt từ 400ms lên 12 giây, đe dọa vi phạm cam kết SLA.
- **Cơ chế phát hiện:** CloudWatch Alarm theo dõi số lượng file trong Delta log partition vượt ngưỡng 500 files/partition.
- **Quy trình Khắc phục (Áp dụng khái niệm Day 18 — Emergency Compaction & Z-Order):**
  1. Kích hoạt khẩn cấp runner tối ưu hóa nhắm mục tiêu vào duy nhất phân vùng đang chịu tải:
     ```python
     dt = DeltaTable("s3://lakehouse-data/silver/llm_events_cleansed")
     dt.optimize.compact(partition_filters=[("date", "=", current_date)], target_size=256*1024*1024)
     dt.optimize.z_order(["tenant_id"], partition_filters=[("date", "=", current_date)])
     ```
  2. Thao tác này gom 10,000 file nhỏ thành ~18 file chuẩn 256 MB trong vòng 60 giây, đưa độ trễ dashboard trở lại dưới 500ms ngay trong chu kỳ refresh tiếp theo.

### Sự cố 3: Rò rỉ file mồ côi (Orphan Files) sau sự cố sập Executor khi đang Compaction
- **Hiện tượng (4:15 AM):** Node chạy job compaction định kỳ bị Spot Instance termination giữa chừng khi đã ghi xong 15 file Parquet mới nhưng chưa kịp hoàn tất commit JSON vào `_delta_log/`. Các file Parquet vô chủ này nằm lại trên S3, không được metadata quản lý nhưng vẫn bị tính tiền lưu trữ.
- **Cơ chế phát hiện:** Job kiểm toán lưu trữ hàng ngày đối soát dung lượng vật lý trên S3 với tổng dung lượng khai báo trong file JSON metadata mới nhất, phát hiện chênh lệch > 50 GB.
- **Quy trình Khắc phục (Áp dụng khái niệm Day 18 — Maintenance FSCK & Orphan Sweep):**
  1. Chạy quy trình quét và thu hồi file mồ côi:
     ```python
     orphans = dt.repair(dry_run=False) # hoặc script quét diff giữa S3 object list và active delta snapshot
     ```
  2. Hệ thống định danh chính xác các file có `modification_time` cũ hơn 6 tiếng mà không nằm trong bất kỳ active transaction nào và thực hiện lệnh xóa vật lý an toàn.

---

## 5. Ước tính chi phí chi tiết (Back-of-the-Envelope FinOps Math)

Ngân sách trần của Giám đốc Tài chính (CFO Cap): **≤ $5,000 USD / tháng**.

### 5.1. Dữ liệu đầu vào và hệ số nén
- Lưu lượng: 1,000,000,000 requests/ngày.
- Kích thước trung bình: 5 KB/request.
- Dung lượng thô (Uncompressed Raw): 5,000,000,000 KB = **5.0 TB/ngày**.
- Tỷ số nén định dạng Parquet với thuật toán ZSTD (Compression Ratio ≈ 4:1):
  - Dung lượng nén thực tế của Bronze: 5.0 TB / 4 = **1.25 TB/ngày**.
- Tầng Silver (loại bỏ headers dư thừa, chuẩn hóa kiểu dữ liệu): **0.80 TB/ngày**.
- Tầng Gold (chỉ lưu aggregate 5 phút × 10,000 tenants × 10 models): **0.002 TB/ngày (2 GB/ngày)**.

### 5.2. Tính toán chi phí lưu trữ (Storage Math)

| Tầng dữ liệu | Thời gian lưu trữ (Retention) | Dung lượng tích lũy | Đơn giá S3 Standard / IA | Thành tiền hàng tháng |
|---|---|---|---|---|
| **Bronze (Raw JSON)** | 7 ngày (S3 Lifecycle Expire) | 7 × 1.25 TB = **8.75 TB** | $0.023 / GB ($23.55 / TB) | 8.75 × $23.55 = **$206.06 / tháng** |
| **Silver (Cleansed)** | 30 ngày (Hot) + 60 ngày (S3-IA) | Hot: 30 × 0.8 TB = **24 TB**<br>IA: 60 × 0.8 TB = **48 TB** | S3 Standard: $23.55 / TB<br>S3-IA: $12.80 / TB | (24 × 23.55) + (48 × 12.80)<br>= 565.20 + 614.40 = **$1,179.60 / tháng** |
| **Gold (Metrics)** | 365 ngày (1 năm toàn vẹn) | 365 × 0.002 TB = **0.73 TB** | S3 Standard: $23.55 / TB | 0.73 × $23.55 = **$17.19 / tháng** |
| **Tổng chi phí lưu trữ** | | **~81.5 TB tổng cộng** | | **$1,402.85 / tháng** |

### 5.3. Tính toán chi phí API Requests (PUT, GET, LIST)
- Ingestion buffer gom micro-batch 60s → 1,440 batches/ngày. Mỗi batch sinh ra ~10 file Parquet dung lượng 128 MB:
  - Số lượng file ghi hàng ngày: 1,440 × 10 = **14,400 PUTs/ngày** = 432,000 PUTs/tháng.
  - Chi phí PUT S3 ($0.005 / 1,000 requests): 432 × $0.005 = **$2.16 / tháng**.
- Truy vấn Dashboard: 100 truy vấn/phút = 4.32 triệu GETs/tháng. Nhờ Z-Order pruning chỉ đọc 5% số file:
  - Chi phí GET S3 ($0.0004 / 1,000 requests): 4,320 × $0.0004 = **$1.73 / tháng**.

### 5.4. Tính toán chi phí Compute xử lý nền tảng
- Cụm Spark Structured Streaming phân tán (3 nodes `c6g.2xlarge` Spot Instances @ $0.136/giờ):
  - 3 nodes × $0.136/hr × 730 giờ = **$298.08 / tháng**.
- Serverless Query Engine cho Dashboard (DuckDB chạy in-container trên cụm backend app hiện hữu):
  - Tận dụng tài nguyên bộ nhớ đệm, ước tính chi phí phụ trợ: **$150.00 / tháng**.

### 5.5. Tổng kết ngân sách FinOps
$$\text{Tổng ngân sách thực tế} = \$1,402.85 \text{ (Storage)} + \$3.89 \text{ (API)} + \$448.08 \text{ (Compute)} = \mathbf{\$1,854.82 \text{ / tháng}}$$
$$\text{Ngân sách còn dư (Surplus Margin)} = \$5,000.00 - \$1,854.82 = \mathbf{\$3,145.18 \text{ (Dư 62.9\%)}}$$

Thiết kế hoàn toàn thỏa mãn ràng buộc tài chính với biên độ dự phòng an toàn rất cao.

---

## 6. Kế hoạch triển khai MVP 1 tuần (One-Week Shippable Slice)

Để chứng minh tính khả thi của kiến trúc trước hội đồng đánh giá kỹ thuật mà không cần xây dựng toàn bộ hệ thống đồ sộ, một **lát cắt MVP tối thiểu (Vertical Slice)** được lập trình và nghiệm thu trong 5 ngày làm việc:

- **Mục tiêu lát cắt (Scope):** Một luồng xử lý hoàn chỉnh từ giả lập traffic tenant, tokenization PII thời gian thực, lưu trữ Delta có Z-Order, cho đến truy vấn tổng hợp dashboard 5 phút bằng DuckDB.
- **Tiêu chuẩn nghiệm thu (Acceptance Criteria):**
  1. Tốc độ ingest đạt tối thiểu 20,000 events/giây trên một máy trạm chuẩn mà không rơi rụng sự kiện.
  2. Dữ liệu tại Silver hoàn toàn che giấu thông tin PII nhạy cảm (100% email/phone được hash).
  3. Truy vấn dashboard theo `tenant_id` trên bảng đã tối ưu Z-Order cho tỷ lệ file pruning ≥ 15× so với bảng chưa tối ưu.
  4. Script dọn dẹp kiểm chứng khả năng thu hồi file mồ côi và thực thi chính sách hết hạn 7 ngày.

---

## 7. Mã nguồn kiểm chứng khả thi (Proof of Concept — PoC)

Mã nguồn thực nghiệm độc lập được lưu trữ tại [`submission/bonus/poc/test_tokenization_finops.py`](poc/test_tokenization_finops.py). Đoạn mã kiểm chứng 3 cơ chế phức tạp nhất:
1. Hàm băm Salted HMAC-SHA256 Tokenization cho throughput cao.
2. Ingest streaming micro-batch vào Delta Lake và gom cụm đa chiều Z-Order theo `tenant_id`.
3. Kiểm tra cơ chế File-pruning và xác thực công thức tính toán chi phí FinOps.
