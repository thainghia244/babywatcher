# So sánh Fixed Threshold và Dynamic Threshold — BabyWatcher

Tài liệu này tổng hợp thực nghiệm so sánh giữa **fixed threshold** (ngưỡng khoảng cách cố định,
tính bằng pixel) và **dynamic threshold** (ngưỡng tính theo `shoulder_width × hệ số`, tự co giãn
theo kích thước cơ thể trẻ trong khung hình) của hệ thống BabyWatcher. Toàn bộ dữ liệu và script
nằm trong `analysis/threshold_comparison/`. Xem báo cáo trực quan đầy đủ tại
`analysis/threshold_comparison/threshold_comparison_report.html`.

> **Lưu ý phân biệt dữ liệu:** thực nghiệm trong tài liệu này dùng bộ ảnh riêng ở `image/` (121
> ảnh) để kiểm tra **logic quyết định threshold** của `process_frame()` — bộ ảnh này **không liên
> quan và không trùng** với dataset `babyMonitor2.v1i.yolov8` (0 ảnh trùng tên giữa hai bên).
> `babyMonitor2.v1i.yolov8` là dataset dùng để **huấn luyện model object detector** (YOLOv8s nhận
> diện baby/blanket/other/toy) — một công đoạn khác, độc lập với so sánh fixed vs dynamic
> threshold ở đây. Các chỉ số huấn luyện model (Precision, Recall, F1, mAP) không thuộc phạm vi
> tài liệu này.

## 1. Bối cảnh và phương pháp

- **Dữ liệu:** toàn bộ 121 ảnh trong `image/` — độc lập với dataset huấn luyện model.
- **Thuật toán:** `src/detector.py` — `BabyWatcher.process_frame()`, chạy ở chế độ single-image
  (`_single_image_mode=True`, `_force_immediate_confirmation=False`) để mỗi ảnh được đánh giá độc
  lập theo đúng logic threshold, không phụ thuộc trạng thái tích lũy giữa các khung hình.
- **Không dùng ground-truth thủ công** — vì việc gán nhãn tay cho 121 ảnh tốn nhiều công sức và
  nằm ngoài phạm vi đã thống nhất, toàn bộ phân tích dựa trên **độ đồng thuận (agreement)** và
  **độ ổn định (stability)** giữa hai cách tiếp cận, không cần biết trạng thái "đúng" tuyệt đối.

### 2 bug đã phát hiện và sửa trong `src/detector.py`

1. **Crash khi không phát hiện pose:** biến `shoulder_width` chưa được khởi tạo trước vòng lặp
   pose, khiến ảnh không có người làm crash toàn bộ pipeline (gây `errors=5` trong các lần chạy
   trước đó). Đã sửa bằng cách khởi tạo `shoulder_width = None` từ đầu hàm `process_frame()`.
2. **Dict trả về thiếu dữ liệu chẩn đoán:** `process_frame()` không trả về các khóa
   `shoulder_width` / `h_m_thresh` / `h_o_thresh` / `h_m_dist` / `h_o_dist` mà các script so sánh
   cần đọc — mọi cột chẩn đoán trong các lần chạy trước đều rỗng. Đã bổ sung các khóa này vào
   dict trả về.

Ngoài ra, script `evaluate_thresholds.py` (đã có sẵn trong repo) bị phát hiện có bug ép
`hand_near_mouth=True` vô điều kiện ở chế độ single-image, khiến kết quả dynamic vs fixed "giống
hệt nhau 100%" một cách vô nghĩa — không được dùng làm cơ sở so sánh. `compare_fixed_thresholds.py`
(đúng logic) được dùng thay thế.

## 2. Vì sao một ngưỡng cố định không đủ

Phân bố `shoulder_width` (khoảng cách hai vai, px) trên 116/121 ảnh có phát hiện pose:

