

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
    
    def __init__(
        self, 
        row,  
        serial, 
        account,
        missions, 
        log_callback, 
        show_status_callback
    ):
        super().__init__()
        self.row = row
        self.serial = serial
        self.account = account
        self.missions = missions
        self.log_callback = log_callback
        self.show_status_callback = show_status_callback
    def log(self, message):
        self.log_callback(f"[{self.serial}] {message}")
    def show_status(self, status):
        self.show_status_callback(self.row, status)
    def run(self):
        self.log(f"Starting account {self.account}...")
        self.show_status(f"Starting account {self.account}...")
        for mission in self.missions:
            if mission == Mission.NV_LV12: #thêm các func chạy của bạn vào đây
                self.log(f"Starting {mission.value}")
                self.show_status(f"Starting {mission.value}")
                sleep(randint(5, 15))  # Simulate work
                self.log(f"Finished {mission.value}")
                self.show_status(f"Finished {mission.value}")
            elif mission == Mission.NV_LV13: #thêm các func chạy của bạn vào đây
                self.log(f"Starting {mission.value}")
                self.show_status(f"Starting {mission.value}")
                sleep(randint(5, 15))  # Simulate work
                self.log(f"Finished {mission.value}")
                self.show_status(f"Finished {mission.value}")
            else:
                self.log(f"Starting {mission.value}")
                self.show_status(f"Starting {mission.value}")
                sleep(randint(5, 15))  # Simulate work
                self.log(f"Finished {mission.value}")
                self.show_status(f"Finished {mission.value}")

        self.log(f"Account {self.account} done!")
        self.show_status(f"Account {self.account} done!")

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
        self.stop_flag = False
        self.current_workers = {}
    
    
    def __thread(self, row, serial, missions):
        counter = 0
        while not self.stop_flag:
            self.logs.emit(f"Starting new thread for {serial} (account {counter + 1})")
            worker = ThreadedWorker(
                row=row, 
                serial=serial, 
                account=counter + 1,
                missions=missions,
                log_callback=self.logs.emit, 
                show_status_callback=self.show_status.emit
            )
            self.current_workers[row] = worker
            worker.start()
            worker.join()
            self.current_workers[row] = None
            counter += 1
    
    def run(self):
        """
        The `run` function creates multiple worker threads to process devices in parallel and waits for
        all threads to finish before printing a message.
        """
        self.listThread = []
        rows = self.app.table_helper.get_checked_rows()
        for row in rows:
            thread = Thread(target=self.__thread, args=(
                row, 
                self.app.get_serial(row), 
                self.app.get_selected_missions()
            ))
            thread.start()
            self.listThread.append(thread)

        for thread in self.listThread:
            thread.join()

        print("All worker threads completed.")
    def stop(self):
        self.stop_flag = True
        for row, worker in self.current_workers.items():
            if worker:
                worker.stop()
        for thread in getattr(self, 'listThread', []):
            self._async_raise(thread, SystemExit)
        for thread in getattr(self, 'listThread', []):
            thread.join(timeout=0.1)

    def pause(self):
        for row, worker in self.current_workers.items():
            if worker:
                worker.pause()
        for thread in getattr(self, 'listThread', []):
            self._suspend_thread(thread)

    def resume(self):
        for row, worker in self.current_workers.items():
            if worker:
                worker.resume()
        for thread in getattr(self, 'listThread', []):
            self._resume_thread(thread)

    def _async_raise(self, thread, exctype):
        if not thread.is_alive() or thread.ident is None:
            return
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(thread.ident), ctypes.py_object(exctype))
        if res == 0:
            raise ValueError("Invalid thread id")
        elif res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_ulong(thread.ident), None)
            raise SystemError("PyThreadState_SetAsyncExc failed")

    def _suspend_thread(self, thread):
        if thread.ident is None:
            return
        thread_handle = ctypes.windll.kernel32.OpenThread(THREAD_SUSPEND_RESUME | THREAD_QUERY_INFORMATION, False, ctypes.c_ulong(thread.ident))
        if not thread_handle:
            return
        ctypes.windll.kernel32.SuspendThread(thread_handle)
        ctypes.windll.kernel32.CloseHandle(thread_handle)

    def _resume_thread(self, thread):
        if thread.ident is None:
            return
        thread_handle = ctypes.windll.kernel32.OpenThread(THREAD_SUSPEND_RESUME | THREAD_QUERY_INFORMATION, False, ctypes.c_ulong(thread.ident))
        if not thread_handle:
            return
        ctypes.windll.kernel32.ResumeThread(thread_handle)
        ctypes.windll.kernel32.CloseHandle(thread_handle)
            