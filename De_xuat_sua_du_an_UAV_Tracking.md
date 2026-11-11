# Đề xuất sửa đổi dự án: UAV Target Tracking 2D

- **Kho mã được rà soát:** [ThanhBan04/Robotics_Final_Project](https://github.com/ThanhBan04/Robotics_Final_Project), nhánh `main`, commit `cd478a3`
- **Ngày rà soát:** 11/11/2026
- **Đối chiếu với:** Hướng dẫn viết báo cáo, Rubric đánh giá, Danh sách 30 chủ đề, Hướng dẫn tìm kiếm demo và mã nguồn (học phần Kỹ thuật Robot)
- **Người thực hiện rà soát:** Claude (trợ lý AI của Anthropic). Nhóm cần tự kiểm tra lại các nhận định trước khi sử dụng.

Tổng cộng **23 điểm cần sửa**, chia 4 nhóm theo mức ưu tiên.

---

## Nhóm A. Lỗi làm sai kết quả (bắt buộc sửa)

| # | Vấn đề | Tệp | Cách sửa | Công sức |
| --- | --- | --- | --- | --- |
| 1 | UKF tạo điểm sigma theo **hàng** thay vì theo **cột** của ma trận Cholesky. UKF vì thế làm việc với phân bố sai, và kết luận "EKF tốt hơn UKF" trong số liệu gốc là do lỗi lập trình | `filters/ukf.py`, hàm `_generate_sigma_points` | Đổi `sqrt_P[i]` thành `sqrt_P[:, i]` (2 dòng). Đã kiểm chứng: sau khi sửa, UKF cho kết quả ngang EKF | Rất nhỏ |
| 2 | Lệnh "rẽ 90°" thực tế chỉ làm mục tiêu đổi hướng 17–24° và mất 25–30% tốc độ. Nguyên nhân: hướng đích được tính lại mỗi bước, lệnh chỉ kéo dài 0,5 s, gia tốc bị giới hạn | `models/target_model.py` | Chốt hướng đích một lần lúc bắt đầu lệnh; rẽ bằng tốc độ góc giới hạn tới khi đạt hướng đích; giữ nguyên độ lớn vận tốc | Nhỏ |
| 3 | Lệnh đổi tốc độ ở kịch bản 11 và 12 bị bỏ qua: kịch bản khai báo `speed` / `target_speed`, mô hình chỉ hiểu `speed_change` / `factor` | `simulation/target_scenario.py`, `models/target_model.py` | Thống nhất tên lệnh và tham số; mã báo lỗi khi gặp loại lệnh lạ | Rất nhỏ |
| 4 | Hình kết quả ghi "vùng thành công ±15%" nhưng mã tính tỉ lệ thành công với ngưỡng ±10% (50 ± 5 m) | `evaluation/plot_results.py` | Sửa dải tô và nhãn thành ±10%, hoặc đưa ngưỡng thành một tham số dùng chung | Rất nhỏ |
| 5 | "Thời gian ổn định" là lần **đầu tiên** chạm vùng 50 ± 5 m. UAV vọt lố ra ngoài ngay sau đó nên con số quá lạc quan | `simulation/simulation_engine.py`, hàm `compute_metrics` | Định nghĩa lại: thời điểm mà từ đó trở đi khoảng cách không rời vùng 50 ± 5 m nữa | Nhỏ |

Bản sửa cho lỗi 1:

```python
# Mã gốc (sai)
sigma_points[i + 1]     = x + sqrt_P[i]
sigma_points[i + 1 + n] = x - sqrt_P[i]

# Đã sửa (đúng): lấy cột của L, với L @ L.T = (n + lambda) * P
sigma_points[i + 1]     = x + sqrt_P[:, i]
sigma_points[i + 1 + n] = x - sqrt_P[:, i]
```

Kết quả kiểm chứng lỗi 1 (RMSE vị trí, trung bình 3 hạt giống 42, 123, 456):

| Kịch bản | EKF (m) | UKF mã gốc (m) | UKF đã sửa (m) |
| --- | --- | --- | --- |
| 1 Cơ bản | 0,91 | 2,83 | 0,91 |
| 4 Mất tín hiệu | 2,13 | 8,88 | 2,15 |
| 5 Bám bình thường | 10,48 | 29,83 | 10,48 |
| 10 Kéo chuột | 40,56 | 96,24 | 40,56 |

---

## Nhóm B. Thiếu sót thiết kế và thực nghiệm (nên sửa, ảnh hưởng điểm C3 và C4)

| # | Vấn đề | Đề xuất | Mức bắt buộc |
| --- | --- | --- | --- |
| 6 | Kết quả trong kho mã chỉ có 1 hạt giống ngẫu nhiên (42). Kịch bản 8, 9 cho kết quả rất khác nhau giữa các hạt giống (sai số EKF từ khoảng 19 m tới khoảng 470 m) | Chạy 20–30 hạt giống, báo cáo trung bình ± độ lệch chuẩn | Nên làm |
| 7 | Ở chế độ chạy cả hai bộ lọc, PID luôn dùng ước lượng của EKF. Chưa có lần chạy nào để **UKF điều khiển UAV**, nên mới so được độ chính xác ước lượng, chưa so được chất lượng bám | Chạy thêm `--filters ekf,ukf` (mã đã hỗ trợ sẵn), so sánh chỉ số bám giữa hai bộ lọc | Nên làm (điểm "Mức 3 – Tốt") |
| 8 | Mọi kịch bản đều trộn giai đoạn tiếp cận ban đầu (UAV cách 150–200 m) với khó khăn cần kiểm tra. RMSE bám 40–55 m chủ yếu do giai đoạn này | Báo cáo riêng chỉ số sau giây thứ 10; hoặc cho UAV xuất phát ở trạng thái đã bám ổn định với các kịch bản 2, 3, 4, 7 | Nên làm |
| 9 | Mất dấu mục tiêu và không tìm lại được. Camera nhìn theo hướng bay; khi mục tiêu ra khỏi nón nhìn 120°, bộ lọc chỉ dự đoán đường thẳng và UAV đuổi theo vị trí ước lượng sai. Ví dụ kịch bản 8, hạt giống 123: từ giây 8,4 không còn phép đo, sai số tăng tới khoảng 760 m | Tối thiểu: nêu là hạn chế. Tốt hơn: cho camera quay về phía mục tiêu ước lượng; khi độ bất định vượt ngưỡng thì giảm tốc và chuyển sang chế độ tìm kiếm; giới hạn thời gian chỉ dự đoán | Tối thiểu phải nêu |
| 10 | UAV vọt lố ở giai đoạn tiếp cận, có lúc chỉ cách mục tiêu 1,7–3 m thay vì 50 m (kịch bản 1, 3, 4, 9). Với UAV thật đây là nguy cơ va chạm | Thêm chỉ số an toàn "khoảng cách nhỏ nhất"; tăng Kd (ví dụ Kd ≈ 2√Kp ≈ 2,8 cho tắt dần tới hạn), giới hạn tốc độ tiếp cận, hoặc thêm thành phần bù vận tốc mục tiêu | Nên làm |
| 11 | Bộ lọc được khởi tạo từ **vị trí và vận tốc thật** của mục tiêu cộng nhiễu (độ lệch chuẩn 10). Nghĩa là bộ lọc biết trước trạng thái thật lúc đầu, trái với nguyên tắc chỉ dùng dữ liệu đo | Khởi tạo từ phép đo đầu tiên (đổi r, θ sang x, y), vận tốc bằng 0 với hiệp phương sai lớn; hoặc nêu rõ đây là giả thiết | Nên làm, hoặc ghi giả thiết |
| 12 | Ma trận nhiễu đo R của bộ lọc giữ nguyên khi kịch bản tăng nhiễu ×3, ×5, ×8 | Ghi rõ giả thiết "bộ lọc không biết nhiễu tăng"; có thể chạy thêm phương án R được cập nhật để so sánh | Ghi giả thiết |
| 13 | Phép đo bị trễ 0,3 s được dùng như phép đo hiện tại, kèm tư thế UAV hiện tại; mỗi bước hàng đợi chỉ trả tối đa một phép đo | Lưu tư thế UAV kèm phép đo, bù trễ trước khi cập nhật; hoặc nêu là hạn chế | Nêu hạn chế |
| 14 | Kịch bản 12: mục tiêu chạy **ra ngoài bản đồ** (x tới 1501 m, bản đồ rộng 1200 m) từ giây 22,7, chiếm 24% thời gian mô phỏng, trong khi UAV bị giới hạn trong bản đồ | Chỉnh quỹ đạo hoặc tốc độ để mục tiêu ở trong bản đồ, hoặc áp giới hạn biên cho cả mục tiêu | Nên sửa |

---

## Nhóm C. Chất lượng mã, khả năng tái lập và minh bạch nguồn

| # | Vấn đề | Đề xuất |
| --- | --- | --- |
| 15 | `batch_runner.py` và `simulation_engine.py` dùng `config.copy()` (sao chép nông) rồi sửa từ điển con như `config['simulation']['random_seed']`, nên thay đổi lan ngược về cấu hình gốc. Hiện chưa làm sai kết quả nhưng dễ gây lỗi khó tìm | Dùng `copy.deepcopy(config)` |
| 16 | Phần `scenario:` trong `config.yaml` (waypoints, `stress_timeline`…) không được mã dùng. Một số giá trị mặc định khác giá trị kịch bản thực dùng (ví dụ nhiễu góc 0,05 trong config, kịch bản dùng 0,03) | Xóa phần không dùng, hoặc ghi chú rõ các kịch bản được định nghĩa trong `simulation/target_scenario.py` |
| 17 | `filterpy` có trong `requirements.txt` nhưng không được dùng | Xóa khỏi danh sách |
| 18 | Giao diện đồ họa ghi đè tốc độ tối đa của mục tiêu (thanh trượt mặc định 30 m/s) và mức nhiễu, nên chạy trên giao diện cho kết quả khác chạy hàng loạt | Khởi tạo thanh trượt theo thông số của kịch bản đang chọn; hoặc ghi rõ trong README |
| 19 | Bộ kiểm thử đạt 65/65 nhưng không phát hiện được lỗi 1, 2, 3 | Thêm kiểm thử: hiệp phương sai tái tạo từ điểm sigma phải bằng P (với P có tương quan); lệnh rẽ phải đạt đúng góc; loại lệnh lạ phải báo lỗi |
| 20 | Kịch bản 8–11 mang tên "tương tác" (chuột, bàn phím) nhưng khi chạy hàng loạt thì dùng quỹ đạo dựng sẵn | Ghi rõ trong README và báo cáo; có thể đổi tên |
| 21 | Không có tệp LICENSE | Thêm giấy phép, ví dụ MIT |
| 22 | README không ghi nguồn tham khảo và chưa khai báo dùng AI, dù kho mã có tệp `UAV_Target_Tracking_Antigravity_Handoff_UPDATED.md` | Thêm mục "Tài liệu tham khảo" và mục "Sử dụng công cụ AI": công cụ nào, hỗ trợ phần nào, nhóm đã kiểm tra lại ra sao |
| 23 | Mô hình mục tiêu dùng Euler hiện (vị trí cập nhật bằng vận tốc cũ), mô hình UAV dùng Euler bán ẩn | Thống nhất một phương pháp tích phân; ảnh hưởng nhỏ |

---

## Nhóm D. Báo cáo (độc lập với việc sửa mã)

- Viết lại theo đúng **5 chương** của hướng dẫn, từ **góc nhìn của nhóm** (không phải góc nhìn người đánh giá bên ngoài):
  1. Giới thiệu
  2. Cơ sở lý thuyết
  3. Nội dung thực hiện
  4. Kết quả và thảo luận
  5. Kết luận và hướng phát triển
- Thêm phần đầu: trang bìa, mục lục, danh mục hình, bảng và từ viết tắt.
- Bổ sung các mục còn thiếu:
  - 1.4 Cấu trúc báo cáo
  - 2.1 Tổng quan các nghiên cứu, giải pháp đã có
  - 2.3 So sánh ưu nhược điểm các phương pháp (EKF, UKF, bộ lọc hạt; PID với các cách điều khiển khác)
  - 3.1 Phát biểu bài toán (đầu vào, đầu ra, giả thiết, ràng buộc, tiêu chí đánh giá)
  - 3.2 Lý do chọn phương pháp
- Gắn mục tiêu ở 1.2 với tiêu chí kiểm chứng định lượng (ví dụ "sai số bám sau giai đoạn tiếp cận < 5 m"), rồi đối chiếu lại ở Chương 5.
- Thêm bảng phân biệt **tham khảo / AI hỗ trợ / tự thực hiện**, kèm mục khai báo việc dùng AI.
- Tài liệu tham khảo theo chuẩn IEEE, có trích dẫn [1], [2] trong thân bài, ghi ngày truy cập và mã commit.
- Đánh số công thức và bảng; mọi hình, bảng đều được nhắc tới trong thân bài.
- Xuất Word đúng quy cách (A4, Times New Roman 13, giãn dòng 1,3–1,5, căn đều, đánh số trang), rồi xuất PDF.
- Cập nhật toàn bộ số liệu và hình sau khi sửa mã.

---

## Thứ tự thực hiện đề xuất

1. **Sửa nhóm A** (lỗi 1–5) cùng các mục nhanh của nhóm C (15, 16, 17, 19).
2. **Sửa lỗi 14 và 11** (mục tiêu ra khỏi bản đồ, khởi tạo bộ lọc), vì ảnh hưởng trực tiếp tới số liệu.
3. **Chạy lại** 12 kịch bản × 20 hạt giống × 2 chế độ điều khiển (EKF, UKF); vẽ lại toàn bộ hình bằng mã của nhóm:

   ```bash
   python batch_runner.py --mode headless --filters ekf,ukf --seeds 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20
   python -m pytest tests -q
   ```

4. **Quyết định mục 9 và 10** (mất dấu, vọt lố): sửa thật, hay nêu là hạn chế kèm hướng phát triển.
5. **Viết lại báo cáo** theo nhóm D.

---

## Mức độ chắc chắn của các nhận định

| Mức | Các mục |
| --- | --- |
| Đã sửa thử và chạy lại để kiểm chứng | 1 |
| Đã kiểm tra trực tiếp trong mã nguồn và dữ liệu chạy lại | 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 21, 22, 23 |
| Đánh giá dựa trên việc đọc mã, chưa viết kiểm thử minh họa | 19 |
| **Chưa chạy thử hiệu quả của cách sửa** | 2, 3, 9, 10, 11, 14 |

Lưu ý: sau khi sửa 2, 3, 11, 14, kết quả có thể **xấu đi** ở một số kịch bản, vì bài toán khi đó đúng như mô tả và khó hơn. Đây là kết quả trung thực và nên được trình bày như vậy trong báo cáo.

Toàn bộ số liệu trong tài liệu này được chạy trên Linux, Python 3.12.3, NumPy 2.5. Kết quả với hạt giống 42 khớp đến từng chữ số với tệp `results/data/batch_20261110_114446/summary.csv` trong kho mã. Trên máy Windows của nhóm, sai khác số thực rất nhỏ có thể làm các kịch bản dễ mất dấu (8, 9) cho kết quả khác; nên chạy lại để đối chiếu.