| Thống kê | Giá trị |
|---|---|
| Nhỏ nhất | 6.5 px |
| Trung vị | 148.9 px |
| Lớn nhất | 498.7 px |
| Độ lệch chuẩn | 85.6 px |

`shoulder_width` dao động hơn **75 lần** giữa ảnh nhỏ nhất và lớn nhất — hệ quả trực tiếp là
ngưỡng dynamic suy ra cũng dao động tương ứng (4.5–349.1 px). Không có hằng số pixel cố định nào
"vừa" với toàn bộ dải này.

## 3. Kết quả phân loại theo từng mức fixed threshold (121 ảnh)

| Mode | SAFE | HAND_TO_MOUTH | OBJECT_TO_MOUTH | Đồng thuận với dynamic |
|---|---:|---:|---:|---:|
| **Dynamic** | 91 | 1 | 29 | — |
| Fixed 30px | 96 | 0 | 25 | 90.9% |
| Fixed 45px | 94 | 1 | 26 | 89.3% |
| Fixed 60px | 93 | 1 | 27 | 90.1% |
| Fixed 80px | 91 | 2 | 28 | 88.4% |
| Fixed 100px | 85 | 4 | 32 | 85.1% |
| Fixed 120px | 79 | 6 | 36 | 81.0% |
| Fixed 140px | 73 | 7 | 41 | 78.5% |
| Fixed 160px | 65 | 8 | 48 | 71.9% |
| Fixed 180px | 61 | 8 | 52 | 68.6% |

Đồng thuận cao nhất chỉ đạt **90.9%** (fixed_30) và giảm gần như tuyến tính khi threshold tăng,
xuống còn **68.6%** ở fixed_180 — không có điểm hội tụ nào cho thấy một fixed threshold có thể
thay thế dynamic threshold an toàn.

### Sai lệch tập trung ở nhóm bé "thân nhỏ" (ở xa camera)

Chia 116 ảnh thành hai nửa theo trung vị `shoulder_width` (149px). Từ threshold ≥120px, nhóm
"thân nhỏ" luôn đồng thuận thấp hơn nhóm "thân lớn" 6–9 điểm phần trăm — đúng dự đoán thiết kế:
ngưỡng cố định lớn gây sai lệch nhiều hơn khi trẻ có kích thước nhỏ hơn trong khung hình.

## 4. Confusion Matrix: Dynamic (tham chiếu) vs Fixed threshold (dự đoán)

Vì không có ground-truth thủ công, ma trận dưới đây dùng **dynamic threshold làm trục "thực tế"**
và từng mức fixed threshold làm trục "dự đoán" — đo fixed threshold lệch khỏi dynamic ở đâu.

**fixed_45px:**

| Dynamic ↓ / Fixed → | SAFE | HAND | OBJECT |
|---|---:|---:|---:|
| SAFE | 86 | 1 | 4 |
| HAND_TO_MOUTH | 1 | 0 | 0 |
| OBJECT_TO_MOUTH | 7 | 0 | 22 |

**fixed_80px:**

| Dynamic ↓ / Fixed → | SAFE | HAND | OBJECT |
|---|---:|---:|---:|
| SAFE | 84 | 2 | 5 |
| HAND_TO_MOUTH | 1 | 0 | 0 |
| OBJECT_TO_MOUTH | 6 | 0 | 23 |

**fixed_140px:**

| Dynamic ↓ / Fixed → | SAFE | HAND | OBJECT |
|---|---:|---:|---:|
| SAFE | 69 | 7 | 15 |
| HAND_TO_MOUTH | 1 | 0 | 0 |
| OBJECT_TO_MOUTH | 3 | 0 | 26 |

