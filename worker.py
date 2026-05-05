

import ctypes
from random import randint
from threading import Thread, Semaphore
from time import sleep, time
from PyQt5.QtCore import QThread, pyqtSignal
from queue import Queue

from mission import Mission
THREAD_SUSPEND_RESUME = 0x0002
THREAD_QUERY_INFORMATION = 0x0040

class ThreadedWorker(Thread):
    def __init__(self, rows_queue: Queue, get_serial_func, get_missions_func, log_callback, show_status_callback):
        super().__init__()
        self.rows_queue = rows_queue
        self.get_serial_func = get_serial_func
        self.get_missions_func = get_missions_func
        self.log_callback = log_callback
        self.show_status_callback = show_status_callback
    def log(self, message):
        self.log_callback(f"[{self.serial}] {message}")
    def work(self, row):
        self.serial = self.get_serial_func(row)
        missions = self.get_missions_func()
        for mission in missions:
            if mission == Mission.NV_LV12:
                self.log(f"Starting {mission.value}")
                self.show_status_callback(row, f"Starting {mission.value}")
                sleep(randint(5, 15))  # Simulate work
                self.log(f"Finished {mission.value}")
                self.show_status_callback(row, f"Finished {mission.value}")
            elif mission == Mission.NV_LV13:
                self.log(f"Starting {mission.value}")
                self.show_status_callback(row, f"Starting {mission.value}")
                sleep(randint(5, 15))  # Simulate work
                self.log(f"Finished {mission.value}")
                self.show_status_callback(row, f"Finished {mission.value}")
            else:
                self.log(f"Starting {mission.value}")
                self.show_status_callback(row, f"Starting {mission.value}")
                sleep(randint(5, 15))  # Simulate work
                self.log(f"Finished {mission.value}")
                self.show_status_callback(row, f"Finished {mission.value}")

        self.log(f"[{self.serial}] Done!")
        self.show_status_callback(row, "Done!")
    def run(self):
        while not self.rows_queue.empty():
            self.row = self.rows_queue.get()
            self.work(self.row)

    def stop(self):
        if hasattr(self, 'row'):
            self.show_status_callback(self.row, "Stopping")
        self._async_raise(SystemExit)

    def pause(self):
        if hasattr(self, 'row'):
            self.show_status_callback(self.row, "Paused")
        if self.ident is None:
            return
        thread_handle = ctypes.windll.kernel32.OpenThread(THREAD_SUSPEND_RESUME | THREAD_QUERY_INFORMATION, False, ctypes.c_ulong(self.ident))
        if not thread_handle:
            return
        ctypes.windll.kernel32.SuspendThread(thread_handle)
        ctypes.windll.kernel32.CloseHandle(thread_handle)

    def resume(self):
        if hasattr(self, 'row'):
            self.show_status_callback(self.row, "Resuming")
        if self.ident is None:
            return
        thread_handle = ctypes.windll.kernel32.OpenThread(THREAD_SUSPEND_RESUME | THREAD_QUERY_INFORMATION, False, ctypes.c_ulong(self.ident))
        if not thread_handle:
            return
        ctypes.windll.kernel32.ResumeThread(thread_handle)
        ctypes.windll.kernel32.CloseHandle(thread_handle)

    def _async_raise(self, exctype):
        if not self.is_alive() or self.ident is None:
            return
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(self.ident), ctypes.py_object(exctype))
        if res == 0:
            raise ValueError("Invalid thread id")
        elif res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(self.ident), None)
            raise SystemError("PyThreadState_SetAsyncExc failed")

class Worker(QThread):
    logs = pyqtSignal(str)
    show_status = pyqtSignal(int, str)  # row, status
    def __init__(self, app):
        super().__init__()
        self.app = app
    
    def run(self):
        """
        The `run` function creates multiple worker threads to process devices in parallel and waits for
        all threads to finish before printing a message.
        """
        self.listThread = []
        self.rows_queue = Queue()
        rows = self.app.table_helper.get_checked_rows()
        for row in rows:
            self.rows_queue.put(row)
        threadCount = self.app.main_widget.threadCount.value()
        for _ in range(min(threadCount, len(rows))):
            worker = ThreadedWorker(self.rows_queue, 
                                    self.app.get_serial, 
                                    self.app.getMissions,
                                    self.logs.emit, 
                                    self.show_status.emit)
            worker.start()
            self.listThread.append(worker)
        for worker in self.listThread:
            worker.join()
        
        print("All worker threads completed.")
    def stop(self):
        for worker in getattr(self, 'listThread', []):
            worker.stop()
        for worker in getattr(self, 'listThread', []):
            worker.join(timeout=0.1)

    def pause(self):
        for worker in getattr(self, 'listThread', []):
            worker.pause()

    def resume(self):
        for worker in getattr(self, 'listThread', []):
            worker.resume()
            