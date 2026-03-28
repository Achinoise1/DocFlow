"""主窗口 - DocFlow 应用的核心界面"""
import os
import uuid
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QLabel, QComboBox, QFileDialog, QScrollArea,
    QFrame, QMessageBox, QSpinBox, QSplitter, QCheckBox, QApplication
)
from PySide6.QtCore import Qt, Slot, QSettings
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

        # 文件列表数据: {file_path: {'widget': FileListItem, 'task_id': str, 'done': bool}}
        self._file_items = {}
        self._output_dir = None
        self._output_paths = []

        # 用户设置
        self._settings = QSettings('DocFlow', 'DocFlow')
        self._current_theme = self._settings.value('theme', 'light')

        self._init_ui()
        self._apply_theme(self._current_theme)

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

        self.theme_btn = QPushButton('🌙')
        self.theme_btn.setObjectName('themeBtn')
        self.theme_btn.setFixedSize(36, 36)
        self.theme_btn.setToolTip('切换主题')
        self.theme_btn.clicked.connect(self._toggle_theme)
        title_layout.addWidget(self.theme_btn)

        main_layout.addLayout(title_layout)

        # ===== 功能选择 Tabs =====
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName('mainTabs')

        self.tab_doc = self._create_tab_page('文档转换', 'doc')
        self.tab_pdf = self._create_tab_page('PDF转换', 'pdf')
        self.tab_image = self._create_tab_page('图片转换', 'image')

        self.tab_widget.addTab(self.tab_doc, '📄 文档转换')
        self.tab_widget.addTab(self.tab_pdf, '📕 PDF转换')
        self.tab_widget.addTab(self.tab_image, '🖼️ 图片转换')

        # 切换Tab时自动剔除不兼容文件
        self.tab_widget.currentChanged.connect(self._on_conversion_type_changed)
        # doc tab的combo切换时也要处理
        doc_combo = self.tab_doc.findChild(QComboBox, 'combo_doc')
        if doc_combo:
            doc_combo.currentIndexChanged.connect(self._on_conversion_type_changed)

        # 固定高度，避免Tab面板撑开
        self.tab_widget.setMaximumHeight(80)

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

        self.auto_open_check = QCheckBox('转换完成后自动打开')
        self.auto_open_check.setChecked(True)
        self.auto_open_check.setObjectName('autoOpenCheck')
        btn_layout.addWidget(self.auto_open_check)

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
        page.setFixedHeight(40)
        layout = QHBoxLayout(page)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)

        # 转换类型选择
        label = QLabel('转换方式:')
        combo = QComboBox()
        combo.setObjectName(f'combo_{tab_type}')
        combo.setMinimumWidth(200)

        if tab_type == 'pdf':
            combo.addItem('PDF → Word', 'pdf_to_word')
            combo.addItem('PDF → PPT', 'pdf_to_ppt')
            combo.addItem('PDF → 图片', 'pdf_to_image')
        elif tab_type == 'image':
            combo.addItem('图片 → PDF（合并）', 'images_to_pdf')
            combo.addItem('图片 → Word', 'images_to_word')
        elif tab_type == 'doc':
            combo.addItem('Word → PDF', 'word_to_pdf')
            combo.addItem('PPT → PDF', 'ppt_to_pdf')

        layout.addWidget(label)
        layout.addWidget(combo)

        # PDF转图片的选项（默认隐藏，只在选择PDF→图片时显示）
        if tab_type == 'pdf':
            self._fmt_label = QLabel('图片格式:')
            self._fmt_combo = QComboBox()
            self._fmt_combo.setObjectName('combo_img_format')
            self._fmt_combo.addItem('PNG', 'png')
            self._fmt_combo.addItem('JPG', 'jpg')
            self._fmt_combo.setFixedWidth(80)

            self._dpi_label = QLabel('DPI:')

            dpi_minus = QPushButton('−')
            dpi_minus.setObjectName('dpiBtn')
            dpi_minus.setFixedSize(28, 28)

            self._dpi_spin = QSpinBox()
            self._dpi_spin.setObjectName('spin_dpi')
            self._dpi_spin.setRange(72, 600)
            self._dpi_spin.setValue(200)
            self._dpi_spin.setSingleStep(50)
            self._dpi_spin.setFixedWidth(60)
            self._dpi_spin.setButtonSymbols(QSpinBox.NoButtons)
            self._dpi_spin.setAlignment(Qt.AlignCenter)

            dpi_plus = QPushButton('+')
            dpi_plus.setObjectName('dpiBtn')
            dpi_plus.setFixedSize(28, 28)

            dpi_minus.clicked.connect(lambda: self._dpi_spin.stepDown())
            dpi_plus.clicked.connect(lambda: self._dpi_spin.stepUp())

            self._pdf_image_widgets = [
                self._fmt_label, self._fmt_combo,
                self._dpi_label, dpi_minus, self._dpi_spin, dpi_plus
            ]

            for w in self._pdf_image_widgets:
                layout.addWidget(w)
                w.setVisible(False)

            combo.currentIndexChanged.connect(self._on_pdf_combo_changed)

        layout.addStretch()
        return page

    def _on_pdf_combo_changed(self, index: int):
        """根据PDF Tab选择显示/隐藏DPI选项"""
        combo = self.tab_pdf.findChild(QComboBox, 'combo_pdf')
        is_pdf_to_image = combo and combo.currentData() == 'pdf_to_image'
        for w in self._pdf_image_widgets:
            w.setVisible(is_pdf_to_image)
    def _on_conversion_type_changed(self, _=None):
        """切换转换类型时自动剔除列表中不兼容的文件"""
        self._filter_files_for_current_type()

    def _filter_files_for_current_type(self):
        """剔除文件列表中不符合当前转换类型的文件"""
        if not self._file_items:
            return
        conversion_type = self._get_current_conversion_type()
        accepted_exts = self._get_accepted_extensions(conversion_type)
        if not accepted_exts:
            return

        to_remove = [
            path for path in list(self._file_items.keys())
            if get_file_ext(path) not in accepted_exts
        ]
        for path in to_remove:
            self._remove_file(path)

        if to_remove:
            names = ', '.join(os.path.basename(p) for p in to_remove)
            self.statusBar().showMessage(f'已移除不匹配的文件：{names}', 4000)
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
        """添加文件到列表，上传时立即校验类型"""
        conversion_type = self._get_current_conversion_type()
        accepted_exts = self._get_accepted_extensions(conversion_type)

        rejected = []
        for path in file_paths:
            if path in self._file_items:
                continue

            # 上传时立即校验，不匹配则拒绝
            if accepted_exts:
                ext = get_file_ext(path)
                if ext not in accepted_exts:
                    rejected.append(os.path.basename(path))
                    continue

            item_widget = FileListItem(path)
            item_widget.remove_clicked.connect(self._remove_file)

            # 插入到 stretch 之前
            idx = self.file_list_layout.count() - 1
            self.file_list_layout.insertWidget(idx, item_widget)

            self._file_items[path] = {
                'widget': item_widget,
                'task_id': None,
                'done': False
            }

        if rejected:
            QMessageBox.warning(
                self, '文件类型不匹配',
                f'以下文件与当前转换模式不匹配，已忽略：\n' + '\n'.join(rejected)
            )

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
            combo = self.tab_doc.findChild(QComboBox, 'combo_doc')
        elif current_tab == 1:
            combo = self.tab_pdf.findChild(QComboBox, 'combo_pdf')
        else:
            combo = self.tab_image.findChild(QComboBox, 'combo_image')

        if combo:
            return combo.currentData()
        return 'to_pdf'

    def _get_pdf_to_image_options(self) -> dict:
        """获取PDF转图片的选项"""
        options = {}
        if hasattr(self, '_fmt_combo') and self._fmt_combo:
            options['format'] = self._fmt_combo.currentData()
        if hasattr(self, '_dpi_spin') and self._dpi_spin:
            options['dpi'] = self._dpi_spin.value()
        return options

    def _get_accepted_extensions(self, conversion_type: str) -> list:
        """根据转换类型获取允许的输入文件扩展名"""
        ext_map = {
            'word_to_pdf': ['.doc', '.docx'],
            'ppt_to_pdf':  ['.ppt', '.pptx'],
            'to_pdf':      ['.doc', '.docx', '.ppt', '.pptx'],
            'pdf_to_word': ['.pdf'],
            'pdf_to_ppt':  ['.pdf'],
            'pdf_to_image': ['.pdf'],
            'images_to_pdf': ['.jpg', '.jpeg', '.png'],
            'images_to_word': ['.jpg', '.jpeg', '.png'],
        }
        return ext_map.get(conversion_type, [])

    def _start_conversion(self):
        """开始转换"""
        if not self._file_items:
            QMessageBox.warning(self, '提示', '请先添加文件')
            return

        self._output_paths.clear()
        conversion_type = self._get_current_conversion_type()

        # 批量图片合并模式
        if conversion_type in ('images_to_pdf', 'images_to_word'):
            self._start_batch_image_conversion(conversion_type)
            return

        # 获取当前转换类型接受的文件扩展名
        accepted_exts = self._get_accepted_extensions(conversion_type)

        options = {}
        if conversion_type == 'pdf_to_image':
            options = self._get_pdf_to_image_options()

        # 只处理未完成的文件
        pending = {}
        skipped = []
        for p, d in self._file_items.items():
            if d['done']:
                continue
            ext = get_file_ext(p)
            if accepted_exts and ext not in accepted_exts:
                skipped.append(os.path.basename(p))
                d['widget'].set_status('类型不匹配', False)
            else:
                pending[p] = d

        if skipped:
            QMessageBox.warning(
                self, '文件类型不匹配',
                f'以下文件不支持当前转换类型，已跳过：\n{", ".join(skipped)}'
            )

        if not pending:
            if not skipped:
                QMessageBox.information(self, '提示', '所有文件已转换完成，请添加新文件')
            return

        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.statusBar().showMessage('正在转换...')

        for path, item_data in pending.items():
            task_id = str(uuid.uuid4())[:8]
            item_data['task_id'] = task_id
            item_data['widget'].set_waiting()

            self.task_manager.submit_task(
                task_id, path, conversion_type,
                self._output_dir, options
            )

    def _start_batch_image_conversion(self, conversion_type: str):
        """批量图片合并转换"""
        image_paths = [p for p, d in self._file_items.items()
                       if get_file_type(p) == 'image' and not d['done']]

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
        # 只标记参与合并的图片文件
        for path, item_data in self._file_items.items():
            if path in image_paths:
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
            item_data['done'] = False
            item_data['task_id'] = None

    # ===== 任务回调 =====

    @Slot(str)
    def _on_task_started(self, task_id: str):
        for item_data in self._file_items.values():
            if item_data['task_id'] == task_id:
                item_data['widget'].set_converting()

    @Slot(str, int)
    def _on_task_progress(self, task_id: str, percent: int):
        for item_data in self._file_items.values():
            if item_data['task_id'] == task_id:
                item_data['widget'].set_progress(percent)

    @Slot(str, bool, str, str)
    def _on_task_finished(self, task_id: str, success: bool, message: str, output_path: str):
        for item_data in self._file_items.values():
            if item_data['task_id'] == task_id:
                if success:
                    item_data['widget'].set_status('✓ 完成', True)
                    item_data['widget'].set_progress(100)
                    item_data['done'] = True
                    if output_path:
                        self._output_paths.append(output_path)
                else:
                    item_data['widget'].set_status('✕ 失败', False)
                # 不 break，批量任务多个文件共享同一 task_id

        if not success:
            self.statusBar().showMessage(f'转换失败: {message}')

    @Slot()
    def _on_all_done(self):
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.statusBar().showMessage('转换完成')

        if self.auto_open_check.isChecked() and self._output_paths:
            if len(self._output_paths) <= 3:
                for path in self._output_paths:
                    if os.path.exists(path):
                        os.startfile(path)
            else:
                folder = os.path.dirname(self._output_paths[0])
                if os.path.isdir(folder):
                    os.startfile(folder)
            self._output_paths.clear()

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

    # ===== 主题切换 =====

    def _apply_theme(self, theme_name: str):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if theme_name == 'dark':
            qss_file = os.path.join(base_dir, 'resources', 'styles.qss')
        else:
            qss_file = os.path.join(base_dir, 'resources', 'styles_light.qss')

        if os.path.exists(qss_file):
            with open(qss_file, 'r', encoding='utf-8') as f:
                QApplication.instance().setStyleSheet(f.read())

        self._current_theme = theme_name
        self._settings.setValue('theme', theme_name)
        self._update_theme_button()

    def _toggle_theme(self):
        new_theme = 'dark' if self._current_theme == 'light' else 'light'
        self._apply_theme(new_theme)

    def _update_theme_button(self):
        if self._current_theme == 'light':
            self.theme_btn.setText('🌙')
            self.theme_btn.setToolTip('切换到深色主题')
        else:
            self.theme_btn.setText('☀️')
            self.theme_btn.setToolTip('切换到浅色主题')
