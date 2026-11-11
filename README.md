# Hệ thống mô phỏng UAV tự động bám đuổi mục tiêu chuyển động trong môi trường 2D

## Mô tả

Hệ thống mô phỏng UAV (Unmanned Aerial Vehicle) có khả năng tự động bám đuổi một mục tiêu chuyển động trong môi trường 2D. Hệ thống sử dụng:

- **Camera giả lập** để thu thập thông tin về mục tiêu (có nhiễu, mất tín hiệu, độ trễ)
- **Extended Kalman Filter (EKF)** và **Unscented Kalman Filter (UKF)** để ước lượng trạng thái mục tiêu
- **PID Controller** để điều khiển UAV duy trì khoảng cách bám đuổi mong muốn
- **Giao diện Pygame** để trực quan hóa mô phỏng theo thời gian thực

### Giả định mô hình

- **Mô hình đo**: Range/Bearing (phi tuyến). Camera giả lập được giả định có khả năng đo khoảng cách (range) thông qua kích thước mục tiêu đã biết và mô hình phối cảnh. Đây là cảm biến mô phỏng, không phải camera đơn thực tế.
- **Mô hình chuyển động**: Constant Velocity (CV) với nhiễu quá trình
- **Môi trường**: Mặt phẳng 2D, không mô phỏng khí động học 3D

---

## Cài đặt

### Yêu cầu
- **Python 3.10+** (đã test trên Python 3.12)
- **Windows** (có file `.bat` hỗ trợ)

### Cài đặt lần đầu

**Cách 1: Dùng file batch (khuyến nghị)**
```
Nhấp đúp setup.bat
```

**Cách 2: Dùng terminal**
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Thư viện sử dụng
| Thư viện | Vai trò |
|---|---|
| NumPy | Vector, ma trận, phép tính số |
| SciPy | Phép tính khoa học |
| Pygame | Giao diện mô phỏng 2D |
| Matplotlib | Biểu đồ khoa học |
| Pandas | Phân tích dữ liệu |
| OpenCV | Camera view (tùy chọn) |
| PyYAML | Đọc file cấu hình |

---

## Cách chạy

### 1. Mô phỏng trực quan (GUI Mode)

```
Nhấp đúp run.bat
```
hoặc
```bash
python main.py --mode gui
```

**Thao tác trong giao diện:**
1. Chọn **Scenario** (kịch bản) từ Control Panel bên phải
2. Chọn **Filter** (EKF / UKF / Both)
3. Điều chỉnh các thông số (noise, PID gains, following distance...)
4. Nhấn **START** để bắt đầu mô phỏng
5. **PAUSE** / **RESET** khi cần
6. Nhấn **SAVE RESULTS** để lưu dữ liệu

### 2. Chế độ tương tác (Interactive Mode)

Chọn scenario "Interactive" trong giao diện:
- **Click chuột trái**: Đặt điểm đích cho mục tiêu
- **Kéo chuột**: Cập nhật điểm đích liên tục
- **WASD**: Điều khiển hướng mục tiêu bằng bàn phím
- **Shift**: Tăng tốc mục tiêu
- **Space**: Giảm tốc / dừng mục tiêu
- **C**: Xóa waypoints
- **Esc**: Thoát

> ⚠️ Lệnh chuột/bàn phím **chỉ điều khiển mục tiêu**. UAV vẫn bám đuổi qua camera → EKF/UKF → PID.

### 3. Chạy nhiều thí nghiệm (Batch Mode)

**Có giao diện:**
```
Nhấp đúp run_batch.bat
```
hoặc
```bash
python batch_runner.py --mode gui
```

**Không giao diện (headless):**
```bash
run_batch.bat --headless
```
hoặc
```bash
python batch_runner.py --mode headless --scenarios 1,2,3,4,5,6,7,8,9,10,11,12 --filters both --seeds 42,123,456
```

### 4. Chạy đơn lẻ không GUI
```bash
python main.py --mode headless --scenario 1 --filter both --seed 42
```

