# Từ một chủ đề đến video truyện ngắn nét phẳng

Sổ tay cho toàn bộ pipeline: cần chuẩn bị gì, mỗi model cần gì để train, đầu vào và đầu ra của từng bước, và repository nào dùng làm nền.

Bước dùng model bạn tự train. Các bước 2, 3 và 6 chỉ phụ thuộc vào kịch bản nên chạy song song được.

## Thông số video

Mọi con số ở các phần sau tính theo mục tiêu này.

| Thông số             | Giá trị                         | Ghi chú                                                                               |
|----------------------|---------------------------------|---------------------------------------------------------------------------------------|
| Thời lượng           | 60 đến 120 giây                 | Nên bắt đầu ở 60-75 giây rồi kéo dài dần khi đã biết người xem ở lại tới đâu          |
| Khung hình           | Dọc 9:16, 1080×1920, 30fps      |                                                                                       |
| Số cảnh              | 45 đến 90                       | Giữ nhịp khoảng 1,3 giây mỗi cảnh như video mẫu                                       |
| Số nền               | 8 đến 12                        | Dùng lại giữa các cảnh và giữa các video                                              |
| Ảnh gốc nhân vật     | 10 đến 25 tư thế                | Mỗi tư thế sinh 4-6 ảnh để chọn, luôn sinh từ ảnh chuẩn                               |
| Khung biến thể       | Phần còn lại của 45-90 cảnh     | Sửa từ ảnh gốc: đổi biểu cảm hoặc tay                                                 |
| Tổng số lần sinh ảnh | Khoảng 250-350 cho video 2 phút | Ước tính; số ảnh không phải thứ cần tiết kiệm, độ ổn định của nhân vật mới là ưu tiên |
| Giọng đọc            | 45 đến 90 câu ngắn              | Mỗi câu đọc trong 1-2 giây                                                            |

Video dài gấp đôi thì khối lượng ảnh, giọng đọc và thời gian duyệt cũng gấp đôi, và giữ người xem tới cuối khó hơn. Vì vậy kịch bản cần nhiều nấc phát triển hơn chứ không chỉ kéo dài một tình huống.

## Kiến trúc

Ba tầng. Tầng huấn luyện chỉ chạy khi cần model mới; tầng sản xuất chạy cho mỗi video; mọi thành phần trao đổi với nhau qua file trong thư mục dự án.

*Sơ đồ: Ba tầng: huấn luyện làm một lần tạo ra file LoRA; sản xuất mỗi video gồm script điều phối gọi Claude, FLUX.2 klein trên GPU, rembg và Pillow, TTS, ffmpeg; và tầng lưu trữ là thư mục dự án mà mọi thành phần đọc và ghi.*

Viền xanh: thành phần liên quan tới model tự train. Mũi tên bên phải: file LoRA sau khi train được lưu vào tầng lưu trữ, và klein đọc nó từ đó khi sinh ảnh nhân vật.

- **Các thành phần không gọi trực tiếp nhau.** Mỗi thành phần đọc file đầu vào và ghi file đầu ra, nên bạn chạy lại riêng một bước mà không ảnh hưởng bước khác.
- **Chỉ một thành phần cần GPU** lúc sản xuất. Phần còn lại chạy trên CPU, nên GPU có thể bật theo đợt rồi tắt.
- **Claude và TTS là dịch vụ ngoài** gọi qua API; có thể thay nhà cung cấp mà không đổi kiến trúc.

## Làm ở máy local trước

Ba chặng. Chỉ chuyển lên AWS khi chặng 2 đã chạy ổn, vì AWS chỉ thay nơi chạy chứ không sửa được quy trình còn lỗi.

### Máy của bạn làm được gì

| GPU trên máy        | Train LoRA                                                                                                 | Sinh ảnh                                           |
|---------------------|------------------------------------------------------------------------------------------------------------|----------------------------------------------------|
| NVIDIA từ 24GB VRAM | Ngay trên máy bằng AI Toolkit                                                                              | Trên máy                                           |
| NVIDIA 12-16GB      | Thuê GPU theo giờ chỉ cho lúc train (Colab L4 hoặc A100, hoặc dịch vụ thuê GPU có sẵn template AI Toolkit) | Trên máy; klein 4B cần khoảng 13GB                 |
| Không có GPU NVIDIA | Thuê GPU theo giờ                                                                                          | Thuê GPU, hoặc gọi API của BFL với LoRA đã tải lên |

Các bước tách nền, ghép cảnh, giọng đọc và dựng video chạy trên CPU, nên máy nào cũng làm được.

### AChặng 1: làm tay từng bước

Mục tiêu: ra được một video 60-75 giây và hiểu từng bước mất bao lâu, hỏng ở đâu.

**Đầu vào:** Dataset đã lọc, một chủ đề truyện

**Công cụ:** AI Toolkit, ComfyUI hoặc script diffusers, rembg, TTS, `build_video.py`

**Đầu ra:** File LoRA đã chọn, video số 1, bảng thời gian từng bước

1.  **Cài AI Toolkit** theo README của repo và mở giao diện web. Lệnh cài đặt thay đổi theo phiên bản nên lấy từ README.
2.  **Train style LoRA.** Tạo job, trỏ vào thư mục dataset, chọn FLUX.2 Klein 4B Base, khai báo 6-8 prompt mẫu, bấm Start. Chọn checkpoint theo hướng dẫn ở phần Train model.
3.  **Tạo ảnh chuẩn ba góc** cho từng nhân vật bằng style LoRA, lưu vào `config/refs/`.
4.  **Viết kịch bản** bằng Claude trong ứng dụng chat, lưu thành `script.json`.
5.  **Sinh nền và nhân vật bằng tay** trong ComfyUI hoặc bằng đoạn script diffusers ở bước 3. Làm tay giúp bạn tìm ra mẫu prompt nào cho kết quả ổn định trước khi đưa vào script.
6.  **Tách nền, ghép cảnh** bằng hai đoạn code ở bước 4 và 5, chỉnh vị trí nhân vật cho tới khi vừa mắt.
7.  **Tạo giọng đọc** cho từng câu, lưu theo số thứ tự cảnh.
8.  **Dựng** bằng `build_video.py`.

Trong lúc làm, ghi lại ba thứ: mẫu prompt đã dùng, vị trí và kích thước nhân vật trong khung, và các lỗi lặp lại. Đây là đầu vào cho chặng 2.

### BChặng 2: tự động hóa ở local

Mục tiêu: một lệnh chạy từ `script.json` ra `output.mp4`, người chỉ can thiệp ở khâu viết kịch bản và duyệt.

**Đầu vào:** Ghi chép từ chặng 1, `script.json`

**Công cụ:** Các script Python, mỗi bước một file

**Đầu ra:** Lệnh `python run_local.py videos/002` chạy trọn pipeline

Quy tắc viết script để sau này đưa lên AWS không phải viết lại:

- Mỗi bước là một file chạy độc lập, nhận đường dẫn thư mục video làm tham số duy nhất.
- Bước nào cũng chỉ đọc file và ghi file trong thư mục đó; không bước nào gọi hàm của bước khác.
- Kết quả đã có thì bỏ qua, để chạy lại sau khi sửa một cảnh không phải làm lại từ đầu.
- Không ghi cứng đường dẫn hay khóa API trong code; đọc từ biến môi trường.

&nbsp;

    steps/
      00_make_cast.py      characters.json                →  config/refs/   (chạy một lần cho cả kênh)
      02_backgrounds.py    script.json + locations.json   →  backgrounds/
      03_characters.py     script.json + characters.json  →  characters/
      04_cutouts.py        characters/                    →  cutouts/
      05_compose.py        cutouts/ + backgrounds/        →  scenes/ (ảnh xem trước + bố cục .json)
      06_voice.py          script.json                    →  audio/
      07_build.py          scenes/ + audio/               →  output.mp4
    run_local.py           gọi lần lượt các bước trên

    """run_local.py: chạy trọn pipeline cho một video. Dùng: python run_local.py videos/002"""
    import subprocess
    import sys

    STEPS = ["02_backgrounds", "03_characters", "04_cutouts", "05_compose", "06_voice", "07_build"]

    video_dir = sys.argv[1]
    for step in STEPS:
        print(f"== {step}")
        subprocess.run([sys.executable, f"steps/{step}.py", video_dir], check=True)
    print(f"Xong: {video_dir}/output.mp4")

Đoạn trên là khung điều phối tối giản. Bước duyệt ảnh nằm giữa bước 03 và 04: chạy tới 03, xóa ảnh hỏng, chạy lại 03 để sinh bù, rồi chạy tiếp.

### CChặng 3: đưa lên AWS

Mục tiêu: cùng những script đó, chạy trên hạ tầng tự bật tự tắt.

| Ở local                           | Trên AWS                             | Phải đổi gì                                                                                 |
|-----------------------------------|--------------------------------------|---------------------------------------------------------------------------------------------|
| Thư mục dự án                     | Bucket S3                            | Thêm bước tải thư mục video xuống đầu mỗi task và đẩy kết quả lên cuối task                 |
| AI Toolkit trên máy               | SageMaker Training Job, Managed Spot | Đóng gói trainer và file cấu hình vào một image trên ECR                                    |
| `02_backgrounds`, `03_characters` | SageMaker Asynchronous Inference     | Tách phần nạp model và phần sinh ảnh thành handler của endpoint; script chỉ còn gửi yêu cầu |
| `04`, `05`, `07`                  | Task ECS trên Fargate Spot           | Một image chứa ba script cùng ffmpeg                                                        |
| `06_voice`                        | Lambda hoặc cùng task ECS            | Gần như không đổi                                                                           |
| `run_local.py`                    | Step Functions                       | Chuyển danh sách bước thành state machine, cho bước 02, 03 và 06 chạy song song             |
| Claude trong ứng dụng chat        | Claude trên Bedrock                  | Một hàm gọi API với prompt đã dùng ổn ở local                                               |

