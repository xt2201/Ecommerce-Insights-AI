# Prompt cho Response Agent

## Template: Giới thiệu khi có câu truy vấn

Đây là những gì tôi tìm được cho '{query}':

---

## Template: Giới thiệu khi không có câu truy vấn

Đây là những gì tôi tìm được:

---

## Template: Không tìm thấy sản phẩm

Tôi không thể tìm được sản phẩm Amazon phù hợp cho yêu cầu của bạn. Vui lòng thử tinh chỉnh câu truy vấn hoặc mở rộng tiêu chí tìm kiếm.

---

## Template: Lựa chọn hàng đầu

• **Lựa chọn hàng đầu**: {title} (điểm {score:.2f})

---

## Template: Giá tốt nhất

• **Giá tốt nhất**: {title} với giá khoảng ${price:,.2f}

---

## Template: Đánh giá cao nhất

• **Đánh giá cao nhất**: {title} được đánh giá {rating}/5 sao

---

## Template: Kết luận

Hãy cho tôi biết nếu bạn muốn so sánh chi tiết hơn, nhiều lựa chọn ngân sách hơn, hoặc theo dõi lịch sử giá cả.

---

## Hướng dẫn tạo Summary

### Cấu trúc Summary:

1. **Phần giới thiệu**
   - Nếu có query: "Đây là những gì tôi tìm được cho '{query}':"
   - Nếu không có query: "Đây là những gì tôi tìm được:"

2. **Lựa chọn hàng đầu** (Top Pick)
   - Luôn hiển thị sản phẩm đứng đầu với điểm số
   - Format: "• Lựa chọn hàng đầu: [Tên sản phẩm] (điểm X.XX)"

3. **Giá tốt nhất** (Best Price) - nếu khác với top pick
   - Chỉ hiển thị nếu sản phẩm rẻ nhất không phải là top pick
   - Format: "• Giá tốt nhất: [Tên] với giá khoảng $XXX.XX"

4. **Đánh giá cao nhất** (Highest Rated) - nếu khác với top pick
   - Chỉ hiển thị nếu sản phẩm có rating cao nhất không phải là top pick
   - Format: "• Đánh giá cao nhất: [Tên] được đánh giá X.X/5 sao"

5. **Insights đáng chú ý**
   - Liệt kê các insights từ phân tích
   - Mỗi insight trên một dòng với "• "

6. **Kết luận**
   - Câu kết: "Hãy cho tôi biết nếu bạn muốn so sánh chi tiết hơn, nhiều lựa chọn ngân sách hơn, hoặc theo dõi lịch sử giá cả."

### Lưu ý:
- Mỗi mục bullet bắt đầu bằng "• "
- Các phần cách nhau bằng newline (\n)
- Giữ ngôn ngữ thân thiện, dễ hiểu
- Tập trung vào thông tin quan trọng nhất
