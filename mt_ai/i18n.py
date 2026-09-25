from __future__ import annotations

import os
import sys

VI = {
    "RENDER":"KẾT XUẤT","Model Manager":"Quản lý mô hình","Scene Analysis":"Phân tích cảnh",
    "Load an image to analyze the scene.":"Mở một ảnh để phân tích cảnh.","Analyze Scene":"Phân tích cảnh",
    "Mood / context":"Bối cảnh / không khí","Geometry Protection":"Bảo vệ hình học",
    "Render Protection":"Bảo vệ khi kết xuất","Camera":"Góc máy","Architecture":"Kiến trúc",
    "Furniture":"Nội thất","Windows":"Cửa sổ","Doors":"Cửa đi","Ceiling":"Trần",
    "Major objects":"Vật thể chính","Text / signage":"Chữ / biển hiệu","Quality":"Chất lượng",
    "Draft":"Nháp","Standard":"Tiêu chuẩn","High":"Cao","Ultra":"Siêu cao",
    "Original":"Ảnh gốc","Rendered":"Ảnh kết xuất","Compare":"So sánh","Output Resolution":"Độ phân giải đầu ra","Match source":"Theo ảnh gốc","Custom":"Tùy chỉnh","Prompt":"Câu lệnh",
    "Open Image":"Mở ảnh","Paste":"Dán ảnh","Suggest Prompt":"Gợi ý câu lệnh",
    "AI Rewrite Prompt":"AI viết lại câu lệnh","Cancel":"Hủy","Retry":"Thử lại","Save Result":"Lưu kết quả",
    "File":"Tệp","Paste Image":"Dán ảnh","Tools":"Công cụ","Interior":"Nội thất",
    "Landscape":"Phong cảnh","Masterplan":"Quy hoạch","Enhance":"Tăng cường","Upscale":"Nâng độ phân giải",
    "Natural":"Tự nhiên","Morning":"Buổi sáng","Afternoon":"Buổi chiều","Golden hour":"Giờ vàng",
    "Blue hour":"Giờ xanh","Night":"Ban đêm","Soft cloudy":"Trời mây dịu","Warm luxury":"Ấm áp sang trọng",
    "Neutral studio":"Studio trung tính","MT AI — Model Manager":"MT AI — Quản lý mô hình",
    "Installed Qwen Image models":"Các mô hình Qwen Image đã cài","Import Existing Model":"Thêm model có sẵn","Install Qwen Image 2.1":"Cài Qwen Image 2.1",
    "Install Prompt Rewriter (optional)":"Cài bộ viết lại câu lệnh (tùy chọn)","Activate selected":"Kích hoạt mục đã chọn",
    "Rollback":"Quay lại phiên bản trước","Available official Qwen updates":"Bản cập nhật Qwen chính thức",
    "Check updates":"Kiểm tra cập nhật","Install selected update":"Cài bản cập nhật đã chọn","Ready":"Sẵn sàng",
    "Language":"Ngôn ngữ","English":"English","Vietnamese":"Tiếng Việt","PowerShell Download Guide":"Hướng dẫn tải bằng PowerShell",
}

def current_language() -> str:
    for arg in sys.argv[1:]:
        if arg.startswith("--lang="):
            return "vi" if arg.split("=",1)[1].lower().startswith("vi") else "en"
    env = os.environ.get("MT_AI_LANG", "").lower()
    if env:
        return "vi" if env.startswith("vi") else "en"
    return "vi"

def tr(text: str, lang: str | None = None) -> str:
    return VI.get(text, text) if (lang or current_language()) == "vi" else text

def localize_widget(root, lang: str | None = None) -> None:
    if (lang or current_language()) != "vi":
        return
    from PySide6.QtWidgets import QAbstractButton, QComboBox, QGroupBox, QLabel, QListWidget
    for obj in [root, *root.findChildren(object)]:
        if isinstance(obj, (QAbstractButton, QLabel, QGroupBox)):
            obj.setText(tr(obj.text(), "vi")) if hasattr(obj, "setText") else obj.setTitle(tr(obj.title(), "vi"))
        if isinstance(obj, QGroupBox):
            obj.setTitle(tr(obj.title(), "vi"))
        if isinstance(obj, QComboBox):
            for i in range(obj.count()):
                obj.setItemText(i, tr(obj.itemText(i), "vi"))
        if isinstance(obj, QListWidget):
            for i in range(obj.count()):
                obj.item(i).setText(tr(obj.item(i).text(), "vi"))
    if hasattr(root, "menuBar"):
        for action in root.menuBar().actions():
            action.setText(tr(action.text().replace("&",""), "vi"))
            menu = action.menu()
            if menu:
                for child in menu.actions():
                    child.setText(tr(child.text().replace("&",""), "vi"))


def reverse_tr(text: str) -> str:
    for source, translated in VI.items():
        if text == translated:
            return source
    return text

def relocalize_widget(root, lang: str) -> None:
    """Switch an already-created window between English and Vietnamese."""
    from PySide6.QtWidgets import QAbstractButton, QComboBox, QGroupBox, QLabel, QListWidget
    for obj in [root, *root.findChildren(object)]:
        if isinstance(obj, QAbstractButton):
            obj.setText(tr(reverse_tr(obj.text()), lang))
        if isinstance(obj, QLabel):
            obj.setText(tr(reverse_tr(obj.text()), lang))
        if isinstance(obj, QGroupBox):
            obj.setTitle(tr(reverse_tr(obj.title()), lang))
        if isinstance(obj, QComboBox):
            for i in range(obj.count()):
                obj.setItemText(i, tr(reverse_tr(obj.itemText(i)), lang))
        if isinstance(obj, QListWidget):
            for i in range(obj.count()):
                obj.item(i).setText(tr(reverse_tr(obj.item(i).text()), lang))
    if hasattr(root, "menuBar"):
        for action in root.menuBar().actions():
            action.setText(tr(reverse_tr(action.text().replace("&", "")), lang))
            menu = action.menu()
            if menu:
                for child in menu.actions():
                    child.setText(tr(reverse_tr(child.text().replace("&", "")), lang))
