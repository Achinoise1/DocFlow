"""任务列表组件 - 展示已提交任务的执行状态与历史记录"""
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QPushButton, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal

from core.conversion_registry import get_by_id


# ---------------------------------------------------------------------------
# 状态常量
# ---------------------------------------------------------------------------
_STATE_MAP = {
    'waiting':    ('等待中',    'waiting'),
    'converting': ('转换中...', 'converting'),
    'done':       ('✓ 完成',   'done'),
    'failed':     ('✕ 失败',   'failed'),
    'cancelled':  ('已取消',   'cancelled'),
}


class TaskListItem(QFrame):
    """单条任务项，展示标题、状态、进度，并提供重试/重新开始按钮。

    对外信号：
        retry_requested(task_id: str) — 用户点击重试或重新开始时发出

    公共方法：
        set_state(state, percent, message, output_path)
        update_progress(percent)

    只读属性：
        state → str  当前状态（waiting / converting / done / failed / cancelled）
    """

    retry_requested = Signal(str)

    def __init__(self, snapshot: dict, parent=None):
        super().__init__(parent)
        self.task_id: str = snapshot['task_id']
        self._state: str = 'waiting'
        self._output_path: str = ''
        self.setObjectName('taskListItem')
        self._init_ui(snapshot)

    # ------------------------------------------------------------------
    # 布局初始化
    # ------------------------------------------------------------------

    def _init_ui(self, snapshot: dict):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(3)

        # ── 第一行：状态点 · 标题 · 进度条 · 状态标签 ──────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        self._status_dot = QLabel()
        self._status_dot.setFixedSize(10, 10)
        self._status_dot.setObjectName('taskStatusDot')
        self._status_dot.setProperty('state', 'waiting')

        self._title_label = QLabel(snapshot['title'])
        self._title_label.setObjectName('taskTitle')
        if snapshot.get('input_path'):
            self._title_label.setToolTip(snapshot['input_path'])

        self._progress_bar = QProgressBar()
        self._progress_bar.setObjectName('taskProgress')
        self._progress_bar.setFixedWidth(100)
        self._progress_bar.setMaximum(100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)

        self._status_label = QLabel('等待中')
        self._status_label.setObjectName('taskStatus')
        self._status_label.setFixedWidth(68)
        self._status_label.setAlignment(Qt.AlignCenter)
        self._status_label.setProperty('state', 'waiting')

        row1.addWidget(self._status_dot)
        row1.addWidget(self._title_label, 1)
        row1.addWidget(self._progress_bar)
        row1.addWidget(self._status_label)

        # ── 第二行：转换类型 · 详细信息 · 操作按钮 ─────────────────────
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        entry = get_by_id(snapshot['conversion_type'])
        type_text = entry['label'] if entry else snapshot['conversion_type']
        self._type_label = QLabel(type_text)
        self._type_label.setObjectName('taskType')

        self._detail_label = QLabel()
        self._detail_label.setObjectName('taskDetail')
        self._detail_label.setVisible(False)

        self._action_btn = QPushButton()
        self._action_btn.setObjectName('retryBtn')
        self._action_btn.setVisible(False)
        self._action_btn.clicked.connect(self._on_action_clicked)

        row2.addWidget(self._type_label)
        row2.addWidget(self._detail_label, 1)
        row2.addWidget(self._action_btn)

        main_layout.addLayout(row1)
        main_layout.addLayout(row2)

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    @property
    def state(self) -> str:
        return self._state

    def set_state(self, state: str, percent: int = 0,
                  message: str = '', output_path: str = '') -> None:
        """更新显示状态。

        Args:
            state:       waiting / converting / done / failed / cancelled
            percent:     进度（converting 时生效）
            message:     错误信息（failed 时显示）
            output_path: 输出路径（done 时显示，可点击打开）
        """
        self._state = state
        self._output_path = output_path

        label_text, prop = _STATE_MAP.get(state, ('未知', 'waiting'))

        # 状态点
        self._status_dot.setProperty('state', prop)
        self._status_dot.style().polish(self._status_dot)

        # 状态标签
        self._status_label.setText(label_text)
        self._status_label.setProperty('state', prop)
        self._status_label.style().polish(self._status_label)

        # 进度条
        if state == 'converting':
            self._progress_bar.setValue(percent)
        elif state == 'done':
            self._progress_bar.setValue(100)
        else:
            self._progress_bar.setValue(0)

        # 详细信息 & 操作按钮
        self._detail_label.setCursor(Qt.ArrowCursor)
        self._detail_label.mousePressEvent = lambda e: None

        if state == 'done' and output_path:
            self._detail_label.setText(f'→ {os.path.basename(output_path)}')
            self._detail_label.setToolTip(output_path)
            self._detail_label.setProperty('role', 'success')
            self._detail_label.style().polish(self._detail_label)
            self._detail_label.setCursor(Qt.PointingHandCursor)
            self._detail_label.mousePressEvent = lambda e: self._open_output()
            self._detail_label.setVisible(True)
            self._action_btn.setVisible(False)

        elif state == 'failed':
            if message:
                short = message[:60] + ('...' if len(message) > 60 else '')
                self._detail_label.setText(short)
                self._detail_label.setToolTip(message)
                self._detail_label.setProperty('role', 'error')
                self._detail_label.style().polish(self._detail_label)
                self._detail_label.setVisible(True)
            else:
                self._detail_label.setVisible(False)
            self._action_btn.setText('重试')
            self._action_btn.setVisible(True)

        elif state == 'cancelled':
            self._detail_label.setVisible(False)
            self._action_btn.setText('重新开始')
            self._action_btn.setVisible(True)

        else:
            self._detail_label.setVisible(False)
            self._action_btn.setVisible(False)

    def update_progress(self, percent: int) -> None:
        """仅更新进度条数值（转换中调用）。"""
        self._progress_bar.setValue(percent)

    # ------------------------------------------------------------------
    # 内部事件
    # ------------------------------------------------------------------

    def _on_action_clicked(self):
        self.retry_requested.emit(self.task_id)

    def _open_output(self):
        if self._output_path and os.path.exists(self._output_path):
            import sys, subprocess
            if sys.platform == 'win32':
                os.startfile(self._output_path)
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', self._output_path])
            else:
                subprocess.Popen(['xdg-open', self._output_path])


