# Quy tắc viết kịch bản

File này mở rộng schema `script.json`. `steps/01_script.py` gửi nguyên văn file này cho model AI mỗi lần viết kịch bản
(kể cả khi tạo video từ trang web: đề tài người dùng nhập được viết thành kịch bản theo đúng các quy tắc dưới đây).
Sửa quy tắc ở đây là đổi cách viết của mọi kịch bản sau, không phải sửa code.
Thông số kỹ thuật đi kèm (prompt của từng khung hình, cỡ, vị trí) nằm ở mục `[shots]` của `config/settings.toml`.

**Nguyên tắc chung: mỗi video phải trông khác các video trước.** Khác về thể loại, nhân vật, bối cảnh, thời gian trong ngày,
thời tiết, khung hình và chuyển động. Phần "Gần đây đã dùng" trong yêu cầu cho biết các video trước đã dùng gì: tránh lặp lại.

## 0. Thể loại, góc kể, cấu trúc

Đề tài người dùng nhập có thể chỉ là một câu ("bố và chiếc xe đạp cũ") hoặc cả câu chuyện dài. Câu ngắn thì tự phát triển
thành truyện đầy đủ; truyện dài thì giữ đúng các chi tiết, nhân vật, diễn biến người dùng đã viết, chỉ chia cảnh và chuyển thành lời Nhật.

**Chọn thể loại hợp với đề tài, không phải lúc nào cũng "gia đình cảm động":**

| Thể loại | Cảm giác | Cách kết |
|---|---|---|
| **2ch感動スレ** (mặc định cho đề tài cảm động) | ấm, rưng rưng | bí mật cảm động hé lộ → nhảy thời gian → kết có hậu |
| Cảm động gia đình | ấm, rưng rưng | twist tình thương bị giấu |
| Hài, đời thường | nhẹ, buồn cười | cú lật hài, câu kết dí dỏm |
| Bí ẩn, hồi hộp | tò mò, căng | lời giải bất ngờ |
| Trả thù nhẹ, công lý (スカッと) | ức chế rồi hả hê | kẻ xấu bị lật mặt |
| Tình yêu, thanh xuân | rung động, tiếc nuối | lời tỏ tình hoặc lời chia tay |
| Công sở, xã hội | áp lực, lựa chọn | quyết định của nhân vật, câu hỏi cho người xem |
| Bài học, ngụ ngôn | suy ngẫm | câu chốt ngắn đáng nhớ |

**Mẫu 2ch感動スレ** (theo video mẫu 950万再生 "缶チューハイと絆"; dùng khi đề tài cảm động, đời thường):
1. Người kể "俺/私" ngôi thứ nhất, nghề / vai cụ thể (nhân viên cửa hàng tiện lợi, tài xế, y tá...), bối cảnh đời thường.
2. **Mâu thuẫn trong 2 giây đầu**: một hành động lạ, khó xử, trái quy tắc (nữ sinh cấp 2 mua rượu). Người xem tự hỏi "rồi sao?".
3. Người kể phản ứng theo lẽ thường (từ chối, nghi ngờ, bực) → nhân vật kia phản ứng bất ngờ (khóc, năn nỉ).
4. **Bí mật cảm động** được hé lộ qua lời thoại (bố vừa mất, món đồ là kỷ niệm của gia đình) + cảnh hồi tưởng (`sepia`).
5. Người kể làm một việc tử tế nhỏ (mua giúp, nói dối thiện ý).
6. **Nhảy thời gian** ("あれから10年" với nền `mood_time_skip`) → nhân vật quay lại, trưởng thành, cảm ơn.
7. Kết bằng **món đồ biểu tượng** xuất hiện từ đầu (lon chuhai) và một câu nhẹ, đọng lại; không giảng đạo lý dài.
Tiêu đề 2 dòng: dòng 1 tên series ngắn gây tò mò (vd 「感動の迷言集」, 「泣ける実話」), dòng 2 nội dung (「〜缶チューハイと絆〜」).

**Đổi góc kể:** ngôi thứ nhất (`narrator` là "tôi"), ngôi thứ ba (người kể đứng ngoài), hoặc gần như toàn lời thoại (ít lời kể).
Lời kể có thể dùng giọng của chính nhân vật chính (đặt `speaker` là tên nhân vật đó).

**Cấu trúc gợi ý** (đổi được theo thể loại): móc câu → 2-3 nấc phát triển, mỗi nấc một chi tiết mới → twist hoặc cao trào → câu kết.
**50-60 cảnh, video 80-100 giây (1 phút 20 đến 1 phút 40), bắt buộc** (giọng đọc đã tăng tốc 1,2 lần). Mỗi cảnh vẫn một câu
ngắn đọc 1-1,5 giây (khoảng 6-14 ký tự tiếng Nhật); **video dài hơn nhờ nhiều cảnh hơn, không nhờ câu dài hơn**. Tổng lời
khoảng 550-700 ký tự (video 003: 58 cảnh, ~700 ký tự ra 114 giây là hơi dài). Để đủ độ dài mà không lan man: câu chuyện có **3-4 nấc** (mỗi nấc 12-18 cảnh, một chi tiết mới), thêm
cảnh phản ứng, cảnh chèn đồ vật, cảnh hồi tưởng, cảnh nền cảm xúc; một câu dài thì tách thành 2-3 cảnh liền nhau với hình
khác nhau (đổi `shot`, nhân vật nói / nhân vật nghe, đồ vật). Không thêm câu thừa không đẩy truyện.

