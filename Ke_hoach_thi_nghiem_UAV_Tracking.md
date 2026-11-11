# Kế hoạch thí nghiệm: UAV Target Tracking 2D

- **Kho mã:** [ThanhBan04/Robotics_Final_Project](https://github.com/ThanhBan04/Robotics_Final_Project). Mã nguồn tại commit `dafa5f9` giống hệt `cd478a3`; commit mới chỉ thêm báo cáo Word.
- **Ngày lập:** 11/11/2026
- **Tài liệu đi kèm:** `De_xuat_sua_du_an_UAV_Tracking.md` (23 điểm cần sửa trong mã). Kế hoạch này giả định **đã sửa xong nhóm A** của tài liệu đó (lỗi 1–5), cùng lỗi 11 và 14.
- **Người lập:** Claude (trợ lý AI của Anthropic). Nhóm cần tự kiểm tra lại trước khi sử dụng.

---

## 1. Vì sao 12 kịch bản là chưa đủ

Chạy lại 12 kịch bản × 20 hạt giống × 2 chế độ điều khiển chỉ bảo đảm **kết quả đúng và có ý nghĩa thống kê**. Để đạt "Mức 3 – Tốt" ("đánh giá có hệ thống trong các điều kiện khác nhau và giải thích được kết quả") và điểm cao ở tiêu chí C3 (30%), C4 (25%), còn ba khoảng trống:

| Khoảng trống | Giải thích | Thí nghiệm khắc phục |
| --- | --- | --- |
| Chưa trả lời được "vì sao" | 12 kịch bản là 12 điểm rời rạc. Kịch bản 3 chỉ cho biết nhiễu ×8 thì sai số khoảng 4,6 m, không cho thấy xu hướng hay ngưỡng gãy | TN2, TN3 (quét tham số) |
| Chưa chứng minh bộ lọc có ích | Không có đối chứng "không dùng bộ lọc" | TN1 |
| So sánh EKF – UKF sẽ ra "gần như bằng nhau" | Phép đo dày (50 Hz), mục tiêu ở xa (khoảng 50 m) nên hàm đo gần như tuyến tính. Không có kịch bản nào làm lộ khác biệt | TN5, TN6, TN7 |

---

## 2. Tổng quan các thí nghiệm

| Mã | Thí nghiệm | Ưu tiên | Mã đã hỗ trợ? | Mục báo cáo |
| --- | --- | --- | --- | --- |
| TN0 | 12 kịch bản × 20 hạt giống × 2 chế độ điều khiển | **Bắt buộc** | Có | 4.1 |
| TN1 | Đối chứng không dùng bộ lọc | **Cao** | Chưa (khoảng 20–30 dòng) | 4.2 |
| TN2 | Quét mức nhiễu đo | **Cao** | Có (cần script quét) | 4.2 |
| TN3 | Quét thời gian mất tín hiệu | **Cao** | Có (cần script quét) | 4.2 |
| TN4 | Chỉ số tỉ lệ mất dấu cho mọi kịch bản | **Cao** | Chưa (khoảng 10 dòng) | 4.1, 4.3 |
| TN5 | Kịch bản làm lộ khác biệt EKF – UKF | Trung bình | Có (đổi tham số) | 4.2 |
| TN6 | Kiểm tra tính nhất quán bộ lọc (NEES/NIS) | Trung bình | Có dữ liệu, cần hàm tính | 4.2 |
| TN7 | Thời gian tính toán EKF và UKF | Trung bình | Chưa (khoảng 5 dòng) | 4.2 |
| TN8 | Quét tham số q và Kp, Kd | Thấp | Có (cần script quét) | 3.2, 4.2 |
| TN9 | Lần chạy do người thật điều khiển | Thấp | Có (ghi và phát lại) | 4.2 |

**Mức đề xuất cho đồ án:**

- **Bắt buộc:** TN0.
- **Nên làm:** TN1–TN4. Đây là phần nâng bài từ "Khá" lên "Tốt", vì tạo ra đồ thị xu hướng và giải thích được nguyên nhân.
- **Nếu còn thời gian:** TN5–TN7. Làm phần so sánh thuật toán có chiều sâu, đúng trọng tâm tiêu chí C3.
- **Tùy chọn:** TN8, TN9.

---

## 3. Quy ước chung cho mọi thí nghiệm

- **Hạt giống ngẫu nhiên:** 20 hạt giống (1–20) cho mọi điểm thí nghiệm. Báo cáo **trung bình ± độ lệch chuẩn**. Với các chỉ số bị ảnh hưởng mạnh bởi lần chạy mất dấu, báo cáo thêm **trung vị**.
- **Tách giai đoạn tiếp cận:**
  - TN0 báo cáo cả hai: toàn bộ thời gian và sau giây thứ 10.
  - TN1, TN2, TN3, TN5 cho UAV **xuất phát ở trạng thái đã bám ổn định**: UAV đặt sẵn cách mục tiêu 50 m phía sau, cùng vận tốc. Như vậy chỉ đo đúng ảnh hưởng của yếu tố đang khảo sát.
- **Bộ chỉ số chuẩn**, tính cho mọi lần chạy:

| Chỉ số | Định nghĩa | Đơn vị |
| --- | --- | --- |
| RMSE vị trí, vận tốc | Sai số giữa ước lượng và trạng thái thật | m, m/s |
| RMSE bám | Căn trung bình bình phương của (khoảng cách thật − 50 m) | m |
| Tỉ lệ bám thành công | Tỉ lệ thời gian khoảng cách nằm trong 50 ± 5 m | % |
| Thời gian ổn định (đã sửa) | Thời điểm từ đó trở đi không rời vùng 50 ± 5 m | s |
| Khoảng cách nhỏ nhất | Chỉ số an toàn va chạm | m |
| Tỉ lệ có phép đo | Tỉ lệ bước camera trả về phép đo | % |
| Mất dấu (TN4) | Có hay không, và thời điểm bắt đầu | có/không, s |

- **Lưu kết quả:** mỗi thí nghiệm một thư mục riêng `results/experiments/TNx/`, gồm `summary.csv`, cấu hình đã dùng và hình vẽ. Ghi lại mã commit khi chạy.

---

## 4. Chi tiết từng thí nghiệm

### TN0. Thí nghiệm chính (bắt buộc)

- **Câu hỏi:** Sau khi sửa lỗi, hệ thống hoạt động thế nào trên 12 kịch bản? EKF hay UKF điều khiển tốt hơn?
- **Thiết kế:** 12 kịch bản × 20 hạt giống × 2 chế độ điều khiển (PID dùng EKF; PID dùng UKF) = **480 lần chạy**.
- **Lệnh chạy** (các tham số này `batch_runner.py` đã hỗ trợ):

  ```bash
  python batch_runner.py --mode headless --scenarios 1,2,3,4,5,6,7,8,9,10,11,12 --filters ekf,ukf --seeds 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20
  ```

- **Đầu ra:**
  - Bảng 12 kịch bản × chỉ số chuẩn, cho hai chế độ điều khiển.
  - Biểu đồ cột RMSE kèm thanh lỗi.
  - Biểu đồ hộp (boxplot) RMSE bám theo kịch bản.
- **Lưu ý:** sau khi sửa lệnh rẽ và đổi tốc độ, kịch bản 2, 6, 7, 11, 12 có thể cho kết quả **xấu hơn** bản gốc. Đây là kết quả trung thực, cần trình bày như vậy.

### TN1. Đối chứng không dùng bộ lọc

- **Câu hỏi:** Bộ lọc Kalman cải thiện chất lượng bám bao nhiêu so với dùng thẳng phép đo?
- **Thiết kế:** 3 phương án đầu vào cho PID:
  1. Phép đo thô: đổi (r, θ) sang (x, y); vận tốc lấy bằng sai phân hai vị trí liên tiếp.
  2. Ước lượng EKF.
  3. Ước lượng UKF.

  Chạy trên kịch bản 1, 3 và 4, xuất phát ở trạng thái đã bám ổn định, 20 hạt giống.
- **Thay đổi mã:**
  - Thêm chế độ `filter_mode = 'none'` trong `simulation/simulation_engine.py`.
  - Khi mất phép đo: giữ giá trị cuối cùng, ghi rõ trong báo cáo.
- **Đầu ra:**
  - Bảng so sánh RMSE bám và độ dao động gia tốc lệnh (độ lệch chuẩn của lệnh gia tốc) giữa 3 phương án.
  - Đồ thị khoảng cách theo thời gian của 3 phương án trên cùng một hình.
- **Kỳ vọng cần kiểm chứng:** không lọc thì lệnh gia tốc dao động mạnh do vi phân của nhiễu; khi mất tín hiệu, UAV mất hướng.

### TN2. Quét mức nhiễu đo

- **Câu hỏi:** Sai số ước lượng và sai số bám thay đổi thế nào khi nhiễu camera tăng? Bộ lọc gãy ở ngưỡng nào?
- **Thiết kế:**
  - σr ∈ {1, 2, 5, 10, 15, 20} m.
  - σθ tăng theo cùng tỉ lệ: σθ = 0,015 × σr rad, tương ứng 0,03 rad ở mức chuẩn σr = 2 m.
  - Mục tiêu đi thẳng; UAV xuất phát đã bám ổn định; 20 hạt giống. Tổng **6 × 20 × 2 = 240 lần chạy**.
  - Hai biến thể: R của bộ lọc **khớp** với nhiễu thật, và R **giữ ở mức chuẩn** (bộ lọc không biết nhiễu tăng, giống kịch bản 3 hiện tại).
- **Thay đổi mã:** script `experiments/sweep_noise.py` sinh cấu hình và gọi `SimulationEngine`.
- **Đầu ra:** đồ thị đường RMSE vị trí và RMSE bám theo σr, có dải độ lệch chuẩn, cho EKF, UKF và hai biến thể R.
- **Phân tích cần có:** mối quan hệ giữa nhiễu và sai số có tuyến tính không; R sai lệch làm hại bao nhiêu; tại mức nhiễu nào tỉ lệ bám thành công giảm dưới 50%.

### TN3. Quét thời gian mất tín hiệu

- **Câu hỏi:** Bộ lọc dự đoán được bao lâu trước khi mất dấu? Mục tiêu đang rẽ thì sao?
- **Thiết kế:**
  - Thời gian mất tín hiệu ∈ {1, 2, 3, 5, 8, 10} s, bắt đầu tại giây thứ 10.
  - Hai loại chuyển động của mục tiêu trong lúc mất tín hiệu: **đi thẳng**, và **đang rẽ** (tốc độ góc khoảng 10°/s).
  - UAV xuất phát đã bám ổn định; 20 hạt giống. Tổng **6 × 2 × 20 × 2 = 480 lần chạy**.
- **Thay đổi mã:** script `experiments/sweep_dropout.py`; cần lệnh rẽ đã sửa (lỗi 2).
- **Đầu ra:**
  - Đồ thị sai số cuối giai đoạn mất tín hiệu theo thời gian mất, so sánh đi thẳng và đang rẽ.
  - Đồ thị tỉ lệ bắt lại được mục tiêu sau khi có tín hiệu trở lại.
  - So sánh sai số thật với độ bất định bộ lọc tự báo, √(Pxx + Pyy).
- **Phân tích cần có:** thời gian mất tín hiệu tối đa vẫn bắt lại được mục tiêu; vì sao mô hình vận tốc không đổi thất bại khi mục tiêu rẽ.

### TN4. Chỉ số tỉ lệ mất dấu

- **Câu hỏi:** Hệ thống mất dấu mục tiêu thường xuyên đến mức nào, ở kịch bản nào?
- **Định nghĩa đề xuất:** một lần chạy được coi là **mất dấu** nếu có ít nhất một trong hai điều kiện:
  - sai số ước lượng vị trí vượt 50 m liên tục quá 2 s;
  - không có phép đo nào liên tục quá 3 s, ngoài các khoảng tắt camera do kịch bản quy định.

  Các ngưỡng này là đề xuất; nhóm nên nêu rõ và có thể thử ngưỡng khác để kiểm tra độ nhạy.
- **Thay đổi mã:** thêm hàm trong `evaluation/tracking_evaluation.py`; áp dụng cho dữ liệu TN0, không cần chạy thêm.
- **Đầu ra:** bảng tỉ lệ mất dấu (%) theo kịch bản và chế độ điều khiển; thời điểm mất dấu trung bình.
- **Phân tích cần có:** liên hệ với nguyên nhân camera nhìn theo hướng bay (lỗi 9 trong tài liệu đề xuất sửa).

### TN5. Kịch bản làm lộ khác biệt giữa EKF và UKF

- **Câu hỏi:** Trong điều kiện nào UKF thực sự tốt hơn EKF?
- **Cơ sở:** độ phi tuyến của hàm đo tăng khi độ bất định vị trí lớn so với khoảng cách tới mục tiêu. Có ba cách tạo điều kiện đó:
  - khoảng cách gần;
  - phép đo thưa;
  - khởi tạo bộ lọc kém chính xác.
- **Thiết kế** (quét từng yếu tố, các yếu tố khác giữ mức chuẩn):

  | Yếu tố | Các mức |
  | --- | --- |
  | Khoảng cách bám mong muốn | 10, 20, 50, 100 m |
  | Tần số đo | 2, 5, 10, 50 Hz |
  | Độ lệch chuẩn sai lệch khởi tạo | 10, 30, 60 m |

  Mục tiêu đi thẳng; 20 hạt giống; EKF và UKF nhận cùng chuỗi phép đo.
- **Thay đổi mã:** script `experiments/sweep_nonlinearity.py`. Các tham số `desired_distance` và `measurement_rate` đã có trong cấu hình; sai lệch khởi tạo cần đưa ra thành tham số.
- **Đầu ra:** đồ thị tỉ số RMSE(UKF) / RMSE(EKF) theo từng yếu tố.
- **Phân tích cần có:** nếu ở mọi điều kiện tỉ số vẫn xấp xỉ 1, đó cũng là kết luận có giá trị: với bài toán này, EKF đủ dùng và rẻ hơn. Kết luận phải dựa trên số liệu, không suy ra từ lý thuyết.

### TN6. Kiểm tra tính nhất quán của bộ lọc (NEES/NIS)

- **Câu hỏi:** Độ bất định mà bộ lọc tự báo có khớp với sai số thật không? Bộ lọc có tự tin quá mức không?
- **Định nghĩa:**
  - NEES (sai số ước lượng chuẩn hóa): ε = eᵀ P⁻¹ e, với e là sai số trạng thái 4 chiều.
  - NIS (phần dư đo chuẩn hóa): ν = yᵀ S⁻¹ y, với y là phần dư 2 chiều.
  - Nếu bộ lọc nhất quán, trung bình NEES xấp xỉ 4 và trung bình NIS xấp xỉ 2. Kiểm định bằng khoảng tin cậy phân phối khi bình phương (chi-square) trên nhiều lần chạy, theo Bar-Shalom và cộng sự (2001).
- **Thiết kế:** áp dụng cho kịch bản 1, 3, 4 và cho TN5; trung bình theo 20 hạt giống tại mỗi bước thời gian.
- **Thay đổi mã:**
  - Hiệp phương sai P đã có trong dữ liệu từng bước.
  - Cần lưu thêm phần dư y và ma trận S ở bước cập nhật của `filters/ekf.py`, `filters/ukf.py`.
  - Viết hàm tính trong `evaluation/estimation_evaluation.py`.
- **Đầu ra:** đồ thị NEES trung bình theo thời gian, kèm dải tin cậy 95%, cho EKF và UKF.
- **Phân tích cần có:** NEES vượt dải tin cậy nghĩa là bộ lọc tự tin quá mức, liên hệ với việc chọn q; kiểm tra lại ở kịch bản nhiễu cao khi R không được cập nhật.

### TN7. Thời gian tính toán

- **Câu hỏi:** UKF chậm hơn EKF bao nhiêu? Có đáng đánh đổi không?
- **Thiết kế:** đo thời gian mỗi bước dự đoán và cập nhật bằng `time.perf_counter()`, trung bình trên 1 lần chạy kịch bản 1 (1 500 bước) × 20 hạt giống.
- **Thay đổi mã:** khoảng 5 dòng trong `simulation_engine.py`.
- **Đầu ra:** bảng thời gian trung bình mỗi bước (micro giây), ghi rõ cấu hình máy chạy.
- **Lưu ý:** con số phụ thuộc máy và việc cài đặt bằng Python; chỉ nên so sánh **tương đối** giữa hai bộ lọc.

### TN8. Quét tham số q và Kp, Kd (tùy chọn)

- **Câu hỏi:** Các thông số đang dùng (q = 5; Kp = 2, Ki = 0,1, Kd = 1,5) có hợp lý không?
- **Thiết kế:**
  - q ∈ {0,5; 1; 2; 5; 10; 20} trên kịch bản 1 và 6.
  - Lưới Kp ∈ {1; 2; 3} × Kd ∈ {1,5; 2,8; 4} trên kịch bản 1, đo vọt lố và khoảng cách nhỏ nhất.
- **Đầu ra:**
  - Đồ thị RMSE theo q.
  - Bản đồ nhiệt (heatmap) RMSE bám và khoảng cách nhỏ nhất theo Kp, Kd.
- **Giá trị cho báo cáo:** làm cơ sở cho mục 3.2 "Lý do chọn phương pháp và thông số", và cho việc khắc phục vọt lố (lỗi 10).

### TN9. Lần chạy do người thật điều khiển (tùy chọn)

- **Câu hỏi:** Hệ thống bám thế nào khi mục tiêu do người điều khiển, khó đoán trước?
- **Thiết kế:**
  - Mỗi thành viên điều khiển mục tiêu ở kịch bản 8–11 trong giao diện, bật ghi (REC).
  - Phát lại tệp `recording.json` ở chế độ không giao diện với 20 hạt giống.
- **Đầu ra:** bảng chỉ số giống TN0; nộp kèm tệp ghi để tái lập.
- **Lưu ý:** cần kiểm tra chức năng phát lại có cho kết quả lặp lại được không trước khi dùng.

---

## 5. Thứ tự thực hiện và ước lượng khối lượng

| Bước | Nội dung | Phụ thuộc |
| --- | --- | --- |
| 1 | Sửa nhóm A và lỗi 11, 14 (theo tài liệu đề xuất sửa) | — |
| 2 | Thêm chế độ không lọc (TN1), chỉ số mất dấu (TN4), đo thời gian (TN7), lưu phần dư y và S (TN6) | Bước 1 |
| 3 | Thêm tùy chọn "xuất phát đã bám ổn định" và tham số sai lệch khởi tạo | Bước 1 |
| 4 | Chạy TN0 và tính TN4 trên dữ liệu TN0 | Bước 1, 2 |
| 5 | Viết các script quét, chạy TN1, TN2, TN3 | Bước 2, 3 |
| 6 | Chạy TN5, TN6, TN7 nếu còn thời gian | Bước 2, 3 |
| 7 | Vẽ hình, lập bảng, viết phân tích vào báo cáo | Bước 4–6 |

**Số lần chạy ước tính:**

| Thí nghiệm | Số lần chạy |
| --- | --- |
| TN0 | 480 |
| TN1 | khoảng 180 |
| TN2 | 240 (gấp đôi nếu chạy cả hai biến thể R) |
| TN3 | 480 |
| TN5 | khoảng 440 |
| **Tổng TN0–TN5** | **khoảng 1 800–2 100** |

Mỗi lần chạy mô phỏng 25–35 s với 1 250–1 750 bước. Tổng thời gian tính phụ thuộc máy, khoảng từ vài chục phút tới vài giờ; nên chạy song song nhiều tiến trình nếu cần. Con số này **chưa được đo thực tế**, cần chạy thử một thí nghiệm nhỏ để ước lượng lại.

---

## 6. Gắn thí nghiệm với báo cáo và rubric

| Thí nghiệm | Vị trí trong báo cáo | Tiêu chí rubric được củng cố |
| --- | --- | --- |
| TN0, TN4 | 4.1 Kết quả đạt được; 4.3 Hạn chế | C4: kết quả có minh chứng, đánh giá giới hạn |
| TN1 | 4.2 Phân tích và đánh giá | C4: so sánh theo tiêu chí rõ ràng; C3: lý giải lựa chọn phương pháp |
| TN2, TN3 | 4.2 Phân tích và đánh giá | C4: phân tích ý nghĩa kỹ thuật; "Mức 3": đánh giá trong các điều kiện khác nhau |
| TN5, TN6, TN7 | 2.3 So sánh phương pháp; 4.2 | C2: đối chiếu lý thuyết với thực nghiệm; C3: phân tích chuyên sâu thuật toán |
| TN8 | 3.2 Lý do chọn phương pháp và thông số | C3: thông số và lập luận đủ rõ để kiểm tra |
| TN9 | 4.2 | C1: gắn với ứng dụng thực tế (mục tiêu do người điều khiển) |

**Nguyên tắc:** hướng dẫn của học phần chỉ yêu cầu tối thiểu 2 kịch bản, và rubric ghi rõ "không đồng nhất độ dài báo cáo hoặc số lượng hình ảnh với chất lượng". Mỗi thí nghiệm chỉ có giá trị khi trả lời một câu hỏi cụ thể và được phân tích trong báo cáo. Nên chọn ít thí nghiệm nhưng phân tích kỹ, hơn là chạy nhiều mà không giải thích.

---

## 7. Mức độ chắc chắn

| Nội dung | Mức độ |
| --- | --- |
| Các tham số `--scenarios`, `--filters`, `--seeds`, `--mode` của `batch_runner.py` | Đã kiểm tra trong mã |
| Chế độ `filter_mode = 'ukf'` cho PID dùng UKF | Đã kiểm tra trong mã |
| Hiệp phương sai P được lưu trong dữ liệu từng bước | Đã kiểm tra trong mã |
| Tham số `desired_distance`, `measurement_rate`, `dropout_duration` có trong cấu hình | Đã kiểm tra trong mã |
| Ước lượng số dòng mã cần thêm | Ước lượng, chưa viết thử |
| Thời gian chạy | **Chưa đo** |
| "Kỳ vọng" ở TN1 và cơ sở của TN5 | Dựa trên lý thuyết; **phải được kiểm chứng bằng số liệu**, không được viết vào báo cáo như kết quả trước khi chạy |
| Ngưỡng định nghĩa mất dấu ở TN4 | Đề xuất, nhóm tự quyết định và nêu rõ |