Ở cả ba mức, sai lệch gần như luôn nằm ở ô **SAFE→OBJECT_TO_MOUTH** (báo động giả) và
**OBJECT_TO_MOUTH→SAFE** (bỏ sót nguy hiểm thật). Khi threshold tăng từ 45px lên 140px, báo động
giả tăng gần 4 lần (4→15 ảnh), trong khi bỏ sót giảm (7→3 ảnh) — hai lỗi kéo ngược chiều nhau,
không có mức threshold cố định nào tối thiểu hóa được cả hai cùng lúc.

## 5. Chứng minh hiệu quả: độ ổn định khi khoảng cách camera / độ phóng đại thay đổi

Đây là bằng chứng trực tiếp cho hiệu quả của dynamic threshold, độc lập với dữ liệu ở các mục
trên. **Ý tưởng:** phóng to/thu nhỏ toàn bộ khung ảnh mô phỏng việc camera đổi khoảng cách hoặc
độ phân giải — hành vi thật trong ảnh không đổi, nên một hệ thống đáng tin cậy không được phép đổi
kết quả chỉ vì ảnh bị resize. Kết quả ở tỉ lệ gốc (1.0×) được dùng làm "đáp án" cho chính ảnh đó ở
7 tỉ lệ còn lại (0.4× – 1.75×).

**Thực nghiệm:** 23 ảnh chọn rải đều theo `shoulder_width`, mỗi ảnh dựng lại ở 8 tỉ lệ, chạy qua
dynamic threshold và 3 mức fixed threshold (45/80/140px) — 736 lượt suy luận.

| Mode | Độ ổn định trung bình | Số ảnh hoàn toàn ổn định |
|---|---:|---:|
| **Dynamic** | **91.9%** | **19 / 23** |
| Fixed 45px | 75.8% | 7 / 23 |
| Fixed 80px | 65.8% | 1 / 23 |
| Fixed 140px | 68.9% | 4 / 23 |

**Ví dụ cụ thể** — ảnh `325703891…jpg` (OBJECT_TO_MOUTH ở tỉ lệ gốc):

| Mode | 0.4× | 0.55× | 0.7× | 0.85× | 1.0× | 1.2× | 1.45× | 1.75× |
|---|---|---|---|---|---|---|---|---|
| Dynamic | OBJECT | OBJECT | OBJECT | OBJECT | OBJECT | OBJECT | OBJECT | OBJECT |
| Fixed 45px | OBJECT | OBJECT | OBJECT | OBJECT | SAFE | OBJECT | OBJECT | OBJECT |
| Fixed 80px | SAFE | SAFE | SAFE | SAFE | SAFE | OBJECT | SAFE | OBJECT |
| Fixed 140px | SAFE | OBJECT | OBJECT | OBJECT | SAFE | OBJECT | SAFE | SAFE |

Dynamic threshold giữ nguyên `OBJECT_TO_MOUTH` ở toàn bộ 8 tỉ lệ. `fixed_140px` đảo trạng thái
**4 lần** trên cùng một cảnh không hề thay đổi — bằng chứng trực tiếp rằng mọi lần đổi kết quả ở
đây là lỗi của phương pháp threshold, không phải do dữ liệu, và fixed threshold mắc lỗi này
thường xuyên hơn dynamic threshold 3–4 lần.

> **Lưu ý kỹ thuật:** khi dựng phép thử này, bộ lọc `sustained_danger_duration` trong
> `process_frame()` phụ thuộc vào thời gian thực giữa các lần gọi liên tiếp trên cùng một
> watcher. Nếu không seed lại `watcher._danger_state_since` về một mốc đủ xa trong quá khứ trước
> mỗi lần gọi, kết quả sẽ phụ thuộc vào tốc độ máy/thứ tự xử lý thay vì thuần túy logic threshold.

### Confusion Matrix: Dynamic threshold tự so với chính nó qua các scale

