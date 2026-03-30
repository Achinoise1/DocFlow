"""LibreOffice 安装引导对话框（macOS / Linux）

在用户执行 Word/PPT 转 PDF 时，若检测到未安装 LibreOffice，
弹出此对话框引导用户自动或手动安装。
"""
import sys
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QProgressBar,
)
from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtCore import QUrl


# ── 后台安装工作线程 ──────────────────────────────────────────────────────────


class _InstallWorker(QThread):
    """在后台线程中运行自动安装，通过信号回传进度和结果"""
    progress = Signal(str)
    finished = Signal(bool, str)  # success, message

    def run(self):
        from utils.libreoffice_manager import install_auto
        success, message = install_auto(progress_callback=self.progress.emit)
        self.finished.emit(success, message)


# ── 对话框 ────────────────────────────────────────────────────────────────────


class LibreOfficeSetupDialog(QDialog):
    """
    LibreOffice 安装引导对话框。

    用法：
        dlg = LibreOfficeSetupDialog(parent=self)
        dlg.exec()
        if dlg.is_ready():   # 安装成功或用户确认已手动安装
            ...
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('需要安装 LibreOffice')
        self.setMinimumWidth(520)
        self.setMinimumHeight(380)
        self.setWindowModality(Qt.ApplicationModal)

        self._worker: _InstallWorker | None = None
        self._ready = False  # 安装成功 / 手动安装确认

        self._init_ui()
        self._refresh_auto_method_label()

    # ── UI ───────────────────────────────────────────────────────────────────

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 18, 20, 16)

        # 标题行
        title = QLabel('⚠️  未检测到 LibreOffice')
        font = QFont()
        font.setPointSize(13)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        # 说明
        self._info_label = QLabel()
        self._info_label.setWordWrap(True)
        self._info_label.setTextFormat(Qt.PlainText)
        layout.addWidget(self._info_label)

        # 进度条（转换中隐藏）
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)   # 不定进度
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 实时日志
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setPlaceholderText('安装日志将在此处实时显示...')
        self.log_view.setMinimumHeight(140)
        layout.addWidget(self.log_view)

        # 状态提示
        self._status_label = QLabel('')
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        # 按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_auto = QPushButton('⬇  自动安装')
        self.btn_auto.setDefault(True)
        self.btn_auto.setMinimumHeight(34)
        self.btn_auto.clicked.connect(self._start_install)

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

        btn_row.addWidget(self.btn_auto)
        btn_row.addWidget(self.btn_recheck)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_manual)
        btn_row.addWidget(self.btn_skip)
        layout.addLayout(btn_row)

    def _refresh_auto_method_label(self):
        """根据当前平台设置提示文字"""
        from utils.libreoffice_manager import get_available_auto_install_method
        method = get_available_auto_install_method()

        if sys.platform == 'darwin':
            import shutil
            if shutil.which('brew'):
                detail = '将通过 Homebrew 自动安装（约 400 MB）。'
            else:
                detail = '将下载官方 DMG 并安装到 ~/Applications（约 400 MB，无需管理员权限）。'
        else:
            if method == 'snap':
                detail = '将通过 snap 自动安装（无需管理员权限）。'
            elif method == 'flatpak':
                detail = '将通过 flatpak 自动安装（无需管理员权限）。'
            elif method in ('apt', 'dnf', 'yum'):
                detail = f'将通过 {method} 自动安装（需要管理员授权）。'
            else:
                detail = '未找到合适的包管理器，建议手动安装。'
                self.btn_auto.setEnabled(False)

        self._info_label.setText(
            'Word / PPT 转 PDF 功能依赖 LibreOffice。\n'
            f'{detail}\n\n'
            '也可点击"打开官网"手动下载安装，完成后点击"重新检测"。'
        )

    # ── 交互 ─────────────────────────────────────────────────────────────────

    def _start_install(self):
        self.btn_auto.setEnabled(False)
        self.btn_recheck.setEnabled(False)
        self.btn_skip.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.log_view.clear()
        self._set_status('')
        self._append_log('开始安装，请稍候...\n')

        self._worker = _InstallWorker(self)
        self._worker.progress.connect(self._append_log)
        self._worker.finished.connect(self._on_install_finished)
        self._worker.start()

    def _append_log(self, msg: str):
        self.log_view.append(msg)
        sb = self.log_view.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_install_finished(self, success: bool, message: str):
        self.progress_bar.setVisible(False)
        self.btn_auto.setEnabled(True)
        self.btn_recheck.setEnabled(True)
        self.btn_skip.setEnabled(True)

        if success:
            self._ready = True
            self._set_status('✅ 安装成功！可以关闭此窗口继续使用。')
            self._append_log(f'\n✅ {message}')
            # 自动关闭
            self.accept()
        else:
            self._set_status('❌ 自动安装失败，请点击"打开官网"手动安装后再"重新检测"。')
            self._append_log(f'\n❌ {message}')

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

    # ── 公共接口 ──────────────────────────────────────────────────────────────

    def is_ready(self) -> bool:
        """返回 LibreOffice 是否已就绪（安装成功或用户确认已手动安装）"""
        return self._ready

    def closeEvent(self, event):
        """关闭时等待工作线程结束，避免悬空线程"""
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(3000)
        super().closeEvent(event)
