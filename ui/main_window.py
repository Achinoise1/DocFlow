"""主窗口 - DocFlow 应用的核心界面"""
import os
import sys
import uuid
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QLabel, QComboBox, QFileDialog,
    QFrame, QMessageBox, QSpinBox, QCheckBox, QSplitter
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QIcon, QGuiApplication

from ui.widgets.drop_zone import DropZone
from ui.widgets.file_list_widget import FileListWidget
from ui.widgets.task_list_widget import TaskListWidget
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
        self._last_tab_index = 0       # 用于 Tab 切换回滚
        self._last_doc_combo_index = 0  # 用于 doc combo 切换回滚

        self._theme_manager = ThemeManager()

        self._init_ui()
        self._theme_manager.apply_system_theme()

        # 跟随系统外观变化自动切换主题
        QGuiApplication.styleHints().colorSchemeChanged.connect(
            lambda _: self._theme_manager.apply_system_theme()
        )

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

        # 切换Tab时清空文件列表（含确认弹窗）
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        # doc tab 的 combo 切换时，若扩展名不同同样弹确认框
        doc_combo = self.tab_doc.findChild(QComboBox, 'combo_doc')
        if doc_combo:
            doc_combo.currentIndexChanged.connect(self._on_doc_combo_type_changed)

        # 固定高度，避免Tab面板撑开
        self.tab_widget.setMaximumHeight(80)

        main_layout.addWidget(self.tab_widget)

        # ===== 左右分栏 (QSplitter) =====
        splitter = QSplitter(Qt.Horizontal)
        splitter.setObjectName('mainSplitter')
        splitter.setChildrenCollapsible(False)

        # ── 左侧：拖拽区 + 文件列表 ──────────────────────────────────
        left_panel = QWidget()
        left_panel.setMinimumWidth(220)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 4, 0)
        left_layout.setSpacing(6)

        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        self.drop_zone.mousePressEvent = lambda e: self._browse_files()
        left_layout.addWidget(self.drop_zone)

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
        left_layout.addLayout(quick_bar)

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
        left_layout.addWidget(file_list_frame, 1)

        # ── 右侧：任务列表 ───────────────────────────────────────────
        right_panel = QWidget()
        right_panel.setMinimumWidth(220)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 0, 0, 0)
        right_layout.setSpacing(0)

        self.task_list_widget = TaskListWidget()
        self.task_list_widget.retry_requested.connect(self._on_retry_requested)
        right_layout.addWidget(self.task_list_widget)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([450, 450])
        main_layout.addWidget(splitter, 1)

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

    def _get_conversion_type_for_tab(self, tab_index: int) -> str:
        """返回指定 Tab 索引对应的当前转换类型 ID。"""
        if tab_index == 0:
            combo = self.tab_doc.findChild(QComboBox, 'combo_doc')
        elif tab_index == 1:
            combo = self.tab_pdf.findChild(QComboBox, 'combo_pdf')
        else:
            combo = self.tab_image.findChild(QComboBox, 'combo_image')
        return combo.currentData() if combo else 'to_pdf'

    def _exts_changed(self, old_type: str, new_type: str) -> bool:
        """判断两种转换类型的接受扩展名集合是否不同，
        且文件列表非空。满足两个条件才需要清空确认。"""
        if not self.file_list_widget.file_paths:
            return False
        return set(self._get_accepted_extensions(old_type)) != \
               set(self._get_accepted_extensions(new_type))

    def _ask_clear_confirm(self) -> bool:
        """弹出确认对话框，用户确认则清空文件列表并返回 True，取消返回 False。"""
        reply = QMessageBox.question(
            self, '切换转换类型',
            '当前文件列表中的文件类型与新转换类型不匹配，切换将清空文件列表。是否继续？',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.file_list_widget.clear_files()
            return True
        return False

    def _on_tab_changed(self, index: int):
        """切换 Tab 时：若新旧转换类型接受扩展名不同且文件列表非空，则弹确认框。"""
        old_type = self._get_conversion_type_for_tab(self._last_tab_index)
        new_type = self._get_conversion_type_for_tab(index)
        if self._exts_changed(old_type, new_type):
            if not self._ask_clear_confirm():
                self.tab_widget.blockSignals(True)
                self.tab_widget.setCurrentIndex(self._last_tab_index)
                self.tab_widget.blockSignals(False)
                return
        self._last_tab_index = index
        self._on_conversion_type_changed()

    def _on_doc_combo_type_changed(self, new_index: int):
        """文档转换 Tab 内切换子类型：若扩展名不同且文件列表非空，则弹确认框。"""
        combo = self.tab_doc.findChild(QComboBox, 'combo_doc')
        if not combo:
            return
        old_type = combo.itemData(self._last_doc_combo_index)
        new_type = combo.itemData(new_index)
        if self._exts_changed(old_type, new_type):
            if not self._ask_clear_confirm():
                combo.blockSignals(True)
                combo.setCurrentIndex(self._last_doc_combo_index)
                combo.blockSignals(False)
                return
        self._last_doc_combo_index = new_index
        self._on_conversion_type_changed()

    def _on_conversion_type_changed(self, _=None):
        """更新拖拽区提示文字（切换 Tab 或 combo 时调用）。"""
        conversion_type = self._get_current_conversion_type()
        entry = get_by_id(conversion_type)
        hint = entry['hint_text'] if entry else '支持 Word、PPT、PDF、图片文件'
        self.drop_zone.set_hint(hint)

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

    def _ensure_libreoffice(self, conversion_type: str) -> bool:
        """
        当转换类型需要 LibreOffice（非 Windows）时，检查其是否已安装。
        若未安装则弹出安装引导对话框。返回 True 表示可以继续转换。
        """
        import sys
        if sys.platform == 'win32':
            return True  # Windows 使用 COM，不需要 LibreOffice
        if conversion_type not in ('word_to_pdf', 'ppt_to_pdf'):
            return True  # 仅 Office → PDF 需要 LibreOffice

        from utils.libreoffice_manager import is_installed
        if is_installed():
            return True

        # 先静默安装（极简进度对话框，无需用户操作）
        from ui.widgets.libreoffice_setup_dialog import (
            LibreOfficeSilentInstallDialog, LibreOfficeSetupDialog,
        )
        silent_dlg = LibreOfficeSilentInstallDialog(parent=self)
        silent_dlg.exec()
        if silent_dlg.is_success():
            return True

        # 静默安装失败/取消，弹出引导对话框供用户重试或手动安装
        dlg = LibreOfficeSetupDialog(parent=self)
        dlg.exec()
        return dlg.is_ready()

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

        # 非 Windows 平台且需要 Office 转换时，确保 LibreOffice 已安装
        if not self._ensure_libreoffice(conversion_type):
            return

        accepted_exts = self._get_accepted_extensions(conversion_type)

        options = {}
        if conversion_type == 'pdf_to_image':
            options = self._get_pdf_to_image_options()

        # 校验文件类型，剔除不匹配项
        to_submit = []
        skipped = []
        for p in self.file_list_widget.file_paths:
            ext = get_file_ext(p)
            if accepted_exts and ext not in accepted_exts:
                skipped.append(os.path.basename(p))
            else:
                to_submit.append(p)

        if skipped:
            QMessageBox.warning(
                self, '文件类型不匹配',
                f'以下文件不支持当前转换类型，已跳过：\n{", ".join(skipped)}'
            )

        if not to_submit:
            return

        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.statusBar().showMessage('正在转换...')

        for path in to_submit:
            task_id = str(uuid.uuid4())[:8]
            snapshot = {
                'task_id': task_id,
                'title': os.path.basename(path),
                'conversion_type': conversion_type,
                'input_path': path,
                'image_paths': None,
                'output_dir': self._output_dir,
                'output_path': None,
                'options': options,
                'is_batch': False,
            }
            self.task_list_widget.add_task(snapshot)
            self.file_list_widget.remove_file(path)
            self.task_manager.submit_task(
                task_id, path, conversion_type,
                self._output_dir, options
            )

    def _start_batch_image_conversion(self, conversion_type: str):
        """批量图片合并转换"""
        image_paths = [
            p for p in self.file_list_widget.file_paths
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
        n = len(image_paths)
        snapshot = {
            'task_id': task_id,
            'title': f'合并 {n} 张图片 → {os.path.basename(save_path)}',
            'conversion_type': conversion_type,
            'input_path': None,
            'image_paths': image_paths,
            'output_dir': self._output_dir,
            'output_path': save_path,
            'options': {},
            'is_batch': True,
        }
        self.task_list_widget.add_task(snapshot)
        for path in image_paths:
            self.file_list_widget.remove_file(path)

        self.task_manager.submit_batch_image_task(
            task_id, image_paths, conversion_type, save_path
        )

    def _cancel_all(self):
        """取消所有转换"""
        self.task_manager.cancel_all()
        self.task_list_widget.cancel_all_pending()
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.statusBar().showMessage('已取消')

    # ===== 重试 =====

    def _on_retry_requested(self, task_id: str):
        """处理任务列表中的重试/重新开始请求。"""
        snapshot = self.task_list_widget.get_snapshot(task_id)
        if not snapshot:
            return
        if snapshot['is_batch']:
            self._retry_batch_task(task_id, snapshot)
        else:
            self._retry_single_task(task_id, snapshot)

    def _retry_single_task(self, old_task_id: str, snapshot: dict):
        input_path = snapshot['input_path']
        if not os.path.exists(input_path):
            QMessageBox.warning(self, '文件不存在',
                f'源文件已不存在：\n{input_path}')
            return
        new_task_id = str(uuid.uuid4())[:8]
        new_snapshot = dict(snapshot)
        new_snapshot['task_id'] = new_task_id
        self.task_list_widget.reset_task(old_task_id, new_task_id, new_snapshot)
        self.task_manager.submit_task(
            new_task_id, input_path,
            snapshot['conversion_type'],
            snapshot['output_dir'],
            snapshot['options']
        )
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.statusBar().showMessage('正在重试...')

    def _retry_batch_task(self, old_task_id: str, snapshot: dict):
        image_paths = snapshot['image_paths']
        missing = [p for p in image_paths if not os.path.exists(p)]
        if missing:
            QMessageBox.warning(self, '文件不存在',
                '以下源文件已不存在：\n' + '\n'.join(os.path.basename(p) for p in missing))
            return
        conversion_type = snapshot['conversion_type']
        ext = '.pdf' if conversion_type == 'images_to_pdf' else '.docx'
        outdir = snapshot['output_dir'] or os.path.dirname(image_paths[0])
        default_path = get_output_path(
            os.path.join(outdir, f'合并文档{ext}'), ext, outdir
        )
        save_path, _ = QFileDialog.getSaveFileName(
            self, '保存文件', default_path,
            'PDF文件 (*.pdf)' if ext == '.pdf' else 'Word文件 (*.docx)'
        )
        if not save_path:
            return
        new_task_id = str(uuid.uuid4())[:8]
        n = len(image_paths)
        new_snapshot = dict(snapshot)
        new_snapshot['task_id'] = new_task_id
        new_snapshot['title'] = f'合并 {n} 张图片 → {os.path.basename(save_path)}'
        new_snapshot['output_path'] = save_path
        self.task_list_widget.reset_task(old_task_id, new_task_id, new_snapshot)
        self.task_manager.submit_batch_image_task(
            new_task_id, image_paths, conversion_type, save_path
        )
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.statusBar().showMessage('正在合并...')

    # ===== 任务回调 =====

    @Slot(str)
    def _on_task_started(self, task_id: str):
        self.task_list_widget.on_task_started(task_id)

    @Slot(str, int)
    def _on_task_progress(self, task_id: str, percent: int):
        self.task_list_widget.on_task_progress(task_id, percent)

    @Slot(str, bool, str, str)
    def _on_task_finished(self, task_id: str, success: bool, message: str, output_path: str):
        collected = self.task_list_widget.on_task_finished(
            task_id, success, message, output_path
        )
        self._output_paths.extend(collected)
        if not success:
            self.statusBar().showMessage(f'转换失败: {message}')

    @Slot()
    def _on_all_done(self):
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.statusBar().showMessage('转换完成')

        if self.auto_open_check.isChecked() and self._output_paths:
            import sys, subprocess
            def _open_path(p):
                if sys.platform == 'win32':
                    os.startfile(p)
                elif sys.platform == 'darwin':
                    subprocess.Popen(['open', p])
                else:
                    subprocess.Popen(['xdg-open', p])
            if len(self._output_paths) <= 3:
                for path in self._output_paths:
                    if os.path.exists(path):
                        _open_path(path)
            else:
                folder = os.path.dirname(self._output_paths[0])
                if os.path.isdir(folder):
                    _open_path(folder)
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

    # ===== 帮助对话框 =====

    def _show_help(self):
        dlg = HelpDialog(self)
        dlg.exec()
