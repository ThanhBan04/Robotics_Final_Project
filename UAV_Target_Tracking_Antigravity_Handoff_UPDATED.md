# HỒ SƠ BÀN GIAO DỰ ÁN CHO ANTIGRAVITY

## Đề tài: Nghiên cứu, thiết kế và mô phỏng hệ thống UAV tự động bám đuổi mục tiêu chuyển động trong môi trường 2D

**Mục đích tài liệu:** Gói đầy đủ nội dung kỹ thuật, các lựa chọn công
cụ, kiến trúc, chức năng, yêu cầu mô phỏng, giao diện và định hướng
triển khai đã trao đổi trong cuộc hội thoại. Tài liệu này được dùng làm
đầu vào cho Antigravity để triển khai dự án trực tiếp trên máy tính.

**Yêu cầu quan trọng đối với Antigravity:** Không chỉ tạo giao diện minh
họa. Phải triển khai hệ thống mô phỏng có mô hình toán và thuật toán
thực sự chạy được. Không được tạo số liệu giả để hiển thị như kết quả
thuật toán. Mọi thông số minh họa trong tài liệu phải được xem là giá
trị ví dụ, không phải kết quả đã đo được.

------------------------------------------------------------------------

# PHẦN I. MÔ TẢ ĐỀ TÀI GỐC

Đề tài tập trung nghiên cứu, thiết kế và mô phỏng hệ thống UAV có khả
năng tự động bám đuổi một mục tiêu chuyển động trong môi trường 2D. Hệ
thống sử dụng camera giả lập để thu thập thông tin về mục tiêu, trong đó
các phép đo có thể chịu ảnh hưởng của nhiễu và sự gián đoạn trong quá
trình quan sát.

Để giải quyết vấn đề sai số đo lường và tính phi tuyến của mô hình quan
sát, đề tài ứng dụng các bộ lọc Kalman phi tuyến, cụ thể là Extended
Kalman Filter (EKF) và Unscented Kalman Filter (UKF), nhằm ước lượng
trạng thái của mục tiêu như vị trí và vận tốc, đồng thời dự đoán trạng
thái trong các bước tiếp theo.

Dựa trên trạng thái ước lượng, bộ điều khiển PID được sử dụng để tính
toán tín hiệu điều khiển, giúp UAV điều chỉnh chuyển động và duy trì
khoảng cách bám đuổi mong muốn so với mục tiêu. Chuyển động của UAV được
mô phỏng thông qua mô hình động học có xét đến vận tốc và giới hạn gia
tốc.

Cuối cùng, hệ thống được đánh giá thông qua các kịch bản mô phỏng khác
nhau như mục tiêu thay đổi hướng di chuyển đột ngột, nhiễu camera, mất
tín hiệu quan sát và độ trễ đo lường. Các kết quả được phân tích dựa
trên sai số ước lượng, sai số bám đuổi và khả năng duy trì ổn định của
hệ thống.

------------------------------------------------------------------------

# PHẦN II. MỤC TIÊU VÀ PHẠM VI HỆ THỐNG

## 2.1. Bốn khối chức năng cốt lõi

1.  Mô hình hóa chuyển động của mục tiêu và UAV.
2.  Mô phỏng camera, tạo dữ liệu đo có nhiễu và mất tín hiệu.
3.  Xây dựng và so sánh hai bộ lọc EKF, UKF để ước lượng trạng thái mục
    tiêu.
4.  Thiết kế bộ điều khiển PID để UAV bám đuổi mục tiêu.

## 2.2. Phạm vi

-   Môi trường mô phỏng 2D.
-   UAV và mục tiêu chuyển động trên mặt phẳng X-Y.
-   Mô hình UAV ở mức động học, có xét vận tốc và giới hạn gia tốc.
-   Không yêu cầu mô phỏng khí động học 3D, lực nâng, động cơ, cánh
    quạt, góc nghiêng hoặc chế tạo UAV thật.
-   Camera là camera giả lập. Không bắt buộc huấn luyện AI/YOLO.
-   Tập trung vào mô hình toán, EKF, UKF, PID và đánh giá định lượng.
-   Giao diện trực quan nên được triển khai bằng Pygame.

## 2.3. Nguyên tắc đánh giá

Phải phân biệt rõ: - **Ground Truth:** trạng thái thực tế được mô hình
mô phỏng tạo ra, gồm vị trí/vận tốc thật của mục tiêu và UAV. -
**Measurement:** dữ liệu camera đo được, có thể nhiễu, mất hoặc trễ. -
**Estimated State:** trạng thái mục tiêu được EKF/UKF ước lượng.

Không được đưa Ground Truth trực tiếp vào PID trong các thí nghiệm đánh
giá chính. PID phải sử dụng trạng thái ước lượng từ EKF hoặc UKF. Có thể
có một chế độ Oracle/Ground Truth làm mốc tham chiếu, nhưng phải ghi rõ
đó không phải kết quả vận hành thực tế.

------------------------------------------------------------------------

# PHẦN III. CÔNG CỤ VÀ MÔI TRƯỜNG PHÁT TRIỂN

## 3.1. Nền tảng chính

-   Ngôn ngữ: Python 3.x.
-   IDE: Visual Studio Code.
-   Hệ điều hành: triển khai trên máy tính cá nhân; cần kiểm tra môi
    trường thực tế trước khi cài đặt.
-   Quản lý mã nguồn: Git, có thể dùng GitHub.
-   Môi trường ảo: `venv`.

## 3.2. Thư viện

  -----------------------------------------------------------------------
  Công cụ/thư viện                    Vai trò
  ----------------------------------- -----------------------------------
  Python                              Ngôn ngữ triển khai toàn bộ hệ
                                      thống

  NumPy                               Vector, ma trận, trạng thái,
                                      covariance, phép tính số

  SciPy                               Các phép tính khoa học, tích phân
                                      và xử lý số

  Pygame                              Giao diện mô phỏng 2D, vòng lặp
                                      thời gian thực, vẽ UAV/mục tiêu/quỹ
                                      đạo

  OpenCV (`opencv-python`)            Tùy chọn: tạo/hiển thị ảnh camera
                                      giả lập, phát hiện mục tiêu trong
                                      khung hình

  Matplotlib                          Tùy chọn: biểu đồ khoa học và đồ
                                      thị phân tích ngoại tuyến

  Pandas                              Lưu và phân tích dữ liệu mô phỏng

  FilterPy                            Chỉ dùng tham khảo/đối chiếu triển
                                      khai Kalman; không chỉ gọi thư viện
                                      mà phải tự hiểu và ưu tiên tự triển
                                      khai EKF/UKF bằng NumPy

  `control` (`python-control`)        Tùy chọn hỗ trợ phân tích hệ thống
                                      điều khiển; PID cơ bản có thể tự
                                      viết bằng NumPy
  -----------------------------------------------------------------------

Lệnh cài đặt gợi ý:

``` bash
python -m venv .venv
```

Windows:

``` powershell
.venv\Scripts\activate
```

Linux/macOS:

``` bash
source .venv/bin/activate
```

Cài thư viện:

``` bash
pip install numpy scipy matplotlib pandas
pip install opencv-python pygame
pip install filterpy control
```

Antigravity cần kiểm tra phiên bản Python, hệ điều hành và khả năng cài
thư viện trên máy trước khi thực hiện. Nên tạo `requirements.txt`.

## 3.3. Lựa chọn Pygame và Matplotlib

Pygame được chọn làm giao diện chính vì: - Hiển thị chuyển động UAV và
mục tiêu theo thời gian thực. - Hiển thị quỹ đạo, vector vận tốc, FOV
camera và khoảng cách. - Có thể tạo nút Start, Pause, Reset. - Có thể
bật/tắt nhiễu, mất tín hiệu, độ trễ. - Có thể hiển thị telemetry và biểu
đồ đơn giản ngay trong cửa sổ.

Matplotlib không bắt buộc cho giao diện chính. Có thể giữ lại để xuất
biểu đồ khoa học chất lượng cao phục vụ báo cáo. Nếu muốn chỉ dùng một
thư viện đồ họa, có thể vẽ các đồ thị đơn giản trực tiếp bằng Pygame,
nhưng không nên xem Pygame là công cụ phân tích khoa học thay thế hoàn
toàn Matplotlib.

## 3.4. ROS 2, Gazebo, AirSim

Không cần đưa ROS 2, Gazebo hoặc AirSim vào phiên bản đầu vì mục tiêu
chỉ là mô phỏng thuật toán 2D. Chỉ xem xét các công cụ này nếu phạm vi
sau này mở rộng sang robot/UAV 3D hoặc tích hợp phần cứng.

------------------------------------------------------------------------

# PHẦN IV. KIẾN TRÚC HỆ THỐNG

Luồng xử lý tổng quát:

1.  Target Motion Model tạo trạng thái thật của mục tiêu.
2.  UAV Motion Model cập nhật trạng thái UAV theo lệnh điều khiển.
3.  Camera Model nhận trạng thái mục tiêu và pose UAV, tạo phép đo.
4.  Measurement đi qua các tình huống nhiễu, mất detection và độ trễ.
5.  EKF hoặc UKF nhận phép đo và pose UAV để ước lượng trạng thái mục
    tiêu.
6.  PID nhận Estimated State và trạng thái UAV, tính lệnh điều khiển.
7.  UAV Motion Model nhận lệnh điều khiển, cập nhật trạng thái UAV.
8.  Pygame hiển thị mô phỏng; dữ liệu được ghi lại để đánh giá.
9.  Vòng lặp tiếp tục theo thời gian mô phỏng.

