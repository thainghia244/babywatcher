# HƯỚNG DẪN CHUYỂN BÁO CÁO MARKDOWN SANG WORD

## 📋 Cách chuyển đổi báo cáo từ Markdown sang Word

### Phương pháp 1: Copy-Paste trực tiếp (Khuyến nghị)

#### Bước 1: Mở Microsoft Word
- Tạo tài liệu Word mới
- Đặt font: **Times New Roman**, size **12pt**
- Line spacing: **1.5 lines**

#### Bước 2: Copy từng phần từ Markdown
1. **Copy phần đầu** (Trang bìa, Lời cảm ơn, Tóm tắt)
2. **Format heading**:
   - `#` → Heading 1 (font 16pt, bold)
   - `##` → Heading 2 (font 14pt, bold)
   - `###` → Heading 3 (font 13pt, bold)

#### Bước 3: Format bảng biểu
- Copy bảng Markdown vào Word
- Chọn bảng → **Table Design** → **Table Styles** → Chọn style phù hợp
- Căn giữa tiêu đề bảng

#### Bước 4: Format code blocks
- Chọn code block → **Courier New**, size 10pt, background gray
- Hoặc sử dụng **Insert** → **Text Box** cho code dài

#### Bước 5: Thêm hình ảnh
- **Insert** → **Pictures** → Chọn hình ảnh
- Đặt caption: "Hình X.X: [Tên hình]"
- Căn giữa hình ảnh

### Phương pháp 2: Sử dụng Pandoc (Cho người dùng nâng cao)

#### Cài đặt Pandoc:
```bash
# Windows với Chocolatey
choco install pandoc

# Hoặc download từ: https://pandoc.org/installing.html
```

#### Chuyển đổi file:
```bash
# Chuyển Markdown sang Word
pandoc BaoCaoDoAnTotNghiep_WordFormat.md -o BaoCaoDoAnTotNghiep.docx

# Với template tùy chỉnh
pandoc BaoCaoDoAnTotNghiep_WordFormat.md -o BaoCaoDoAnTotNghiep.docx --reference-doc template.docx
```

### Phương pháp 3: Sử dụng Online Tools

#### Các công cụ online miễn phí:
1. **Markdown to Word**: https://www.markdowntoword.com/
2. **CloudConvert**: https://cloudconvert.com/md-to-docx
3. **ILovePDF**: https://www.ilovepdf.com/markdown-to-word

---

## 🎨 HƯỚNG DẪN FORMAT TRONG WORD

### 1. Font và Spacing
- **Font chính**: Times New Roman, 12pt
- **Line spacing**: 1.5 lines
- **Paragraph spacing**: Before 0pt, After 6pt

### 2. Heading Styles
```
Heading 1: Font 16pt, Bold, Center (cho tiêu đề chương)
Heading 2: Font 14pt, Bold (cho tiêu đề mục)
Heading 3: Font 13pt, Bold (cho tiêu đề tiểu mục)
```

### 3. Page Setup
- **Margins**: Top/Bottom 2.5cm, Left/Right 3cm
- **Paper size**: A4
- **Orientation**: Portrait

### 4. Header/Footer
- **Header**: Tên đề tài (trang lẻ), Tên sinh viên (trang chẵn)
- **Footer**: Số trang (căn giữa)

### 5. Table of Contents
- **References** → **Table of Contents** → **Automatic Table 1**
- Update TOC sau khi hoàn thành

### 6. List of Figures/Tables
- **References** → **Insert Caption** cho từng hình/bảng
- **References** → **Insert Table of Figures**

---

## 📝 CHECKLIST FORMAT BÁO CÁO

### Trang bìa ✅
- [ ] Tên trường, khoa
- [ ] Tên đề tài (in đậm, font 18pt)
- [ ] Thông tin sinh viên, GVHD
- [ ] Thời gian thực hiện

### Lời cảm ơn ✅
- [ ] Cảm ơn GVHD, trường, gia đình
- [ ] Font 12pt, canh lề đều

### Tóm tắt ✅
- [ ] 300-500 từ
- [ ] Nêu mục tiêu, phương pháp, kết quả

### Mục lục ✅
- [ ] Tự động tạo từ heading
- [ ] Cập nhật số trang

### Nội dung chính ✅
- [ ] Font Times New Roman 12pt
- [ ] Line spacing 1.5
- [ ] Căn lề đều (Justify)

### Hình ảnh & Bảng biểu ✅
- [ ] Caption cho mỗi hình/bảng
- [ ] Tham chiếu trong text
- [ ] Căn giữa, font 11pt

### Tài liệu tham khảo ✅
- [ ] Format chuẩn APA/IEEE
- [ ] Sắp xếp theo thứ tự alphabet

### Phụ lục ✅
- [ ] Code blocks với font monospace
- [ ] Hình ảnh minh họa

---

## 🔧 TEMPLATES WORD SẴN SÀNG

### Template cơ bản cho sinh viên:
1. **Download template**: Tìm "Đồ án tốt nghiệp template" trên Google
2. **Sử dụng Pandoc** với reference doc:
   ```bash
   pandoc input.md -o output.docx --reference-doc template.docx
   ```

### Các template có sẵn:
- Template trường Đại học Bách khoa
- Template trường Đại học Công nghệ
- Template chung cho các trường

---

## 💡 MẸO FORMAT CHUYÊN NGHIỆP

### 1. Consistent Formatting
- Sử dụng Styles trong Word để đảm bảo nhất quán
- Tạo style cho: Normal, Heading 1-3, Code, Caption

### 2. Professional Look
- Tránh font màu, hiệu ứng
- Sử dụng màu đen cho text chính
- Gray nhẹ cho captions

### 3. Page Breaks
- Chèn page break trước mỗi chương mới
- Không để heading ở cuối trang

### 4. Cross-references
- Sử dụng **References** → **Cross-reference** cho hình/bảng
- Tự động cập nhật khi thêm/xóa

### 5. Final Check
- Spell check toàn bộ document
- Kiểm tra page numbers
- Verify tất cả links và references

---

## 🚀 QUY TRÌNH HOÀN CHỈNH

### Bước 1: Viết nội dung trong Markdown
- Tập trung vào content, không lo format
- Sử dụng syntax Markdown chuẩn

### Bước 2: Convert sang Word
- Copy-paste từng phần hoặc dùng Pandoc
- Áp dụng formatting theo checklist

### Bước 3: Review và Edit
- Đọc lại toàn bộ document
- Kiểm tra logic và flow
- Fix lỗi format

### Bước 4: Final Export
- Save as PDF cho submission
- Keep Word file để chỉnh sửa sau

---

## 📞 HỖ TRỢ

Nếu gặp vấn đề khi format:
1. **Check Word version**: Sử dụng Word 2016+
2. **Update Pandoc**: Version mới nhất
3. **Test với file nhỏ**: Convert phần nhỏ trước
4. **Use online tools**: Nếu Pandoc không hoạt động

**File báo cáo của bạn đã sẵn sàng để convert sang Word! 🎉**