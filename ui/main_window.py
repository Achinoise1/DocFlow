"""主窗口 - DocFlow 应用的核心界面"""
import os
import sys
import uuid
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QLabel, QComboBox, QFileDialog,
    QFrame, QMessageBox, QSpinBox, QCheckBox
)
from PySide6.QtCore import Qt, Slot, QSettings
from PySide6.QtGui import QIcon

from ui.widgets.drop_zone import DropZone
from ui.widgets.file_list_widget import FileListWidget
from ui.widgets.help_dialog import HelpDialog
from core.task_manager import TaskManager
from core.conversion_registry import get_by_id, get_by_tab
from ui.theme_manager import ThemeManager
from utils.file_utils import (
    get_file_type, get_file_ext, get_output_path, is_supported_file
)
from utils.logger import logger


class MainWindow(QMainWindow):
    """DocFlow 主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle('DocFlow - 文档转换工具')
        self.setMinimumSize(800, 600)
        self.resize(900, 680)

        # 设置窗口图标
        if getattr(sys, 'frozen', False):
            icon_path = os.path.join(sys._MEIPASS, 'resources', 'icons', 'app_icon.svg')
        else:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'resources', 'icons', 'app_icon.svg')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # 任务管理器
        self.task_manager = TaskManager(self)
        self.task_manager.task_started.connect(self._on_task_started)
        self.task_manager.task_progress.connect(self._on_task_progress)
        self.task_manager.task_finished.connect(self._on_task_finished)
        self.task_manager.all_tasks_done.connect(self._on_all_done)

        self._output_dir = None
        self._output_paths = []

        # 用户设置
        self._settings = QSettings('DocFlow', 'DocFlow')
        self._theme_manager = ThemeManager(self._settings)
        self._current_theme = self._theme_manager.load_saved_theme()

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

        self.help_btn = QPushButton('❓')
        self.help_btn.setObjectName('themeBtn')
        self.help_btn.setFixedSize(36, 36)
        self.help_btn.setToolTip('使用指南')
        self.help_btn.clicked.connect(self._show_help)
        title_layout.addWidget(self.help_btn)

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

        # 拖拽区下方：快捷选择按钮行
        quick_bar = QHBoxLayout()
        quick_bar.setContentsMargins(0, 0, 0, 0)
        quick_bar.setSpacing(8)
        browse_files_btn = QPushButton('📄 选择文件')
        browse_files_btn.setObjectName('outputBtn')
        browse_files_btn.clicked.connect(self._browse_files)
        browse_dir_btn = QPushButton('📁 选择目录')
        browse_dir_btn.setObjectName('outputBtn')
        browse_dir_btn.clicked.connect(self._browse_directory)
        quick_bar.addWidget(browse_files_btn)
        quick_bar.addWidget(browse_dir_btn)
        quick_bar.addStretch()
        main_layout.addLayout(quick_bar)

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

        self.file_list_widget = FileListWidget()
        self.file_list_widget.file_count_changed.connect(self._update_file_count)
        file_list_layout.addWidget(self.file_list_widget)

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

        # 初始化拖拽区域提示文字
        self._on_conversion_type_changed()

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

        for entry in get_by_tab(tab_type):
            combo.addItem(entry['label'], entry['id'])

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
        """切换转换类型时：更新提示文字、剔除不兼容文件"""
        conversion_type = self._get_current_conversion_type()
        entry = get_by_id(conversion_type)
        hint = entry['hint_text'] if entry else '支持 Word、PPT、PDF、图片文件'
        self.drop_zone.set_hint(hint)
        self._filter_files_for_current_type()

    def _filter_files_for_current_type(self):
        """剔除文件列表中不符合当前转换类型的文件"""
        if not self.file_list_widget.file_paths:
            return
        conversion_type = self._get_current_conversion_type()
        accepted_exts = self._get_accepted_extensions(conversion_type)
        if not accepted_exts:
            return

        to_remove = [
            path for path in self.file_list_widget.file_paths
            if get_file_ext(path) not in accepted_exts
        ]
        for path in to_remove:
            self.file_list_widget.remove_file(path)

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

    def _browse_directory(self):
        """打开目录选择对话框，自动筛选匹配文件"""
        dir_path = QFileDialog.getExistingDirectory(self, '选择目录')
        if dir_path:
            self._add_files([dir_path])

    def _on_files_dropped(self, paths: list):
        self._add_files(paths)

    def _add_files(self, file_paths: list):
        """添加文件到列表，校验类型；目录路径会被自动展开"""
        conversion_type = self._get_current_conversion_type()
        accepted_exts = self._get_accepted_extensions(conversion_type)
        rejected = self.file_list_widget.add_files(file_paths, accepted_exts)
        if rejected:
            QMessageBox.warning(
                self, '文件类型不匹配',
                f'以下文件与当前转换模式不匹配，已忽略：\n' + '\n'.join(rejected)
            )

    def _clear_files(self):
        """清空文件列表"""
        self.file_list_widget.clear_files()

    def _update_file_count(self, count: int = None):
        if count is None:
            count = len(self.file_list_widget.file_paths)
        self.file_count_label.setText(f'文件列表 ({count})')

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
        entry = get_by_id(conversion_type)
        return entry['input_exts'] if entry else []

    def _start_conversion(self):
        """开始转换"""
        if not self.file_list_widget.file_paths:
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

        # 只处理未完成的文件，类型不匹配则跳过
        pending_paths = []
        skipped = []
        for p in self.file_list_widget.pending_paths:
            ext = get_file_ext(p)
            if accepted_exts and ext not in accepted_exts:
                skipped.append(os.path.basename(p))
                self.file_list_widget.mark_skipped(p)
            else:
                pending_paths.append(p)

        if skipped:
            QMessageBox.warning(
                self, '文件类型不匹配',
                f'以下文件不支持当前转换类型，已跳过：\n{", ".join(skipped)}'
            )

        if not pending_paths:
            if not skipped:
                QMessageBox.information(self, '提示', '所有文件已转换完成，请添加新文件')
            return

        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.statusBar().showMessage('正在转换...')

        for path in pending_paths:
            task_id = str(uuid.uuid4())[:8]
            self.file_list_widget.set_task_id(path, task_id)
            self.task_manager.submit_task(
                task_id, path, conversion_type,
                self._output_dir, options
            )

    def _start_batch_image_conversion(self, conversion_type: str):
        """批量图片合并转换"""
        image_paths = [
            p for p in self.file_list_widget.pending_paths
            if get_file_type(p) == 'image'
        ]

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
        for path in image_paths:
            self.file_list_widget.set_task_id(path, task_id)

        self.task_manager.submit_batch_image_task(
            task_id, image_paths, conversion_type, save_path
        )

    def _cancel_all(self):
        """取消所有转换"""
        self.task_manager.cancel_all()
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.statusBar().showMessage('已取消')
        self.file_list_widget.reset_all_tasks()

    # ===== 任务回调 =====

    @Slot(str)
    def _on_task_started(self, task_id: str):
        self.file_list_widget.update_task_state(task_id, 'started')

    @Slot(str, int)
    def _on_task_progress(self, task_id: str, percent: int):
        self.file_list_widget.update_task_state(task_id, 'progress', percent=percent)

    @Slot(str, bool, str, str)
    def _on_task_finished(self, task_id: str, success: bool, message: str, output_path: str):
        paths = self.file_list_widget.update_task_state(
            task_id, 'finished', success=success, output_path=output_path
        )
        self._output_paths.extend(paths)
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
        self._theme_manager.apply(theme_name)
        self._current_theme = theme_name
        self._update_theme_button()

    def _show_help(self):
        dlg = HelpDialog(self)
        dlg.exec()

    def _toggle_theme(self):
        new_theme = self._theme_manager.toggle(self._current_theme)
        self._apply_theme(new_theme)

    def _update_theme_button(self):
        self.theme_btn.setText(self._theme_manager.get_button_icon(self._current_theme))
        tooltip = '切换到深色主题' if self._current_theme == 'light' else '切换到浅色主题'
        self.theme_btn.setToolTip(tooltip)