### Điều kiện để chuyển chặng

- **Từ 1 sang 2:** đã có một video hoàn chỉnh, một checkpoint LoRA được chọn, và mẫu prompt cho kết quả ổn định ở phần lớn các cảnh.
- **Từ 2 sang 3:** đã làm ít nhất 3-5 video bằng một lệnh, biết thời gian và tỷ lệ ảnh hỏng của từng bước, và số liệu xem cho thấy định dạng này đáng làm tiếp.
- **Chưa nên lên AWS nếu:** bạn chỉ làm một vài video mỗi tuần. Ở mức đó máy local hoặc GPU thuê theo giờ rẻ và ít việc vận hành hơn.

## Hạ tầng AWS

Thiết kế theo một nguyên tắc: không có máy nào chạy khi không có việc. GPU chỉ bật khi có hàng đợi, và tự về 0 khi hết.

*Sơ đồ: Step Functions điều phối mỗi video và gọi Bedrock, SageMaker Async Endpoint, dịch vụ TTS và ECS trên Fargate Spot. CloudWatch alarm cùng Application Auto Scaling đưa endpoint từ 0 máy lên khi có hàng đợi và về 0 khi hết việc. SageMaker Training Job dùng Managed Spot để train LoRA. Mọi thành phần đọc và ghi vào một bucket S3.*

Viền xanh: nơi model tự train được tạo ra và được dùng.

### Vai trò từng dịch vụ

| Dịch vụ                                            | Làm gì                                                                                                          | Tính tiền khi nào                                   |
|----------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|-----------------------------------------------------|
| Step Functions                                     | Điều phối một video: kịch bản, rồi song song nền, nhân vật và giọng đọc, rồi ghép và dựng. Tự thử lại bước lỗi. | Theo số lần chuyển trạng thái, rất nhỏ ở quy mô này |
| Bedrock (Claude)                                   | Viết `script.json` từ chủ đề                                                                                    | Theo token                                          |
| SageMaker Asynchronous Inference                   | Sinh ảnh nền và nhân vật bằng klein 4B gắn LoRA. Yêu cầu vào hàng đợi, kết quả ghi ra S3.                       | Theo giờ máy, chỉ khi có máy đang chạy              |
| Polly hoặc TTS ngoài                               | Giọng đọc từng câu. Polly có giọng tiếng Nhật; ngôn ngữ khác cần kiểm tra danh sách hỗ trợ.                     | Theo ký tự                                          |
| ECS trên Fargate Spot                              | Tách nền, ghép cảnh, chạy `build_video.py`. Chỉ cần CPU.                                                        | Theo giây chạy, giá Spot                            |
| SageMaker Training Job                             | Train LoRA bằng Managed Spot, checkpoint ghi ra S3 để chạy tiếp nếu bị thu hồi máy                              | Theo giây chạy, giá Spot                            |
| ECR                                                | Chứa image container cho train, inference và dựng                                                               | Theo dung lượng                                     |
| S3                                                 | Nơi duy nhất lưu dữ liệu; các thành phần trao đổi qua đây                                                       | Theo dung lượng                                     |
| CloudWatch, Application Auto Scaling, SNS, Budgets | Co giãn endpoint, cảnh báo lỗi và chi phí                                                                       | Gần như bằng 0                                      |

### Cơ chế co giãn bằng alarm

Endpoint dạng asynchronous là loại endpoint SageMaker cho phép số máy tối thiểu bằng 0. Việc co giãn dùng hai chính sách:

1.  **Từ 0 lên 1.** Khi có yêu cầu trong hàng đợi mà chưa có máy nào, metric `HasBacklogWithoutCapacity` bằng 1. Một CloudWatch alarm trên metric này kích hoạt chính sách step scaling để thêm một máy.
2.  **Từ 1 lên nhiều hơn, và về lại 0.** Chính sách target tracking bám theo metric `ApproximateBacklogSizePerInstance` (số yêu cầu đang chờ chia cho số máy). Hàng đợi dài thì thêm máy; hàng đợi về 0 thì sau thời gian chờ, số máy giảm về 0.

&nbsp;

    import boto3

    ENDPOINT = "klein-lora-async"
    RESOURCE = f"endpoint/{ENDPOINT}/variant/AllTraffic"
    aas = boto3.client("application-autoscaling")
    cw = boto3.client("cloudwatch")
    DIM = [{"Name": "EndpointName", "Value": ENDPOINT}]

    # Cho phép số máy từ 0 đến 2
    aas.register_scalable_target(
        ServiceNamespace="sagemaker", ResourceId=RESOURCE,
        ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        MinCapacity=0, MaxCapacity=2)

    # Bám theo độ dài hàng đợi; hết việc thì về 0 sau 5 phút
    aas.put_scaling_policy(
        PolicyName="backlog-target-tracking", ServiceNamespace="sagemaker",
        ResourceId=RESOURCE, ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        PolicyType="TargetTrackingScaling",
        TargetTrackingScalingPolicyConfiguration={
            "TargetValue": 60.0,              # khoảng 60 ảnh đang chờ cho mỗi máy
            "CustomizedMetricSpecification": {
                "MetricName": "ApproximateBacklogSizePerInstance",
                "Namespace": "AWS/SageMaker", "Dimensions": DIM, "Statistic": "Average"},
            "ScaleInCooldown": 300, "ScaleOutCooldown": 120})

    # Từ 0 lên 1 khi có hàng đợi mà chưa có máy
    step = aas.put_scaling_policy(
        PolicyName="wake-from-zero", ServiceNamespace="sagemaker",
        ResourceId=RESOURCE, ScalableDimension="sagemaker:variant:DesiredInstanceCount",
        PolicyType="StepScaling",
        StepScalingPolicyConfiguration={
            "AdjustmentType": "ChangeInCapacity", "MetricAggregationType": "Average", "Cooldown": 300,
            "StepAdjustments": [{"MetricIntervalLowerBound": 0, "ScalingAdjustment": 1}]})

    cw.put_metric_alarm(
        AlarmName="klein-has-backlog-without-capacity",
        Namespace="AWS/SageMaker", MetricName="HasBacklogWithoutCapacity", Dimensions=DIM,
        Statistic="Average", Period=60, EvaluationPeriods=2, DatapointsToAlarm=2,
        Threshold=1, ComparisonOperator="GreaterThanOrEqualToThreshold",
        TreatMissingData="missing", AlarmActions=[step["PolicyARN"]])

Tên metric và cách ghép hai chính sách theo tài liệu của AWS. Các con số `TargetValue`, thời gian chờ và số máy tối đa là gợi ý ban đầu, cần chỉnh theo tốc độ sinh ảnh thực tế. Đoạn code này chưa được chạy thử trên tài khoản AWS.

**Cái giá của việc về 0 là thời gian khởi động.** Yêu cầu đầu tiên sau khi endpoint ngủ phải chờ máy bật và nạp model, thường vài phút. Với việc sinh ảnh theo lô cho video thì chấp nhận được; Step Functions chỉ cần chờ kết quả xuất hiện trên S3 hoặc nhận thông báo qua SNS.

### Alarm bảo vệ chi phí

- **Endpoint thức quá lâu.** Alarm khi số máy lớn hơn 0 liên tục quá 2 giờ, gửi SNS. Đây là dấu hiệu hàng đợi bị kẹt hoặc chính sách về 0 không hoạt động.
- **Yêu cầu lỗi.** Cấu hình endpoint gửi kết quả lỗi vào một SNS topic, để yêu cầu hỏng không lặng lẽ biến mất.
- **Step Functions thất bại.** Alarm trên số lần chạy thất bại.
- **AWS Budgets.** Đặt ngân sách tháng với cảnh báo ở 50%, 80% và 100%.
- **Training job chạy quá lâu.** Đặt thời gian tối đa cho job, ví dụ 4 giờ, để job treo tự dừng.

### Các quyết định giúp giảm chi phí

| Quyết định                                        | Tác dụng                                                                                                     |
|---------------------------------------------------|--------------------------------------------------------------------------------------------------------------|
| Endpoint asynchronous với số máy tối thiểu bằng 0 | Tránh khoản trên 1.100 USD mỗi tháng của một máy `ml.g5.2xlarge` chạy liên tục                               |
| Managed Spot cho training                         | Giảm khoảng 50-70% so với giá thường; checkpoint mỗi 250 bước nên bị thu hồi máy không mất công              |
| ECS trên Fargate Spot cho phần CPU                | Không cần giữ máy chủ nào; việc bị ngắt thì Step Functions chạy lại                                          |
| Một máy GPU đơn (`ml.g5` hoặc `ml.g6`)            | klein 4B chỉ cần khoảng 13GB VRAM, không cần máy nhiều GPU                                                   |
| Gom yêu cầu theo lô                               | Gửi toàn bộ ảnh của một video cùng lúc để máy chỉ thức một lần                                               |
| Không dùng NAT Gateway                            | Tránh khoản phí cố định hằng tháng; dùng S3 gateway endpoint (miễn phí) và subnet công khai cho task Fargate |
| Lifecycle trên S3                                 | Tự xóa `build_tmp/` và ảnh trung gian sau vài ngày; chuyển video cũ sang lớp lưu trữ rẻ                      |
| Dùng lại nền trong `library/`                     | Giảm số ảnh phải sinh cho mỗi video                                                                          |