Sơ đồ logic:

``` text
             TARGET MOTION MODEL
                 (Ground Truth)
                        |
                        v
                 SIMULATED CAMERA <------ UAV pose / camera pose
                        |
                        v
       Measurement: noise / dropout / delay / FOV
                        |
              +---------+---------+
              |                   |
              v                   v
             EKF                 UKF
              |                   |
              +---------+---------+
                        |
                 Estimated Target State
                        |
                        v
                  PID CONTROLLER
                        |
                 Acceleration command
                        |
                        v
                   UAV DYNAMICS
                        |
                 Updated UAV state
                        |
                        +------ feedback to camera and next loop

Pygame: visualize all objects and controls.
Logging/Evaluation: save Ground Truth, measurements, estimates, control commands and metrics.
```

Lưu ý: EKF và UKF là hai lựa chọn bộ lọc có thể chuyển đổi trong cùng
một pipeline. Trong mỗi lần chạy nên chọn EKF hoặc UKF; cũng có thể có
chế độ chạy cả hai trên cùng một chuỗi measurement để so sánh song song.
PID cần nhận đầu ra của bộ lọc đang được chọn.

------------------------------------------------------------------------

# PHẦN V. CHI TIẾT TỪNG KHỐI

## KHỐI 1. MÔ HÌNH HÓA CHUYỂN ĐỘNG MỤC TIÊU VÀ UAV

### 5.1. Công cụ

-   Python.
-   NumPy.
-   SciPy (nếu cần tích phân hoặc hỗ trợ tính toán).
-   Matplotlib tùy chọn để kiểm tra quỹ đạo ban đầu.

### 5.2. Target Motion Model

Dùng vector trạng thái 2D:

\[ X_k =
```{=tex}
\begin{bmatrix}
x_k\\y_k\\v_{x,k}\\v_{y,k}
\end{bmatrix}
```
\]

Trong đó: - (x_k,y_k): vị trí mục tiêu. - (v\_{x,k},v\_{y,k}): vận tốc
theo hai trục.

Mô hình Constant Velocity (CV) cơ bản:

\[ X\_{k+1}=FX_k+w_k \]

\[ F=
```{=tex}
\begin{bmatrix}
1&0&\Delta t&0\\
0&1&0&\Delta t\\
0&0&1&0\\
0&0&0&1
\end{bmatrix}
```
\]

Trong đó (w_k) là process noise. Cần định nghĩa rõ mô hình nhiễu quá
trình và covariance (Q), không chỉ thêm nhiễu tùy tiện.

Các kịch bản chuyển động mục tiêu tối thiểu: - Chuyển động thẳng đều. -
Chuyển động đổi hướng theo cung/đường cong. - Đổi hướng đột ngột. -
Tăng/giảm tốc. - Chuyển động theo waypoint hoặc quỹ đạo định nghĩa
trước.

Nên tạo một interface thống nhất, ví dụ `target.step(dt, t)` trả về
Ground Truth state.

### 5.3. UAV Motion Model

Mô hình động học 2D có trạng thái:

\[ X_u =
```{=tex}
\begin{bmatrix}
x_u\\y_u\\v_{x,u}\\v_{y,u}
\end{bmatrix}
```
\]

PID tạo gia tốc điều khiển (a_x,a_y). UAV model cần: - Giới hạn độ lớn
gia tốc. - Giới hạn vận tốc. - Cập nhật vận tốc và vị trí theo bước thời
gian (`\Delta `{=tex}t). - Có thể thêm giới hạn gia tốc thay đổi (jerk)
nếu cần, nhưng không bắt buộc. - Xử lý biên môi trường mô phỏng.

Cập nhật đơn giản:

\[ v\_{x,k+1}=v\_{x,k}+a\_{x,k}`\Delta `{=tex}t \]

\[ v\_{y,k+1}=v\_{y,k}+a\_{y,k}`\Delta `{=tex}t \]

\[ x\_{k+1}=x_k+v\_{x,k}`\Delta `{=tex}t \]

\[ y\_{k+1}=y_k+v\_{y,k}`\Delta `{=tex}t \]

Cần thực hiện saturation sau khi tính gia tốc/vận tốc để bảo đảm giới
hạn.

### 5.4. Đầu ra khối 1

-   `target_model.py`
-   `uav_model.py`
-   Trạng thái Ground Truth theo thời gian.
-   Các quỹ đạo mục tiêu có thể tái lập bằng random seed.

------------------------------------------------------------------------

## KHỐI 2. MÔ PHỎNG CAMERA, NHIỄU VÀ MẤT TÍN HIỆU

### 5.5. Nhiệm vụ camera

Camera đóng vai trò cảm biến thị giác (Visual Sensor), quan sát mục tiêu
và tạo dữ liệu đo cho EKF/UKF. Camera không trực tiếp điều khiển UAV.

Nhiệm vụ: 1. Phát hiện mục tiêu có nằm trong vùng quan sát hay không. 2.
Xác định vị trí/đặc trưng mục tiêu trong ảnh hoặc phép đo tương đối. 3.
Tạo dữ liệu đo có nhiễu. 4. Mô phỏng mất detection. 5. Mô phỏng độ trễ
đo. 6. Tuân thủ tần số lấy mẫu và FOV.

### 5.6. Công cụ

-   NumPy: tạo nhiễu, dropout, delay và dữ liệu đo.
-   OpenCV: tùy chọn nếu muốn hiển thị khung hình camera, hình mục tiêu,
    bounding box và pixel centroid.
-   Nếu chỉ giả lập measurement bằng toán học, OpenCV không bắt buộc.

### 5.7. Hai lựa chọn mô hình đo

**Phương án A -- đo tọa độ X,Y trực tiếp**

\[ z_k=
```{=tex}
\begin{bmatrix}
x_k\\y_k
\end{bmatrix}
```
+v_k \]

Đây là mô hình quan sát tuyến tính nếu tọa độ được cung cấp trực tiếp.
Nó đơn giản, dễ kiểm thử, nhưng không tạo được lý do rõ ràng để cần
EKF/UKF thay cho Kalman Filter tuyến tính. Có thể dùng làm baseline kiểm
thử.

**Phương án B -- Range/Bearing tương đối**

\[ z_k=
```{=tex}
\begin{bmatrix}
r_k\\\theta_k
\end{bmatrix}
```
\]

\[ r_k=`\sqrt{(x_t-x_u)^2+(y_t-y_u)^2}`{=tex} \]

\[
`\theta`{=tex}\_k=`\operatorname{atan2}`{=tex}(y_t-y_u,x_t-x_u)-`\psi`{=tex}\_u
\]

Trong đó: - (x_t,y_t): vị trí mục tiêu. - (x_u,y_u): vị trí UAV. -
(`\psi`{=tex}\_u): hướng/yaw của UAV. - (r): khoảng cách tương đối. -
(`\theta`{=tex}): góc phương vị tương đối.

Mô hình này phi tuyến, phù hợp để nghiên cứu EKF và UKF.

**Cảnh báo mô hình vật lý:** Camera đơn thông thường không đo trực tiếp
khoảng cách. Nếu dùng range-bearing, cần ghi rõ range được suy ra từ
kích thước mục tiêu đã biết, mô hình phối cảnh/hiệu chuẩn, hoặc đây là
camera giả lập kết hợp giả định cảm biến range. Không được tuyên bố
camera đơn tự đo range nếu không có cơ sở. Một lựa chọn khác là chỉ đo
bearing, nhưng cần nghiên cứu khả năng quan sát (observability) và điều
kiện chuyển động để ước lượng được range.

Tọa độ pixel ((u,v)) không đồng nghĩa với tọa độ thế giới ((x,y)).
Chuyển đổi cần mô hình camera, hiệu chuẩn và giả định hình học phù hợp.

### 5.8. Nhiễu và tình huống quan sát

-   Gaussian measurement noise: (z_k=h(X_k)+v_k),
    (v_k`\sim `{=tex}N(0,R)).
-   Detection dropout: không có phép đo ở một số frame/khoảng thời gian.
-   FOV: mục tiêu ngoài vùng quan sát thì không tạo detection.
-   Measurement delay: phép đo trả về được thu nhận ở thời điểm trước.
-   Có thể bổ sung outlier hoặc nhiễu tăng theo khoảng cách nếu cần.

Khi mất measurement, bộ lọc thực hiện Prediction nhưng bỏ qua
Measurement Update. Không được thay phép đo bị mất bằng giá trị 0.

Đối với delay, cần xử lý có nguyên tắc: lưu timestamp của measurement;
không được gắn measurement cũ vào thời điểm hiện tại như thể nó mới.
Phiên bản cơ bản có thể mô phỏng delay cố định và đánh giá ảnh hưởng;
phiên bản nâng cao có thể dùng out-of-sequence measurement handling.

### 5.9. Đầu ra khối 2

-   `camera_model.py`
-   Measurement có timestamp.
-   Trạng thái detection (detected/not detected).
-   Các tham số noise, dropout, delay, FOV cấu hình được.
-   Nếu dùng OpenCV: khung hình camera và bounding box/centroid.

------------------------------------------------------------------------

## KHỐI 3. XÂY DỰNG VÀ SO SÁNH EKF, UKF

### 5.10. Công cụ

