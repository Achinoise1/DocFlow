"""任务管理器 - 管理转换任务的线程池调度"""
import os
import traceback
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, Slot

from utils.logger import logger
from core.converter.dispatcher import dispatch, dispatch_batch


class TaskSignals(QObject):
    """任务信号"""
    started = Signal(str)        # task_id
    progress = Signal(str, int)  # task_id, percent
    finished = Signal(str, bool, str, str)  # task_id, success, message, output_path
    all_done = Signal()


class ConvertTask(QRunnable):
    """单个转换任务"""

    def __init__(self, task_id: str, input_path: str, conversion_type: str,
                 output_dir: str = None, options: dict = None):
        super().__init__()
        self.task_id = task_id
        self.input_path = input_path
        self.conversion_type = conversion_type
        self.output_dir = output_dir or os.path.dirname(input_path)
        self.options = options or {}
        self.signals = TaskSignals()
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    @Slot()
    def run(self):
        if self._cancelled:
            self.signals.finished.emit(self.task_id, False, '已取消', '')
            return

        self.signals.started.emit(self.task_id)
        self.signals.progress.emit(self.task_id, 10)

        try:
            result = self._do_convert()
            self.signals.progress.emit(self.task_id, 100)
            self.signals.finished.emit(self.task_id, True, f'转换成功: {os.path.basename(result)}', result)
        except Exception as e:
            logger.error(f'任务 {self.task_id} 失败: {traceback.format_exc()}')
            self.signals.finished.emit(self.task_id, False, str(e), '')

    def _do_convert(self) -> str:
        return dispatch(self.conversion_type, self.input_path, self.output_dir, self.options)


class BatchImageTask(QRunnable):
    """批量图片合并任务（多图合一）"""

    def __init__(self, task_id: str, image_paths: list, conversion_type: str,
                 output_path: str):
        super().__init__()
        self.task_id = task_id
        self.image_paths = image_paths
        self.conversion_type = conversion_type
        self.output_path = output_path
        self.signals = TaskSignals()

    @Slot()
    def run(self):
        self.signals.started.emit(self.task_id)
        self.signals.progress.emit(self.task_id, 10)

        try:
            dispatch_batch(self.conversion_type, self.image_paths, self.output_path)

            self.signals.progress.emit(self.task_id, 100)
            self.signals.finished.emit(
                self.task_id, True,
                f'转换成功: {os.path.basename(self.output_path)}',
                self.output_path
            )
        except Exception as e:
            logger.error(f'批量任务 {self.task_id} 失败: {traceback.format_exc()}')
            self.signals.finished.emit(self.task_id, False, str(e), '')


class TaskManager(QObject):
    """任务管理器 - 管理所有转换任务"""

    task_started = Signal(str)
    task_progress = Signal(str, int)
    task_finished = Signal(str, bool, str, str)
    all_tasks_done = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(4)
        self._tasks = {}
        self._pending_count = 0

    def submit_task(self, task_id: str, input_path: str, conversion_type: str,
                    output_dir: str = None, options: dict = None):
        """提交单个转换任务"""
        task = ConvertTask(task_id, input_path, conversion_type, output_dir, options)
        task.signals.started.connect(self._on_task_started)
        task.signals.progress.connect(self._on_task_progress)
        task.signals.finished.connect(self._on_task_finished)

        self._tasks[task_id] = task
        self._pending_count += 1
        self.thread_pool.start(task)

    def submit_batch_image_task(self, task_id: str, image_paths: list,
                                conversion_type: str, output_path: str):
        """提交批量图片合并任务"""
        task = BatchImageTask(task_id, image_paths, conversion_type, output_path)
        task.signals.started.connect(self._on_task_started)
        task.signals.progress.connect(self._on_task_progress)
        task.signals.finished.connect(self._on_task_finished)

        self._tasks[task_id] = task
        self._pending_count += 1
        self.thread_pool.start(task)

    def cancel_all(self):
        """取消所有任务"""
        for task in self._tasks.values():
            if hasattr(task, 'cancel'):
                task.cancel()
        self._tasks.clear()
        self._pending_count = 0

    def _on_task_started(self, task_id: str):
        self.task_started.emit(task_id)

    def _on_task_progress(self, task_id: str, percent: int):
        self.task_progress.emit(task_id, percent)

    def _on_task_finished(self, task_id: str, success: bool, message: str, output_path: str):
        self.task_finished.emit(task_id, success, message, output_path)
        self._pending_count -= 1
        if self._pending_count <= 0:
            self._pending_count = 0
            self.all_tasks_done.emit()