## 0b. Nhân vật và bối cảnh: dùng lại hoặc tạo mới

Danh sách nhân vật và bối cảnh có sẵn được gửi kèm. **Dùng lại khi hợp, tạo mới khi câu chuyện cần** — không ép câu chuyện
vào nhân vật và bối cảnh cũ. Thứ tạo mới được lưu lại cho các video sau dùng tiếp.

**Nhân vật mới** (`new_characters` trong `script.json`):
```json
"new_characters": {
  "grandpa_fisher": {"prompt": "japanese man in his seventies, white crew cut, tanned skin, navy fisherman jacket, rubber boots",
                     "voice": "old_man", "colour": "#90A4AE"}
}
```
- Tên: chữ thường không dấu, nối bằng `_`, nói rõ vai (`grandpa_fisher`, `teacher_young`, `rival_girl`). Không trùng tên có sẵn.
- `prompt` tiếng Anh, chỉ tả ngoại hình cố định: tuổi, giới tính, kiểu và màu tóc, **từng món trang phục kèm màu và họa tiết**
  (vd `olive green bomber jacket, black hoodie, beige chino pants, white sneakers`), phụ kiện luôn mang theo (balo, kính, mũ).
  Không tả hành động, cảm xúc, bối cảnh. Trang phục này giữ nguyên suốt video: `action` không nhắc tới quần áo khác, không đổi màu. Mỗi nhân vật phải **khác hẳn** nhân vật khác trong cùng video (màu áo, kiểu tóc, vóc dáng)
  để người xem nhận ra ngay.
- `voice`: `man`, `woman`, `old_man`, `old_woman`, `boy`, `girl`, `young_man`, `young_woman`.
- `colour`: màu viền phụ đề, khác màu các nhân vật khác trong video.
- Đa dạng: đổi tuổi (trẻ con, học sinh, người già), nghề (bác sĩ, đầu bếp, tài xế, giáo viên, nông dân), vóc dáng, phong cách.
  Không phải video nào cũng là bố, mẹ, "tôi".

**Bối cảnh mới** (`new_locations`):
```json
"new_locations": {
  "seaside_town_morning": "a small japanese fishing port in the early morning, boats, blue sea, seagulls, soft sunlight"
}
```
- Tên: không dấu, nối bằng `_`, có thời điểm hoặc thời tiết nếu quan trọng (`school_rooftop_sunset`, `street_rain_night`).
- Mô tả tiếng Anh: nơi chốn, **thời gian trong ngày, thời tiết, mùa**, 3-5 đồ vật đặc trưng, màu chủ đạo. Không có người.
  Không cần ghi phong cách vẽ (code tự thêm).
- Cùng một nơi khác thời điểm là bối cảnh khác (`kitchen_morning` khác `kitchen` ban đêm): dùng để thể hiện thời gian trôi.

**Nền cảm xúc** (có sẵn, dùng lại được, không cần khai `new_locations`): dùng cho khoảnh khắc cảm xúc thay vì nơi chốn thật,
như video mẫu (nền xoáy tối khi khổ cực, đồng hồ khi "10年後", hoa anh đào khi tốt nghiệp):
`mood_dark_swirl` khổ cực, tuyệt vọng · `mood_time_skip` nhảy thời gian ("あれから10年", "半年後") · `mood_sakura` tốt nghiệp,
khởi đầu mới · `mood_warm_memory` kỷ niệm đẹp, hồi tưởng ấm · `mood_happy_sparkle` vui, bất ngờ tốt · `mood_shock` sốc ·
`mood_rain_sad` buồn, cô đơn · `mood_night_stars` lặng lẽ suy nghĩ. Mỗi video dùng 1-3 nền cảm xúc ở các điểm then chốt.

**Bối cảnh trong một video:**
- Ít nhất **6 bối cảnh khác nhau** (tính cả nền cảm xúc `mood_*`, tối đa 3 nền cảm xúc), trong đó ít nhất **1 ngoài trời**.
  Không quá 30% số cảnh ở cùng một bối cảnh.
- Đổi **thời gian trong ngày** theo câu chuyện: sáng, trưa, hoàng hôn, đêm. Không để cả video đều là ban đêm trong nhà.
- Dùng thời tiết và mùa để tạo không khí: mưa cho đoạn buồn, tuyết, hoa anh đào, lá đỏ mùa thu, nắng hè.
- Gợi ý nơi chốn ít dùng: sân thượng trường, cửa hàng tiện lợi, quán ramen, bến xe buýt, công viên, bãi biển, đền thờ,
  ga tàu nông thôn, bệnh viện, siêu thị, xe buýt, phòng thay đồ, sân bóng, nhà kho, cánh đồng lúa, phố mua sắm, sân bay.