### 5. Chạy bộ thí nghiệm khoa học toàn diện (TN0 -> TN7)
Để tái lập đầy đủ toàn bộ số liệu thống kê Monte Carlo, quét tham số, phân tích phi tuyến và đánh giá tính nhất quán:
```bash
python experiments/run_experiments.py --seeds 20
```
Hoặc chạy từng thí nghiệm độc lập:
```bash
python experiments/run_experiments.py --exp tn0 --seeds 20  # Monte Carlo 12 kịch bản
python experiments/run_experiments.py --exp tn1            # Đối chứng không dùng bộ lọc
python experiments/run_experiments.py --exp tn2            # Quét mức nhiễu cảm biến
python experiments/run_experiments.py --exp tn3            # Quét thời gian mất tín hiệu
python experiments/run_experiments.py --exp tn4            # Tách camera dropout và estimation loss
python experiments/run_experiments.py --exp tn5            # Quét phi tuyến EKF vs UKF
python experiments/run_experiments.py --exp tn6            # NEES/NIS và benchmark tốc độ
```
Kết quả và biểu đồ được tự động lưu trong `results/experiments/`.

Lưu ý: scenario 8–12 là chế độ tương tác khi chạy GUI. Khi chạy batch/headless,
các scenario này dùng quỹ đạo điều khiển định sẵn trong `simulation/target_scenario.py`
để bảo đảm tái lập; chúng không nhận thao tác chuột/bàn phím thật.

---

## 7 Kịch bản kiểm thử định trước

| STT | Kịch bản | Mô tả |
|---|---|---|
| 1 | Baseline | Chuyển động thẳng, nhiễu thấp, không dropout |
| 2 | Sudden Maneuver | Mục tiêu đổi hướng 90° đột ngột |
| 3 | High Noise | Nhiễu camera tăng dần theo thời gian |
| 4 | Lost Detection | Camera mất tín hiệu 5 giây |
| 5 | Normal Tracking | UAV xuất phát lệch, bám mục tiêu hình sin |
| 6 | Turning Tracking | Mục tiêu đổi hướng trong khi bị bám |
| 7 | Combined Stress | Kết hợp đổi hướng + nhiễu + mất tín hiệu + delay |

## 5 Bài thử tương tác

| STT | Bài thử | Thao tác |
|---|---|---|
| 8 | Click Command | Click chuột đặt điểm đích |
| 9 | Waypoint | Click nhiều điểm tạo chuỗi waypoint |
| 10 | Mouse Drag | Kéo chuột liên tục |
| 11 | Keyboard Control | WASD + Shift + Space |
| 12 | Evasive | Đổi hướng/tăng tốc đột ngột |

---

## Cấu trúc dự án

```
UAV_Target_Tracking/
├── main.py                  # Entry point
├── batch_runner.py          # Batch experiment runner
├── config.yaml              # Cấu hình mặc định
├── requirements.txt         # Thư viện Python
├── setup.bat                # Cài đặt lần đầu
├── run.bat                  # Mở GUI Pygame
├── run_batch.bat            # Mở Batch Runner
├── run_headless.bat         # Chạy không giao diện
│
├── models/
│   ├── target_model.py      # Mô hình chuyển động mục tiêu
│   ├── uav_model.py         # Mô hình động học UAV
│   └── camera_model.py      # Camera giả lập + noise/dropout/delay
│
├── filters/
│   ├── ekf.py               # Extended Kalman Filter
│   └── ukf.py               # Unscented Kalman Filter
│
├── control/
│   └── pid_controller.py    # PID controller + desired following point
│
├── simulation/
│   ├── simulation_engine.py # Vòng lặp mô phỏng chính
│   ├── target_scenario.py   # 12 kịch bản (7 kiểm thử định trước + 5 bài thử tương tác)
│   └── interactive_target.py # Điều khiển tương tác + record/replay
│
├── interface/
│   ├── dashboard.py         # Pygame dashboard chính
│   ├── draw_objects.py      # Vẽ UAV, target, FOV, trails...
│   ├── control_panel.py     # Nút, slider, dropdown
│   └── telemetry.py         # Panel hiển thị dữ liệu
│
├── evaluation/
│   ├── estimation_evaluation.py  # So sánh EKF/UKF
│   └── tracking_evaluation.py    # Đánh giá bám đuổi
│
├── results/                 # Kết quả mô phỏng
│   ├── data/                # CSV và metrics
│   ├── figures/             # Biểu đồ
│   └── reports/             # Báo cáo
│
└── tests/                   # Unit tests
    ├── test_target_model.py
    ├── test_uav_model.py
    ├── test_camera_model.py
    ├── test_ekf.py
    ├── test_ukf.py
    └── test_pid.py
```

---

## Cấu hình

