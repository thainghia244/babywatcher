# Danh sách hình ảnh cho báo cáo đồ án (BaoCaoDoAnTotNghiep_Full.md)

Thư mục này chứa các hình đã được xuất ra file ảnh (.png) sẵn sàng để chèn vào Word.
Các biểu đồ mermaid trong file .md gốc **không tự hiển thị được trong Word** — đã được
render sẵn ra .png ở đây để dùng thay thế.

| File ảnh | Chèn vào mục | Chú thích (caption) dùng trong Word |
|---|---|---|
| `Hinh_3.2_so_do_luong_xu_ly.png` | Mục 3.3 (ngay sau câu "Hình 3.2 dưới đây minh họa quy trình này bằng một biểu đồ luồng.") | Hình 3.2. Sơ đồ luồng xử lý của hệ thống |
| `Hinh_5.1_phan_bo_su_kien_nguy_hiem.png` | Mục 5.3, sau câu "Hình 5.1 dưới đây minh họa phân bố thực tế của các sự kiện nguy hiểm ghi nhận." | Hình 5.1. Phân bố sự kiện nguy hiểm (HAND_TO_MOUTH 78,9% / OBJECT_TO_MOUTH 21,1%) |
| `Hinh_5.1b_confusion_matrix_dynamic.png` | Mục 5.3.1 (Confusion Matrix), ngay sau Bảng 5.1b | Hình 5.1b. Confusion Matrix — chế độ Dynamic threshold (121 ảnh, accuracy 72,7%) |
| `Hinh_5.1b_phu_luc_confusion_matrix_fixed_80.png` | Phụ lục / mục 5.3.1 (tùy chọn, để so sánh với dynamic) | Phụ lục. Confusion Matrix — Fixed threshold 80px |
| `Hinh_5.1b_phu_luc_confusion_matrix_fixed_110.png` | Phụ lục / mục 5.3.1 (tùy chọn) | Phụ lục. Confusion Matrix — Fixed threshold 110px |
| `Hinh_5.1b_phu_luc_confusion_matrix_fixed_140.png` | Phụ lục / mục 5.3.1 (tùy chọn) | Phụ lục. Confusion Matrix — Fixed threshold 140px |
| `Hinh_5.3b_confusion_matrix_object_detector_100epoch.png` | Mục 5.2.3.4, sau Bảng 5.3c | Hình 5.3b. Confusion Matrix (số lượng tuyệt đối) — object detector, tập test (mô hình 100 epoch) |
| `Hinh_5.3c_confusion_matrix_normalized_100epoch.png` | Mục 5.2.3.4 | Hình 5.3c. Confusion Matrix (chuẩn hóa) — object detector, tập test |
| `Hinh_5.3d_PR_curve_100epoch.png` | Mục 5.2.3.4 | Hình 5.3d. Precision-Recall Curve — object detector, tập test |
| `Hinh_5.3e_F1_curve_100epoch.png` | Mục 5.2.3.4 | Hình 5.3e. F1-Confidence Curve — object detector, tập test |
| `Hinh_5.3f_Precision_curve_100epoch.png` | Mục 5.2.3.4 | Hình 5.3f. Precision-Confidence Curve — object detector, tập test |
| `Hinh_5.3g_Recall_curve_100epoch.png` | Mục 5.2.3.4 | Hình 5.3g. Recall-Confidence Curve — object detector, tập test |

> ⚠️ **Lưu ý đánh số:** file .md gốc đã lỡ dùng "Hình 5.3"/"Hình 5.4" cho 2 ảnh minh họa ở mục 5.5 (xem
> phần "Thiếu" bên dưới) — trùng tiền tố với "Hình 5.3b–5.3g" mới thêm ở mục 5.2.3.4. Khi đánh số lại
> trong Word, bạn nên đổi thành số thứ tự liên tục thật (ví dụ 5.4, 5.5, 5.6... cho các hình mới, rồi
> dịch số của Hình 5.3/5.4 cũ ở mục 5.5 xuống) thay vì giữ nguyên "5.3b" như trong bản nháp này.

## ⚠️ Thiếu — cần bạn tự bổ sung

Báo cáo còn tham chiếu 2 ảnh **không tồn tại trong project** (đường dẫn `images/a5.jpg` và
`images/a4.jpg`, dùng cho **Hình 5.3** và **Hình 5.4** ở mục 5.5 — ảnh minh họa kết quả
phát hiện thực tế trên ảnh đầu vào/đầu ra). Bạn cần tự chụp/xuất 2 ảnh này từ hệ thống thật
(ví dụ chạy `main.py <ảnh>` rồi lưu kết quả) và đặt tên:
- `Hinh_5.3_anh_thuc_nghiem_1.jpg` — Hình 5.3. Ảnh thực nghiệm 1 – minh họa kết quả phát hiện trên ảnh đầu vào.
- `Hinh_5.4_anh_thuc_nghiem_2.jpg` — Hình 5.4. Ảnh thực nghiệm 2 – minh họa kết quả phát hiện thực tế trên dữ liệu thử nghiệm.