- Mỗi bối cảnh dùng ở ít nhất 2 cảnh (đỡ tốn ảnh); bối cảnh mới chỉ tạo khi thật sự dùng.

## 1. Đồ vật: vẽ luôn trong ảnh, không ghép

**Chỉ vẽ kèm nhân vật thứ cầm nắm, mang trên người được.** Đồ đạc cố định và thứ không cầm được (ghế, ghế dài, tay vịn treo,
cột, cửa, cửa sổ, tường, quầy, bàn, giường, xe, cây, tòa nhà) thuộc về **ảnh nền**: tả trong bối cảnh (`location` hoặc
`new_locations`), không viết vào `action`. Ảnh nhân vật vẽ kèm ghế hay cửa sẽ lệch màu, lệch phối cảnh với nền (video 008:
ghế tím trên tàu ghế xanh, tay vịn lơ lửng, khung cửa sổ trắng trống).
- Chỉ vào thứ không cầm được: `"pointing toward the right with one hand"` (cánh cửa nằm sẵn trong nền), không viết "pointing at the door".
- Nhân vật **ngồi**: dùng `shot` `half` hoặc `close` (cắt ngang hông, không thấy ghế), `action` chỉ tả thân trên
  (`"seated, hands resting on knees"`). Cần thấy cả người ngồi thì ngồi bệt trên sàn, không có ghế.
- Nắm tay vịn, dựa tường, mở cửa: đổi sang tư thế không cần đồ đạc (`"swaying, one hand raised above his head as if holding a strap"`)
  hoặc dùng cảnh chèn đồ vật (`object`) cho chi tiết đó.

**Đồ cầm tay: đếm rõ, nói rõ tay nào, nói rõ thứ không có** (model hay vẽ nhân đôi đồ vật):
- `"holding one paper bag in his right hand, left hand empty"`, không viết `"holding a paper bag"`.
- Đồ vật đổi chỗ thì tả cả trạng thái mới: `"holding one grey flat cap in his right hand, no hat on his head"`.
- **Giữ trạng thái đồ vật liên tục giữa các cảnh**: cảnh trước đã đưa túi cho người khác thì cảnh sau người đó cầm túi, người
  đưa tay không; mũ đã cởi thì các cảnh sau ghi `no hat on his head` cho tới khi đội lại.

- Nhân vật cầm, ôm, đeo, đẩy đồ vật thì ghi luôn vào `action`, ảnh nhân vật được sinh kèm đồ vật đó.
  Ví dụ: `"holding a white smartphone to her ear"`, `"pulling a small red rolling suitcase"`, `"holding a glass beer mug full of golden beer"`.
- Mô tả đồ vật cụ thể: chất liệu, màu, trạng thái (rỗng hay đầy, mới hay cũ). Mô tả mơ hồ thì model tự đoán.
- Trạng thái cơ thể khó vẽ (mang thai, ốm, bị thương) dễ ra hình kỳ lạ; thể hiện bằng đồ vật cùng ý thay vào
  (mang thai: cầm đôi tất em bé hoặc ảnh siêu âm; ốm: miếng dán hạ sốt trên trán, khăn quàng).
- Cảnh không có nhân vật, đồ vật là chủ thể (hai cốc chạm nhau, lá thư trên bàn): `"characters": []` và `"object"` mô tả cả nhóm đồ vật trong một ảnh.
- **Tránh màu xanh lá** cho trang phục, tóc, đồ vật của nhân vật và cảnh đồ vật (ảnh vẽ trên nền xanh lá rồi tách theo màu:
  đồ xanh lá dễ bị khoét lủng). Chọn màu khác (xanh dương, vàng, đỏ, nâu, cam...). Thật cần xanh lá (lá cây, ếch) thì vẫn được,
  bước tạo việc sẽ đổi nền tách sang xanh dương.
- **Cảnh đồ vật (`object`) mô tả ngắn, kiểu tranh minh họa**: 1 câu, tối đa ~15 từ, chỉ loại vật, màu chính, trạng thái
  (`"a grey trash bin with a blue notebook sticking out"`). Không tả chất liệu, vết mòn, nếp nhăn, kích thước giấy (B5), ánh sáng,
  "close-up", "realistic": mô tả càng chi tiết kiểu ảnh chụp thì ảnh càng giống ảnh thật, mất nét Irasutoya.
- **Chữ trong ảnh**: model vẽ ảnh không viết được chữ Nhật đúng (ra chữ giả, sai nét). Đồ vật có chữ (sổ, thư, biển, màn hình
  tin nhắn) chỉ tả là `"with handwritten lines"` / `"with a few lines of text"`, không ghi nội dung chữ trong `object`/`action`.
  Nội dung cần người xem đọc được thì đặt thành lớp chữ (`{"word": "消えろ"}`) hoặc để trong câu thoại / phụ đề.
