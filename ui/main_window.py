"""主窗口 - DocFlow 应用的核心界面"""
import os
import uuid
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QLabel, QComboBox, QFileDialog, QScrollArea,
    QFrame, QMessageBox, QSpinBox, QSplitter
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QIcon

from ui.widgets.drop_zone import DropZone, FileListItem
from core.task_manager import TaskManager
from utils.file_utils import (
    get_file_type, get_file_ext, get_output_path, is_supported_file,
    SUPPORTED_EXTENSIONS
)
from utils.logger import logger


class MainWindow(QMainWindow):
    """DocFlow 主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle('DocFlow - 文档转换工具')
        self.setMinimumSize(800, 600)
        self.resize(900, 680)

        # 任务管理器
        self.task_manager = TaskManager(self)
        self.task_manager.task_started.connect(self._on_task_started)
        self.task_manager.task_progress.connect(self._on_task_progress)
        self.task_manager.task_finished.connect(self._on_task_finished)
        self.task_manager.all_tasks_done.connect(self._on_all_done)

        # 文件列表数据: {file_path: {'widget': FileListItem, 'task_id': str}}
        self._file_items = {}
        self._output_dir = None

        self._init_ui()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(16, 12, 16, 12)

        # ===== 标题 =====
        title_label = QLabel('DocFlow')
        title_label.setObjectName('appTitle')
        subtitle_label = QLabel('本地离线文档转换工具')
        subtitle_label.setObjectName('appSubtitle')

        title_layout = QHBoxLayout()
        title_v = QVBoxLayout()
        title_v.setSpacing(2)
        title_v.addWidget(title_label)
        title_v.addWidget(subtitle_label)
        title_layout.addLayout(title_v)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)

        # ===== 功能选择 Tabs =====
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName('mainTabs')

        self.tab_pdf = self._create_tab_page('PDF转换', 'pdf')
        self.tab_image = self._create_tab_page('图片转换', 'image')
        self.tab_doc = self._create_tab_page('文档转换', 'doc')

        self.tab_widget.addTab(self.tab_pdf, '📕 PDF转换')
        self.tab_widget.addTab(self.tab_image, '🖼️ 图片转换')
        self.tab_widget.addTab(self.tab_doc, '📄 文档转换')

        main_layout.addWidget(self.tab_widget)

        # ===== 拖拽区域 =====
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        self.drop_zone.mousePressEvent = lambda e: self._browse_files()
        main_layout.addWidget(self.drop_zone)

        # ===== 文件列表区域 =====
        file_list_frame = QFrame()
        file_list_frame.setObjectName('fileListFrame')
        file_list_layout = QVBoxLayout(file_list_frame)
        file_list_layout.setContentsMargins(0, 0, 0, 0)
        file_list_layout.setSpacing(4)

        file_header = QHBoxLayout()
        self.file_count_label = QLabel('文件列表 (0)')
        self.file_count_label.setObjectName('fileCountLabel')
        clear_btn = QPushButton('清空列表')
        clear_btn.setObjectName('clearBtn')
        clear_btn.clicked.connect(self._clear_files)
        file_header.addWidget(self.file_count_label)
        file_header.addStretch()
        file_header.addWidget(clear_btn)
        file_list_layout.addLayout(file_header)

        # 可滚动文件列表
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(120)
        scroll_area.setMaximumHeight(250)
        scroll_area.setObjectName('fileScrollArea')

        self.file_list_container = QWidget()
        self.file_list_layout = QVBoxLayout(self.file_list_container)
        self.file_list_layout.setSpacing(4)
        self.file_list_layout.setContentsMargins(4, 4, 4, 4)
        self.file_list_layout.addStretch()

        scroll_area.setWidget(self.file_list_container)
        file_list_layout.addWidget(scroll_area)

        main_layout.addWidget(file_list_frame)

        # ===== 操作按钮 =====
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.output_btn = QPushButton('📁 选择输出目录')
        self.output_btn.setObjectName('outputBtn')
        self.output_btn.clicked.connect(self._select_output_dir)

        self.output_label = QLabel('输出到源文件目录')
        self.output_label.setObjectName('outputLabel')

        btn_layout.addWidget(self.output_btn)
        btn_layout.addWidget(self.output_label)
        btn_layout.addStretch()

        self.start_btn = QPushButton('▶ 开始转换')
        self.start_btn.setObjectName('startBtn')
        self.start_btn.setFixedHeight(40)
        self.start_btn.setMinimumWidth(140)
        self.start_btn.clicked.connect(self._start_conversion)

        self.cancel_btn = QPushButton('⏹ 取消全部')
        self.cancel_btn.setObjectName('cancelBtn')
        self.cancel_btn.setFixedHeight(40)
        self.cancel_btn.clicked.connect(self._cancel_all)
        self.cancel_btn.setEnabled(False)

        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.cancel_btn)

        main_layout.addLayout(btn_layout)

        # ===== 状态栏 =====
        self.statusBar().showMessage('就绪')

    def _create_tab_page(self, title: str, tab_type: str) -> QWidget:
        """创建一个功能Tab页面"""
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # 转换类型选择
        label = QLabel('转换方式:')
        combo = QComboBox()
        combo.setObjectName(f'combo_{tab_type}')
        combo.setMinimumWidth(200)

        if tab_type == 'pdf':
            combo.addItem('Word/PPT → PDF', 'to_pdf')
            combo.addItem('PDF → Word', 'pdf_to_word')
            combo.addItem('PDF → PPT', 'pdf_to_ppt')
            combo.addItem('PDF → 图片', 'pdf_to_image')
        elif tab_type == 'image':
            combo.addItem('图片 → PDF（合并）', 'images_to_pdf')
            combo.addItem('图片 → Word', 'images_to_word')
        elif tab_type == 'doc':
            combo.addItem('Word → PDF', 'to_pdf')
            combo.addItem('PPT → PDF', 'to_pdf')
            combo.addItem('PDF → Word', 'pdf_to_word')

        layout.addWidget(label)
        layout.addWidget(combo)

        # PDF转图片的选项
        if tab_type == 'pdf':
            fmt_label = QLabel('图片格式:')
            fmt_combo = QComboBox()
            fmt_combo.setObjectName('combo_img_format')
            fmt_combo.addItem('PNG', 'png')
            fmt_combo.addItem('JPG', 'jpg')
            fmt_combo.setFixedWidth(80)

            dpi_label = QLabel('DPI:')
            dpi_spin = QSpinBox()
            dpi_spin.setObjectName('spin_dpi')
            dpi_spin.setRange(72, 600)
            dpi_spin.setValue(200)
            dpi_spin.setSingleStep(50)
            dpi_spin.setFixedWidth(80)

            layout.addWidget(fmt_label)
            layout.addWidget(fmt_combo)
            layout.addWidget(dpi_label)
            layout.addWidget(dpi_spin)

        layout.addStretch()
        return page

    # ===== 文件操作 =====

    def _browse_files(self):
        """打开文件选择对话框"""
        filters = '所有支持的文件 (*.doc *.docx *.ppt *.pptx *.pdf *.jpg *.jpeg *.png);;' \
                  'Word文件 (*.doc *.docx);;PPT文件 (*.ppt *.pptx);;' \
                  'PDF文件 (*.pdf);;图片文件 (*.jpg *.jpeg *.png)'
        files, _ = QFileDialog.getOpenFileNames(self, '选择文件', '', filters)
        if files:
            self._add_files(files)

    def _on_files_dropped(self, files: list):
        self._add_files(files)

    def _add_files(self, file_paths: list):
        """添加文件到列表"""
        for path in file_paths:
            if path in self._file_items:
                continue

            item_widget = FileListItem(path)
            item_widget.remove_clicked.connect(self._remove_file)

            # 插入到 stretch 之前
            idx = self.file_list_layout.count() - 1
            self.file_list_layout.insertWidget(idx, item_widget)

            self._file_items[path] = {
                'widget': item_widget,
                'task_id': None
            }

        self._update_file_count()

    def _remove_file(self, file_path: str):
        """从列表中移除文件"""
        if file_path in self._file_items:
            widget = self._file_items[file_path]['widget']
            self.file_list_layout.removeWidget(widget)
            widget.deleteLater()
            del self._file_items[file_path]
            self._update_file_count()

    def _clear_files(self):
        """清空文件列表"""
        for path in list(self._file_items.keys()):
            self._remove_file(path)

    def _update_file_count(self):
        self.file_count_label.setText(f'文件列表 ({len(self._file_items)})')

    def _select_output_dir(self):
        """选择输出目录"""
        dir_path = QFileDialog.getExistingDirectory(self, '选择输出目录')
        if dir_path:
            self._output_dir = dir_path
            # 显示缩短路径
            display = dir_path if len(dir_path) <= 40 else '...' + dir_path[-37:]
            self.output_label.setText(f'输出到: {display}')

    # ===== 转换操作 =====

    def _get_current_conversion_type(self) -> str:
        """获取当前选中的转换类型"""
        current_tab = self.tab_widget.currentIndex()
        if current_tab == 0:
            combo = self.tab_pdf.findChild(QComboBox, 'combo_pdf')
        elif current_tab == 1:
            combo = self.tab_image.findChild(QComboBox, 'combo_image')
        else:
            combo = self.tab_doc.findChild(QComboBox, 'combo_doc')

        if combo:
            return combo.currentData()
        return 'to_pdf'

    def _get_pdf_to_image_options(self) -> dict:
        """获取PDF转图片的选项"""
        options = {}
        fmt_combo = self.tab_pdf.findChild(QComboBox, 'combo_img_format')
        dpi_spin = self.tab_pdf.findChild(QSpinBox, 'spin_dpi')
        if fmt_combo:
            options['format'] = fmt_combo.currentData()
        if dpi_spin:
            options['dpi'] = dpi_spin.value()
        return options

    def _start_conversion(self):
        """开始转换"""
        if not self._file_items:
            QMessageBox.warning(self, '提示', '请先添加文件')
            return

        conversion_type = self._get_current_conversion_type()

        # 批量图片合并模式
        if conversion_type in ('images_to_pdf', 'images_to_word'):
            self._start_batch_image_conversion(conversion_type)
            return

        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.statusBar().showMessage('正在转换...')

        options = {}
        if conversion_type == 'pdf_to_image':
            options = self._get_pdf_to_image_options()

        for path, item_data in self._file_items.items():
            task_id = str(uuid.uuid4())[:8]
            item_data['task_id'] = task_id
            item_data['widget'].set_waiting()

            self.task_manager.submit_task(
                task_id, path, conversion_type,
                self._output_dir, options
            )

    def _start_batch_image_conversion(self, conversion_type: str):
        """批量图片合并转换"""
        image_paths = [p for p in self._file_items.keys()
                       if get_file_type(p) == 'image']

        if not image_paths:
            QMessageBox.warning(self, '提示', '请添加图片文件')
            return

        ext = '.pdf' if conversion_type == 'images_to_pdf' else '.docx'
        outdir = self._output_dir or os.path.dirname(image_paths[0])
        output_path = get_output_path(
            os.path.join(outdir, f'合并文档{ext}'), ext, outdir
        )

        # 询问输出文件名
        save_path, _ = QFileDialog.getSaveFileName(
            self, '保存文件', output_path,
            'PDF文件 (*.pdf)' if ext == '.pdf' else 'Word文件 (*.docx)'
        )
        if not save_path:
            return

        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.statusBar().showMessage('正在合并...')

        task_id = str(uuid.uuid4())[:8]
        # 标记所有文件
        for item_data in self._file_items.values():
            item_data['task_id'] = task_id
            item_data['widget'].set_waiting()

        self.task_manager.submit_batch_image_task(
            task_id, image_paths, conversion_type, save_path
        )

    def _cancel_all(self):
        """取消所有转换"""
        self.task_manager.cancel_all()
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.statusBar().showMessage('已取消')

        for item_data in self._file_items.values():
            item_data['widget'].set_waiting()

    # ===== 任务回调 =====

    @Slot(str)
    def _on_task_started(self, task_id: str):
        for item_data in self._file_items.values():
            if item_data['task_id'] == task_id:
                item_data['widget'].set_converting()
                break

    @Slot(str, int)
    def _on_task_progress(self, task_id: str, percent: int):
        for item_data in self._file_items.values():
            if item_data['task_id'] == task_id:
                item_data['widget'].set_progress(percent)
                break

    @Slot(str, bool, str)
    def _on_task_finished(self, task_id: str, success: bool, message: str):
        for item_data in self._file_items.values():
            if item_data['task_id'] == task_id:
                if success:
                    item_data['widget'].set_status('✓ 完成', True)
                    item_data['widget'].set_progress(100)
                else:
                    item_data['widget'].set_status('✕ 失败', False)
                break

        if not success:
            self.statusBar().showMessage(f'转换失败: {message}')

    @Slot()
    def _on_all_done(self):
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.statusBar().showMessage('转换完成')

    # ===== 拖拽支持（窗口级别） =====

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path) and is_supported_file(path):
                files.append(path)
        if files:
            self._add_files(files)
