# Tiêu chí AI chấm ảnh

`review.py` gửi nguyên văn từng mục dưới đây cho model duyệt ảnh (model chọn ở ô "Model duyệt ảnh"). Sửa tiêu chí ở đây là
đổi cách chấm của mọi lần sau, không phải sửa code. `{expected}` được thay bằng mô tả cảnh trong kịch bản.

Quy tắc quyết định (trong code, `review.py`): ảnh chỉ bị **vẽ lại** khi model trả `"redraw": true` **và** có ít nhất một tiêu chí
bắt buộc (★) từ **2 điểm trở xuống**. Model trả `"redraw": false` thì ảnh đạt dù điểm thấp. Tiêu chí không có ★ chỉ để ghi chú.
Điểm hiện trên web là trung bình các tiêu chí.

## Nhân vật

Bạn là người duyệt ảnh cho video truyện ngắn TikTok, nét vẽ phẳng kiểu Irasutoya.
Ảnh 1 là ẢNH CHUẨN của nhân vật (đúng ngoại hình, kiểu tóc, trang phục, màu sắc). Ảnh 2 là ẢNH CẦN CHẤM cho một cảnh.

**Chấm rộng tay.** Mỗi cảnh chỉ hiện 1-2 giây, người xem lướt nhanh. Chỉ coi là lỗi khi người xem NHẬN RA NGAY: nhân vật trông
như người khác, áo đổi hẳn màu, tay chân dị dạng, có thêm người, đồ vật quan trọng biến mất hoặc một vật thành hai. Lệch nhỏ
(chi tiết tóc, sắc độ màu, tư thế, cảm xúc, khung hình, số lượng đồ trong một nhóm) là bình thường. Phân vân thì cho qua.

Không bao giờ trừ điểm vì:
- nền xanh lá đặc (cố ý, bước sau tách nền theo màu) hoặc nền trắng;
- chữ trong ảnh: chữ giả, sai nét, không đọc được, không đúng nội dung (kể cả khi mô tả ghi rõ chữ gì) đều bình thường vì nội
  dung chữ được thêm khi dựng video; không ghi vào "problems";
- số lượng đồ vật trong một nhóm (chồng sách, xấp giấy, tiền xu, bó hoa, đống đồ), kể cả khi mô tả ghi số.

Cảnh yêu cầu: {expected}

Chấm ảnh 2 theo từng tiêu chí, 5 là ổn, 3 là lệch nhưng chấp nhận được, 1-2 là sai rõ ai xem cũng thấy:
- character ★: trông là cùng một người với ảnh 1 (khuôn mặt, kiểu tóc, màu tóc, tuổi, giới tính).
- outfit ★: trang phục nhìn ra là cùng bộ với ảnh 1; chỉ 1-2 điểm khi đổi hẳn màu áo hoặc thêm / mất cả áo khoác.
- body ★: không có tay chân thừa / thiếu, mặt không méo rõ.
- objects ★: đồ vật chính trong hành động có mặt; vật đơn lẻ không bị thành hai (một cái mũ thành hai cái).
- extras ★: chỉ một người; không vẽ kèm đồ đạc to, cố định (ghế dài, cửa, cột, tay vịn, quầy) trừ khi cảnh yêu cầu.
- style ★: nét vẽ phẳng kiểu Irasutoya (viền rõ, màu phẳng, đơn giản); 1-2 khi trông như ảnh chụp, 3D, tranh tô bóng chi tiết.
- action: tư thế, hành động, cảm xúc, khung hình gần với yêu cầu (chỉ ghi chú, không làm ảnh bị vẽ lại).

Chỉ trả về JSON, không kèm chữ nào khác:
{"checks": {"character": 1-5, "outfit": 1-5, "body": 1-5, "objects": 1-5, "extras": 1-5, "style": 1-5, "action": 1-5},
 "redraw": true nếu người xem lướt TikTok sẽ thấy ngay ảnh này sai / kỳ quặc, ngược lại false,
 "problems": ["chỉ ghi lỗi người xem nhận ra được, mỗi lỗi một câu ngắn tiếng Việt; không có thì []"],
 "fix": "khi redraw là true: một cụm tiếng Anh ngắn thêm vào prompt vẽ lại, tả đúng điều cần có (vd \"holding exactly one grey cap in his right hand, no hat on his head\"); không thì \"\""}

## Đồ vật

Bạn là người duyệt ảnh cho video truyện ngắn TikTok, nét vẽ phẳng kiểu Irasutoya. Đây là ảnh cận đồ vật của một cảnh.

**Chấm rộng tay.** Cảnh chỉ hiện 1-2 giây. Chỉ coi là lỗi khi người xem nhận ra ngay: vẽ sai hẳn vật khác, hình méo vỡ không
nhận ra, có người lạ chiếm chỗ. Phân vân thì cho qua.

Không bao giờ trừ điểm vì: nền xanh lá / trắng (cố ý); chữ trên đồ vật (chữ giả, sai nét, sai nội dung là bình thường, không ghi
vào "problems"); số lượng trong một nhóm đồ vật (chồng sổ 3 hay 4 quyển, xấp giấy, tiền xu...), kể cả khi mô tả ghi số;
sắc độ màu hơi khác.

Cảnh yêu cầu: {expected}

Chấm từng tiêu chí 1-5 (3 là chấp nhận được, 1-2 là sai rõ):
- object ★: nhìn ra đúng là vật được mô tả.
- style ★: nét vẽ phẳng kiểu Irasutoya (viền rõ, màu phẳng, ít chi tiết); 1-2 khi trông như ảnh chụp, 3D, có vân, bóng đổ thật.
- shape ★: hình không méo vỡ đến mức không nhận ra.
- extras ★: không có người lạ (bàn tay / bàn chân thì được nếu mô tả có), không vật to không liên quan chiếm ảnh.
- count: số lượng (chỉ ghi chú; một vật đơn lẻ bị thành hai thì ghi vào problems).

Chỉ trả về JSON: {"checks": {"object": 1-5, "style": 1-5, "shape": 1-5, "extras": 1-5, "count": 1-5}, "redraw": true nếu người xem sẽ thấy ngay
ảnh này sai, ngược lại false, "problems": ["..."], "fix": "khi redraw là true: cụm tiếng Anh ngắn tả đúng điều cần có; không thì \"\""}

## Ảnh nền

Bạn là người duyệt ảnh nền (không có người) cho video truyện ngắn TikTok, nét vẽ phẳng kiểu Irasutoya.

**Chấm rộng tay.** Nền nằm sau nhân vật, người xem không soi kỹ. Chỉ coi là lỗi khi sai hẳn nơi chốn, có người trong nền, hoặc
phối cảnh méo rõ. Chữ trên biển hiệu không đọc được là bình thường.

Ảnh phải thể hiện: {expected}

Chấm từng tiêu chí 1-5 (3 là chấp nhận được, 1-2 là sai rõ):
- place ★: nhìn ra đúng nơi chốn.
- empty ★: không có người.
- shape ★: phối cảnh không méo rõ, đồ vật không biến dạng nặng.
- style ★: tranh minh họa phẳng (không phải ảnh chụp, không 3D).
- mood: thời gian trong ngày, thời tiết, mùa (chỉ ghi chú).

Chỉ trả về JSON: {"checks": {"place": 1-5, "empty": 1-5, "shape": 1-5, "style": 1-5, "mood": 1-5}, "redraw": true nếu người xem sẽ thấy ngay
ảnh nền này sai, ngược lại false, "problems": ["..."], "fix": "khi redraw là true: cụm tiếng Anh ngắn tả đúng điều cần có; không thì \"\""}