- Tấm ảnh chụp, bức tranh, màn hình: tả rõ khung (`"a single old instant photograph with a thick white border"`) rồi mới tả
  nội dung bên trong (`"inside the photo frame ..."`); không thì model vẽ thẳng nội dung thay vì tấm ảnh.
- Không có lớp đồ vật riêng. Lớp riêng chỉ dành cho sticker và chữ tượng thanh.

## 2. Khung hình (`shot`): không phải cảnh nào cũng toàn thân

Mỗi cảnh có nhân vật chọn một khung hình:

| `shot` | Ảnh sinh ra | Dùng khi |
|---|---|---|
| `full` | Toàn thân | Có hành động cả người: đi, chạy, nhảy, ngồi, cúi chào, kéo vali; nhân vật bước vào hoặc rời khung; giới thiệu nhân vật lần đầu |
| `half` | Nửa người từ thắt lưng trở lên | Hội thoại, phản ứng, cầm đồ vật trước ngực, gọi điện; phần lớn các câu thoại |
| `close` | Cận mặt và vai | Cảm xúc mạnh: khóc, sốc, bật cười, câu nói then chốt, cú twist |

- Đa dạng: không quá 3 cảnh liền nhau cùng một khung hình. Một video 60 giây nên có cả ba loại.
- Cảm xúc càng mạnh thì khung càng gần. Hành động càng nhiều thì khung càng rộng.
- Cảnh có hai nhân vật: dùng `full` hoặc `half`, không dùng `close`.
- Cảnh có hai nhân vật: mỗi người được sinh thành một ảnh riêng với cùng `action`, nên `action` phải tả **một người**
  (`"walking forward, smiling"`), không viết "side by side", "together", "each other" (mỗi ảnh sẽ vẽ hai người).
- Bỏ trống `shot` thì mặc định `full`.

## 3. Bố cục: nhân vật to, ít nền thừa

- Lớp nhân vật chính để trống `size` và `at`: bước dựng tự lấy cỡ và vị trí theo `shot` (mục `[shots]` của `settings.toml`).
  `half` và `close` đứng sát mép dưới khung hình như máy quay cắt ngang người.
- Chỉ ghi `size`, `at` khi cần đặt khác thường (hai nhân vật: `left` và `right`; nhân vật đi vào bằng `path`).
- Ảnh nhân vật có **bối cảnh vẽ dính** (nấp sau cột, đứng cạnh tường, trước cửa): đặt `"at": "edge_left"` hoặc `"edge_right"`
  để phần cột, tường dán sát mép khung như một phần cảnh, và để nhân vật đứng yên (`"anim": "none"`). Không cho lớp này
  đi vào, đi ra, nhún, lắc (cột sẽ trôi theo) và không dùng `alt_pose` (ảnh thứ hai hay vẽ lệch cột hoặc mất đồ vật).
  Tốt hơn nữa là tránh: chỉ tả bối cảnh trong `location`, còn `action` tả nhân vật.
- Nhân vật chiếm phần lớn nửa dưới khung hình. Tiêu đề và phụ đề nằm ở khoảng 30% phía trên, không đặt gì quan trọng ở đó.

## 4. Sticker và chữ tượng thanh

- Sticker neo vào nhân vật: `<id>.beside_left`, `<id>.beside_right`, `<id>.above`, cỡ `tiny`. Vị trí và cỡ tự khớp với nhân vật, không cần chỉnh tay.
- Chọn sticker theo cảm xúc: ngạc nhiên `exclaim`, thắc mắc `question`, bối rối hoặc căng thẳng `sweat`, buồn `gloom` hoặc `tear`,
  tức `anger`, sốc `lines`, vui hoặc tự hào `sparkle` hoặc `spark`, yêu thương `heart`.
- Tối đa 2 sticker một cảnh. Khoảng một nửa số cảnh không cần sticker.
- Chữ tượng thanh (`word`) dành cho câu cần nhấn: tiếng động (ガチャ, カチン, ドン, ザーッ, ピンポーン), cảm xúc (ホッ, ドキドキ, プンプン, ズーン).
  Tối đa 1 mỗi cảnh, khoảng 1/4 số cảnh. Chọn từ hợp với âm thanh thật của cảnh, không lặp một từ quá 2 lần trong video.

## 5. Hiệu ứng (vẽ bằng code, `effects.py`)

Lớp hiệu ứng: `{"effect": "<tên>", "on": "<id nhân vật>", "start": 0.2, "duration": 1.2, "colour": "#RRGGBB"}`.
`on`, `start`, `duration`, `colour` tùy chọn (hiệu ứng bám nhân vật thì bắt buộc có `on`). Thứ tự trong `layers` là thứ tự vẽ.