-   NumPy: ma trận trạng thái, covariance, phép tính.
-   SciPy: hỗ trợ phép toán số.
-   FilterPy: chỉ dùng tham khảo hoặc đối chiếu.
-   Matplotlib/Pygame: hiển thị kết quả.

Ưu tiên tự triển khai thuật toán bằng NumPy để nhóm hiểu và giải thích
được phương trình.

### 5.11. State vector

Với mô hình CV:

\[ X_k =
```{=tex}
\begin{bmatrix}
x_k\\y_k\\v_{x,k}\\v_{y,k}
\end{bmatrix}
```
\]

Đầu ra ước lượng:

\[ `\hat `{=tex}X_k =
```{=tex}
\begin{bmatrix}
\hat x_k\\\hat y_k\\\hat v_{x,k}\\\hat v_{y,k}
\end{bmatrix}
```
\]

### 5.12. EKF

Cần triển khai đầy đủ: - Khởi tạo state và covariance. - Prediction. -
Tính Jacobian của mô hình chuyển động/quan sát khi cần. -
Innovation/residual. - Innovation covariance. - Kalman gain. -
Measurement update. - Cập nhật covariance theo cách ổn định số, ưu tiên
dạng Joseph nếu phù hợp. - Xử lý góc bằng angle wrapping nếu measurement
có bearing. - Bỏ qua update khi detection bị mất.

Với mô hình phi tuyến:

\[ x\_{k+1}=f(x_k)+w_k \]

\[ z_k=h(x_k)+v_k \]

EKF tuyến tính hóa quanh estimate hiện tại bằng Jacobian.

### 5.13. UKF

Cần triển khai: - Sigma points. - Trọng số mean/covariance. - Prediction
qua mô hình phi tuyến. - Tính predicted measurement. - Innovation
covariance. - Cross covariance. - Kalman gain. - Measurement update. -
Xử lý circular mean/angle residual nếu có bearing. - Bỏ qua update khi
detection bị mất.

UKF sử dụng Unscented Transform thay cho việc tuyến tính hóa bằng
Jacobian.

### 5.14. So sánh công bằng

EKF và UKF phải dùng: - Cùng mô hình động học. - Cùng mô hình quan
sát. - Cùng chuỗi measurement. - Cùng Q, R hoặc cấu hình nhiễu tương
đương. - Cùng trạng thái khởi tạo và covariance khởi tạo. - Cùng random
seed trong một lần so sánh.

Nên hỗ trợ chạy EKF và UKF song song trên cùng dữ liệu để so sánh.

### 5.15. Chỉ số đánh giá

-   RMSE Position.
-   RMSE Velocity.
-   Sai số theo từng trục X, Y.
-   Sai số theo thời gian.
-   Khả năng phục hồi sau dropout.
-   Sai số trong thời gian target đổi hướng.
-   Thời gian tính toán mỗi update (nếu cần).
-   Innovation/NIS hoặc chỉ số consistency nếu nhóm đủ khả năng triển
    khai.

### 5.16. Đầu ra khối 3

-   `ekf.py`
-   `ukf.py`
-   `estimation_evaluation.py`
-   Biểu đồ Ground Truth vs Measurement vs EKF vs UKF.
-   Bảng RMSE và các chỉ số đánh giá.

------------------------------------------------------------------------

## KHỐI 4. PID CONTROLLER VÀ UAV BÁM ĐUỔI

### 5.17. Công cụ

-   NumPy: tính sai số và PID.
-   `python-control`: tùy chọn để phân tích hệ thống, đáp ứng và kiểm
    chứng.
-   Matplotlib/Pygame: hiển thị đáp ứng.

PID cơ bản có thể tự triển khai bằng NumPy; không bắt buộc dùng
`python-control`.

### 5.18. Mục tiêu bám đuổi

UAV không nhất thiết phải trùng vị trí với target. Đề tài yêu cầu duy
trì khoảng cách bám đuổi mong muốn.

Cần xác định rõ chiến lược: - UAV đuổi đến một điểm phía sau mục tiêu ở
khoảng cách mong muốn; hoặc - UAV duy trì khoảng cách tương đối và hướng
tiếp cận đã chọn.

Không nên chỉ đặt setpoint bằng đúng vị trí mục tiêu nếu yêu cầu là duy
trì khoảng cách, vì cách đó có thể khiến UAV va/chạm hoặc bám sát không
đúng mục tiêu thiết kế.

Có thể tạo desired position từ target estimated state và hướng chuyển
động mục tiêu:

\[ p\_{`\text{desired}`{=tex}} = p\_{`\text{target}`{=tex}} -
d\_{`\text{desired}`{=tex}}`\hat{v}`{=tex}\_{`\text{target}`{=tex}} \]

Trong đó hướng vận tốc cần chuẩn hóa trước khi nhân với khoảng cách. Cần
xử lý trường hợp tốc độ mục tiêu gần 0.

### 5.19. PID hai trục

Sai số:

\[ e_x=x\_{`\text{desired}`{=tex}}-x_u \]

\[ e_y=y\_{`\text{desired}`{=tex}}-y_u \]

Gia tốc điều khiển:

\[ a_x=K_pe_x+K_i`\int `{=tex}e_xdt+K_d`\frac{de_x}{dt}`{=tex} \]

\[ a_y=K_pe_y+K_i`\int `{=tex}e_ydt+K_d`\frac{de_y}{dt}`{=tex} \]

Cần có: - Discrete PID theo timestep. - Giới hạn gia tốc (saturation). -
Anti-windup cho thành phần tích phân. - Lọc đạo hàm nếu dữ liệu noisy. -
Reset/initialization đúng cách. - Điều chỉnh Kp, Ki, Kd. - Giới hạn vận
tốc UAV do UAV model thực hiện.

### 5.20. Đánh giá điều khiển

-   Tracking distance error.
-   RMSE tracking error.
-   Thời gian hội tụ/settling time.
-   Overshoot nếu phù hợp.
-   Khả năng duy trì khoảng cách.
-   Khả năng bám khi target đổi hướng.
-   Khả năng phục hồi sau mất camera.
-   Khả năng điều khiển khi measurement delay.

Cần chạy so sánh PID sử dụng EKF và PID sử dụng UKF. Có thể bổ sung
Ground Truth PID làm mốc lý tưởng, nhưng phải phân biệt rõ.

### 5.21. Đầu ra khối 4

-   `pid_controller.py`
-   `tracking_evaluation.py`
-   Biểu đồ khoảng cách và tracking error.
-   Các lệnh gia tốc điều khiển theo thời gian.

------------------------------------------------------------------------

# PHẦN VI. GIAO DIỆN PYGAME

## 6.1. Mục tiêu giao diện

Nếu dùng Pygame thay cho Matplotlib làm giao diện chính, cửa sổ mô phỏng
nên có phong cách dashboard giám sát UAV 2D hoặc game mô phỏng kỹ thuật.
Pygame không phải thuật toán điều khiển; nó chỉ phụ trách hiển thị,
tương tác và điều khiển kịch bản mô phỏng.

## 6.2. Bố cục đề xuất

Chia giao diện thành 3 khu vực:

### Khu vực 1 -- Simulation Environment

Hiển thị: - Mặt phẳng tọa độ X-Y có grid. - UAV bằng biểu tượng drone
màu xanh. - Target bằng hình tròn/biểu tượng màu đỏ. - Ground Truth
trajectory. - Estimated trajectory/estimated position bằng nét đứt hoặc
màu khác. - Measurement points. - Camera FOV (hình quạt hoặc hình
nón). - Velocity vectors. - Đường nối UAV--Target. - Desired following
point và desired distance. - Vùng biên môi trường.

Cần phân biệt rõ các đối tượng bằng màu, kiểu đường và legend. Không
được vẽ Estimated Position trùng với Ground Truth nếu thuật toán không
cho kết quả như vậy.

### Khu vực 2 -- System Monitoring / Telemetry

Hiển thị: - UAV position X, Y. - UAV velocity Vx, Vy và speed. - Target
Ground Truth (có thể chỉ bật trong chế độ debug/evaluation). - Target
estimated position X, Y. - Estimated velocity Vx, Vy. - Range và bearing
measurement. - Tracking distance. - Camera status: Tracking / Lost /
Delayed. - Selected filter: EKF hoặc UKF. - PID status. - Simulation
time và FPS. - RMSE hoặc tracking error trong quá trình chạy nếu tính
được.

### Khu vực 3 -- Control Panel

Các điều khiển: - START. - PAUSE. - RESET. - Chọn EKF/UKF. - Noise
ON/OFF và noise level. - LOST SIGNAL / dropout duration. - DELAY ON/OFF
và delay duration. - TARGET TURN hoặc chọn scenario. - Chọn target
speed. - Desired following distance. - Điều chỉnh Kp, Ki, Kd. - Có thể
thêm nút lưu kết quả/export CSV.

Các điều khiển phải hoạt động thực sự, không phải nút trang trí.

## 6.3. Ví dụ bố cục dữ liệu

Ví dụ các ô telemetry: - UAV X: 125.4 m - Target X: 240.8 m - Distance:
32.5 m - Filter: EKF Active - PID: Active

Đây chỉ là giá trị minh họa cho thiết kế giao diện, không phải kết quả
thực nghiệm.

## 6.4. Vẽ biểu đồ bằng Pygame

Có thể vẽ biểu đồ realtime: - Tracking error vs time. - Estimated
position error vs time. - UAV speed vs time. - Target speed vs time. -
Range vs time.

