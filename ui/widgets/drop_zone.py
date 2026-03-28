"""自定义UI组件 - 拖拽区域、文件列表项等"""
import os
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QProgressBar,
    QPushButton, QListWidget, QListWidgetItem, QAbstractItemView,
    QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent

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

        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path) and is_supported_file(path):
                files.append(path)

        if files:
            self.files_dropped.emit(files)
            event.acceptProposedAction()
        else:
            event.ignore()


class FileListItem(QWidget):
    """文件列表中的单个文件项"""
    remove_clicked = Signal(str)

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setObjectName('fileListItem')

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # 文件类型图标
        file_type = get_file_type(file_path)
        icon_map = {
            'word': '📄', 'ppt': '📊', 'pdf': '📕', 'image': '🖼️'
        }
        icon_label = QLabel(icon_map.get(file_type, '📎'))
        icon_label.setFixedWidth(30)
        icon_label.setObjectName('fileIcon')

        # 文件信息
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        name_label = QLabel(os.path.basename(file_path))
        name_label.setObjectName('fileName')
        size_label = QLabel(get_friendly_size(file_path))
        size_label.setObjectName('fileSize')
        info_layout.addWidget(name_label)
        info_layout.addWidget(size_label)

        # 状态和进度
        self.status_label = QLabel('等待中')
        self.status_label.setObjectName('fileStatus')
        self.status_label.setFixedWidth(80)
        self.status_label.setAlignment(Qt.AlignCenter)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(120)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setObjectName('fileProgress')

        # 删除按钮
        remove_btn = QPushButton('✕')
        remove_btn.setObjectName('removeBtn')
        remove_btn.setFixedSize(28, 28)
        remove_btn.clicked.connect(lambda: self.remove_clicked.emit(self.file_path))

        layout.addWidget(icon_label)
        layout.addLayout(info_layout, 1)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label)
        layout.addWidget(remove_btn)

    def set_status(self, status: str, success: bool = True):
        self.status_label.setText(status)
        if success:
            self.status_label.setProperty('state', 'success')
        else:
            self.status_label.setProperty('state', 'error')
        self.status_label.style().polish(self.status_label)

    def set_progress(self, value: int):
        self.progress_bar.setValue(value)

    def set_waiting(self):
        self.status_label.setText('等待中')
        self.status_label.setProperty('state', 'waiting')
        self.status_label.style().polish(self.status_label)
        self.progress_bar.setValue(0)

    def set_converting(self):
        self.status_label.setText('转换中...')
        self.status_label.setProperty('state', 'converting')
        self.status_label.style().polish(self.status_label)