| Hiệu ứng | Bám nhân vật | Đặt trong `layers` | Dùng khi |
|---|---|---|---|
| `aura` | có | trước lớp nhân vật (nằm sau) | Xúc động, ấm áp, tự hào, thánh thiện. Đổi màu: hồng `#FFB3D1` cho yêu thương |
| `rays` | có | trước lớp nhân vật | Khoảnh khắc lớn: nhận ra sự thật, cú twist, câu nói then chốt |
| `sparkles` | có | sau lớp nhân vật | Vui, đẹp, tỏa sáng, kỷ niệm đẹp |
| `hearts` | có | sau lớp nhân vật | Yêu thương, cảm động vui |
| `tears` | có | sau lớp nhân vật | Khóc (nhân vật trong ảnh cũng nên có `emotion` crying) |
| `speed_lines` | không | trước lớp nhân vật | Sốc, bất ngờ, nhấn mạnh mạnh; hợp với `motion: shake` |
| `flash` | không | sau cùng | Bất ngờ, chuyển ý đột ngột; chỉ kéo dài 0,35 giây đầu |
| `gloom` | không | trước lớp nhân vật | Buồn, cô đơn, hối hận |
| `rain` | không | sau lớp nhân vật | Buồn, cảnh ngoài trời (hợp với bối cảnh trời mưa) |
| `confetti` | không | sau cùng | Ăn mừng, kết thúc vui |

- Hiệu ứng là điểm nhấn: khoảng 1/3 số cảnh có, tối đa 2 hiệu ứng một cảnh. Dồn nhiều vào cao trào và cú twist.
- Có thể ghép: `aura` + `rays` + `sparkles` cho khoảnh khắc đẹp nhất; `gloom` + `rain` cho đoạn buồn nhất.
- Không dùng sticker và hiệu ứng cùng ý trong một cảnh (vd sticker `tear` cùng hiệu ứng `tears`).
- Mỗi video dùng ít nhất 4 loại hiệu ứng khác nhau; chọn theo thể loại (hài: `speed_lines`, `flash`; tình cảm: `hearts`, `aura`;
  bí ẩn: `gloom`, `rays`; ăn mừng: `confetti`, `sparkles`).

## 6. Chuyển động và chuyển cảnh

**Mặc định để trống.** Cảnh không ghi `anim` (lớp nhân vật chính), `motion`, `transition` thì bước dựng tự chọn (`variety.py`):
anim theo `emotion`, motion theo `beat`, chuyển cảnh theo thay đổi bối cảnh và hồi tưởng, và không lặp với 2 cảnh trước.
Nhân vật nửa người không ghi `at` thì luân phiên giữa, hơi trái, hơi phải. Chỉ ghi tay khi có chủ ý rõ.
Vì bước dựng chọn anim theo `emotion`, hãy viết `emotion` **đa dạng và cụ thể** (`nervous`, `embarrassed`, `furious`, `relieved`,
`suspicious`, `determined`, `heartbroken`, `giggling`...) thay vì lặp `happy` / `sad`.

| Loại | Giá trị | Ghi tay khi |
|---|---|---|
| `anim` nhân vật | `nod` gật, `shake_no` lắc, `sway` đung đưa, `tilt` nghiêng, `breathe` thở nhẹ, `shiver` run, `hop` nhảy lò cò, `sink` chùng xuống, `float` bồng bềnh, `punch` bật mạnh, `spin_in` xoay vào, `lean_in` chồm tới, `rise` trồi lên, `bounce`, `jump`, `pulse`, `approach`, `recede`, `exit_left`/`exit_right`, `slide_left`/`slide_right`, `drop`, `pop`, `none` | Hành động cụ thể: rời đi (`exit_*`), tiến lại (`approach`), dậm chân (`jump`), bước vào (`path` từ `off_left`/`off_right`) |
| `motion` máy quay | `punch_in` giật zoom, `focus` zoom vào mặt, `dutch` nghiêng khung, `drift` trôi nhẹ, `dolly_left`/`dolly_right` trượt kèm zoom, `tilt_up`/`tilt_down` lia dọc, `zoom_in`, `zoom_out`, `pan_left`/`pan_right`, `shake` rung, `none` | `shake` khi sốc mạnh; `dutch` khi bất an; `tilt_up` khi mở đầu ở bối cảnh rộng ngoài trời |
| `transition` chuyển cảnh | `cut`, `fade` mờ, `push_left`/`push_right`/`push_up` đẩy, `whip` lia nhanh, `zoom` zoom xuyên, `flash` chớp trắng, `wipe` quét chéo, `iris` mở vòng tròn | `flash` vào twist; `fade` vào hồi tưởng (tự chọn sẵn); `whip` khi nhảy địa điểm đột ngột |

- Không quá 2 cảnh liền nhau cùng một `anim` hoặc cùng một `motion` (bước dựng cảnh báo khi lặp 3 cảnh).
- `alt_pose` (hai tư thế luân phiên) cho cảnh cần cử động lặp lại: đi bộ, chạy, nói chuyện (`"mouth open while talking"`), vẫy tay,
  gõ phím, ăn uống, khóc nấc. Mỗi `alt_pose` tốn thêm một ảnh; khoảng 1/4 số cảnh là vừa.
- Nhân vật **bước vào khung** (`path` từ `off_left`/`off_right`) và **rời khung** (`exit_left`/`exit_right`) ít nhất 2 lần mỗi video:
  làm khung hình sống, không đứng yên một chỗ.
