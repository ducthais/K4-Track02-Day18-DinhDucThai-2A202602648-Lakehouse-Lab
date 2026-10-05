# K4-Track02-Day18 — Thông tin bài nộp

- **Họ và tên:** Đinh Đức Thái
- **Mã số sinh viên (MSSV):** 2A202602648
- **Mã bài lab:** `K4-Track02-Day18`
- **Tên repository:** `K4-Track02-Day18-DinhDucThai-2A202602648-Lakehouse-Lab`
- **GitHub URL:** https://github.com/ducthais/K4-Track02-Day18-DinhDucThai-2A202602648-Lakehouse-Lab
- **Đường thực thi (Execution Path):** Lightweight path (Python native APIs: `deltalake` 1.x, `pyiceberg` 0.9.x, `duckdb` 1.2.x, `polars` 1.13.x; không dùng JVM / Docker)
- **Phiên bản Python:** Python 3.11.9 (win32, x64)
- **Hệ điều hành:** Windows 11 Home / Pro

---

## Tóm tắt kết quả kiểm tra (Verification Summary)

| Hạng mục kiểm tra | Lệnh thực thi | Kết quả | Chi tiết |
|---|---|---|---|
| **Smoke Test** | `python scripts/verify_lite.py` | **9/9 PASS** | delta-rs, duckdb vector, pyiceberg catalog, polars đều hoạt động offline |
| **Pytest Suite** | `python -m pytest -v` | **24/24 PASS** | 100% green trong 6.49s (`tests/test_lab18.py`) |
| **Headless Notebooks** | `python scripts/run_all.py` | **8/8 PASS** | Toàn bộ 8 notebooks chạy thành công trong 43.5s |
| **Executed Notebooks** | `submission/notebooks/*.ipynb` | **8/8 Hoàn thành** | Đầy đủ cell outputs, không có lỗi chưa xử lý |
| **Screenshots** | `submission/screenshots/*.png` | **8/8 Đầy đủ** | Minh chứng số liệu chi tiết theo từng tiêu chí trong `RUBRIC.md` |
| **Bonus Architecture** | `submission/bonus/ARCHITECTURE.md` | **Hoàn thành** | Đề tài A: LLM Observability quy mô 1B req/ngày, kèm PoC |

---

## Danh mục artifacts nộp bài

```text
submission/
├── INFO.md
├── REFLECTION.md
├── AI_USAGE.md
├── notebooks/
│   ├── 01_delta_basics.ipynb
│   ├── 02_optimize_zorder.ipynb
│   ├── 03_time_travel.ipynb
│   ├── 04_medallion.ipynb
│   ├── 05_iceberg_catalog.ipynb
│   ├── 06_maintenance.ipynb
│   ├── 07_vectors_multimodal.ipynb
│   └── 08_agents_provenance.ipynb
├── screenshots/
│   ├── nb01_delta_log.png
│   ├── nb02_optimize.png
│   ├── nb03_time_travel.png
│   ├── nb04_medallion.png
│   ├── nb05_iceberg_catalog.png
│   ├── nb06_maintenance.png
│   ├── nb07_vectors_multimodal.png
│   └── nb08_agents_provenance.png
└── bonus/
    ├── ARCHITECTURE.md
    └── poc/
        └── test_tokenization_finops.py
```