Matplotlib vẫn có thể được dùng ở chế độ hậu xử lý để xuất biểu đồ báo
cáo. Không cần nhúng Matplotlib vào Pygame nếu làm phức tạp kiến trúc.

------------------------------------------------------------------------

# PHẦN VII. KỊCH BẢN THỬ NGHIỆM VÀ CHẾ ĐỘ ĐIỀU KHIỂN MỤC TIÊU

## 7.1. Phân biệt hai chế độ vận hành

Hệ thống phải có hai chế độ vận hành độc lập:

**A. Predefined Scenario Mode – Mục tiêu chạy theo kịch bản/quỹ đạo định trước**
- Người dùng chọn một kịch bản có sẵn hoặc cấu hình quỹ đạo và tham số ban đầu.
- Chương trình tự sinh chuyển động Ground Truth của mục tiêu theo kịch bản.
- Đây là chế độ chính để chạy thí nghiệm có thể lặp lại, so sánh EKF/UKF và đánh giá PID.
- Các kịch bản 1–7 bên dưới thuộc nhóm này. Chúng là các tình huống kiểm thử thuật toán, không phải chỉ là bảy hình dạng quỹ đạo khác nhau.

**B. Interactive Target Control Mode – Người dùng điều khiển mục tiêu trực tiếp**
- Người dùng điều khiển mục tiêu bằng chuột hoặc bàn phím trong cửa sổ Pygame.
- Lệnh chuột/bàn phím chỉ đi vào Target Motion Model.
- UAV không được nhận trực tiếp tọa độ chuột, phím nhấn hoặc Ground Truth của mục tiêu. UAV chỉ nhận measurement từ camera, sau đó EKF/UKF ước lượng và PID điều khiển UAV.
- Chế độ này dùng để trình diễn và kiểm tra khả năng bám đuổi trong tình huống tương tác khó dự đoán. Các kịch bản 8–12 thuộc nhóm này hoặc là bài thử mở rộng từ nhóm này.

Hai chế độ phải dùng chung Target Motion Model, Camera Model, Filter, PID và UAV Model. Chỉ nguồn tạo lệnh cho mục tiêu là khác nhau.

## 7.2. Nhóm A – 7 kịch bản kiểm thử định trước

Các kịch bản 1–7 chủ yếu dùng mục tiêu tự di chuyển theo kịch bản được chương trình thiết lập. Một số kịch bản tập trung đánh giá bộ lọc, một số đánh giá PID và một kịch bản đánh giá toàn hệ thống.

| STT | Kịch bản | Cấu hình/tình huống | Mục tiêu đánh giá |
|---|---|---|---|
| 1 | Normal / Baseline | Mục tiêu chuyển động đều theo quỹ đạo đơn giản; camera noise thấp; không dropout/delay | Baseline Position RMSE, Velocity RMSE và khả năng bám cơ bản |
| 2 | Sudden Target Maneuver | Mục tiêu đang đi thẳng thì đổi hướng đột ngột, ví dụ 90 độ tại một thời điểm cấu hình được | Sai số cực đại, khả năng thích nghi và thời gian hội tụ lại của EKF/UKF; phản ứng PID |
| 3 | High Measurement Noise | Giữ chuyển động mục tiêu; tăng dần noise camera theo các mức thấp/trung bình/cao | Độ nhạy với nhiễu, Position RMSE, Velocity RMSE |
| 4 | Lost Detection | Camera mất detection trong một khoảng thời gian, sau đó khôi phục | Prediction-only, covariance tăng, sai số trong lúc mất đo và recovery sau khi có đo lại |
| 5 | Normal Tracking | Mục tiêu di chuyển bình thường; UAV xuất phát lệch vị trí và bám giữ khoảng cách mong muốn | Tracking RMSE, settling time, khả năng duy trì khoảng cách |
| 6 | Target Turning Tracking | Mục tiêu đổi hướng đột ngột trong khi UAV đang bám | Maximum tracking error, thời gian UAV trở lại vùng bám, dao động/overshoot |
| 7 | Combined Stress Test | Kết hợp đổi hướng, tăng nhiễu, mất detection và measurement delay theo timeline cấu hình | Đánh giá tổng thể chuỗi camera → EKF/UKF → PID → UAV |

Ví dụ timeline cho kịch bản 7 (cần cho phép cấu hình lại):
- 0–5 s: camera hoạt động bình thường.
- 5–8 s: mục tiêu đổi hướng.
- 8–12 s: camera tăng nhiễu.
- 12–15 s: camera mất detection.
- 15–20 s: camera khôi phục và có measurement delay.

Kịch bản 7 là stress test tổng hợp, không dùng làm căn cứ duy nhất để kết luận EKF hay UKF tốt hơn. Cần phân tích các kịch bản riêng để cô lập nguyên nhân sai số.

## 7.3. Nhóm B – Quỹ đạo định trước có thể cấu hình

Trong Predefined Scenario Mode, ngoài các tình huống 1–7, giao diện nên cho phép chọn hình dạng quỹ đạo:
- Straight Line: đường thẳng.
- Circular: đường tròn.
- Sinusoidal: đường hình sin.
- Zigzag: đường ziczac.
- Waypoint: đi qua danh sách điểm định trước.
- Random/Random Waypoint: thay đổi hướng có giới hạn và có random seed để tái lập.

Cho phép cấu hình vị trí ban đầu X/Y, vận tốc, gia tốc hoặc tốc độ mục tiêu, bán kính/tần số quỹ đạo, danh sách waypoint, thời điểm đổi hướng và random seed. Mục tiêu phải di chuyển theo mô hình động học có giới hạn vận tốc/gia tốc; không teleport giữa các điểm.

Các hình dạng quỹ đạo này là lựa chọn tạo chuyển động. Chúng có thể được kết hợp với điều kiện cảm biến (noise, dropout, delay) để tạo ra nhiều thí nghiệm khác nhau. Không cần coi mỗi hình dạng là một kịch bản đánh giá độc lập bắt buộc.

## 7.4. Nhóm C – 5 bài thử tương tác mục tiêu

| STT | Bài thử | Cách thao tác | Mục tiêu đánh giá |
|---|---|---|---|
| 8 | Interactive Straight/Point Command | Click chuột để đặt điểm đích; mục tiêu tự di chuyển đến điểm đó | UAV có bám được mục tiêu sau khi đổi đích không |
| 9 | Interactive Waypoint | Click nhiều điểm để tạo chuỗi waypoint | Bám theo mục tiêu qua nhiều đoạn đường và góc cua |
| 10 | Mouse Drag Target | Giữ và kéo chuột để thay đổi điểm đích liên tục | Khả năng bám đuổi theo lệnh thay đổi liên tục |
| 11 | Keyboard Controlled Target | WASD điều khiển hướng; Shift tăng tốc; Space dừng | Tracking error và response time khi người dùng điều khiển |
| 12 | Sudden Escape / Evasive Target | Người dùng đột ngột đổi hướng, tăng tốc hoặc đổi lệnh liên tục | Maximum separation, tracking success rate, giới hạn bám đuổi |

Quy tắc điều khiển tương tác:
- Click chuột trái: đặt vị trí đích/waypoint cho mục tiêu.
- Giữ và kéo chuột trái: cập nhật vị trí đích liên tục; mục tiêu phải di chuyển đến đích theo giới hạn vận tốc/gia tốc, không được teleport theo con trỏ.
- Click nhiều lần: thêm waypoint vào hàng đợi; có thao tác xóa/hủy waypoint.
- WASD: tạo lệnh hướng hoặc vận tốc cho mục tiêu.
- Shift: tăng tốc trong giới hạn cấu hình.
- Space: giảm tốc/dừng mục tiêu theo mô hình động học, không đặt vận tốc bằng 0 tức thời nếu điều đó vi phạm giới hạn gia tốc.
- R: phát lệnh đổi hướng hoặc reset hướng theo cách được mô tả trên giao diện.
- Esc: thoát/chuyển chế độ tương tác theo quy ước giao diện.

Có thể cho phép cấu hình tốc độ mục tiêu và giới hạn gia tốc trong Interactive Mode. Không được để thao tác người dùng làm thay đổi trực tiếp trạng thái UAV.

## 7.5. Nguyên tắc chạy thử và lưu dữ liệu

- Mỗi kịch bản phải có cấu hình riêng và được lưu cùng kết quả.
- Với kịch bản ngẫu nhiên/noise, lưu random seed.
- Khi so sánh EKF và UKF, hai bộ lọc phải nhận cùng một chuỗi measurement, cùng timestamp và cùng điều kiện khởi tạo.
- Với interactive mode, ghi log timestamp và lệnh chuột/bàn phím cùng Ground Truth để có thể phân tích lại. Các lần chạy tương tác khác nhau không mặc nhiên có thể so sánh trực tiếp nếu chuỗi lệnh không giống nhau.
- Khi mất detection, filter chỉ Prediction, không được thay measurement bị mất bằng (0,0).
- Ghi riêng dữ liệu Ground Truth, Measurement, Estimate, PID command và UAV state.


------------------------------------------------------------------------

# PHẦN VIII. CẤU TRÚC THƯ MỤC DỰ ÁN ĐỀ XUẤT

