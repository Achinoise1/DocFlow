"""LibreOffice 安装对话框（macOS / Linux）

安装流程：
  1. LibreOfficeSilentInstallDialog  — 极简静默对话框，自动在后台安装
     - 成功 → accept()，调用方 is_success() 返回 True，直接继续转换
     - 失败/取消 → reject()，调用方再弹出 LibreOfficeSetupDialog
  2. LibreOfficeSetupDialog          — 安装失败后的引导对话框
     - 供用户选择：重试自动安装 / 手动安装后重新检测 / 跳过
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QProgressBar,
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFont


# ── 后台安装工作线程 ──────────────────────────────────────────────────────────


class _InstallWorker(QThread):
    """在后台线程中运行自动安装，通过信号回传进度和结果"""
    progress = Signal(str)
    finished = Signal(bool, str)  # success, message

    def run(self):
        from utils.libreoffice_manager import install_auto
        success, message = install_auto(progress_callback=self.progress.emit)
        self.finished.emit(success, message)

    def cancel(self):
        """取消安装：终止子进程并请求线程中断"""
        from utils.libreoffice_manager import cancel_install
        cancel_install()
        self.requestInterruption()


# ── 静默安装对话框（极简 UI，自动安装，成功即关闭）────────────────────────────


class LibreOfficeSilentInstallDialog(QDialog):
    """
    极简的静默安装对话框。

    打开后立即在后台安装 LibreOffice：
    - 安装成功 → accept()，is_success() 返回 True
    - 安装失败/取消 → reject()，is_success() 返回 False

    调用方在 exec() 返回后判断 is_success()；
    若为 False 则弹出 LibreOfficeSetupDialog 引导用户处理。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('正在安装 LibreOffice...')
        self.setFixedWidth(420)
        self.setWindowModality(Qt.ApplicationModal)
        # 隐藏关闭按钮，防止意外关闭导致行为不一致
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)

        self._worker: _InstallWorker | None = None
        self._success = False
        self._cancelled = False

        self._init_ui()
        QTimer.singleShot(100, self._start_install)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 18, 20, 16)

        label = QLabel(
            'Word / PPT 转 PDF 功能依赖 LibreOffice。\n'
            '正在自动安装，请稍候（首次安装约需下载数百 MB）…'
        )
        label.setWordWrap(True)
        layout.addWidget(label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)
        layout.addWidget(self._progress_bar)

        self._status_label = QLabel('')
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_cancel = QPushButton('取消安装')
        self._btn_cancel.clicked.connect(self._on_cancel)
        btn_row.addWidget(self._btn_cancel)
        layout.addLayout(btn_row)

    def _start_install(self):
        self._worker = _InstallWorker(self)
        self._worker.progress.connect(self._status_label.setText)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_cancel(self):
        self._cancelled = True
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._btn_cancel.setEnabled(False)
            self._status_label.setText('正在取消，请稍候...')

    def _on_finished(self, success: bool, _message: str):
        self._progress_bar.setVisible(False)
        if success and not self._cancelled:
            self._success = True
            self.accept()
        else:
            self.reject()

    def is_success(self) -> bool:
        """返回安装是否成功"""
        return self._success

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._cancelled = True
            self._worker.cancel()
            self._worker.wait(5000)
        super().closeEvent(event)


# ── 安装失败引导对话框 ─────────────────────────────────────────────────────────