### Ước tính cho mỗi video

Với video 1-2 phút, khoảng 250-350 ảnh cộng thời gian khởi động thường nằm trong 30-45 phút máy GPU, tức khoảng 1 USD ở giá khoảng 1,5 USD mỗi giờ. Phần Bedrock, TTS và Fargate cộng lại thường nhỏ hơn khoản này. Đây là ước tính, chưa phải số đo; số thật phụ thuộc thời gian khởi động và tốc độ sinh ảnh trên máy bạn chọn.

**Phương án đơn giản hơn khi mới bắt đầu.** Với một vài video mỗi ngày, bạn có thể bỏ hẳn endpoint và chạy bước sinh ảnh như một job theo lô cho từng video: không có gì để co giãn, không có alarm cần cấu hình, và chi phí tương đương. Endpoint asynchronous đáng dùng khi nhiều video xếp hàng cùng lúc, vì máy đang thức sẽ xử lý tiếp mà không phải khởi động lại.

## Chuẩn bị

Những thứ cần có trước khi chạy bước đầu tiên.

### Quyết định cần chốt trước

- **Nguồn nét vẽ.** Điều khoản và trang hỏi đáp của irasutoya.com hiện không nói gì về việc dùng tranh để train AI: không cho phép rõ, cũng không cấm rõ. Trước khi dùng LoRA cho kênh kiếm tiền, hãy hỏi qua trang liên hệ của họ, hoặc dùng công cụ chính thức AIいらすとや, hoặc train trên ảnh tự sinh để có nét riêng.
- **Nhân vật.** Dùng nhân vật tự thiết kế. Nhân vật có bản quyền chỉ hợp để thử nghiệm.
- **Ngôn ngữ và giọng đọc** của kênh, vì nó quyết định công cụ TTS và font phụ đề.
- **Tên kênh và tiêu đề** không chứa chữ いらすとや: trang gốc cấm cách đặt tên gây hiểu nhầm là hợp tác chính thức.

### Quy tắc thiết kế nhân vật

- Mỗi nhân vật nhận ra được chỉ bằng hai ba mảng màu lớn: màu áo, màu quần, kiểu tóc.
- Không dùng họa tiết nhỏ, chữ, logo hay phụ kiện lặt vặt. Đây là những thứ trôi đầu tiên giữa các ảnh.
- Hai nhân vật trong cùng một truyện không trùng màu áo.
- Mỗi nhân vật có một bảng ảnh chuẩn ba góc: trước, nghiêng, sau.

### Phần cứng

| Việc                 | Cần                     | Ghi chú                                                                            |
|----------------------|-------------------------|------------------------------------------------------------------------------------|
| Train LoRA           | GPU NVIDIA từ 24GB VRAM | Máy riêng, Colab (L4 hoặc A100), hoặc SageMaker `ml.g5.2xlarge` khoảng 1,5 USD/giờ |
| Sinh ảnh             | GPU khoảng 13GB VRAM    | Bản klein 4B distilled; không có GPU thì gọi API của BFL với LoRA đã tải lên       |
| Tách nền, ghép, dựng | CPU thường              | Chạy được trên laptop                                                              |

### Phần mềm và tài khoản

- Python 3.10 trở lên, `ffmpeg` và `ffprobe` trong PATH, Node.js (cho giao diện web của AI Toolkit).
- Tài khoản Hugging Face và token đọc, để tải FLUX.2 klein.
- Quyền dùng Claude (ứng dụng chat hoặc API) cho bước kịch bản.
- Một công cụ TTS: VOICEVOX chạy máy riêng (tiếng Nhật, miễn phí), hoặc một dịch vụ trả phí cho ngôn ngữ khác.
- Font có đủ ký tự của ngôn ngữ phụ đề, ví dụ Noto Sans CJK JP cho tiếng Nhật, Be Vietnam Pro cho tiếng Việt.
- Nhạc nền có giấy phép dùng cho video kiếm tiền.

### Cấu trúc thư mục dự án

    shorts-pipeline/
      config/
        characters.json      mô tả cố định của từng nhân vật
        locations.json       mô tả cố định của từng bối cảnh
        refs/                ảnh chuẩn của từng nhân vật: trước, nghiêng, sau
      loras/
        style.safetensors    style LoRA sau khi train
      library/backgrounds/   ảnh nền dùng lại giữa các video
      videos/
        001-ten-video/
          script.json        kịch bản (đầu ra bước 1)
          backgrounds/       nền dùng trong video này
          characters/        ảnh nhân vật nền trắng (bước 3)
          cutouts/           ảnh nhân vật đã tách nền (bước 4)
          scenes/            ảnh cảnh đã ghép (bước 5)
          audio/             giọng đọc từng câu (bước 6)
          output.mp4         video hoàn chỉnh (bước 7)
      build_video.py         script dựng

## Repository nền

Bạn không cần viết lại phần nào trong bảng này. Phần tự viết chỉ là các script nối chúng lại.