``` text
UAV_Target_Tracking/
│
├── main.py
├── README.md
├── requirements.txt
├── config.yaml
│
├── models/
│   ├── target_model.py
│   ├── uav_model.py
│   └── camera_model.py
│
├── filters/
│   ├── ekf.py
│   └── ukf.py
│
├── control/
│   └── pid_controller.py
│
├── simulation/
│   ├── simulation_engine.py
│   ├── target_scenario.py
│   └── interactive_target.py
│
├── interface/
│   ├── dashboard.py
│   ├── draw_objects.py
│   ├── control_panel.py
│   ├── mouse_controller.py
│   ├── keyboard_controller.py
│   └── telemetry.py
│
├── evaluation/
│   ├── estimation_evaluation.py
│   └── tracking_evaluation.py
│
├── results/
│   ├── figures/
│   ├── data/
│   └── reports/
│
└── tests/
    ├── test_target_model.py
    ├── test_uav_model.py
    ├── test_camera_model.py
    ├── test_ekf.py
    ├── test_ukf.py
    └── test_pid.py
```

Có thể điều chỉnh cấu trúc nếu cần, nhưng phải giữ phân tách rõ model,
camera, filter, controller, simulation, interface và evaluation.

------------------------------------------------------------------------

# PHẦN IX. GIAO DIỆN MODULE VÀ HỢP ĐỒNG DỮ LIỆU

Dự án do một người triển khai. Vì vậy, cần thiết kế interface giữa các module thống nhất ngay từ đầu để tránh phụ thuộc vòng và dễ kiểm thử.

| Module | Input | Output |
|---|---|---|
| Target Model | thời gian, dt, scenario hoặc target command | target Ground Truth state |
| UAV Model | acceleration command, dt | UAV state |
| Camera Model | target state, UAV pose, timestamp | measurement, timestamp, detection status |
| EKF | measurement, UAV pose, timestamp | estimated state, covariance |
| UKF | measurement, UAV pose, timestamp | estimated state, covariance |
| PID | estimated target state, UAV state, dt | acceleration command |
| Simulation Engine | config, selected filter, controls | điều phối vòng lặp và dữ liệu |
| Mouse/Keyboard Controller | sự kiện chuột/phím | target command, không điều khiển UAV |
| Evaluation | Ground Truth, measurement, estimate, UAV state | metrics và file kết quả |

Cấu trúc estimate có thể thống nhất:

```python
estimated_state = {
    "x": x,
    "y": y,
    "vx": vx,
    "vy": vy
}
```

Trong code thực tế nên dùng dataclass hoặc kiểu dữ liệu có kiểm tra, bao gồm timestamp và covariance nếu cần. PID không được phụ thuộc vào việc state đến từ EKF hay UKF.

Mouse/Keyboard Controller chỉ gửi target command tới Target Motion Model. Không được truyền tọa độ con trỏ, phím bấm hoặc Ground Truth trực tiếp vào PID/UAV.

------------------------------------------------------------------------

# PHẦN X. KẾ HOẠCH TRIỂN KHAI CHO MỘT NGƯỜI

Tiến độ tham khảo 6 tuần; có thể kéo dài hoặc rút ngắn tùy thời hạn và kinh nghiệm lập trình.

| Tuần | Công việc | Kết quả cần đạt |
|---|---|---|
| 1 | Nghiên cứu mô hình động học, mô hình camera, EKF/UKF, PID; chốt hệ tọa độ, state vector, timestep và measurement model | Đặc tả toán học và cấu hình thống nhất |
| 2 | Xây dựng Target Model, UAV Model, predefined scenarios; kiểm thử chuyển động độc lập | Ground Truth và quỹ đạo chạy đúng |
| 3 | Xây dựng Camera Model, noise, FOV, dropout, delay; triển khai EKF và UKF | Measurement và state estimation hoạt động |
| 4 | Xây dựng PID, desired following point, giới hạn vận tốc/gia tốc, anti-windup; kiểm thử baseline tracking | UAV bám được mục tiêu trong baseline |
| 5 | Xây dựng Pygame Dashboard, interactive mouse/keyboard, tích hợp toàn bộ hệ thống | Hai chế độ predefined và interactive hoạt động |
| 6 | Chạy 12 bài thử, tính metrics, lưu CSV, sửa lỗi, hoàn thiện README và báo cáo | Bộ kết quả thực nghiệm có thể tái lập |

Thứ tự ưu tiên nếu thời gian hạn chế:
1. Hoàn thành mô hình và pipeline chạy không GUI.
2. Hoàn thành EKF/UKF và kiểm chứng bằng dữ liệu đo.
3. Hoàn thành PID và baseline tracking.
4. Hoàn thành Pygame dashboard.
5. Bổ sung interactive control và các stress test.
6. Hoàn thiện phân tích, biểu đồ và báo cáo.

Không nên làm giao diện trước khi mô hình và thuật toán cốt lõi đã chạy đúng.

------------------------------------------------------------------------

# PHẦN XII. KẾT QUẢ CẦN CÓ ĐỂ CHỨNG MINH ĐỀ TÀI

## 12.1. Quỹ đạo bám đuổi 2D

Phải thể hiện: - Target trajectory. - UAV trajectory. - Ground Truth. -
Estimated target position. - Khoảng cách bám đuổi theo thời gian hoặc
tại từng thời điểm.

## 12.2. So sánh EKF và UKF

Biểu đồ: - Measurement và Ground Truth. - EKF estimate và Ground
Truth. - UKF estimate và Ground Truth. - Sai số vị trí theo thời gian. -
Sai số vận tốc theo thời gian.

## 12.3. Sai số bám đuổi

Biểu đồ: - Desired following distance. - Actual following distance. -
Tracking error theo thời gian.

## 12.4. Phục hồi khi mất tín hiệu

Phải chỉ rõ: - Khoảng thời gian camera mất detection. - EKF/UKF tiếp tục
prediction ra sao. - Sai số tăng thế nào. - Khi measurement quay lại,
estimate phục hồi ra sao. - UAV có duy trì được tracking hay không.

## 12.5. Bảng metrics

Tối thiểu: - Position RMSE. - Velocity RMSE. - Tracking RMSE. -
Mean/maximum tracking distance error. - Recovery time sau dropout. - Có
thể bổ sung settling time, overshoot, computation time.

Không được đặt trước kết quả đẹp hoặc ép EKF/UKF phải có thuật toán nào
tốt hơn. Kết quả phải được sinh ra từ mô phỏng và đo lường thực tế.


## 12.6. Chỉ số bổ sung cho Interactive Target Control

- Interactive Tracking RMSE: RMSE sai số bám đuổi trong các lần điều khiển tương tác.
- Response Time: thời gian từ khi target command thay đổi đến khi UAV bắt đầu phản ứng có ý nghĩa.
- Maximum Separation: khoảng cách lớn nhất giữa UAV và target trong lần chạy.
- Tracking Success Rate: tỷ lệ thời gian sai số bám nằm trong ngưỡng cho phép.
- Maximum Trackable Target Speed: vận tốc mục tiêu lớn nhất mà UAV vẫn đáp ứng tiêu chí tracking đã định nghĩa.
- Recovery Time: thời gian UAV quay lại vùng tracking sau một lệnh đổi hướng/thoát ly.

Để đo Maximum Trackable Target Speed có ý nghĩa, cần tăng tốc độ mục tiêu theo các mức có kiểm soát, giữ nguyên giới hạn UAV, controller, timestep và tiêu chí tracking. Báo cáo cả điều kiện thử và ngưỡng thành công; không suy ra một con số duy nhất từ một lần chạy.

------------------------------------------------------------------------

# PHẦN XIII. CÁC ĐIỂM KỸ THUẬT PHẢI KIỂM SOÁT

1.  Nếu camera đo trực tiếp X,Y thì mô hình quan sát tuyến tính; Kalman
    Filter tuyến tính có thể đủ. Để nghiên cứu EKF/UKF, nên chọn mô hình
    quan sát phi tuyến như range-bearing hoặc bearing-only, nhưng phải
    giải thích đúng giả định vật lý.
2.  Camera đơn không tự đo được range nếu không có giả định/thuật toán
    suy ra khoảng cách.
3.  Pixel coordinates không tự động bằng world coordinates.
4.  Khi mất detection, phải bỏ qua measurement update, không thay
    measurement bằng 0.
5.  Với bearing, phải xử lý angle wrapping và circular mean.
6.  Measurement delay phải giữ timestamp và không được gán sai thời
    điểm.
7.  EKF và UKF phải nhận cùng dữ liệu để so sánh công bằng.
8.  PID phải dùng Estimated State trong bài đánh giá chính.
9.  PID cần saturation và anti-windup.
10. Desired following point phải duy trì khoảng cách, không đơn giản
    luôn đặt trùng với target.
11. Pygame chỉ là giao diện và simulation visualization, không thay thế
    thuật toán.
12. Dùng random seed để tái lập kết quả.
13. Lưu toàn bộ dữ liệu thô và cấu hình từng lần chạy.
14. Kiểm thử từng module trước khi tích hợp.

------------------------------------------------------------------------

# PHẦN XIV. YÊU CẦU TRIỂN KHAI DÀNH CHO ANTIGRAVITY

## 14.1. Vai trò

Bạn là AI coding agent có nhiệm vụ triển khai toàn bộ dự án trên máy
tính hiện tại theo hồ sơ kỹ thuật này. Hãy kiểm tra môi trường, tạo
project, viết code, cài dependencies, chạy chương trình, kiểm thử và sửa
lỗi cho đến khi có một phiên bản hoạt động.

## 14.2. Quy tắc triển khai

-   Trước tiên kiểm tra thư mục làm việc, hệ điều hành, phiên bản Python
    và các thư viện hiện có.