class LibreOfficeSetupDialog(QDialog):
    """
    LibreOffice 安装失败后的引导对话框。

    供用户选择：重试自动安装 / 手动安装后重新检测 / 跳过。
    用法：
        dlg = LibreOfficeSetupDialog(parent=self)
        dlg.exec()
        if dlg.is_ready():  # 安装成功或用户确认已手动安装
            ...
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('LibreOffice 安装失败')
        self.setMinimumWidth(520)
        self.setMinimumHeight(360)
        self.setWindowModality(Qt.ApplicationModal)

        self._worker: _InstallWorker | None = None
        self._ready = False
        self._cancelled = False

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 18, 20, 16)

        # 标题
        title = QLabel('❌  LibreOffice 自动安装失败')
        font = QFont()
        font.setPointSize(13)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        # 说明
        info = QLabel(
            'Word / PPT 转 PDF 功能依赖 LibreOffice，自动安装未能完成。\n'
            '可点击"重试"再次自动安装，或"打开官网"手动下载安装后点击"重新检测"。'
        )
        info.setWordWrap(True)
        info.setTextFormat(Qt.PlainText)
        layout.addWidget(info)

        # 进度条（重试时显示）
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 实时日志
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText('安装日志将在此处实时显示...')
        self.log_view.setMinimumHeight(120)
        layout.addWidget(self.log_view)

        # 状态提示
        self._status_label = QLabel('')
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_retry = QPushButton('↺ 重试')
        self.btn_retry.setDefault(True)
        self.btn_retry.setMinimumHeight(34)
        self.btn_retry.clicked.connect(self._start_install)

        self.btn_recheck = QPushButton('🔄 重新检测')
        self.btn_recheck.setToolTip('手动安装完成后点击此处重新检测')
        self.btn_recheck.setMinimumHeight(34)
        self.btn_recheck.clicked.connect(self._recheck)

        self.btn_manual = QPushButton('🌐 打开官网')
        self.btn_manual.setMinimumHeight(34)
        self.btn_manual.clicked.connect(self._open_website)

        self.btn_skip = QPushButton('跳过')
        self.btn_skip.setMinimumHeight(34)
        self.btn_skip.setToolTip('跳过后 Word/PPT 转 PDF 功能将不可用')
        self.btn_skip.clicked.connect(self.reject)

        btn_row.addWidget(self.btn_retry)
        btn_row.addWidget(self.btn_recheck)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_manual)
        btn_row.addWidget(self.btn_skip)
        layout.addLayout(btn_row)

    def _start_install(self):
        self.btn_retry.setEnabled(False)
        self.btn_recheck.setEnabled(False)
        self.btn_skip.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.log_view.clear()
        self._set_status('')
        self._append_log('开始安装，请稍候...\n')
        self._cancelled = False

        self._worker = _InstallWorker(self)
        self._worker.progress.connect(self._append_log)
        self._worker.finished.connect(self._on_install_finished)
        self._worker.start()

    def _on_install_finished(self, success: bool, message: str):
        self.progress_bar.setVisible(False)
        self.btn_retry.setEnabled(True)
        self.btn_recheck.setEnabled(True)
        self.btn_skip.setEnabled(True)

        if self._cancelled or message == '已取消':
            self._set_status('安装已取消。')
            self._append_log('\n⚠ 已取消')
            return

        if success:
            self._ready = True
            self._set_status('✅ 安装成功！')
            self._append_log(f'\n✅ {message}')
            self.accept()
        else:
            self._set_status('❌ 安装失败，请重试或手动安装。')
            self._append_log(f'\n❌ {message}')

    def _append_log(self, msg: str):
        self.log_view.append(msg)
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _recheck(self):
        from utils.libreoffice_manager import is_installed
        if is_installed():
            self._ready = True
            self._set_status('✅ 检测到 LibreOffice，准备就绪！')
            self.accept()
        else:
            self._set_status('未检测到 LibreOffice，请确认安装已完成。')

    def _open_website(self):
        QDesktopServices.openUrl(
            QUrl('https://www.libreoffice.org/download/download-libreoffice/')
        )

    def _set_status(self, text: str):
        self._status_label.setText(text)

    def is_ready(self) -> bool:
        """返回 LibreOffice 是否已就绪（安装成功或用户确认已手动安装）"""
        return self._ready

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._cancelled = True
            self._worker.cancel()
            self._worker.wait(5000)
        super().closeEvent(event)
