# Hướng dẫn sử dụng và bảo dưỡng pin xe điện

> Tài liệu mẫu viết cho bài thực hành (Session 05). Nội dung là hướng dẫn chung, không thay thế sách hướng dẫn của
> nhà sản xuất xe. Các mã lỗi trong mục 9 là mã minh họa; mỗi hãng dùng bộ mã riêng.

## 1. Giới thiệu và phạm vi

Pin là bộ phận đắt nhất của một chiếc xe điện và quyết định quãng đường đi được, tốc độ sạc cũng như giá trị bán lại
của xe. Một bộ pin được dùng đúng cách có thể giữ phần lớn dung lượng sau nhiều năm; một bộ pin thường xuyên bị sạc
đầy rồi để nóng dưới nắng sẽ xuống cấp nhanh hơn đáng kể.

Hướng dẫn này áp dụng cho ô tô điện và xe máy điện dùng pin lithium-ion. Tài liệu giải thích sự khác nhau giữa các loại
pin, các cách sạc, mức sạc nên dùng hằng ngày, ảnh hưởng của nhiệt độ, cách cất giữ xe khi không dùng, chính sách bảo
hành thường gặp, ý nghĩa của các mã lỗi và những quy tắc an toàn. Các con số trong tài liệu là giá trị tham khảo; khi
có khác biệt, hãy làm theo sách hướng dẫn đi kèm xe của bạn.

Một vài thuật ngữ dùng xuyên suốt tài liệu:

- **SoC (State of Charge)**: mức pin hiện tại, tính bằng phần trăm dung lượng khả dụng.
- **SoH (State of Health)**: sức khỏe pin, tức dung lượng còn lại so với khi xe mới.
- **BMS (Battery Management System)**: hệ thống quản lý pin, theo dõi điện áp, dòng điện và nhiệt độ của từng cụm cell.
- **kWh**: đơn vị năng lượng của pin; **kW**: công suất của bộ sạc.

## 2. Hai loại pin phổ biến: LFP và NMC

Phần lớn xe điện hiện nay dùng một trong hai hóa học pin: **LFP** (lithium sắt phốt phát) hoặc **NMC** (lithium
niken mangan coban). Cả hai đều là pin lithium-ion, nhưng có đặc tính khác nhau nên cách sạc khuyến nghị cũng khác nhau.

Pin **LFP** có mật độ năng lượng thấp hơn, nghĩa là cùng một khối lượng pin thì xe đi được quãng đường ngắn hơn. Bù
lại, LFP chịu được nhiều chu kỳ sạc xả hơn, ổn định nhiệt tốt hơn và ít chịu ảnh hưởng khi sạc đầy 100%. Điện áp của
cell LFP gần như không đổi trong khoảng giữa của dải sạc, vì vậy BMS khó ước lượng chính xác mức pin; nhiều nhà sản xuất
khuyên sạc đầy 100% ít nhất mỗi tuần một lần để BMS hiệu chỉnh lại SoC.

Pin **NMC** có mật độ năng lượng cao hơn nên phù hợp với xe cần quãng đường dài. Pin NMC nhạy hơn với việc nằm lâu ở
mức sạc cao và ở nhiệt độ cao. Với loại pin này, việc giữ mức sạc hằng ngày khoảng 80% giúp làm chậm quá trình suy
giảm dung lượng.

Cách nhận biết xe của bạn dùng loại pin nào: xem thông số kỹ thuật trong sách hướng dẫn, nhãn trên giấy chứng nhận của
xe, hoặc mục thông tin pin trong màn hình cài đặt. Một số xe hiển thị trực tiếp khuyến nghị "sạc đến 100%" khi dùng
LFP và "sạc đến 80%" khi dùng NMC.

## 3. Các cấp độ sạc: AC chậm, AC tại nhà và DC nhanh

Có ba cách sạc thường gặp, khác nhau ở loại dòng điện và công suất.

**Sạc AC chậm từ ổ cắm thông thường.** Bộ sạc di động cắm vào ổ điện dân dụng 220 V, công suất khoảng 1,8 đến 3,7
kW. Cách này chậm nhưng không cần lắp đặt thêm, phù hợp khi xe chạy ít mỗi ngày hoặc khi đi xa nhà. Ổ cắm và dây điện
phải chịu được dòng điện liên tục trong nhiều giờ; không dùng ổ cắm nối dài hay ổ cắm đã lỏng.