-   Không tự ý xóa hoặc ghi đè các file có sẵn của người dùng.
-   Nếu thư mục dự án đã tồn tại, kiểm tra nội dung trước khi sửa.
-   Tạo virtual environment.
-   Tạo `requirements.txt`, `README.md` và file cấu hình.
-   Viết code theo module, không dồn toàn bộ vào một file.
-   Dùng type hints và docstrings cho các hàm quan trọng.
-   Có kiểm tra input và xử lý lỗi.
-   Tách logic mô phỏng khỏi giao diện Pygame.
-   Không để giao diện làm nghẽn vòng lặp tính toán.
-   Dùng fixed simulation timestep; render có thể chạy theo FPS riêng.
-   Không hard-code các kết quả RMSE minh họa.
-   Không giả lập rằng EKF/UKF đã chạy nếu chưa thực sự triển khai.
-   Tạo unit tests cho các module.
-   Chạy chương trình và kiểm thử thực tế sau khi viết code.
-   Nếu có lỗi, tự phân tích và sửa; không chỉ báo lỗi rồi dừng.
-   Ghi lại các giả định mô hình trong README và báo cáo kỹ thuật.
-   Không thêm các framework nặng như ROS2/Gazebo/AirSim nếu chưa có yêu
    cầu.
-   Không huấn luyện YOLO hoặc AI detection nếu chưa cần thiết.

## 14.3. Các giai đoạn Antigravity phải thực hiện

**Giai đoạn A -- Kiểm tra và khởi tạo** 1. Kiểm tra môi trường. 2. Tạo
thư mục dự án và virtual environment. 3. Cài thư viện. 4. Tạo cấu trúc
thư mục. 5. Viết README và config.

**Giai đoạn B -- Mô hình nền** 1. Implement target model. 2. Implement
UAV model. 3. Tạo scenario. 4. Viết unit test. 5. Tạo chế độ chạy không
GUI để xác minh Ground Truth.

**Giai đoạn C -- Camera** 1. Implement camera measurement model. 2. Chọn
và ghi rõ mô hình measurement. 3. Implement noise, FOV, dropout, delay.
4. Viết test cho từng trường hợp. 5. Nếu chọn OpenCV, tạo camera view
trực quan; nếu không, không thêm dependency không cần thiết.

**Giai đoạn D -- EKF/UKF** 1. Implement EKF. 2. Implement UKF. 3. Kiểm
thử prediction/update. 4. Kiểm thử missing measurement. 5. Kiểm thử
angle handling nếu dùng bearing. 6. So sánh trên cùng measurement
sequence.

**Giai đoạn E -- PID** 1. Implement PID rời rạc. 2. Implement desired
following point. 3. Implement saturation và anti-windup. 4. Kiểm tra UAV
model phản hồi đúng lệnh. 5. Tuning PID ở baseline trước khi thêm noise
lớn.

**Giai đoạn F -- Tích hợp** 1. Implement simulation engine. 2. Kết nối
target, camera, filter, PID và UAV. 3. Hỗ trợ chuyển EKF/UKF. 4. Hỗ trợ
chạy song song EKF/UKF để so sánh. 5. Ghi log dữ liệu.

**Giai đoạn G -- Pygame Dashboard và Interactive Control**
1. Xây dựng màn hình mô phỏng.
2. Vẽ UAV, target, quỹ đạo, measurement, estimated position, FOV và vectors.
3. Xây dựng telemetry và control panel.
4. Xây dựng Predefined Scenario Mode với các quỹ đạo Straight, Circular, Sinusoidal, Zigzag, Waypoint và Random.
5. Xây dựng Interactive Target Control bằng chuột và bàn phím.
6. Đảm bảo lệnh chuột/phím chỉ tác động Target Motion Model; UAV vẫn chỉ dùng camera → EKF/UKF → PID.
7. Đảm bảo Start/Pause/Reset, chọn filter, chọn scenario và sensor fault controls hoạt động.

**Giai đoạn H -- Evaluation và hoàn thiện**
1. Chạy đủ 7 kịch bản định trước và 5 bài thử tương tác (tổng cộng 12 bài thử được mô tả ở Phần VII).
2. Tính metrics từ dữ liệu thực.
3. Xuất CSV, biểu đồ và báo cáo.
4. Viết hướng dẫn chạy.
5. Kiểm tra lại toàn bộ chương trình từ đầu.

## 14.4. Tiêu chí nghiệm thu

Dự án chỉ được coi là hoàn thành khi:

-   Chạy được bằng một lệnh được ghi trong README.
-   Cửa sổ Pygame hiển thị được UAV và target chuyển động.
-   Có Predefined Scenario Mode với các quỹ đạo Straight, Circular, Sinusoidal, Zigzag, Waypoint và Random.
-   Có Interactive Target Control bằng chuột và bàn phím; mục tiêu di chuyển theo giới hạn vận tốc/gia tốc, không teleport.
-   Có thể lưu/log target commands trong interactive mode.
-   UAV không nhận trực tiếp lệnh chuột/phím hoặc Ground Truth của target.
-   Camera tạo measurement có noise.
-   Có thể tạo dropout và delay.
-   EKF chạy được và trả về estimated state.
-   UKF chạy được và trả về estimated state.
-   Có thể chuyển đổi EKF/UKF.
-   Có thể chạy cả hai trên cùng dữ liệu để so sánh.
-   PID sử dụng estimated state để điều khiển UAV.
-   UAV có giới hạn vận tốc và gia tốc.
-   UAV có thể duy trì khoảng cách bám đuổi trong baseline scenario.
-   Các predefined scenarios chạy được và có thể tái lập bằng config/random seed.
-   Người dùng có thể điều khiển target bằng chuột/bàn phím trong Interactive Mode.
-   Khi target đổi hướng hoặc người dùng điều khiển target, hệ thống vẫn tiếp tục hoạt động và có dữ liệu đánh giá.
-   Khi camera mất detection, filter thực hiện prediction-only.
-   Khi camera khôi phục, filter tiếp tục update.
-   Có dữ liệu CSV và metrics.
-   Có unit tests cơ bản.
-   README mô tả cách cài đặt, chạy, điều khiển giao diện và cấu hình.
-   Không có số liệu giả hoặc biểu đồ chỉ mang tính trang trí.

## 14.5. Cách làm việc và báo cáo tiến độ

Hãy làm theo từng giai đoạn và sau mỗi giai đoạn: - Liệt kê file đã
tạo/sửa. - Nêu chức năng đã hoàn thành. - Nêu lệnh đã chạy. - Nêu kết
quả test thực tế. - Nêu vấn đề còn tồn tại. - Không tuyên bố hoàn thành
nếu chưa chạy thử.

Nếu gặp một lựa chọn kỹ thuật chưa được xác định (đặc biệt là camera
measurement model, range/bearing, bearing-only, camera calibration), hãy
nêu rõ giả định, chọn phương án đơn giản nhưng có cơ sở, ghi lại trong
README và tiếp tục triển khai. Không được âm thầm tạo giả định vật lý
sai.

------------------------------------------------------------------------

# PHẦN XV. PROMPT NGẮN ĐỂ BẮT ĐẦU TRONG ANTIGRAVITY

Hãy đọc toàn bộ tài liệu bàn giao này và triển khai dự án UAV Target
Tracking 2D trực tiếp trong workspace hiện tại. Dự án do một người thực hiện; không cần tạo kế hoạch phân chia nhân sự.

Không chỉ tạo demo giao diện. Hãy xây dựng một hệ thống mô phỏng thực sự
gồm: 1. Target Motion Model. 2. UAV Motion Model. 3. Simulated Camera
với measurement noise, FOV, detection dropout và measurement delay. 4.
EKF tự triển khai. 5. UKF tự triển khai. 6. PID controller với desired
following distance, acceleration/velocity limits và anti-windup. 7.
Simulation Engine. 8. Pygame Dashboard. 9. Evaluation và CSV logging.
10. Unit tests và README.
11. Predefined Scenario Mode với các quỹ đạo cấu hình được.
12. Interactive Target Control bằng chuột và bàn phím, trong đó lệnh người dùng chỉ điều khiển target model.

Ưu tiên Python, NumPy, SciPy và Pygame. OpenCV là tùy chọn nếu cần
camera view trực quan. Matplotlib chỉ cần cho biểu đồ hậu xử lý nếu
thuận tiện.

Hãy triển khai theo thứ tự từng module, kiểm thử từng module, sau đó
tích hợp. Đảm bảo EKF/UKF dùng cùng measurement sequence để so sánh. PID
phải dùng estimated state trong bài đánh giá chính. Mọi kết quả và biểu
đồ phải lấy từ mô phỏng thật, không dùng số liệu giả. Trước khi hoàn tất, chạy thử 7 kịch bản định trước và 5 bài thử tương tác (12 bài thử tổng cộng), đồng thời báo cáo kết quả nghiệm thu theo các tiêu chí ở Phần XIV.

**Kết thúc hồ sơ bàn giao.**

------------------------------------------------------------------------

# PHẦN XVI. QUY TRÌNH VẬN HÀNH SAU KHI ANTIGRAVITY TRIỂN KHAI XONG

## 16.1. Mục tiêu sử dụng cuối cùng

Sau khi Antigravity hoàn thành việc phát triển, cài đặt, kiểm thử và nghiệm thu dự án, người dùng cuối chỉ cần mở chương trình Pygame để chạy các kịch bản mô phỏng thông thường. Không cần mở Antigravity mỗi lần muốn sử dụng phần mềm.