- `filter: sepia` cho đoạn hồi tưởng.
- **Luôn có chuyển động**: không đặt `motion: none` (bước dựng luôn chọn zoom, trôi, lia chậm khi bỏ trống).
- **Cao trào, twist**: `transition: flash` + `motion: shake` hoặc `punch_in` + hiệu ứng `rays` / `speed_lines`; đổi biểu cảm mạnh
  thì `motion: punch_in` (zoom giật).

**Cảm xúc phải có hiệu ứng (hình + tiếng)**: cảnh có `emotion` mạnh mà chưa ghi hiệu ứng / sticker / chữ thì bước dựng tự
gắn một gói phản ứng: bất ngờ (`shocked`, `surprised`, `stunned`) → 集中線 + ！ + zoom giật + ドン; khoe, đắc ý (`proud`, `smug`,
`confident`) → tia sáng + ✦ lấp lánh + シャキーン; vui (`overjoyed`, `excited`, `laughing`) → lấp lánh; yêu, ngượng (`blushing`,
`touched`) → tim; khóc (`crying`) → nước mắt; tuyệt vọng (`despair`) → tối + vạch ガーン; giận (`angry`) → 集中線 + 💢 + rung;
sợ (`scared`) → tối + mồ hôi; lúng túng (`awkward`) → mồ hôi; khó hiểu (`confused`) → ？. Vì vậy ghi `emotion` bằng **đúng
các từ trên**, đổi cảm xúc thường xuyên (không 2 cảnh liền cùng cảm xúc), và dành cảm xúc mạnh cho khoảng 1/2 số cảnh.
Tiếng hiệu ứng: khoảng 30% số cảnh, cảnh cảm xúc mạnh luôn có, nhỏ hơn giọng 7 dB (nghe rõ, không lấn lời). Nhạc nền tự chọn theo
`genre` (cảm động → しみじみ, buồn → 悲しい, hài → コミカル, bí ẩn → 怪しい, tình yêu / đời thường → ほのぼの, công sở / xã hội →
シリアス; `"bgm": "kanashii"` để chọn nhóm khác, `"bgm": "none"` để tắt). **Khoảng lặng ở câu chốt**: bước dựng tắt nhạc 0,7 giây
ở đầu cảnh vào twist, cảnh `shake` / `flash` (tối đa 4 lần); thêm `"music_stop": true` cho cảnh chốt câu hài / câu đinh để câu
đó rơi vào khoảng lặng (video mẫu 愛彼女弁当: nhạc im bặt đúng câu "う〜ん味がしねぇ！"). Video hài nhạc to hơn (nhỏ hơn giọng 11 dB),
cảm động / buồn nhỏ hơn (18 dB). Bảng tiếng hiệu ứng (tiếng thật từ 効果音ラボ,
`library/sfx/lab/`):

| Gắn theo | Tiếng |
|---|---|
| **Chữ tượng thanh** (`word`) | ドン/バーン → taiko ドン · ドドン · ジャン → ジャジャーン · ガーン → ショック · ズーン/ショボ → しょげる · チーン → chuông chùa · ピコ/ピン → ピコッ · ハッ/エッ → 驚く · キラ/ピカ → きらーん · シャキ → シャキーン · ボヨ/ピョン → ボヨン · ヒュー → ヒューン · ドキ → tim đập · ゴゴゴ · ダッ/タタ → chạy · ブル/カタカタ/ガクガク → run · ズキ/グキ → グキッ · ポロ → giọt nước mắt · ポタ → giọt nước · ジャラ/チャリ → tiền xu · ガチャ/ギィ → mở cửa · コンコン → gõ cửa · スタスタ/テクテク → bước chân · ビシ → ツッコミ · ズコ → ずっこける · ガタンゴトン → tàu chạy · プシュー → cửa tàu · ジリリ → chuông reo · プルル/ピロ → điện thoại · ブーッ/ヴー → rung · パシャ/カシャ → máy ảnh · カタカタカタ → gõ phím · カチッ/ポチ → bấm nút · **シーン → cố ý im lặng** · chữ khác → ポン |
| Sticker | `exclaim` 驚く · `question` 目が点 · `sweat` ヒューン · `gloom` しょげる · `tear` giọt nước mắt · `anger` ドン · `lines` ショック · `heart`, `sparkle` きらーん · `spark` ピコッ |
| Hiệu ứng | `flash` ドドン · `speed_lines` ドン · `gloom` ショック · `tears` giọt nước mắt · `rays` シャキーン · `sparkles`, `hearts`, `confetti`, `aura` きらきら |
| Chuyển động | `shake`, `punch_in` ドン · anim `hop`/`jump`/`bounce` ボヨン · `punch` ドン · `pop`/`spin_in`/`drop` ポン · `shiver` run · `sink` しょげる |
| Nhịp truyện | chuyển cảnh, đổi bối cảnh → シーン切り替え (whoosh) · vào `twist` → ジャジャーン · vào hồi tưởng (`sepia`) → 回想 · cảnh cuối video hài → ちゃんちゃん♪ |