| Dùng cho                 | Repository                                                                                                      | Vai trò                                                                                               |
|--------------------------|-----------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| Train LoRA               | [ostris/ai-toolkit](https://github.com/ostris/ai-toolkit)                                                       | Trainer được Black Forest Labs giới thiệu, có giao diện web. Đây là repo nền chính của phần training. |
| Train LoRA (thay thế)    | [huggingface/diffusers](https://github.com/huggingface/diffusers/blob/main/examples/dreambooth/README_flux2.md) | Script DreamBooth LoRA cho FLUX.2, hợp khi muốn đóng gói thành SageMaker Training Job.                |
| Base model để train      | `black-forest-labs/FLUX.2-klein-base-4B`                                                                        | Bản chưa distill, giấy phép Apache 2.0.                                                               |
| Base model để sinh ảnh   | `black-forest-labs/FLUX.2-klein-4B`                                                                             | Bản distilled 4 bước, nhanh. Gắn LoRA đã train trên bản base.                                         |
| Code inference tham khảo | [black-forest-labs/flux2](https://github.com/black-forest-labs/flux2)                                           | Code tối thiểu để sinh và chỉnh sửa ảnh bằng FLUX.2.                                                  |
| Tách nền                 | [danielgatis/rembg](https://github.com/danielgatis/rembg)                                                       | Thư viện Python tách nền hàng loạt.                                                                   |
| Giọng đọc tiếng Nhật     | [VOICEVOX/voicevox_engine](https://github.com/VOICEVOX/voicevox_engine)                                         | Engine TTS chạy máy riêng, gọi qua HTTP. Mỗi giọng có điều khoản ghi nguồn riêng.                     |
| Ghép ảnh                 | Pillow                                                                                                          | Dán nhân vật lên nền.                                                                                 |
| Dựng video               | ffmpeg                                                                                                          | Chuyển động, phụ đề ASS, trộn âm thanh.                                                               |

Tài liệu train chính thức: [docs.bfl.ai](https://docs.bfl.ai/flux_2/flux2_klein_training.md) và bài hướng dẫn [trên Hugging Face](https://huggingface.co/blog/black-forest-labs/flux-2-klein-lora).

## Train model

Chỉ có hai loại model đáng tự train. Mọi thứ khác dùng model có sẵn.

### Style LoRA: dạy nét vẽ

Bắt buộc. Đây là thứ tạo ra nét riêng cho mọi ảnh nhân vật.

**Đầu vào:** 100-150 ảnh cùng nét, mỗi ảnh một file caption `.txt` cùng tên

**Công cụ:** AI Toolkit, base `FLUX.2-klein-base-4B`

**Đầu ra:** Các file `.safetensors` theo từng mốc và ảnh mẫu của mỗi mốc

### Chuẩn bị dataset

- Ảnh PNG hoặc JPG, nền trắng (đổ nền trắng cho PNG trong suốt), cạnh ngắn từ khoảng 700px.
- Đa dạng chủ thể: người theo độ tuổi và nghề, cảm xúc mạnh, hai người tương tác, góc nhìn từ sau và nghiêng, con vật, đồ vật.
- Mỗi nhóm ảnh gần trùng nhau chỉ giữ 1-2 ảnh. Bỏ biểu đồ, ảnh chữ, sơ đồ, ảnh chỉ có nét viền.
- Caption dạng `irasutoya_style, a firefighter holding a hose, serious face, white background`. Mô tả nội dung, không mô tả phong cách.

### Thông số

| Thông số        | Giá trị              | Nguồn                                |
|-----------------|----------------------|--------------------------------------|
| Kiến trúc model | FLUX.2 Klein 4B Base | Tài liệu BFL                         |
| Learning rate   | 8e-5 đến 1e-4        | Tài liệu BFL                         |
| Lưu checkpoint  | Mỗi 250 bước         | Ví dụ của BFL                        |
| Độ phân giải    | 1024                 | Gợi ý ban đầu                        |
| Rank            | 16 đến 32            | Gợi ý ban đầu                        |
| Tổng số bước    | 1500 đến 3000        | Gợi ý ban đầu, chọn mốc bằng ảnh mẫu |

Các dòng "gợi ý ban đầu" là điểm xuất phát thường gặp, chưa phải giá trị đã kiểm chứng cho bộ ảnh của bạn.

### Cách chọn checkpoint

- Khai báo 6-8 prompt mẫu cố định, trong đó một nửa là thứ không có trong dataset (phi hành gia ăn mì, con mèo lái xe).
- Chọn mốc sớm nhất đã ra đúng nét mà vẫn theo đúng prompt.
- Dấu hiệu train quá tay: prompt khác nhau ra cùng một nhân vật, hoặc ảnh mẫu giống hệt ảnh trong dataset.

### Character LoRA: giữ nguyên một nhân vật

Tùy chọn, làm sau khi style LoRA đã ổn. Điều kiện để train nằm ở mục [Giữ nhân vật ổn định](#on-dinh).

**Đầu vào:** 15-20 ảnh của đúng một nhân vật, sinh bằng style LoRA rồi chọn tay

**Công cụ:** AI Toolkit, cùng base model

**Đầu ra:** Một file `.safetensors` cho mỗi nhân vật

- Ảnh phải cùng mặt, cùng trang phục, khác tư thế, biểu cảm và góc nhìn.
- Caption dùng trigger riêng, ví dụ `chr_repairman, fixing a bicycle tire, angry face, white background`. Không mô tả ngoại hình, vì trigger gánh phần đó.
- Khi sinh ảnh, gắn cùng lúc style LoRA và character LoRA.

### Model không tự train

| Model                        | Dùng ở bước | Cần chuẩn bị                                       |
|------------------------------|-------------|----------------------------------------------------|
| Claude                       | Kịch bản    | Prompt hệ thống kèm schema và hai file cấu hình    |
| FLUX.2 klein 4B (không LoRA) | Background  | Tải weights, mẫu prompt nền                        |
| Model tách nền của rembg     | Tách nền    | Tự tải ở lần chạy đầu                              |
| TTS                          | Giọng đọc   | Chọn giọng cho từng nhân vật, ghi lại mã giọng     |
| Image-to-video (tùy chọn)    | Dựng        | Chỉ dùng cho vài cảnh cao trào, trả tiền theo clip |

## Giữ nhân vật ổn định

Cùng một nhân vật phải giống nhau giữa các khung trong một phân cảnh, giữa các phân cảnh, và giữa các video.

*Sơ đồ: Ảnh chuẩn của nhân vật ở gốc. Ảnh gốc của từng phân cảnh đều sinh từ ảnh chuẩn. Các khung biến thể trong một phân cảnh được sửa từ ảnh gốc của phân cảnh đó.*

Viền xanh: ảnh chuẩn, điểm neo duy nhất của nhân vật.

- **Ảnh gốc của mỗi phân cảnh luôn sinh từ ảnh chuẩn.** Hai phân cảnh giống nhau vì cùng nhìn vào một ảnh mẫu.
- **Các khung trong một phân cảnh sửa từ ảnh gốc của phân cảnh đó.** Chỉ đổi mặt hoặc tay.
- **Không nối chuỗi từ phân cảnh này sang phân cảnh khác.** Mỗi lần sao chép qua model lệch một chút; với cấu trúc cây, mọi ảnh cách ảnh chuẩn tối đa hai bước.

### Ảnh tham chiếu hay character LoRA

|                   | Ảnh tham chiếu                                             | Character LoRA                                                          |
|-------------------|------------------------------------------------------------|-------------------------------------------------------------------------|
| Chuẩn bị          | Một bảng ảnh chuẩn ba góc                                  | 15-20 ảnh đã chọn, một lần train cho mỗi nhân vật                       |
| Thêm nhân vật mới | Vài phút                                                   | Hàng giờ; trên Kaggle T4, lần train 1500 bước của bạn chạy khoảng 5 giờ |
| Độ ổn định        | Tốt với nét phẳng đơn giản; yếu hơn ở tư thế khó và góc lạ | Tốt nhất, kể cả tư thế khó                                              |
| Hợp với           | Nhân vật chỉ xuất hiện trong một vài video                 | Nhân vật dùng lại ở nhiều video                                         |

### Hướng đề xuất

1.  **Làm video đầu tiên bằng ảnh tham chiếu và cấu trúc cây.** Không cần lần train nào thêm, và các ảnh gốc được duyệt trở thành dữ liệu train cho bước 4.
2.  **Dựng một dàn diễn viên cố định 8-10 nhân vật kiểu mẫu** dùng lại cho mọi truyện: ông chú, cậu bé, người mẹ, bà cụ, ông cụ, cô gái trẻ, nhân viên văn phòng, bác sĩ. Mỗi truyện chọn vai từ dàn này thay vì thiết kế nhân vật mới. Người xem quen mặt, và công sức đầu tư vào từng nhân vật được dùng lại.
3.  **Đo tỷ lệ ảnh gốc bị loại ở bước 3b** cho từng nhân vật qua vài video đầu.
4.  **Train character LoRA cho 2-3 nhân vật chính của dàn ngay khi có đủ 15-20 ảnh gốc đã duyệt**, tức là sau video đầu tiên. Với các nhân vật còn lại, train khi tỷ lệ ảnh gốc bị loại vẫn cao (ví dụ trên một phần ba) dù đã có ảnh chuẩn ba góc.
5.  **Không train LoRA cho nhân vật chỉ dùng một lần.** Thời gian train lớn hơn nhiều so với phần ổn định thu được.

Ưu tiên của dự án là độ ổn định của nhân vật, không phải số ảnh hay thời gian train. Mức một phần ba là gợi ý ban đầu, chỉnh theo số liệu thật.

### Những thứ không giữ được nhân vật

- **Giữ nguyên seed.** Seed chỉ cố định nhiễu ban đầu; đổi prompt thì khuôn mặt vẫn đổi.
- **Chỉ dựa vào style LoRA.** Nó giữ nét vẽ, không giữ nhận dạng của từng người.
- **Mô tả thật dài.** Mô tả cố định giữ được trang phục và màu, nhưng mặt vẫn trôi nếu không có ảnh tham chiếu.

## Chấm điểm độ ổn định

Cách quyết định một ảnh có đúng nhân vật hay không, và cách đặt ngưỡng.

### Hai thước đo

|          | Danh sách kiểm tra bằng model thị giác                                | Độ giống embedding (DINOv2)                           |
|----------|-----------------------------------------------------------------------|-------------------------------------------------------|
| Cách làm | Hỏi từng đặc điểm có hoặc không, sinh từ trường `prompt` của nhân vật | Cắt vùng nhân vật, tính độ giống cosine với ảnh chuẩn |
| Bắt được | Sai đặc điểm cụ thể: màu áo, kiểu tóc, thiếu giày                     | Tổng thể trông khác: tỷ lệ cơ thể, hình dạng đầu      |
| Chi phí  | Một lượt gọi API mỗi ảnh                                              | Gần như bằng 0, chạy trên CPU                         |
| Ngưỡng   | Mọi mục đều phải đúng                                                 | Phải đo trên ảnh của mình, xem bên dưới               |
| Vai trò  | Quyết định đạt hay không                                              | Loại ảnh nhầm nhân vật, xếp hạng các ứng viên         |

    {
      "toc_den_ngan": true,
      "ao_lien_quan_xanh_navy": true,
      "giay_nau": false,
      "long_may_day": true,
      "dung_do_tuoi": true
    }

Không hỏi model thị giác "giống bao nhiêu điểm": điểm kiểu đó dao động giữa các lần gọi. Danh sách có hoặc không ổn định hơn.

### Tính độ giống bằng DINOv2

DINOv2 là model nhúng ảnh mã nguồn mở đã train sẵn; không cần train thêm. Bản small khoảng 22 triệu tham số, chạy được trên CPU.

    import torch
    from PIL import Image
    from transformers import AutoImageProcessor, AutoModel

    processor = AutoImageProcessor.from_pretrained("facebook/dinov2-small")
    model = AutoModel.from_pretrained("facebook/dinov2-small").eval()

    def embed(path):
        inputs = processor(images=Image.open(path).convert("RGB"), return_tensors="pt")
        with torch.no_grad():
            return torch.nn.functional.normalize(model(**inputs).pooler_output, dim=-1)

    similarity = (embed("config/refs/repairman_front.png") @ embed("characters/001.png").T).item()

Đây là cách dùng chuẩn của model, chưa được chạy trong dự án này.

### Đặt ngưỡng cho độ giống

Không có con số chung. Với ảnh nét phẳng trên nền trắng, điểm thường dồn về phía cao vì nét vẽ và nền giống nhau: cùng nhân vật khác tư thế thường khoảng 0,6-0,9, khác nhân vật cùng nét thường khoảng 0,4-0,7. Hai khoảng này là ước lượng, chưa phải số đo, và chúng chồng lên nhau, nên phải đo:

1.  Lấy 20 ảnh của một nhân vật đã được người xác nhận là đúng, và 10 ảnh của các nhân vật khác trong dàn.
2.  Tính độ giống của cả 30 ảnh với ảnh chuẩn.
3.  Xếp theo điểm, tìm chỗ hai nhóm tách nhau, đặt ngưỡng ngay trên điểm cao nhất của nhóm sai.
4.  Ưu tiên không cho ảnh sai lọt qua, chấp nhận loại nhầm một số ảnh đúng.

Nếu hai nhóm chồng lên nhau, không dùng ngưỡng tuyệt đối; dựa vào kiểm tra khoảng cách bên dưới và danh sách kiểm tra.

### Kiểm tra khoảng cách với nhân vật khác

So ảnh ứng viên với ảnh chuẩn của mọi nhân vật trong dàn. Ảnh chỉ đạt khi nó giống ảnh chuẩn của đúng nhân vật hơn mọi nhân vật khác, với một khoảng cách tối thiểu (điểm xuất phát gợi ý 0,05-0,10, cũng cần đo). Kiểm tra này bắt được lỗi nguy hiểm nhất là nhân vật này bị vẽ thành nhân vật kia, và ổn định hơn ngưỡng tuyệt đối khi đổi tư thế hoặc đổi checkpoint.

### Cấu hình

    {
      "embedding_model": "facebook/dinov2-small",
      "min_similarity": null,
      "min_margin_vs_other_characters": null,
      "checklist_must_all_pass": true,
      "candidates_per_base_pose": 5,
      "max_retries": 4
    }

Hai giá trị `null` được điền sau bước đo; khi còn `null` thì bỏ qua kiểm tra tương ứng. Đo lại mỗi khi đổi model nhúng hoặc đổi checkpoint LoRA.

### Đọc tỷ lệ ảnh đạt

- **Phần lớn ảnh đạt mà nhân vật vẫn trôi:** ngưỡng lỏng, hoặc danh sách kiểm tra thiếu đặc điểm đang trôi. Thêm đặc điểm đó vào.
- **Rất ít ảnh đạt:** không hạ ngưỡng. Xem lại thiết kế nhân vật, ảnh chuẩn, hoặc train character LoRA cho nhân vật đó.

## Chuyển động

Mỗi cảnh có kiểu chuyển động riêng tùy nội dung. Claude chọn kiểu khi viết kịch bản, từ một bộ từ vựng cố định; cùng một mục trong kịch bản sinh ra cả prompt ảnh lẫn lệnh chuyển động nên hai thứ luôn khớp nhau.

### Bộ kiểu cơ bản của trường `motion`

| Nhóm               | Giá trị                                                                      | Tác động lên                             | Số ảnh nhân vật             |
|--------------------|------------------------------------------------------------------------------|------------------------------------------|-----------------------------|
| Máy quay           | `zoom_in`, `zoom_out`, `pan_left`, `pan_right`, `shake`, `none`              | Cả khung hình                            | 1                           |
| Di chuyển nhân vật | `approach`, `recede`, `enter_left`, `enter_right`, `exit_left`, `exit_right` | Riêng lớp nhân vật; nền gần như đứng yên | 1                           |
| Tại chỗ            | `bob`, `jump`, `pop_in`                                                      | Riêng lớp nhân vật                       | 1                           |
| Dự phòng           | `i2v`                                                                        | Cả cảnh, qua model image-to-video        | 1, hoặc 2 nếu có khung cuối |

Với `approach`, lớp nhân vật phóng to dần (ví dụ từ 50% lên 100%) và trượt xuống cùng lúc để chân bám theo mặt đường; `recede` làm ngược lại. Bảng này là điểm xuất phát: video đầu tiên chỉ cần `zoom_in`, `zoom_out`, `shake`, `approach`, `none` và `alt_pose`.

### Trường `alt_pose`: hai tư thế luân phiên

Đây là kiểu tổng quát nhất và kết hợp được với mọi giá trị `motion` trừ `i2v`. Khi `alt_pose` có nội dung:

1.  Bước 3 sinh ảnh gốc như thường, rồi sửa ra một ảnh thứ hai theo mô tả trong `alt_pose`, lưu thành `characters/003_alt.png`.
2.  Bước dựng đổi qua lại giữa hai ảnh mỗi khoảng 0,25 giây.

Cùng một cơ chế làm được bước chân, vẫy tay, gõ búa, đạp xe, ăn, nói chuyện. Ảnh thứ hai sửa từ ảnh gốc nên nhân vật giữ nguyên; cần kiểm tra hai ảnh chồng khít nhau ở phần thân.

### Cảnh `i2v`

- Dùng cho hành động không diễn tả được bằng bộ cơ bản: ôm nhau, ngã, leo lên xe.
- Đầu vào là ảnh cảnh đã ghép và trường `i2v_prompt`, ví dụ "The boy runs to his mother and they hug, camera static". Model nào nhận cả khung đầu và khung cuối thì đưa thêm ảnh kết thúc để dễ kiểm soát.
- Clip sinh ra lưu thành `clips/031.mp4`; bước dựng dùng clip đó thay cho ảnh tĩnh, cắt hoặc kéo cho khớp độ dài giọng đọc.
- Giới hạn tối đa 5 cảnh `i2v` mỗi video, ghi rõ trong lệnh cho Claude. Đây là bước tốn tiền theo clip và hay phải sinh lại.

### Quy tắc để hệ thống không vỡ

- Schema của kịch bản liệt kê các giá trị hợp lệ; script kiểm tra trước khi chạy và báo lỗi rõ ràng.
- Giá trị lạ lọt qua thì bước dựng dùng `zoom_in` làm mặc định, không dừng cả video.
- Trường `motion` đọc được và sửa tay được trước khi sinh ảnh.
- Khi một kiểu chuyển động lặp lại ở nhiều video mà chưa có tên, thêm nó vào bộ cơ bản.

## Hiệu ứng

Lớp hiệu ứng chồng lên cảnh ở khâu dựng, lấy từ một thư viện dùng lại và chọn theo cảm xúc của cảnh.

### Thứ tự các lớp trong một cảnh, từ dưới lên

| Lớp          | Gồm                                                                   | Tạo bằng                                                                                   |
|--------------|-----------------------------------------------------------------------|--------------------------------------------------------------------------------------------|
| 1\. Nền      | Bối cảnh, bầu trời; hoặc nền cảm xúc như nền xoáy tối, nền đỏ tia     | klein không LoRA; nền cảm xúc sinh một lần rồi dùng lại                                    |
| 2\. Nhân vật | Người, tư thế, biểu cảm, nước mắt, giọt mồ hôi trên mặt               | klein + style LoRA, rồi tách nền                                                           |
| 3\. Hiệu ứng | Đường tốc độ, lấp lánh, hoa, sao; nhãn dán cạnh đầu như dấu chấm than | Vẽ bằng code, hoặc sinh bằng LoRA trên nền trắng rồi tách nền và cho chuyển động bằng code |
| 4\. Chữ      | Tiêu đề, phụ đề                                                       | Bước dựng                                                                                  |

### Trường `effect`

Để `null` hoặc một tên có trong `library/effects/`. Bộ khởi đầu gợi ý:

| Giá trị                          | Loại                       | Dùng khi                      |
|----------------------------------|----------------------------|-------------------------------|
| `gloom_swirl`                    | Nền cảm xúc                | Tuyệt vọng, kiệt sức          |
| `red_burst`                      | Nền cảm xúc                | Sốc, hốt hoảng                |
| `blue_glow`                      | Nền cảm xúc                | Quyết tâm                     |
| `speed_lines`                    | Lớp phủ, vẽ bằng code      | Nhấn mạnh, bất ngờ            |
| `sparkles`                       | Lớp phủ                    | Vui, hy vọng                  |
| `flowers`                        | Lớp phủ                    | Hạnh phúc, cảm động           |
| `exclaim`, `sweat`, `anger_mark` | Nhãn dán cạnh đầu nhân vật | Ngạc nhiên, lo lắng, tức giận |

- Nhãn dán được đặt theo khung bao của nhân vật ghi trong `scenes/NNN.json`, không cần căn tay.
- Hoa và sao không ghi vào prompt nhân vật: bước tách nền hay xóa các chi tiết nhỏ quanh người.
- Video đầu tiên chỉ cần hai nền cảm xúc và `speed_lines`.

## Các file cấu hình

Ba file này nối mọi bước với nhau. Hai file đầu viết một lần cho cả kênh, file thứ ba sinh mới cho mỗi video.

### config/characters.json

    {
      "repairman": {
        "prompt": "middle-aged man, short black hair, thick eyebrows, navy coverall, brown shoes",
        "reference": ["config/refs/repairman_front.png", "config/refs/repairman_side.png", "config/refs/repairman_back.png"],
        "lora": "loras/chr_repairman.safetensors",
        "voice": "voice_id_cua_giong_nam_tram",
        "colour": "#4FC3F7"
      },
      "boy": {
        "prompt": "ten-year-old boy, short black hair, green striped t-shirt, orange pants",
        "reference": ["config/refs/boy_front.png", "config/refs/boy_side.png", "config/refs/boy_back.png"],
        "lora": null,
        "voice": "voice_id_cua_giong_tre_em",
        "colour": "#7CD992"
      }
    }

### config/locations.json

    {
      "shop_inside": "detailed anime background, inside a small bicycle repair shop, tools on the wall, warm afternoon light, no people, vertical 9:16",
      "street":      "detailed anime background, quiet residential street in Japan, warm afternoon light, no people, vertical 9:16"
    }

### videos/\<tên\>/script.json

    {
      "title": ["Dòng tiêu đề 1", "Dòng tiêu đề 2"],
      "font": "Noto Sans CJK JP",
      "speakers": { "narrator": "#4FC3F7", "boy": "#7CD992", "mother": "#F48FB1" },
      "scenes": [
        {
          "id": 1,
          "text": "Câu thoại hiện trên màn hình",
          "speaker": "narrator",
          "characters": ["repairman"],
          "action": "kneeling and fixing a bicycle tire",
          "emotion": "serious",
          "location": "shop_inside",
          "position": "center",
          "motion": "zoom_in",
          "alt_pose": null,
          "effect": null,
          "based_on": null
        },
        {
          "id": 2,
          "text": "Câu thoại tiếp theo, cùng tư thế",
          "speaker": "narrator",
          "characters": ["repairman"],
          "action": "same pose",
          "emotion": "surprised",
          "location": "shop_inside",
          "position": "center",
          "motion": "none",
          "alt_pose": null,
          "effect": "red_burst",
          "based_on": 1
        },
        {
          "id": 3,
          "text": "Cảnh có chuyển động thật",
          "speaker": "narrator",
          "characters": ["boy"],
          "action": "pushing a bicycle, walking toward the camera",
          "emotion": "shy",
          "location": "street",
          "position": "center",
          "motion": "approach",
          "alt_pose": "the other leg stepping forward",
          "effect": null,
          "based_on": null
        }
      ]
    }

`based_on` để `null` nghĩa là cảnh có tư thế mới và cần một ảnh gốc sinh từ ảnh chuẩn. Ghi số của một cảnh khác nghĩa là cảnh này chỉ là biến thể: lấy ảnh gốc của cảnh đó rồi sửa biểu cảm hoặc tay. `based_on` chỉ được trỏ tới một cảnh có `based_on` bằng `null`, không trỏ tới một biến thể khác.

Giá trị hợp lệ của `motion` và `alt_pose` nằm ở mục [Chuyển động](#chuyen-dong); của `effect` ở mục [Hiệu ứng](#hieu-ung). Cảnh dùng image-to-video có thêm trường `i2v_prompt`.

## Từng bước của pipeline

Mỗi bước ghi rõ nhận gì, làm gì, trả ra gì.

### 1Kịch bản

**Đầu vào:** Chủ đề, `characters.json`, `locations.json`, schema

**Công cụ:** Claude

**Đầu ra:** `script.json` 45-90 cảnh

- Yêu cầu Claude chỉ dùng tên nhân vật và bối cảnh có trong hai file cấu hình, mỗi câu thoại ngắn (đọc trong 1-2 giây), và trả về JSON đúng schema.
- Công thức của thể loại: kể ngôi thứ nhất, mở đầu bằng tình huống, cú twist cảm động ở cuối.
- Video 1-2 phút cần cấu trúc rõ hơn video dưới 1 phút: tình huống trong 5 giây đầu, hai hoặc ba nấc phát triển, mỗi nấc có một chi tiết mới giữ người xem, rồi twist và câu kết. Yêu cầu Claude ghi rõ mỗi cảnh thuộc nấc nào.
- Người duyệt: đọc to một lượt, cắt câu thừa. Bước này ảnh hưởng tới lượt xem nhiều nhất.

### 2Background

**Đầu vào:** Danh sách `location` trong kịch bản, `locations.json`

**Công cụ:** FLUX.2 klein 4B, không gắn LoRA

**Đầu ra:** `backgrounds/<location>.png`, 1080×1920

- Video 1-2 phút thường cần 8-12 nền. Nền đã có trong `library/backgrounds/` thì lấy lại, không sinh mới.
- Luôn ghi "no people" trong prompt để nền không có sẵn nhân vật lạ.
- Không gắn style LoRA ở bước này, để nền giữ độ chi tiết kiểu anime tương phản với nhân vật phẳng.

### 3Ảnh nhân vật

**Đầu vào:** Mỗi cảnh: `characters`, `action`, `emotion`, `based_on`; cùng `characters.json` và ảnh chuẩn trong `config/refs/`

**Công cụ:** FLUX.2 klein 4B + style LoRA (+ character LoRA), chế độ có ảnh tham chiếu

**Đầu ra:** `characters/001.png`, nền trắng, mỗi cảnh một ảnh

Bước này chia làm ba phần, theo cấu trúc cây ở mục [Giữ nhân vật ổn định](#on-dinh).

### 3a. Ảnh gốc cho tư thế mới

Áp dụng cho cảnh có `based_on` bằng `null`. Đưa ảnh chuẩn của nhân vật làm tham chiếu, prompt mô tả tư thế:

    irasutoya_style, the same character as in the reference images, {characters.json → prompt}, {action}, {emotion} face, full body, white background

    import torch
    from diffusers import Flux2KleinPipeline
    from PIL import Image

    pipe = Flux2KleinPipeline.from_pretrained(
        "black-forest-labs/FLUX.2-klein-4B", torch_dtype=torch.bfloat16
    ).to("cuda")
    pipe.load_lora_weights("loras/style.safetensors")

    refs = [Image.open(p) for p in character["reference"]]      # trước, nghiêng, sau
    image = pipe(prompt=prompt, image=refs, height=1024, width=1024,
                 num_inference_steps=4, guidance_scale=1.0).images[0]
    image.save("characters/001.png")

Đây là khung tham khảo. Tên lớp, tên tham số nhận ảnh tham chiếu và số bước cần đối chiếu với model card của klein trước khi dùng.

- Sinh 4-6 ảnh cho mỗi tư thế với seed khác nhau. Ảnh gốc là nơi nhân vật dễ lệch nhất, nên đây là chỗ đáng chi nhiều lần sinh.
- Ảnh gốc luôn sinh từ ảnh chuẩn, không lấy ảnh của phân cảnh trước làm mẫu, để sai lệch không cộng dồn.
- Cảnh có hai nhân vật: sinh từng người riêng rồi ghép ở bước 5.

### 3b. Kiểm tra ảnh gốc

Chi tiết ở mục [Chấm điểm độ ổn định](#cham-diem). Thứ tự áp dụng cho các ứng viên của một tư thế:

1.  Loại ảnh hỏng theo luật cứng: bị cắt cụt, quá nhỏ, nhiều mảnh rời.
2.  Loại ảnh giống một nhân vật khác trong dàn hơn nhân vật đúng.
3.  Loại ảnh không qua danh sách kiểm tra của model thị giác; mọi mục đều phải đúng.
4.  Trong số còn lại, chọn ảnh có độ giống với ảnh chuẩn cao nhất.

- Không ảnh nào đạt thì sinh thêm với seed khác, tối đa 4 lần, sau đó đánh dấu cho người xem.
- Một video chỉ có 10-25 ảnh gốc, nên đây là chỗ kiểm tra kỹ nhất.

### 3c. Khung biến thể

Áp dụng cho cảnh có `based_on` trỏ tới một cảnh khác. Lấy ảnh gốc của cảnh đó làm ảnh đầu vào và chỉ yêu cầu thay đổi:

    irasutoya_style, change the expression to {emotion}, {action}, keep the character, clothes, pose and white background unchanged

- Phần không được nhắc tới trong lệnh sẽ giữ nguyên, nên các khung trong một phân cảnh khớp nhau.
- Biến thể thừa hưởng nhận dạng từ ảnh gốc, chỉ cần kiểm tra nhanh lỗi hình.

### 4Tách nền

**Đầu vào:** `characters/*.png`

**Công cụ:** rembg

**Đầu ra:** `cutouts/*.png`, nền trong suốt

    from pathlib import Path
    from PIL import Image
    from rembg import remove

    for p in sorted(Path("characters").glob("*.png")):
        remove(Image.open(p)).save(Path("cutouts") / p.name)

Nét phẳng trên nền trắng tách rất sạch. Chỗ hay lỗi là chi tiết màu trắng sát mép (áo trắng, khói), nên lướt qua kết quả một lượt.

### 5Ghép cảnh

**Đầu vào:** `cutouts/`, `backgrounds/`, `location` và `position` của từng cảnh

**Công cụ:** Pillow; klein chế độ edit cho cảnh có tương tác

**Đầu ra:** `scenes/001.png` (ảnh xem trước, 1080×1920) và `scenes/001.json` (bố cục các lớp)

    from PIL import Image

    bg = Image.open("backgrounds/shop_inside.png").convert("RGBA").resize((1080, 1920))
    ch = Image.open("cutouts/001.png")
    ch.thumbnail((820, 1100))                      # nhân vật chiếm khoảng 3/4 chiều ngang
    x = (1080 - ch.width) // 2                     # position: center
    y = 1920 - ch.height - 260                     # đứng trên "mặt đất"
    bg.alpha_composite(ch, (x, y))
    bg.convert("RGB").save("scenes/001.png")

- Phần trên cùng của khung (khoảng 300px) dành cho tiêu đề, phần ngay dưới dành cho phụ đề, nên đặt nhân vật ở nửa dưới.
- Cảnh nhân vật phải chạm vào đồ vật trong nền: đưa ảnh nhân vật và ảnh nền vào klein edit kèm lệnh đặt nhân vật vào cảnh.

### 6Giọng đọc

**Đầu vào:** `text` và `speaker` của từng cảnh, mã giọng trong `characters.json`

**Công cụ:** VOICEVOX hoặc một dịch vụ TTS

**Đầu ra:** `audio/001.wav`, mỗi cảnh một file

- Mỗi câu một file riêng, để độ dài file quyết định thời lượng cảnh.
- Bỏ dấu ngoặc và ký hiệu khỏi câu trước khi gửi cho TTS; phụ đề vẫn giữ nguyên.
- Nghe lại toàn bộ một lượt: lỗi đọc sai tên riêng và ngắt nghỉ là phổ biến nhất.

### 7Dựng video

**Đầu vào:** `script.json`, `scenes/`, `audio/`, `music.mp3`

**Công cụ:** `build_video.py` (ffmpeg)

**Đầu ra:** `output.mp4`, 1080×1920, 30fps

- Mỗi cảnh dài bằng file giọng đọc cộng 0,15 giây nghỉ.
- Chuyển động lấy từ trường `motion`; phụ đề viền màu theo `speaker`; tiêu đề cố định ở trên suốt video.
- Bản hiện tại của script (v1) dựng từ ảnh đã ghép và chỉ có các kiểu chuyển động máy quay. Các kiểu di chuyển nhân vật, `alt_pose`, hiệu ứng và cảnh image-to-video cần bản v2 dựng từ các lớp tách rời; xem mục [Bàn giao](#ban-giao).
- Nhạc nền lặp lại và hạ âm lượng xuống 12% so với giọng đọc.
- Muốn dùng image-to-video cho vài cảnh: thay clip của cảnh đó trong `build_tmp/` trước bước nối.

Mã nguồn đầy đủ ở phần [Script dựng video](#script).

### 8Kiểm tra và đăng

**Đầu vào:** `output.mp4`

**Công cụ:** Mắt và tai người

**Đầu ra:** Video đã đăng, số liệu sau 48 giờ

- Nhân vật đúng người, đúng trang phục ở mọi cảnh.
- Phụ đề khớp lời đọc, không tràn ra ngoài khung, không che mặt nhân vật.
- Không có cảnh lỗi hình (thừa tay, mặt méo, viền trắng quanh nhân vật).
- Ba giây đầu đã nêu được tình huống.
- Cảnh hỏng thì sinh lại riêng cảnh đó rồi chạy lại bước 7.

## Script dựng video

Đã chạy thử với dữ liệu giả gồm 6 cảnh và đủ 6 kiểu chuyển động. Chưa thử với ảnh và giọng đọc thật của bạn.

    """Dựng video dọc từ ảnh cảnh + giọng đọc + kịch bản.

    Đầu vào (cùng thư mục dự án):
      script.json       kịch bản (xem ví dụ bên dưới)
      scenes/001.png    ảnh cảnh đã ghép, tỉ lệ 9:16 (nên 1080x1920 trở lên)
      audio/001.wav     giọng đọc của từng cảnh
      music.mp3         nhạc nền (không bắt buộc)
    Đầu ra:
      output.mp4        1080x1920, 30fps

    Chạy:  python build_video.py            (cần ffmpeg và ffprobe trong PATH)

    script.json:
    {
      "title": ["Dòng tiêu đề 1", "Dòng tiêu đề 2"],
      "font": "Noto Sans CJK JP",
      "speakers": {"narrator": "#4FC3F7", "boy": "#7CD992", "mother": "#F48FB1"},
      "scenes": [
        {"id": 1, "text": "Câu thoại", "speaker": "narrator", "motion": "zoom_in"}
      ]
    }
    motion: zoom_in | zoom_out | pan_left | pan_right | shake | none
    """
    import json
    import subprocess
    from pathlib import Path

    W, H, FPS = 1080, 1920, 30
    PAD = 0.15           # giây nghỉ sau mỗi câu
    MUSIC_VOLUME = 0.12  # nhạc nền so với giọng đọc
    TMP = Path("build_tmp")

    def run(*args):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *map(str, args)], check=True)

    def duration(path):
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                              "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
        return float(out.stdout.strip())

    def motion_filter(kind, frames):
        """Trả về chuỗi filter tạo chuyển động cho một ảnh tĩnh."""
        big = f"scale={W * 2}:{H * 2}:force_original_aspect_ratio=increase,crop={W * 2}:{H * 2}"
        centre = "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
        zp = lambda z, pos=centre: f"{big},zoompan=z='{z}':{pos}:d={frames}:s={W}x{H}:fps={FPS}"
        step = 0.12 / max(frames, 1)
        if kind == "zoom_in":
            return zp(f"1+{step}*on")
        if kind == "zoom_out":
            return zp(f"1.12-{step}*on")
        if kind in ("pan_left", "pan_right"):
            travel = f"(iw-iw/zoom)*on/{frames}"
            x = travel if kind == "pan_right" else f"(iw-iw/zoom)-{travel}"
            return zp("1.1", f"x='{x}':y='ih/2-(ih/zoom/2)'")
        if kind == "shake":
            return (f"{zp('1.06')},crop={W - 40}:{H - 40}:"
                    f"20+14*sin(2*PI*t*9):20+14*cos(2*PI*t*7),scale={W}:{H}")
        return zp("1")

    def ass_colour(hex_colour):
        r, g, b = hex_colour[1:3], hex_colour[3:5], hex_colour[5:7]
        return f"&H00{b}{g}{r}".upper()

    def ass_time(t):
        h, rem = divmod(t, 3600)
        m, s = divmod(rem, 60)
        return f"{int(h)}:{int(m):02d}:{s:05.2f}"

    def write_subtitles(script, timings, total, path):
        font = script.get("font", "Arial")
        lines = [
            "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 0", "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, "
            "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV",
            f"Style: Title,{font},92,&H0066D9FF,&H00000000,&H00000000,1,1,8,0,8,40,40,90",
        ]
        for name, colour in script["speakers"].items():
            lines.append(f"Style: {name},{font},72,&H00FFFFFF,{ass_colour(colour)},&H00000000,1,1,9,0,8,70,70,470")
        lines += ["", "[Events]", "Format: Layer, Start, End, Style, Text"]
        title = r"\N".join(script.get("title", []))
        if title:
            lines.append(f"Dialogue: 0,{ass_time(0)},{ass_time(total)},Title,{title}")
        for scene, (start, end) in zip(script["scenes"], timings):
            text = scene["text"].replace("\n", r"\N")
            lines.append(f"Dialogue: 1,{ass_time(start)},{ass_time(end)},{scene['speaker']},{text}")
        path.write_text("\n".join(lines), encoding="utf-8")

    def main():
        script = json.loads(Path("script.json").read_text(encoding="utf-8"))
        TMP.mkdir(exist_ok=True)
        clips, timings, clock = [], [], 0.0

        for scene in script["scenes"]:
            name = f"{scene['id']:03d}"
            audio = Path("audio") / f"{name}.wav"
            length = duration(audio) + PAD
            frames = round(length * FPS)
            clip = TMP / f"{name}.mp4"
            run("-i", Path("scenes") / f"{name}.png", "-i", audio,
                "-vf", motion_filter(scene.get("motion", "zoom_in"), frames) + ",format=yuv420p",
                "-af", f"apad=whole_dur={frames / FPS}", "-frames:v", frames, "-r", FPS,
                "-c:v", "libx264", "-preset", "fast", "-crf", 18, "-c:a", "aac", "-ar", 48000, "-ac", 2, clip)
            clips.append(clip)
            timings.append((clock, clock + frames / FPS))
            clock += frames / FPS
            print(f"cảnh {name}: {length:.2f}s")

        concat = TMP / "concat.txt"
        concat.write_text("".join(f"file '{c.name}'\n" for c in clips), encoding="utf-8")
        joined = TMP / "joined.mp4"
        run("-f", "concat", "-safe", 0, "-i", concat, "-c", "copy", joined)

        subs = TMP / "subs.ass"
        write_subtitles(script, timings, clock, subs)
        video_filter = f"ass={subs.as_posix()}"
        common = ["-c:v", "libx264", "-preset", "medium", "-crf", 20, "-c:a", "aac", "-b:a", "192k",
                  "-movflags", "+faststart", "output.mp4"]
        if Path("music.mp3").exists():
            run("-i", joined, "-stream_loop", -1, "-i", "music.mp3", "-filter_complex",
                f"[0:v]{video_filter}[v];[1:a]volume={MUSIC_VOLUME}[m];"
                f"[0:a][m]amix=inputs=2:duration=first:normalize=0[a]",
                "-map", "[v]", "-map", "[a]", "-t", clock, *common)
        else:
            run("-i", joined, "-vf", video_filter, *common)
        print(f"Xong: output.mp4 ({clock:.1f}s, {len(clips)} cảnh)")

    if __name__ == "__main__":
        main()

Chạy trong thư mục của video: `python ../../build_video.py`. File tạm nằm trong `build_tmp/`, xóa được sau khi xong.

## Chi phí và rủi ro

| Khoản                            | Ước tính                                                      | Ghi chú                                                                                                |
|----------------------------------|---------------------------------------------------------------|--------------------------------------------------------------------------------------------------------|
| Train một lần style LoRA         | 2-5 USD                                                       | 1-3 giờ trên `ml.g5.2xlarge`; thời gian là ước lượng, chưa đo                                          |
| Cả quá trình thử nghiệm train    | 10-30 USD                                                     | Thường cần 3-6 lần chạy                                                                                |
| Sinh ảnh cho một video           | Không có phí theo ảnh nếu tự chạy GPU; dưới 5 USD nếu gọi API | 250-350 ảnh. Phí theo ảnh chỉ có khi thuê API của BFL chạy hộ, từ 0,014 USD mỗi megapixel cho klein 4B |
| Endpoint inference chạy liên tục | Trên 1.100 USD mỗi tháng                                      | Nên tránh: chạy theo đợt rồi tắt                                                                       |

**Rủi ro lớn nhất không nằm ở kỹ thuật.** Làm tay một video trọn vẹn bằng công cụ có sẵn trước khi train và viết code. Nếu video đó không giữ được người xem, vấn đề nằm ở kịch bản, và LoRA hay pipeline không sửa được chuyện đó.

### Các lưu ý khác

- **Chính sách kiếm tiền của YouTube.** Chính sách "inauthentic content" loại nội dung sản xuất hàng loạt theo khuôn mẫu khỏi chương trình kiếm tiền, trong khi vẫn cho phép dùng công cụ AI để hỗ trợ kể chuyện. Pipeline này nằm sát ranh giới đó. Đọc trang trợ giúp chính thức của YouTube trước khi đầu tư nhiều; giữ khâu viết và duyệt kịch bản cho người; không đăng số lượng lớn chỉ vì pipeline làm được.
- **Truyện phải là của mình.** Học công thức từ kênh khác, không dùng lại cốt truyện hay lời thoại của họ.
- **Độ phân giải lúc train.** Lần train hiện tại chạy ở khoảng 512px. Với nét phẳng thì nhiều khả năng vẫn ổn khi sinh ở 1024px. Chỉ train lại ở 768 hoặc 1024 nếu ảnh thử có mép nhòe hoặc bố cục lạ, và khi đó chỉ đổi độ phân giải.
- **Ghi lại nguồn gốc mỗi ảnh:** prompt, seed, tên checkpoint LoRA, ảnh tham chiếu đã dùng.
- **Khóa phiên bản thư viện** vào `requirements.txt` ngay khi mọi thứ chạy được; diffusers cài từ nhánh chính thay đổi hằng ngày.
- **`.gitignore`** cho khóa API, file `.safetensors`, dataset và thư mục `videos/`.
- **Giấy phép giọng đọc và nhạc.** Mỗi giọng VOICEVOX có điều khoản ghi nguồn riêng; nhạc nền cần giấy phép cho video kiếm tiền.
- **Trần chi phí cho API:** số lần thử tối đa cho mỗi cảnh và một trần tổng cho mỗi video, áp dụng cho giám khảo thị giác, TTS và image-to-video.

### Thứ tự làm hợp lý

1.  Chốt nguồn nét vẽ và thiết kế 3-5 nhân vật.
2.  Làm tay video đầu tiên.
3.  Lọc dataset, viết caption, train style LoRA.
4.  Viết các script nối bước 2 đến 7, chạy thử với một kịch bản.
5.  Đăng 3-5 video, đọc số liệu, rồi mới tính tới character LoRA và image-to-video.

## Bàn giao để triển khai

Trạng thái hiện tại, thứ tự việc cần làm, và điều kiện hoàn thành của từng việc. Phạm vi là chặng 1 và 2 ở local; chưa làm phần AWS.

### Đã có

| Thứ                              | Trạng thái                                                                                                                                                                              |
|----------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Style LoRA                       | Đã train xong trên Kaggle T4 bằng ai-toolkit 0.13.23, base FLUX.2 klein 4B, rank 16, 1500 bước, lưu mỗi 250 bước, 178 ảnh theo log train, trigger `irasutoya_style`. Đã chọn checkpoint 750 bước sau khi so sánh sáu mốc ở 1024px; file này được lưu thành loras/style.safetensors. |
| `build_video.py` (v1)            | Đã chạy thử với 6 cảnh giả: ghép ảnh đã dựng sẵn với giọng đọc, 6 kiểu chuyển động máy quay, phụ đề ASS theo người nói, tiêu đề, nhạc nền. Chưa thử với dữ liệu thật.                   |
| `download_irasutoya.py`          | Đã viết, chưa chạy thử trong môi trường viết ra nó.                                                                                                                                     |
| Các đoạn code trong tài liệu này | Là khung tham khảo, chưa chạy trên GPU.                                                                                                                                                 |

### Cần xác minh trước khi viết code

- API của diffusers cho FLUX.2 klein: tên lớp pipeline, tham số nhận ảnh tham chiếu, cách gọi chế độ sửa ảnh, số bước và guidance của bản distilled. Đối chiếu với model card và tài liệu diffusers hiện hành.
- `load_lora_weights` có nhận file do ai-toolkit xuất ra không. Tên khóa trong file có dạng `diffusion_model.double_blocks.N...lora_A.weight`.
- Gắn đồng thời hai LoRA (style và character) và đặt trọng số cho từng cái.
- Điều khoản của Irasutoya về việc dùng tranh để train vẫn chưa có câu trả lời rõ; cần hỏi trước khi dùng LoRA cho kênh kiếm tiền.

### Thứ tự triển khai

| \#  | Việc                                                                                                                                                                                                                                                                                               | Hoàn thành khi                                                                                                  |
|-----|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|
| 1   | Khung dự án theo cấu trúc thư mục ở phần Chuẩn bị; ba file cấu hình mẫu; hàm kiểm tra `script.json` theo schema (giá trị hợp lệ của `motion`, `effect`; `based_on` chỉ trỏ tới cảnh gốc; tên nhân vật và bối cảnh có trong cấu hình)                                                               | Kịch bản mẫu hợp lệ thì qua; kịch bản sai thì báo đúng dòng sai                                                 |
| 2   | Một module sinh ảnh dùng chung: sinh từ chữ, sinh có ảnh tham chiếu, sửa ảnh; nạp và tháo LoRA; nạp model một lần cho cả lô; ghi kèm mỗi ảnh một dòng nguồn gốc (prompt, seed, checkpoint LoRA, ảnh tham chiếu)                                                                                    | Ba hàm chạy được trên GPU với checkpoint LoRA đã chọn                                                           |
| 3   | Một module chấm điểm theo mục Chấm điểm độ ổn định: luật cứng (cắt cụt, quá nhỏ, nhiều mảnh), độ giống DINOv2 với ảnh chuẩn, khoảng cách với các nhân vật khác trong dàn, và danh sách kiểm tra có hoặc không do model thị giác trả về dạng JSON; kèm một lệnh đo để tìm ngưỡng từ ảnh đã gắn nhãn | Chấm được một thư mục ảnh và xuất bảng điểm; ngưỡng đã được đo trên khoảng 30 ảnh gắn nhãn tay cho mỗi nhân vật |
| 4   | `00_make_cast.py`: sinh ứng viên mặt trước, lọc, chấm, thử độ bền bằng vài tư thế, sinh góc nghiêng và sau lưng, xuất tấm tổng hợp chờ duyệt                                                                                                                                                       | Một lệnh cho ra `config/refs/` và tấm tổng hợp của từng nhân vật                                                |
| 5   | `02_backgrounds.py` và `03_characters.py` (3a ảnh gốc từ ảnh chuẩn, 3b chấm và sinh lại, 3c biến thể theo `based_on` và `alt_pose`)                                                                                                                                                                | Chạy trên kịch bản mẫu, bỏ qua ảnh đã có, xuất danh sách cảnh cần người xem                                     |
| 6   | `04_cutouts.py`, `05_compose.py` (xuất ảnh xem trước và file bố cục các lớp), `06_voice.py`                                                                                                                                                                                                        | Mỗi cảnh có ảnh xem trước, file bố cục và file giọng đọc                                                        |
| 7   | `07_build.py` (v2): dựng từ các lớp tách rời; thêm các kiểu di chuyển nhân vật, `alt_pose`, lớp hiệu ứng, và dùng `clips/NNN.mp4` cho cảnh `i2v`. Giữ cách xử lý phụ đề, tiêu đề, nhạc của v1.                                                                                                     | Video thử có đủ một cảnh cho mỗi kiểu chuyển động và mỗi loại hiệu ứng                                          |
| 8   | `run_local.py` và một báo cáo cuối: thời gian từng bước, số ảnh sinh lại, các cảnh bị đánh dấu                                                                                                                                                                                                     | Một lệnh chạy từ `script.json` ra `output.mp4`                                                                  |

### Quy ước chung cho mọi script

- Mỗi bước là một file chạy độc lập, tham số duy nhất là đường dẫn thư mục video.
- Chỉ đọc và ghi file trong thư mục đó và trong `config/`, `loras/`, `library/`; không bước nào gọi hàm của bước khác, trừ hai module dùng chung ở việc 2 và 3.
- Kết quả đã có thì bỏ qua; có cờ để ép chạy lại một cảnh.
- Khóa API và đường dẫn model đọc từ biến môi trường.
- Có `.gitignore` cho khóa, model, dataset và `videos/`; phiên bản thư viện được ghi cố định trong `requirements.txt`.
- Mọi vòng tự sinh lại và mọi lệnh gọi API trả phí đều có số lần tối đa.
- Ưu tiên code ngắn, dễ đọc; không thêm lớp trừu tượng khi chưa cần.

### Để sau, không làm trong đợt này

- Hạ tầng AWS.
- Character LoRA, cho tới khi có nhân vật thỏa điều kiện ở mục Giữ nhân vật ổn định.
- Phân tích video tham khảo để dựng thư viện ví dụ cho bước "đạo diễn dựng": tách cảnh, đo vị trí và độ to nhân vật, đọc phụ đề, gắn nhãn cảm xúc và hiệu ứng, rồi cho Claude dùng các cảnh tương tự làm ví dụ khi chọn loại cảnh, chuyển động và hiệu ứng. Chỉ giữ số đo, không giữ video.
- Fine-tune model dựng.

Thông số có ghi nguồn BFL lấy từ tài liệu của Black Forest Labs; giá SageMaker và API là giá tra cứu tại thời điểm viết, cần kiểm tra lại trước khi dùng.