# ---------------------------------------------------------------------------
# TaskListWidget
# ---------------------------------------------------------------------------

class TaskListWidget(QWidget):
    """任务列表容器，管理所有任务条目的生命周期与状态。

    对外信号：
        retry_requested(task_id: str) — 冒泡自 TaskListItem，由 main_window 处理

    对外方法：
        add_task(snapshot)
        on_task_started(task_id)
        on_task_progress(task_id, percent)
        on_task_finished(task_id, success, message, output_path) → list[str]
        cancel_all_pending()
        clear_completed()
        get_snapshot(task_id) → dict | None
        reset_task(old_task_id, new_task_id, snapshot)
    """

    retry_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: dict = {}      # task_id → TaskListItem
        self._snapshots: dict = {}  # task_id → snapshot dict
        self._init_ui()

    # ------------------------------------------------------------------
    # 布局初始化
    # ------------------------------------------------------------------

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # 顶部操作栏
        header = QHBoxLayout()
        self._count_label = QLabel('任务列表 (0)')
        self._count_label.setObjectName('taskCountLabel')
        clear_btn = QPushButton('清除已完成')
        clear_btn.setObjectName('clearBtn')
        clear_btn.clicked.connect(self.clear_completed)
        header.addWidget(self._count_label)
        header.addStretch()
        header.addWidget(clear_btn)
        layout.addLayout(header)

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName('taskScrollArea')

        self._container = QWidget()
        self._list_layout = QVBoxLayout(self._container)
        self._list_layout.setSpacing(4)
        self._list_layout.setContentsMargins(4, 4, 4, 4)
        self._list_layout.addStretch()

        scroll.setWidget(self._container)
        layout.addWidget(scroll)

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    def _update_count(self):
        self._count_label.setText(f'任务列表 ({len(self._items)})')

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    def add_task(self, snapshot: dict) -> None:
        """添加一条任务（开始转换时由 main_window 调用）。"""
        task_id = snapshot['task_id']
        self._snapshots[task_id] = snapshot

        item = TaskListItem(snapshot)
        item.retry_requested.connect(self.retry_requested)

        idx = self._list_layout.count() - 1
        self._list_layout.insertWidget(idx, item)
        self._items[task_id] = item
        self._update_count()

    def on_task_started(self, task_id: str) -> None:
        if task_id in self._items:
            self._items[task_id].set_state('converting', percent=10)

    def on_task_progress(self, task_id: str, percent: int) -> None:
        if task_id in self._items:
            self._items[task_id].update_progress(percent)

    def on_task_finished(self, task_id: str, success: bool,
                         message: str, output_path: str) -> list:
        """更新任务完成状态，返回成功任务的输出路径列表（供自动打开使用）。"""
        collected = []
        if task_id in self._items:
            state = 'done' if success else 'failed'
            self._items[task_id].set_state(
                state, percent=100 if success else 0,
                message=message, output_path=output_path
            )
            if success and output_path:
                collected.append(output_path)
        return collected

    def cancel_all_pending(self) -> None:
        """将所有等待中/转换中的任务标记为已取消。"""
        for item in self._items.values():
            if item.state in ('waiting', 'converting'):
                item.set_state('cancelled')

    def clear_completed(self) -> None:
        """移除所有已完成（done）的任务条目。"""
        to_remove = [tid for tid, item in self._items.items()
                     if item.state == 'done']
        for tid in to_remove:
            item = self._items.pop(tid)
            self._snapshots.pop(tid, None)
            self._list_layout.removeWidget(item)
            item.deleteLater()
        self._update_count()

    def get_snapshot(self, task_id: str) -> dict:
        """返回任务快照，重试时由 main_window 调用。"""
        return self._snapshots.get(task_id)

    def reset_task(self, old_task_id: str, new_task_id: str,
                   snapshot: dict) -> None:
        """复用已有 item widget，更新 task_id 后重置为等待中状态（重试时调用）。"""
        if old_task_id not in self._items:
            return
        item = self._items.pop(old_task_id)
        self._snapshots.pop(old_task_id, None)

        item.task_id = new_task_id
        item.set_state('waiting')

        self._items[new_task_id] = item
        self._snapshots[new_task_id] = snapshot