Thêm: バシッ/ボコッ → đấm · パチン/ビンタ → tát · バタン/ドサッ → ngã · ブン/シュッ/ヒュン → vung · ピンポーン → đúng ·
ブブー → sai · ピロン → tin nhắn · ピッ → bíp · ビー → cảnh báo · チクタク → đồng hồ · ドゥルル → trống dồn · ゾクッ/ヒィ → rùng rợn ·
パクッ/モグモグ/ゴクッ → ăn uống · パンパカパーン → kèn · ホッ → nhẹ nhõm · hiệu ứng `aura` → オーラ, `confetti` → ファンファーレ.

**Tiếng nền theo bối cảnh** (tự động, nhỏ dưới giọng, nối liền qua các cảnh cùng bối cảnh): đặt tên bối cảnh có từ khóa để có tiếng nền:
`rain` mưa · `storm` giông · `snow`/`wind` gió · `train_car` tàu chạy · `station`/`platform` ga · `classroom` lớp ồn · `schoolyard` sân
trường · `park` công viên · `beach`/`sea` sóng biển · `port` cảng · `river` sông · `supermarket`/`convenience`/`drugstore`/`shop` cửa hàng ·
`restaurant`/`ramen`/`cafe` quán · `airport` sân bay · `festival` lễ hội pháo hoa · `street`/`road`/`town` phố · `city` phố đông ·
`country`/`field`/`forest` quê mùa hè · `dining` bữa cơm gia đình; không khớp thì `morning` chim sẻ, `dusk`/`evening` quạ, `night` côn trùng
đêm. Trong nhà yên tĩnh (`kitchen`, `bedroom`, `office`, `hospital`...) không có tiếng nền. Cảnh muốn đổi: `"ambient": "amb_rain"`
(hoặc `null` để tắt).

**Viết chữ tượng thanh có chủ ý để có tiếng đúng**: tàu chạy ガタンゴトン, điện thoại reo プルルル, chạy ダッ, tim đập ドキドキ,
nhận ra ハッ, cú sốc ガーン; khoảng lặng nặng nề thì シーン (không có tiếng). Muốn thêm tiếng ở cảnh không có các thứ trên:
`"sfx": ["heartbeat"]` hoặc `"sfx": [{"name": "chiin", "at": 0.4}]` (tên nhóm: tên thư mục trong `library/sfx/lab/`).

## 7. Đa dạng hình ảnh trong một video

Cứ khoảng 5 cảnh nên có ít nhất một cảnh khác kiểu "một nhân vật nhìn thẳng":
- **Cảnh chèn cận đồ vật** (`object`): tay cầm lá thư, chiếc ví mở, màn hình điện thoại, hộp cơm; dùng cho chi tiết manh mối.
- **Nhìn từ sau lưng** (`action`: `"seen from behind, ..."`): nhân vật rời đi, đứng nhìn ra cửa sổ, đứng trước cửa.
- **Nghiêng, nhìn nghiêng** (`"in side view, ..."`): đang đi, đang ngồi làm việc, đạp xe.
- **Hai, ba nhân vật cùng khung** (`"characters": ["clerk", "girl"]`): đối thoại, đưa đồ cho nhau, cúi đầu cảm ơn, gia đình
  quây quần. **Khoảng 1/3 số cảnh có từ 2 nhân vật trở lên** (video mẫu: cô gái và nhân viên ở quầy, hai mẹ con cúi đầu, cả nhà
  nâng ly). Mỗi người một ảnh riêng, đặt `at` `left` / `right` (3 người: thêm `center`), `action` mỗi người tả riêng hướng nhìn
  về phía người kia (`"facing right toward the clerk"`).
- **Nhân vật bước vào hoặc rời khung** (`path` từ `off_left`/`off_right`, `exit_left`/`exit_right`).
- **Cảnh trống chỉ có bối cảnh** (`"characters": []`, không `object`, layers chỉ có chữ tượng thanh hoặc hiệu ứng): khoảng lặng,
  chuyển thời gian ("その夜。", "半年後。"), giới thiệu nơi chốn mới. Mỗi khi đổi sang bối cảnh ngoài trời mới, cân nhắc mở bằng một cảnh trống.
- **Đổi khung hình liên tục:** không quá 3 cảnh liền nhau cùng `shot`.
- **Tư thế đa dạng** trong `action`: ngồi, quỳ, nằm, chạy, cúi đầu, ôm, chỉ tay, giơ tay, ôm mặt, nhảy cẫng — không chỉ đứng.

**Đa dạng nội dung:**
- Đổi bối cảnh theo diễn biến (mục 0b).
- Xen kẽ người kể (`narrator`) với lời thoại của nhân vật; lời thoại trực tiếp làm câu chuyện sống hơn.
- Mỗi nấc phát triển có ít nhất một chi tiết hình ảnh mới (đồ vật, bối cảnh, hành động) để người xem có thứ mới để nhìn.
- Cú twist nên gắn với một đồ vật hoặc hành động đã xuất hiện từ đầu video (cài cắm rồi mở nút).
- **Không viết câu chỉ có dấu câu** (`……。`, `…！？`): không có tiếng đọc, cảnh thành im lặng chết. Muốn tả nhân vật
  lặng người thì để lời kể nói thay (`健太は、何も言えなかった。`) hoặc một tiếng ngắn đọc được (`え…`, `…うん`).
