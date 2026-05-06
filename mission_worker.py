




import time

from mission import Mission


class MissionWorker:
    def __init__(
        self, 
        missions,
        serial, 
        log_signal, 
        show_status_signal
    ):
        super().__init__()
        self.missions = missions
        self.serial = serial
        self.log_signal = log_signal
        self.show_status_signal = show_status_signal
    def login(self, account):
        self.log_signal(f"Starting login for account {account}...")
        self.show_status_signal(f"Starting login for account {account}...")
        time.sleep(2)  # Simulate login time
        self.log_signal(f"Account {account} logged in!")
        self.show_status_signal(f"Account {account} logged in!")
    def mission_lv12(self, name):
        self.log_signal(f"Starting {name}")
        self.show_status_signal(f"Starting {name}")
        time.sleep(5)  # Simulate work
        self.log_signal(f"Done {name}")
        self.show_status_signal(f"Done {name}")
    def mission_lv13(self, name):
        self.log_signal(f"Starting {name}")
        self.show_status_signal(f"Starting {name}")
        time.sleep(5)  # Simulate work
        self.log_signal(f"Done {name}")
        self.show_status_signal(f"Done {name}")
    def run_missions(self):
        for mission in self.missions:
            if mission == Mission.NV_LV12:
                self.mission_lv12(mission.value)
            elif mission == Mission.NV_LV13:
                self.mission_lv13(mission.value)