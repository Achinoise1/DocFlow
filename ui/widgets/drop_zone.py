"""自定义UI组件 - 拖拽区域、文件列表项等"""
import os
import sys
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap


def _get_icon_path(filename: str) -> str:
    """返回 resources/icons/<filename> 的绝对路径，兼容 PyInstaller 打包。"""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        # ui/widgets/drop_zone.py -> ../../.. = 项目根目录
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, 'resources', 'icons', filename)


_FILE_TYPE_ICONS = {
    'word': _get_icon_path('word.svg'),
    'ppt':  _get_icon_path('ppt.svg'),
    'pdf':  _get_icon_path('pdf.svg'),
    'image': _get_icon_path('image.svg'),
}

from utils.file_utils import is_supported_file, get_file_type, get_friendly_size


class DropZone(QFrame):
    """拖拽上传区域"""
    files_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setObjectName('dropZone')
        self.setMinimumHeight(180)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.icon_label = QLabel('📂')
        self.icon_label.setObjectName('dropIcon')
        self.icon_label.setAlignment(Qt.AlignCenter)

        self.text_label = QLabel('拖拽文件到这里，或点击选择文件')
        self.text_label.setObjectName('dropText')
        self.text_label.setAlignment(Qt.AlignCenter)

        self.hint_label = QLabel('支持 Word、PPT、PDF、图片文件')
        self.hint_label.setObjectName('dropHint')
        self.hint_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.addWidget(self.hint_label)

    def set_hint(self, hint_text: str):
        """更新底部提示文字"""
        self.hint_label.setText(hint_text)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setProperty('dragOver', True)
            self.style().polish(self)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setProperty('dragOver', False)
        self.style().polish(self)

    def dropEvent(self, event: QDropEvent):
        self.setProperty('dragOver', False)
        self.style().polish(self)

        paths = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                paths.append(path)          # 目录：交给主窗口筛选展开
            elif os.path.isfile(path) and is_supported_file(path):
                paths.append(path)

        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()
        else:
            event.ignore()


class FileListItem(QWidget):
    """文件列表中的单个文件项（纯展示，不含任务状态）"""
    remove_clicked = Signal(str)

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setObjectName('fileListItem')

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # 文件类型图标
        file_type = get_file_type(file_path)
        icon_label = QLabel()
        icon_label.setFixedSize(28, 28)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setObjectName('fileIcon')
        icon_path = _FILE_TYPE_ICONS.get(file_type)
        if icon_path:
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                icon_label.setPixmap(
                    pixmap.scaled(22, 22, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )

        # 文件信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        name_label = QLabel(os.path.basename(file_path))
        name_label.setObjectName('fileName')
        size_label = QLabel(get_friendly_size(file_path))
        size_label.setObjectName('fileSize')
        info_layout.addWidget(name_label)
        info_layout.addWidget(size_label)

        # 删除按钮
        remove_btn = QPushButton('×')
        remove_btn.setObjectName('removeBtn')
        remove_btn.setFixedSize(28, 28)
        remove_btn.clicked.connect(lambda: self.remove_clicked.emit(self.file_path))

        layout.addWidget(icon_label)
        layout.addLayout(info_layout, 1)
        layout.addWidget(remove_btn)
