# Prompt cho Analysis Agent

## Template: Thông báo khi không có sản phẩm

Không tìm thấy sản phẩm nào từ SerpAPI.

---

## Template: Thông báo khi chỉ có một sản phẩm

Chỉ có một sản phẩm có sẵn; khả năng so sánh bị hạn chế

---

## Template: Rationale (Lý do đánh giá sản phẩm)

Điểm giá trị: {score:.2f} | Giá: ${price:,.2f} | Đánh giá: {rating}/5 | Số lượt đánh giá: {reviews_count}

### Hướng dẫn xây dựng rationale:
- Bắt đầu với "Điểm giá trị: X.XX"
- Nếu có giá: thêm "Giá: $X,XXX.XX"
- Nếu có rating: thêm "Đánh giá: X.X/5"
- Nếu có số lượt đánh giá: thêm "Số lượt đánh giá: XXX"
- Các phần cách nhau bằng " | "

---

## Template: Insights về giá

Khoảng chênh lệch giá giữa các lựa chọn: ${spread:,.2f}

---

## Template: Insights về sản phẩm được đánh giá nhiều nhất

Sản phẩm có nhiều đánh giá nhất: {title} ({reviews_count} đánh giá)

---

## Hướng dẫn phân tích

### Nhiệm vụ:
1. Tìm sản phẩm rẻ nhất (cheapest)
2. Tìm sản phẩm có rating cao nhất (highest_rated)
3. Tính điểm giá trị (value score) cho mỗi sản phẩm
4. Xác định sản phẩm có giá trị tốt nhất (best_value)
5. Tạo các insights đáng chú ý (noteworthy_insights)

### Tính điểm giá trị (Value Score):
- Điểm dựa trên: giá cả, rating, và số lượng đánh giá
- Sản phẩm có điểm cao nhất = giá trị tốt nhất
- Cân nhắc cả chất lượng (rating) và độ tin cậy (số lượt đánh giá)

### Insights cần tạo:
- Nếu có >= 2 sản phẩm: tính khoảng chênh lệch giá
- Liệt kê sản phẩm có nhiều đánh giá nhất
- Các nhận xét đáng chú ý khác về danh sách sản phẩm