**Sạc AC tại nhà bằng wallbox.** Bộ sạc gắn tường có công suất 7,4 kW (một pha) hoặc 11 kW (ba pha). Đây là cách sạc
chính của đa số người dùng: cắm xe buổi tối, sáng hôm sau pin đã đủ cho cả ngày. Wallbox cần đường dây riêng, aptomat
chống giật và nên do thợ điện có chứng chỉ lắp đặt. Bộ sạc trong xe (on-board charger) giới hạn công suất AC tối đa:
nếu xe chỉ nhận 7,4 kW thì wallbox 11 kW cũng chỉ sạc ở 7,4 kW.

**Sạc nhanh DC.** Trạm sạc nhanh cấp dòng một chiều trực tiếp vào pin với công suất từ 30 kW đến hơn 150 kW. Sạc
nhanh rất tiện cho các chuyến đi dài, nhưng công suất cao làm pin nóng hơn. Công suất sạc DC không giữ nguyên trong cả
quá trình: xe nhận công suất cao nhất ở mức pin thấp, sau đó giảm dần khi pin vượt khoảng 50 đến 60%, và giảm mạnh sau
80%. Vì vậy dừng sạc nhanh ở khoảng 80% thường tiết kiệm thời gian hơn chờ đến 100%.

## 4. Thời gian sạc tham khảo

Bảng dưới đây ước tính thời gian sạc một bộ pin 60 kWh từ 10% lên 80% (khoảng 42 kWh năng lượng nạp vào), đã tính
khoảng 10% tổn hao. Thời gian thực tế phụ thuộc vào nhiệt độ pin, công suất tối đa xe nhận được và đường cong sạc của
từng mẫu xe.

| Loại bộ sạc      | Công suất | Thời gian 10% → 80% (pin 60 kWh) | Phù hợp với                            |
| ------------------- | ----------- | ---------------------------------- | ----------------------------------------- |
| Ổ cắm dân dụng  | 2,3 kW      | khoảng 20 giờ                    | xe chạy ít, sạc qua đêm nhiều ngày |
| Bộ sạc di động  | 3,7 kW      | khoảng 12–13 giờ                | sạc qua đêm, đi xa nhà               |
| Wallbox một pha    | 7,4 kW      | khoảng 6–7 giờ                  | sạc hằng ngày tại nhà                |
| Wallbox ba pha      | 11 kW       | khoảng 4–5 giờ                  | nhà có điện ba pha, văn phòng       |
| Trạm sạc nhanh DC | 50 kW       | khoảng 55–65 phút               | dừng nghỉ trên đường dài           |
| Trạm sạc nhanh DC | 150 kW      | khoảng 25–35 phút               | trạm trên cao tốc                      |

Với xe máy điện, pin thường có dung lượng 1,5 đến 4 kWh và sạc bằng bộ sạc rời 0,5 đến 1 kW, nên thời gian sạc đầy từ
pin cạn thường từ 3 đến 8 giờ.

## 5. Mức sạc khuyến nghị cho sử dụng hằng ngày

Pin lithium-ion xuống cấp nhanh hơn khi nằm lâu ở mức sạc rất cao hoặc rất thấp. Nguyên tắc chung:

- **Pin NMC**: đặt giới hạn sạc hằng ngày ở **80%**, chỉ sạc lên **100%** ngay trước một chuyến đi dài và khởi hành
  sớm sau khi sạc đầy. Tránh để xe nằm nhiều ngày ở 100%.
- **Pin LFP**: có thể sạc lên **100%** hằng ngày nếu nhà sản xuất cho phép, và nên sạc đầy ít nhất mỗi tuần một lần
  để BMS hiệu chỉnh mức pin.
- **Mức thấp**: tránh để pin xuống dưới **10%** thường xuyên. Khi pin dưới 5%, xe có thể giới hạn công suất để bảo vệ
  pin.