- Câu thoại ngắn, đọc trong 1-2 giây. Phụ đề chữ to (cỡ 144, khoảng 6 chữ một dòng): tối đa khoảng 12 ký tự tiếng Nhật
  để vừa 2 dòng. Câu dài hơn thì tự đặt `\n` ở chỗ ngắt tự nhiên (sau 、, giữa hai cụm từ), vd `"冷凍庫には今も、\nジョッキが2つ。"`;
  không quá 3 dòng.

## 8. Giữ chân người xem (TikTok)

Người xem quyết định lướt qua trong 1-2 giây đầu và rời đi ở bất kỳ chỗ nào câu chuyện hết câu hỏi. Kịch bản phải luôn để mở ít nhất một câu hỏi.

- **Móc câu trong 2 giây đầu:** cảnh 1-2 là chi tiết lạ hoặc mâu thuẫn, không phải giới thiệu nhân vật. Vd "父の財布から、写真が落ちた。知らない女の子だった。" (bắt đầu giữa sự việc).
  Đổi kiểu móc câu giữa các video: câu hỏi, câu nói gây sốc, cảnh hành động, con số lạ, lời thoại giữa chừng.
- **Tiêu đề cũng là móc câu:** nêu chi tiết lạ, không kể kết; vd `["父の財布にあった", "知らない女の子の写真"]`.
- **Cứ 15-20 giây một câu hỏi mới hoặc một chi tiết lật lại điều vừa tin:** nghi ngờ → manh mối → nghi ngờ lớn hơn. Ghi rõ nấc (`beat`) cho từng cảnh.
- **Twist giả trước twist thật:** khoảng giữa video, một chi tiết làm người xem tưởng đã hiểu (vd ngoại tình), rồi lật lại; twist thật ở khoảng 3/4 video.
- **Cài cắm rồi mở nút:** đồ vật hoặc câu nói ở đầu video phải quay lại ở twist (tấm ảnh, cuốn sổ, hộp cơm). Dùng lại đúng ảnh đó (trường `reuse` trong file dựng kịch bản) để người xem nhận ra.
- **Kết thành vòng lặp:** câu cuối nối về cảnh đầu (vd "今、私の財布にも、あの写真が入っている。") để người xem muốn xem lại từ đầu.
- **Nhịp nhanh:** mỗi cảnh 1-2 giây, đổi khung hình, bối cảnh hoặc chuyển động liên tục; không để 2 cảnh liền nhau giống hệt nhau về hình.
- **Lời thoại trực tiếp ở các điểm căng** (câu hỏi, cãi nhau, lời thú nhận); lời kể dùng để nối, ngắn gọn.
- **Cao trào cảm xúc có hình rõ:** cận mặt, hiệu ứng (`rays`, `aura`, `tears`), không nói giảm.
- **Độ dài:** 80-100 giây (50-60 cảnh), không ngắn hơn, không dài hơn. Dài nhờ thêm nấc truyện, cảnh phản ứng, cảnh chèn, hồi tưởng,
  không nhờ câu thừa. Cứ khoảng 10 cảnh phải có ít nhất 1 cảnh nhiều lớp hiệu ứng (sticker + chữ tượng thanh + `effect`).

## 9. Tự kiểm trước khi trả kết quả

- [ ] Thể loại và góc kể hợp đề tài, khác các video gần đây.
- [ ] Ít nhất 6 bối cảnh, có ngoài trời, có ít nhất 2 thời điểm trong ngày khác nhau; không bối cảnh nào quá 30% số cảnh.
- [ ] Nhân vật mới (nếu có) đã khai trong `new_characters`, bối cảnh mới trong `new_locations`; mọi tên dùng trong cảnh đều có sẵn hoặc vừa khai.
- [ ] Đủ 3 loại `shot`, không quá 3 cảnh liền cùng `shot`; có cảnh chèn đồ vật, cảnh nhìn sau lưng hoặc nghiêng, cảnh bước vào/rời khung.
- [ ] `emotion` đa dạng; ít nhất 4 loại hiệu ứng; sticker và chữ tượng thanh không lặp quá 2 lần.
- [ ] Móc câu ở 2 giây đầu, twist gắn với chi tiết đã cài, câu kết nối về đầu.
- [ ] **50-60 cảnh, tổng lời 550-700 ký tự** (đếm lại trước khi trả). Không `action` nào có ghế, cửa, tay vịn, quầy, bàn... (đồ cố định nằm trong nền); nhân vật ngồi dùng `half` / `close`.
- [ ] Đồ cầm tay ghi số lượng và tay cầm; trạng thái đồ vật (cầm, đưa, cởi mũ) liên tục giữa các cảnh; trang phục không đổi.