File `config.yaml` chứa tất cả thông số mặc định. Có thể chỉnh sửa:

- `simulation.dt` — Bước thời gian (mặc định 0.02s)
- `camera.measurement_model` — `"range_bearing"` hoặc `"xy"`
- `camera.noise_range_std` — Nhiễu khoảng cách
- `camera.fov_angle` — Góc FOV camera (độ)
- `filter.selected` — `"ekf"`, `"ukf"`, hoặc `"both"`
- `pid.kp`, `pid.ki`, `pid.kd` — Tham số PID
- `pid.desired_distance` — Khoảng cách bám mong muốn (m)

---

## Chỉ số đánh giá

| Chỉ số | Mô tả |
|---|---|
| Position RMSE | Sai số vị trí ước lượng (EKF/UKF so với Ground Truth) |
| Velocity RMSE | Sai số vận tốc ước lượng |
| Tracking RMSE | Sai số khoảng cách bám so với mong muốn |
| Settling Time | Thời gian hội tụ đến khoảng cách bám |
| Max Separation | Khoảng cách lớn nhất giữa UAV và target |
| Tracking Success Rate | Tỷ lệ thời gian trong vùng bám cho phép |
| Recovery Time | Thời gian phục hồi sau mất tín hiệu |

---

## Kết quả đầu ra

Mỗi lượt chạy lưu vào `results/data/`:
- `data.csv` — Dữ liệu từng bước (Ground Truth, measurement, estimate, PID, tracking)
- `config.json` — Cấu hình thí nghiệm
- `metrics.json` — Các chỉ số đánh giá
- `recording.json` — Lệnh tương tác (nếu dùng Interactive Mode)

---

## Xử lý lỗi thường gặp

| Lỗi | Giải pháp |
|---|---|
| `ModuleNotFoundError: No module named 'pygame'` | Chạy `setup.bat` hoặc `pip install pygame` |
| `ModuleNotFoundError: No module named 'yaml'` | `pip install pyyaml` |
| Cửa sổ đen không hiển thị | Kiểm tra driver đồ họa, thử resize cửa sổ |
| Script .bat không chạy | Click phải → Run as Administrator |

---

## Ghi chú kỹ thuật

1. **EKF và UKF tự triển khai** bằng NumPy, không chỉ gọi thư viện FilterPy
2. **PID sử dụng Estimated State** từ EKF/UKF, **KHÔNG dùng Ground Truth**
3. Khi camera mất detection → Filter chỉ Prediction, **không thay measurement bằng 0**
4. Khi so sánh EKF/UKF → Cùng measurement sequence, cùng seed, cùng khởi tạo
5. Mục tiêu di chuyển theo giới hạn vận tốc/gia tốc, **không teleport**
6. Random seed được lưu để **tái lập kết quả**
7. Các kịch bản 8–11 khi chạy hàng loạt (headless / batch) sử dụng quỹ đạo định sẵn (deterministic) để đảm bảo khả năng tái lập khoa học
8. Phương pháp tích phân số học Euler bán ẩn (Semi-implicit Euler) được áp dụng thống nhất cho cả mô hình động học UAV và mục tiêu

---

## Tác giả & Giấy phép

- **Tác giả:** Nguyễn Thanh Bản (ThanhBan04) — Sinh viên học phần Kỹ thuật Robot
- **Giấy phép:** [MIT License](LICENSE)

---

## Tài liệu tham khảo

1. R. E. Kalman, "A New Approach to Linear Filtering and Prediction Problems," *Journal of Basic Engineering*, vol. 82, no. 1, pp. 35-45, 1960.
2. S. J. Julier and J. K. Uhlmann, "Unscented Filtering and Nonlinear Estimation," *Proceedings of the IEEE*, vol. 92, no. 3, pp. 401-422, Mar. 2004.
3. Y. Bar-Shalom, X. R. Li, and T. Kirubarajan, *Estimation with Applications to Tracking and Navigation: Theory Algorithms and Software*. John Wiley & Sons, 2004.
4. P. Corke, *Robotics, Vision and Control: Fundamental Algorithms In MATLAB*, 2nd ed. Springer, 2017.
5. K. J. Astrom and T. Hagglund, *Advanced PID Control*. ISA, 2006.
6. A. Sakai et al., "PythonRobotics: a Python code collection of robotics algorithms," *arXiv:1808.10703*, 2018.