Giới hạn sạc được đặt trong ứng dụng của xe hoặc trên màn hình trung tâm, mục "Sạc" hoặc "Charge limit". Một số
wallbox cũng cho đặt lịch sạc, nhờ đó pin sạc xong ngay trước giờ đi làm thay vì nằm ở mức cao suốt đêm.

Sạc nhiều lần một ít (ví dụ từ 40% lên 70% mỗi tối) không gây hại cho pin lithium-ion. Pin lithium-ion không có
"hiệu ứng nhớ" như pin NiCd thế hệ cũ, nên không cần xả cạn trước khi sạc.

## 6. Ảnh hưởng của nhiệt độ

Nhiệt độ là yếu tố ảnh hưởng mạnh nhất đến tuổi thọ pin sau mức sạc. Khoảng nhiệt độ làm việc lý tưởng của pin
lithium-ion là khoảng 15 đến 35 °C.

**Trời nóng.** Pin nóng trên 45 °C sẽ suy giảm nhanh hơn, nhất là khi đồng thời ở mức sạc cao. Ở Việt Nam, xe đỗ
ngoài trời giữa trưa hè có thể làm pin nóng lên đáng kể. Nên đỗ xe trong bóng râm hoặc nhà xe, tránh sạc nhanh DC liên
tiếp nhiều lần khi trời nóng, và để hệ thống làm mát pin hoạt động (không tắt chế độ làm mát để tiết kiệm điện).

**Trời lạnh.** Ở nhiệt độ thấp, phản ứng hóa học trong pin chậm lại: quãng đường đi được giảm và tốc độ sạc nhanh
giảm rõ rệt. Nhiều xe có chức năng làm ấm pin trước khi sạc nhanh (preconditioning); hãy bật chức năng này bằng cách
chọn trạm sạc làm điểm đến trong bản đồ của xe.

**Sau khi chạy đường dài.** Pin vừa chạy tốc độ cao liên tục sẽ nóng. Nếu có thể, nghỉ vài phút trước khi sạc nhanh,
hoặc để xe tự điều chỉnh công suất sạc.

## 7. Bảo quản khi không sử dụng lâu ngày

Khi xe không được dùng trong thời gian dài (đi công tác, xe dự phòng, xe trưng bày), cách cất giữ đúng giúp pin không bị
suy giảm hoặc xả quá sâu.

- Để mức pin trong khoảng **40 đến 60%** trước khi cất xe. Không cất xe ở 100% và không để pin cạn.
- Đỗ xe ở nơi khô ráo, thoáng mát, tránh ánh nắng trực tiếp.
- Pin vẫn tự xả chậm và các hệ thống điện tử của xe vẫn tiêu thụ một ít điện. Kiểm tra mức pin mỗi tháng một lần và
  sạc bổ sung về khoảng 50% nếu cần.
- Nếu xe có chế độ cất giữ (storage mode hoặc transport mode), bật chế độ này để giảm điện năng tiêu thụ khi đỗ.
- Với xe máy điện có pin tháo rời, cất pin trong nhà ở nhiệt độ phòng, không đặt cạnh nguồn nhiệt.

Ắc quy 12 V (loại pin nhỏ cấp điện cho đèn, khóa và hệ thống điều khiển) cũng có thể bị cạn khi xe đứng lâu. Nhiều xe
tự sạc ắc quy 12 V từ pin chính, nhưng nếu xe báo lỗi khởi động sau thời gian dài không dùng, hãy kiểm tra ắc quy này
trước.

## 8. Suy giảm dung lượng và bảo hành

Mọi bộ pin đều mất dần dung lượng theo thời gian và số chu kỳ sạc. Mức suy giảm thường nhanh hơn trong một đến hai năm
đầu, sau đó chậm lại. Quãng đường đi được giảm vài phần trăm sau vài năm là hiện tượng bình thường.

Chính sách bảo hành pin thường gặp trên thị trường là **8 năm hoặc 160.000 km**, tùy điều kiện nào đến trước, kèm cam
kết dung lượng còn lại tối thiểu khoảng **70%**. Điều kiện cụ thể khác nhau giữa các hãng, vì vậy hãy đọc kỹ sổ bảo
hành của xe. Một số điểm cần lưu ý:

- Bảo hành thường không áp dụng khi pin bị hư hỏng do va chạm, ngập nước, tự ý tháo mở hoặc sửa chữa ở nơi không được
  ủy quyền.
- Giữ lại hóa đơn bảo dưỡng định kỳ và lịch sử cập nhật phần mềm; đây là căn cứ khi yêu cầu bảo hành.
- SoH được đo bằng thiết bị chẩn đoán tại xưởng dịch vụ. Con số quãng đường dự kiến trên màn hình không phải là phép đo
  SoH, vì nó còn phụ thuộc vào cách lái gần đây và nhiệt độ.

Khi mua xe điện đã qua sử dụng, nên yêu cầu báo cáo SoH từ xưởng dịch vụ và kiểm tra thời hạn bảo hành pin còn lại.

## 9. Mã lỗi pin thường gặp (minh họa)

Khi BMS phát hiện bất thường, màn hình hiển thị cảnh báo kèm mã lỗi. Bảng dưới đây là bộ mã minh họa dùng trong tài
liệu này; mã thực tế trên xe của bạn có thể khác.

- **E-101: Mất kết nối giao tiếp với bộ sạc.** Thường do súng sạc cắm chưa chặt hoặc đầu nối bẩn. Rút súng sạc, kiểm
  tra đầu nối, cắm lại. Nếu lỗi lặp lại ở nhiều trạm sạc khác nhau, mang xe đến xưởng dịch vụ.
- **E-217: Nhiệt độ pin quá cao khi sạc nhanh.** Xe tự giảm hoặc dừng công suất sạc DC. Dừng sạc, để xe nghỉ ở nơi
  thoáng mát 15 đến 30 phút rồi sạc lại với công suất thấp hơn. Nếu lỗi xuất hiện khi trời không nóng, cần kiểm tra hệ
  thống làm mát pin.
- **E-305: Chênh lệch điện áp giữa các cụm cell vượt ngưỡng.** BMS phát hiện các cụm cell không cân bằng. Sạc đầy
  chậm bằng nguồn AC để BMS cân bằng cell; nếu lỗi vẫn còn, cần kiểm tra tại xưởng.
- **E-412: Phát hiện rò điện cách điện.** Đây là lỗi an toàn nghiêm trọng. Không sạc và không lái xe; liên hệ dịch vụ
  cứu hộ của hãng.
- **E-520: Ắc quy 12 V yếu.** Xe có thể không khởi động hệ thống cao áp. Sạc hoặc thay ắc quy 12 V.

Không xóa mã lỗi bằng thiết bị chẩn đoán không chính hãng khi chưa xác định nguyên nhân; lịch sử mã lỗi giúp kỹ thuật
viên chẩn đoán chính xác hơn.

## 10. An toàn khi sạc và khi xảy ra sự cố

Pin xe điện chứa năng lượng lớn ở điện áp cao (thường 400 V hoặc 800 V trên ô tô). Tuân thủ các quy tắc sau:

- Chỉ dùng bộ sạc và dây sạc đạt chuẩn, không dùng ổ cắm nối dài, không tự chế đầu chuyển.
- Không sạc khi đầu nối, dây sạc hoặc ổ cắm bị ướt, nứt, cháy xém.
- Không tự tháo mở bộ pin hay các dây cáp màu cam (dây cao áp).
- Sau va chạm mạnh hoặc khi xe bị ngập nước, không sạc và không khởi động xe; gọi dịch vụ cứu hộ và thông báo xe là
  xe điện.
- Nếu thấy khói, mùi khét hoặc tiếng nổ lách tách từ khu vực pin: dừng xe ở nơi an toàn, tắt xe, đưa mọi người ra xa
  ít nhất 15 m và gọi cứu hỏa (114). Đám cháy pin lithium-ion có thể bùng lại sau khi đã dập, nên cần lực lượng chuyên
  nghiệp xử lý.
- Với xe máy điện sạc trong nhà, đặt xe xa lối thoát hiểm và vật dễ cháy, không sạc qua đêm khi không có người ở nhà.

Tuân thủ những nguyên tắc trên giúp pin bền hơn, xe vận hành an toàn hơn và giữ quyền lợi bảo hành của bạn.