Khác với mục 4 (dynamic vs fixed), ma trận này dùng **chính dynamic threshold ở tỉ lệ ảnh gốc
(1.0×) làm trục "thực tế"**, và dynamic threshold ở 7 tỉ lệ resize còn lại làm trục "dự đoán" —
gộp trên cả 23 ảnh (161 cặp ảnh×scale). Đây là cách duy nhất để có một "confusion matrix" thật sự
đúng nghĩa cho dynamic threshold khi không có nhãn ground-truth: so nó với chính đáp án của nó.

| Dynamic @ 1.0× ↓ / Dynamic @ scale khác → | SAFE | HAND | OBJECT |
|---|---:|---:|---:|
| SAFE | 75 | 0 | 2 |
| HAND_TO_MOUTH | 0 | 0 | 0 |
| OBJECT_TO_MOUTH | 11 | 0 | 73 |

Trùng khớp 148/161 cặp (91.9% — khớp đúng với độ ổn định trung bình ở bảng trên). Toàn bộ 13 cặp
lệch đều nằm ở ô **OBJECT_TO_MOUTH → SAFE** (11 cặp) và **SAFE → OBJECT_TO_MOUTH** (2 cặp), không
có trường hợp nào liên quan đến HAND_TO_MOUTH. Lỗi phổ biến nhất của dynamic threshold khi ảnh bị
resize là **bỏ sót** OBJECT_TO_MOUTH (đổi thành SAFE) nhiều hơn là báo động giả — ngược hướng với
fixed threshold ở mức cao (mục 4), vốn thiên về tạo báo động giả khi threshold lớn.

## 6. Kết luận

1. **Bằng chứng trực tiếp:** dynamic threshold ổn định hơn fixed threshold khi camera đổi khoảng
   cách/độ phóng đại — 91.9% so với 66–76% (mục 5). Đây là phép thử không phụ thuộc việc chọn
   threshold nào "đúng", chỉ đo xem hệ thống có tự mâu thuẫn với chính nó hay không.
2. **Không có fixed threshold tương đương với dynamic.** Đồng thuận cao nhất đo được chỉ 90.9%
   (fixed_30) — ngay cả lựa chọn tốt nhất trong dải khảo sát vẫn khác dynamic trên ~1/10 số ảnh.
3. **Độ nhạy với lựa chọn threshold rất cao đối với fixed.** Từ 30px lên 180px, tỉ lệ ảnh SAFE
   giảm từ 96 xuống 61 (giảm 36%) — hiệu năng fixed threshold phụ thuộc mạnh vào việc "đoán đúng"
   một hằng số, điều không khả thi khi khoảng cách camera/kích thước bé thay đổi.
4. **Dynamic threshold thích nghi theo ngữ cảnh từng ảnh**, vì được suy ra trực tiếp từ
   `shoulder_width` — đại lượng phản ánh đúng tỉ lệ cơ thể/khoảng cách camera trong từng khung
   hình, thay vì ép mọi ảnh dùng chung một hằng số pixel.
5. **Sai lệch của fixed threshold lệch hẳn về phía bé ở xa camera** (thân nhỏ trong khung hình) —
   xác nhận trực tiếp giả thuyết thiết kế ở mục 3.2.4.1 của báo cáo đồ án.

## Nguồn dữ liệu

- `analysis/threshold_comparison/compare_fixed_thresholds.csv`, `.json` — kết quả phân loại 121
  ảnh × 10 mode (dynamic + 9 mức fixed).
- `analysis/threshold_comparison/dynamic_diagnostics.csv` — shoulder_width và threshold động cho
  từng ảnh.
- `analysis/threshold_comparison/confusion_matrices.json` — ma trận nhầm lẫn dynamic vs từng mức
  fixed.
- `analysis/threshold_comparison/scale_invariance_raw.csv`, `scale_invariance_summary.json` — dữ
  liệu thô và tổng hợp phép thử độ ổn định theo scale.
- `analysis/threshold_comparison/threshold_comparison_report.html` — báo cáo trực quan đầy đủ
  (biểu đồ + bảng tương tác).

*Sinh ngày 2026-08-06.*
