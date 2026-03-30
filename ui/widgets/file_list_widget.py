"""文件列表组件 - 封装文件列表的显示、管理与任务状态更新"""
import os

from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea
from PySide6.QtCore import Signal

from ui.widgets.drop_zone import FileListItem
from utils.file_utils import get_file_ext


class FileListWidget(QWidget):
    """可滚动文件列表组件，管理文件的添加、移除与任务状态更新。

    对外暴露的信号：
        file_count_changed(int)  — 文件总数发生变化时发出
        file_removed(str)        — 单个文件被移除时发出（携带文件路径）

    对外暴露的属性：
        file_paths   → list[str]   当前所有文件路径（按添加顺序）
        pending_paths → list[str]  尚未完成转换的文件路径
        task_id_map  → dict        {task_id: [file_path, ...]} 映射

    对外暴露的方法：
        add_files(file_paths, accepted_exts) → list[str]  返回被拒绝的文件名
        remove_file(file_path)
        clear_files()
        collect_files_from_dir(dir_path, accepted_exts) → list[str]
        set_task_id(file_path, task_id)
        mark_skipped(file_path)
        reset_all_tasks()
        update_task_state(task_id, state, percent, success, output_path) → list[str]
    """

    file_count_changed = Signal(int)   # 文件数量变化
    file_removed = Signal(str)         # 单个文件被移除，携带路径

    def __init__(self, parent=None):
        super().__init__(parent)
        # 内部状态: {file_path: {'widget': FileListItem, 'task_id': str|None, 'done': bool}}
        self._file_items: dict = {}
        self._init_ui()

    # ------------------------------------------------------------------
    # 布局初始化
    # ------------------------------------------------------------------

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(120)
        scroll_area.setMaximumHeight(250)
        scroll_area.setObjectName('fileScrollArea')

        self._container = QWidget()
        self._list_layout = QVBoxLayout(self._container)
        self._list_layout.setSpacing(4)
        self._list_layout.setContentsMargins(4, 4, 4, 4)
        self._list_layout.addStretch()

        scroll_area.setWidget(self._container)
        layout.addWidget(scroll_area)

    # ------------------------------------------------------------------
    # 属性
    # ------------------------------------------------------------------

    @property
    def file_paths(self) -> list:
        """返回当前所有文件路径（按添加顺序）。"""
        return list(self._file_items.keys())

    @property
    def pending_paths(self) -> list:
        """返回尚未完成转换的文件路径。"""
        return [p for p, d in self._file_items.items() if not d['done']]

    @property
    def task_id_map(self) -> dict:
        """返回 {task_id: [file_path, ...]} 映射，供 main_window 查询。"""
        result = {}
        for path, data in self._file_items.items():
            tid = data['task_id']
            if tid:
                result.setdefault(tid, []).append(path)
        return result

    # ------------------------------------------------------------------
    # 文件管理
    # ------------------------------------------------------------------

    def collect_files_from_dir(self, dir_path: str, accepted_exts: list) -> list:
        """递归扫描目录，返回所有符合扩展名的文件路径。

        Args:
            dir_path:      目录绝对路径
            accepted_exts: 接受的扩展名列表（如 ['.doc', '.docx']），
                           空列表表示接受所有文件

        Returns:
            匹配的文件路径列表
        """
        result = []
        for root, _, files in os.walk(dir_path):
            for fname in files:
                fpath = os.path.join(root, fname)
                if not accepted_exts or get_file_ext(fpath) in accepted_exts:
                    result.append(fpath)
        return result

    def add_files(self, file_paths: list, accepted_exts: list) -> list:
        """添加文件到列表，目录会被自动展开扫描。

        Args:
            file_paths:    文件或目录路径列表
            accepted_exts: 接受的扩展名列表，空列表表示全部接受

        Returns:
            被拒绝的文件名列表（类型不匹配），供调用方弹窗提示
        """
        # 展开目录
        expanded = []
        for p in file_paths:
            if os.path.isdir(p):
                found = self.collect_files_from_dir(p, accepted_exts)
                expanded.extend(found)
            else:
                expanded.append(p)

        rejected = []
        for path in expanded:
            if path in self._file_items:
                continue

            if accepted_exts:
                if get_file_ext(path) not in accepted_exts:
                    rejected.append(os.path.basename(path))
                    continue

            item_widget = FileListItem(path)
            item_widget.remove_clicked.connect(self.remove_file)

            # 插入到末尾 stretch 之前，保持 stretch 始终在底部
            idx = self._list_layout.count() - 1
            self._list_layout.insertWidget(idx, item_widget)

            self._file_items[path] = {
                'widget': item_widget,
                'task_id': None,
                'done': False,
            }

        self.file_count_changed.emit(len(self._file_items))
        return rejected

    def remove_file(self, file_path: str) -> None:
        """从列表中移除指定文件。"""
        if file_path not in self._file_items:
            return
        widget = self._file_items[file_path]['widget']
        self._list_layout.removeWidget(widget)
        widget.deleteLater()
        del self._file_items[file_path]
        self.file_count_changed.emit(len(self._file_items))
        self.file_removed.emit(file_path)

    def clear_files(self) -> None:
        """清空文件列表。"""
        for path in list(self._file_items.keys()):
            self.remove_file(path)

    # ------------------------------------------------------------------
    # 任务状态管理
    # ------------------------------------------------------------------

    def set_task_id(self, file_path: str, task_id: str) -> None:
        """为指定文件绑定任务 ID，并将 widget 状态置为「等待中」。

        在 _start_conversion() 提交任务前调用。
        """
        if file_path in self._file_items:
            self._file_items[file_path]['task_id'] = task_id
            self._file_items[file_path]['widget'].set_waiting()

    def mark_skipped(self, file_path: str) -> None:
        """将指定文件标记为「类型不匹配」（转换时被跳过）。"""
        if file_path in self._file_items:
            self._file_items[file_path]['widget'].set_status('类型不匹配', False)

    def reset_all_tasks(self) -> None:
        """重置所有文件的任务状态（取消后调用）。"""
        for item_data in self._file_items.values():
            item_data['widget'].set_waiting()
            item_data['done'] = False
            item_data['task_id'] = None

    def update_task_state(self, task_id: str, state: str,
                          percent: int = 0,
                          success: bool = True,
                          output_path: str = '') -> list:
        """更新任务对应文件的 UI 状态，合并三个任务回调的 widget 操作。

        Args:
            task_id:     任务 ID
            state:       'started' | 'progress' | 'finished'
            percent:     进度百分比（state='progress' 时有效）
            success:     是否成功（state='finished' 时有效）
            output_path: 输出路径（state='finished' 且 success=True 时有效）

        Returns:
            成功完成时收集到的输出路径列表
            （批量任务多个文件共享同一 task_id，故返回列表）
        """
        collected = []
        for item_data in self._file_items.values():
            if item_data['task_id'] != task_id:
                continue

            if state == 'started':
                item_data['widget'].set_converting()

            elif state == 'progress':
                item_data['widget'].set_progress(percent)

            elif state == 'finished':
                if success:
                    item_data['widget'].set_status('✓ 完成', True)
                    item_data['widget'].set_progress(100)
                    item_data['done'] = True
                    if output_path and output_path not in collected:
                        collected.append(output_path)
                else:
                    item_data['widget'].set_status('✕ 失败', False)
                # 不 break：批量任务多个文件共享同一 task_id

        return collected
