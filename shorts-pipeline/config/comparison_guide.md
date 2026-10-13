# Video phân tích Nhật Bản với nước khác

Các quy tắc này thay cho quy tắc tiểu phẩm ngắn. Mục tiêu 110–130 giây, khoảng 2 phút.
28–36 cảnh, mỗi cảnh một ý hoàn chỉnh, đa số 18–30 ký tự tiếng Nhật, tổng khoảng 600–700 ký tự.
Không chia một câu thành nhiều cảnh chỉ để tăng số cảnh. Không kéo dài bằng khoảng lặng, phản ứng lặp hoặc đọc chậm.

## Nội dung và nhịp

- 0–5 giây: mở bằng nghịch lý hoặc câu hỏi ảnh hưởng đến lựa chọn thật của người xem. Đưa chi tiết hấp dẫn nhất lên đầu;
  không chào hỏi, không thách đấu chung chung, không hứa nội dung mà phần sau không trả lời.
- 5–15 giây: nêu đúng phạm vi: sản phẩm/dịch vụ nào, điều kiện và tiêu chí nào; cho người xem biết câu trả lời sẽ giúp gì.
- 15–85 giây: 3 luận điểm. Mỗi luận điểm có kết luận ngắn → dẫn chứng → giải thích nguyên nhân → tác động thực tế.
  Giữa các luận điểm có câu hỏi chuyển ý tự nhiên; mỗi 15–25 giây đưa một phát hiện hoặc ví dụ mới.
- 85–110 giây: phản biện mạnh nhất và giới hạn của so sánh, khi nào nước kia có lợi thế, điều gì làm kết quả thay đổi.
- 110–130 giây: trả lời câu hỏi mở đầu; kết luận theo nhu cầu người xem và một câu hỏi bình luận cụ thể.

Lời kể narrator chiếm khoảng 80%; hai linh vật chỉ xen một câu hỏi hoặc phản biện ngắn ở vài mốc.
Nhật dùng mascot_jpn đầu cờ tròn trắng với hình tròn đỏ; nước khác dùng linh vật có sẵn.
Không mặc định bên thắng, không bắt buộc Nhật thắng mọi tiêu chí. Giải thích lợi thế Nhật bằng bằng chứng liên quan.
Số liệu chỉ lấy từ đề tài hoặc SỐ LIỆU THẬT đã cung cấp, đúng đơn vị/năm/phạm vi. Không có nguồn phù hợp thì dùng
ví dụ định tính có điều kiện, không tự bịa phần trăm, năm sử dụng hoặc tuyên bố đại diện cả quốc gia.
Không dùng chỉ số ngoài chủ đề để kết luận: ví dụ tử vong giao thông đường bộ không chứng minh độ an toàn đường sắt.
Ảnh kho chỉ minh họa, không dùng ảnh để chứng minh hãng, địa điểm hoặc một sự cố cụ thể khi chưa xác minh.
Không miệt thị dân tộc, không chính trị/chiến tranh/lãnh thổ. Tên hãng phải đúng nước và nhận xét phải có căn cứ.

## Hình và tiếng

Mỗi cảnh có một tiêu điểm: một linh vật, một hình minh họa, một ảnh thật hoặc một bảng so sánh.
Không hai linh vật đứng hai bên mọi cảnh. Không chữ tượng thanh, sticker, pháo sáng, rung, giật zoom hoặc nhạc đối đầu.
Máy đứng yên khi đọc bảng; chỉ zoom nhẹ ở mở đầu/phát hiện. Chuyển cảnh cut. Không punchline, alt_pose hoặc sfx dồn dập.
Tối đa 3 bảng số liệu, mỗi bảng một chỉ số. Không vương miện, không điểm thắng thua; số liệu chưa đủ thì bỏ bảng.
Bảng dùng compare: {"label": "tên chỉ số", "japan": "giá trị kèm đơn vị", "other": "giá trị kèm đơn vị",
"source": "nguồn/năm ngắn gọn nếu đã được cung cấp", "country": "ISO3"}.
source chỉ dùng nguồn đã có, không tự đặt. Phải giải thích ý nghĩa số liệu trong lời đọc.
2–4 cảnh photo nếu có ích: {"query": "2–5 từ khóa tiếng Anh đúng chủ thể", "caption": "chú thích Nhật ngắn"}.
Không photo và compare cùng cảnh. Không full, motion_level hoặc i2v_prompt.

Giữ schema JSON chuẩn: title gồm 2 dòng ngắn (dòng đầu câu hỏi/chủ đề, dòng sau phạm vi), genre, speakers, voices,
scenes. Mỗi cảnh có id, beat, text, speaker, tone, location, characters, shot, action, emotion, layers.
beat: hook/setup/development/reveal/ending. tone chủ yếu narration/calm/normal; phản biện không cần hét.
Mọi cảnh có lời đọc. shot chủ yếu half, xen close khi cần; action và emotion mô tả tiếng Anh, emotion tiết chế.
Lớp nhân vật: {"id": "mascot_jpn", "image": "cutouts/001.png", "anim": "none"} nếu cảnh chỉ có một nhân vật;
nhiều nhân vật dùng tên cutouts/001_mascot_jpn.png tương ứng. characters khai đúng nhân vật cần sinh, tối đa 2.
Ảnh/bảng: vẫn có thể khai 1 linh vật làm nguồn cảnh, renderer sẽ ưu tiên ảnh/bảng và ẩn linh vật.
Không ghi chữ cần đọc vào ảnh AI; chữ và số liệu do renderer vẽ.
Không để nhân vật cầm bàn, ghế, cửa, quầy: đồ cố định nằm trong bối cảnh. Dùng lại bối cảnh, nhân vật có sẵn;
nhân vật mới cần prompt tiếng Anh, voice, colour, bối cảnh mới cần mô tả tiếng Anh trong new_locations.