Antigravity là công cụ hỗ trợ phát triển và bảo trì mã nguồn. Chương trình Python/Pygame được tạo ra mới là ứng dụng độc lập dùng để vận hành mô phỏng trên máy tính.

## 16.2. Hai cách chạy chương trình

### A. GUI Mode – chạy mô phỏng trực quan bằng Pygame

Đây là chế độ sử dụng thông thường:
1. Khởi chạy ứng dụng bằng file chạy nhanh do Antigravity tạo (ưu tiên `run.bat` trên Windows).
2. Cửa sổ Pygame mở ra.
3. Chọn Predefined Scenario hoặc Interactive Target Control.
4. Chọn bộ lọc EKF, UKF hoặc chế độ so sánh cả hai nếu phù hợp.
5. Cấu hình các thông số cần thiết.
6. Nhấn START để chạy mô phỏng.
7. Quan sát UAV, target, camera/FOV, quỹ đạo, estimated position và telemetry.
8. PAUSE/RESUME/RESET khi cần.
9. Khi kết thúc, lưu dữ liệu và xem kết quả đánh giá.

### B. Batch Runner GUI – quản lý thí nghiệm bằng giao diện riêng

Đây là giao diện quản lý thí nghiệm độc lập với cửa sổ mô phỏng Pygame. Người dùng có thể chọn kịch bản, filter, số lần chạy, random seed và cấu hình; nhấn RUN ALL để hệ thống tự thực thi các lượt mô phỏng ở chế độ không render đồ họa. Như vậy, người dùng vẫn thao tác bằng giao diện nhưng không cần mở cửa sổ Pygame cho từng lượt chạy.

### C. Headless/CLI Mode – chạy hoàn toàn không có giao diện đồ họa

Chế độ này dùng cho tự động hóa nâng cao, chạy từ CMD/PowerShell hoặc file batch. Chương trình chạy simulation engine trực tiếp, không mở Pygame và cũng không mở Batch Runner GUI. Chế độ này phù hợp khi cần chạy dài hoặc tích hợp quy trình kiểm thử tự động.

Cả GUI Mode, Batch Runner GUI và Headless/CLI Mode phải dùng chung simulation engine, mô hình, bộ lọc, controller và cấu hình. Không được viết các bộ thuật toán riêng có thể tạo ra kết quả khác nhau.

## 16.3. Yêu cầu file chạy nhanh trên Windows

Antigravity cần tạo tối thiểu:

- `setup.bat`: tạo virtual environment và cài `requirements.txt`; chỉ cần chạy ở lần cài đặt đầu tiên hoặc khi dependencies thay đổi.
- `run.bat`: kích hoạt virtual environment và mở Pygame Simulation GUI.
- `run_batch.bat`: mặc định mở Batch Runner GUI riêng (không mở Pygame); người dùng chọn thí nghiệm và nhấn RUN ALL. Batch Runner GUI sẽ gọi simulation engine ở chế độ không render.
- `run_batch.bat --headless`: chạy batch hoàn toàn bằng CMD/PowerShell, không mở Pygame và không mở Batch Runner GUI.
- Có thể tạo `run_headless.bat` như shortcut tương đương cho `run_batch.bat --headless` nếu thuận tiện.

Các file batch phải:
- Kiểm tra Python có sẵn hay không.
- Hiển thị thông báo lỗi dễ hiểu nếu thiếu Python hoặc dependencies.
- Không tự ý xóa dữ liệu hoặc kết quả cũ.
- Giữ cửa sổ terminal mở khi có lỗi để người dùng đọc được thông báo.
- Dùng đường dẫn tương đối từ thư mục dự án để có thể di chuyển project.

README phải ghi rõ cách chạy bằng giao diện và bằng terminal. Cú pháp CLI gợi ý:

```bash
python main.py --mode gui
python batch_runner.py --mode gui
python main.py --mode batch --headless --config config.yaml
```

Antigravity có thể chọn cú pháp khác, nhưng phải thống nhất và ghi rõ trong README cũng như file `.bat`. Lưu ý phân biệt rõ Batch Runner GUI (có giao diện quản lý nhưng không render Pygame) với Headless/CLI (không có bất kỳ giao diện đồ họa nào).

## 16.4. Scenario Manager trong Pygame

Giao diện Pygame phải có màn hình/quản lý kịch bản cho phép người dùng:
- Chọn một trong các kịch bản định trước.
- Chọn Interactive Target Control.
- Chọn EKF, UKF hoặc EKF+UKF comparison.
- Thiết lập thời gian mô phỏng và timestep.
- Thiết lập camera measurement rate, noise, FOV, dropout và delay.
- Thiết lập vận tốc/gia tốc mục tiêu.
- Thiết lập giới hạn vận tốc/gia tốc UAV.
- Thiết lập desired following distance.
- Thiết lập PID gains hoặc chọn cấu hình PID đã lưu.
- Chọn random seed hoặc chế độ seed tự động.
- Lưu và tải cấu hình thí nghiệm.

Các giá trị cấu hình cần có giới hạn hợp lệ và đơn vị rõ ràng. Không cho phép thay đổi tham số tạo ra cấu hình vô nghĩa mà không cảnh báo người dùng.

## 16.5. Batch Experiment Runner

Antigravity phải xây dựng Batch Experiment Runner để người dùng không phải tự chạy từng lần bằng tay.

Chức năng tối thiểu:
1. Chọn một hoặc nhiều kịch bản tự động.
2. Chọn EKF, UKF hoặc cả hai.
3. Chọn số lần chạy cho mỗi cấu hình.
4. Chọn danh sách random seed hoặc seed range.
5. Chọn thời lượng mô phỏng và các tham số camera/UAV/PID.
6. Tự động chạy từng cấu hình.
7. Ghi lại trạng thái từng lượt: pending/running/completed/failed.
8. Có thể tiếp tục các lượt chưa hoàn thành sau khi chương trình bị gián đoạn, không ghi đè kết quả đã có.
9. Tính metrics theo từng lượt và tổng hợp mean, standard deviation, min/max hoặc percentile phù hợp.
10. Xuất CSV và báo cáo tổng hợp.

Nếu chạy EKF và UKF để so sánh, cả hai phải nhận cùng một chuỗi measurement đã sinh từ cùng một lần mô phỏng camera. Không được sinh hai chuỗi nhiễu độc lập cho hai filter trong cùng một phép so sánh.

Đối với các kịch bản tương tác chuột/bàn phím, Batch Runner không thể tự tạo cùng một hành vi người dùng nếu không có input được ghi lại. Vì vậy cần có chức năng record/replay:
- Ghi lệnh chuột/bàn phím cùng timestamp.
- Lưu thành file trajectory/command log.
- Phát lại chính xác cùng chuỗi lệnh để so sánh EKF và UKF.
- Có thể tạo các kịch bản tự động tương đương như scripted escape để kiểm thử lặp lại.

## 16.6. Kết quả và dữ liệu đầu ra

Mỗi lượt chạy phải lưu tối thiểu:
- Cấu hình thí nghiệm.
- Scenario ID/name.
- Random seed.
- Filter selection.
- Timestamp/time step.
- Target Ground Truth.
- UAV Ground Truth/state.
- Camera measurement và measurement timestamp.
- Detection status.
- EKF estimate và covariance nếu bật EKF.
- UKF estimate và covariance nếu bật UKF.
- PID command.
- Actual tracking distance và desired distance.
- Các trạng thái dropout/delay/noise.
- Metrics tính được.

Cấu trúc kết quả gợi ý:

```text
results/
  scenario_01_baseline/
    run_001/
      config.json
      data.csv
      metrics.json
    run_002/
      config.json
      data.csv
      metrics.json
    summary.csv
  scenario_02_sudden_turn/
  scenario_03_high_noise/
  ...
  interactive_recordings/
    recording_001.json
  summary/
    EKF_UKF_comparison.csv
    tracking_performance.csv
    experiment_report.pdf
```

Không được ghi đè kết quả trước đó nếu người dùng chưa xác nhận. Mỗi run cần có ID duy nhất hoặc thư mục riêng.

## 16.7. Điều kiện nghiệm thu vận hành

Dự án chỉ được bàn giao để người dùng sử dụng thường xuyên khi:
- Có thể mở GUI bằng `run.bat` trên Windows sau khi setup ban đầu.
- Có thể mở GUI bằng lệnh được ghi trong README.
- Có thể chọn và chạy các kịch bản từ Pygame mà không cần sửa code.
- Có thể thao tác Start, Pause, Resume và Reset.
- Có thể chọn filter và cấu hình các thông số.
- Interactive mode nhận chuột/bàn phím và điều khiển target đúng giới hạn động học.
- UAV không nhận trực tiếp mouse/keyboard command hoặc target Ground Truth.
- Có thể chạy headless/batch mode độc lập với Pygame.
- Có thể chạy nhiều random seed và xuất kết quả.
- Record/replay tương tác hoạt động và tái lập được chuỗi lệnh.
- CSV, metrics và cấu hình được lưu đầy đủ.
- Tắt/mở lại ứng dụng không làm mất dữ liệu đã lưu.
- README hướng dẫn rõ cách setup lần đầu, chạy GUI, chạy batch, vị trí kết quả và cách khắc phục lỗi thường gặp.

## 16.8. Quy trình sử dụng sau khi bàn giao

Sau khi cài đặt lần đầu:

1. Người dùng mở thư mục dự án.
2. Nhấp đúp `run.bat` hoặc chạy lệnh GUI trong README.
3. Chọn scenario và cấu hình trên Pygame.
4. Nhấn START để mô phỏng.
5. Xem kết quả và lưu dữ liệu.
6. Khi cần chạy nhiều lần để lấy số liệu nghiên cứu, nhấp đúp `run_batch.bat` để mở Batch Runner GUI, chọn cấu hình và nhấn RUN ALL. Nếu muốn chạy hoàn toàn không có giao diện, chạy `run_batch.bat --headless` hoặc `run_headless.bat`.

Người dùng không cần mở Antigravity trong quy trình vận hành bình thường. Chỉ cần dùng lại Antigravity khi muốn phát triển tính năng, sửa lỗi hoặc thay đổi thuật toán.

------------------------------------------------------------------------

# PHẦN XVII. YÊU CẦU CUỐI CÙNG BỔ SUNG CHO ANTIGRAVITY

Ngoài toàn bộ yêu cầu ở các phần trước, hãy triển khai ứng dụng theo hướng có thể sử dụng độc lập sau khi phát triển xong:

1. Pygame GUI là ứng dụng vận hành chính để người dùng chọn và chạy các kịch bản.
2. Người dùng không cần mở Antigravity để chạy mô phỏng thường ngày.
3. Tạo `setup.bat` để cài đặt lần đầu; `run.bat` để mở Pygame Simulation GUI; `run_batch.bat` để mở Batch Runner GUI; và hỗ trợ `run_batch.bat --headless` (hoặc `run_headless.bat`) để chạy hoàn toàn không có giao diện.
4. Tạo Scenario Manager cho phép cấu hình và lưu/tải các kịch bản.
5. Tạo Batch Experiment Runner có thể chạy headless, chạy nhiều scenario/random seed, theo dõi tiến độ, tiếp tục sau gián đoạn và xuất dữ liệu/metrics.
6. GUI và Batch phải dùng chung simulation engine và cùng các module thuật toán.
7. Với kịch bản tương tác, phải có record/replay lệnh chuột/bàn phím để tái lập cùng một chuỗi điều khiển khi so sánh EKF và UKF.
8. Bảo toàn kết quả cũ, không tự động ghi đè dữ liệu.
9. Viết README hướng dẫn setup lần đầu, chạy GUI, chạy batch, cấu hình, vị trí lưu kết quả và xử lý lỗi.
10. Trước khi bàn giao, kiểm tra thực tế cả ba luồng: Pygame GUI bằng `run.bat`; Batch Runner GUI bằng `run_batch.bat`; Headless/CLI bằng `run_batch.bat --headless` hoặc `run_headless.bat`.

Mục tiêu bàn giao cuối cùng là một ứng dụng mô phỏng UAV Target Tracking 2D chạy độc lập trên máy tính: người dùng chỉ cần khởi chạy Pygame, chọn kịch bản và chạy; khi cần thực nghiệm số lượng lớn thì sử dụng Batch Experiment Runner. Antigravity chỉ được dùng lại khi cần sửa đổi hoặc phát triển phần mềm.

**Kết thúc phần bổ sung vận hành.**


------------------------------------------------------------------------

# PHẦN XVIII. QUY TRÌNH SỬ DỤNG CÁC FILE SAU KHI ANTIGRAVITY BÀN GIAO

Phần này chốt quy trình vận hành dành cho người dùng. Antigravity phải triển khai đúng để người dùng không cần tự mở CMD hoặc nhập lệnh trong quá trình sử dụng thông thường.

## 18.1. Các file khởi chạy và mục đích

| File | Khi nào sử dụng | Kết quả |
|---|---|---|
| `setup.bat` | Chỉ lần đầu cài đặt hoặc khi dependencies thay đổi | Tạo `.venv`, cài thư viện và kiểm tra môi trường |
| `run.bat` | Mỗi khi muốn quan sát UAV bay trong mô phỏng | Mở cửa sổ Pygame Simulation |
| `run_batch.bat` | Mỗi khi muốn chạy nhiều thí nghiệm bằng giao diện | Mở Batch Runner GUI riêng; không mở cửa sổ Pygame |
| `run_batch.bat --headless` | Khi muốn chạy hoàn toàn không có giao diện đồ họa | Chạy batch qua CMD/PowerShell, không mở Pygame hoặc Batch Runner GUI |
| `run_headless.bat` | Shortcut tùy chọn cho người thường xuyên chạy headless | Tương đương `run_batch.bat --headless` |

## 18.2. Quy trình lần đầu tiên

1. Cài Python phiên bản tương thích nếu máy chưa có. Antigravity phải kiểm tra phiên bản Python mà dự án hỗ trợ và ghi rõ trong README.
2. Giải nén/đặt toàn bộ thư mục dự án tại vị trí mong muốn.
3. Nhấp đúp `setup.bat`.
4. Chờ chương trình tạo môi trường ảo `.venv`, cài dependencies từ `requirements.txt` và chạy kiểm tra import cơ bản.
5. Nếu setup báo lỗi, đọc thông báo và xử lý trước khi chạy GUI hoặc batch.

`setup.bat` không được xóa `.venv`, dữ liệu hoặc kết quả cũ một cách âm thầm. Nếu cần cài lại, phải thông báo rõ và yêu cầu xác nhận trước khi xóa môi trường hiện có.

## 18.3. Quy trình mô phỏng trực quan

1. Nhấp đúp `run.bat`.
2. Pygame Simulation GUI mở ra.
3. Chọn Predefined Scenario hoặc Interactive Target Control.
4. Chọn quỹ đạo hoặc phương thức điều khiển mục tiêu.
5. Chọn EKF, UKF hoặc chế độ so sánh phù hợp.
6. Cấu hình camera noise, FOV, measurement rate, dropout, delay, PID và giới hạn động học.
7. Nhấn START để chạy; dùng PAUSE/RESUME/RESET khi cần.
8. Quan sát UAV, target, Ground Truth, Measurement, Estimated State, FOV và telemetry.
9. Kết thúc lượt chạy và lưu dữ liệu/metrics.

Trong chế độ tương tác, người dùng điều khiển target bằng chuột hoặc WASD. UAV chỉ được bám đuổi qua camera → EKF/UKF → PID, không được nhận trực tiếp tọa độ con trỏ hoặc lệnh bàn phím.

## 18.4. Quy trình chạy Batch bằng giao diện

1. Nhấp đúp `run_batch.bat`.
2. Batch Runner GUI riêng mở ra. Đây không phải cửa sổ Pygame.
3. Chọn một hoặc nhiều predefined scenarios/scripted scenarios.
4. Chọn EKF, UKF hoặc cả hai.
5. Chọn số lần lặp, random seeds và các thông số thí nghiệm.
6. Nhấn RUN ALL.
7. Batch Runner gọi simulation engine ở chế độ không render hình ảnh; do đó không cần mở Pygame cho từng lượt chạy.
8. Theo dõi trạng thái pending/running/completed/failed.
9. Khi hoàn thành, xem bảng metrics và mở thư mục `results/`.

Đối với thí nghiệm so sánh EKF và UKF, cả hai filter phải nhận cùng measurement sequence được tạo từ cùng một lần chạy camera. Không được sinh hai chuỗi nhiễu độc lập để so sánh.

## 18.5. Quy trình chạy hoàn toàn không giao diện (Headless/CLI)

Chỉ sử dụng khi cần tự động hóa, chạy từ CMD/PowerShell hoặc tích hợp test. Ví dụ:

```bat
run_batch.bat --headless
```

Hoặc:

```bat
run_headless.bat
```

Headless mode không mở Pygame và cũng không mở Batch Runner GUI. Kết quả vẫn phải được ghi vào `results/` theo cùng định dạng với Batch Runner GUI.

## 18.6. Nguyên tắc chung cho cả ba cách chạy

- `run.bat`, Batch Runner GUI và Headless/CLI phải dùng chung simulation engine và các module thuật toán.
- Không được có một bộ EKF/UKF/PID riêng cho GUI và một bộ khác cho batch.
- Các thông số cấu hình phải lưu được và có thể tái lập.
- Không tự động ghi đè kết quả đã tồn tại.
- Khi một lượt chạy thất bại, ghi trạng thái và nguyên nhân lỗi; không đánh dấu completed.
- Khi đóng ứng dụng hoặc bị gián đoạn, dữ liệu các lượt đã hoàn thành phải được bảo toàn.
- README phải có hướng dẫn bằng tiếng Việt, kèm ảnh chụp giao diện thực tế sau khi triển khai nếu có thể.

**Tóm tắt quy trình người dùng:**

```text
LẦN ĐẦU:
setup.bat

MÔ PHỎNG VÀ QUAN SÁT UAV:
run.bat  →  Pygame  →  Chọn kịch bản  →  START

CHẠY NHIỀU THÍ NGHIỆM BẰNG GIAO DIỆN:
run_batch.bat  →  Batch Runner GUI  →  Chọn cấu hình  →  RUN ALL

CHẠY HOÀN TOÀN KHÔNG GIAO DIỆN:
run_batch.bat --headless
hoặc run_headless.bat
```

Người dùng chỉ cần chạy `setup.bat` ở lần đầu. Các lần sử dụng tiếp theo chọn `run.bat` để mô phỏng trực quan hoặc `run_batch.bat` để quản lý và chạy thí nghiệm hàng loạt. Antigravity không cần mở trong quá trình vận hành thường ngày.

**Kết thúc phần bổ sung quy trình vận hành.**
