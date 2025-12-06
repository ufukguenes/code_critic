from PyQt6.QtCore import QThread, pyqtSignal
import os
import time
import subprocess


class ModifiedTimeDiffChecker(QThread):
    result_ready = pyqtSignal(bool)

    def __init__(self, project_path, parent=None):
        super().__init__(parent)
        self.project_path = project_path

    def run(self):
        try:
            cmd = [
                "/bin/bash",
                "-c",
                "git ls-files -c -o --exclude-standard -z | xargs -0 stat --format='%Y' | sort -n | tail -n 1",
            ]
            result = subprocess.run(
                cmd, cwd=self.project_path, capture_output=True, text=True
            )
            last_modified_timestamp = int(result.stdout)

            current_time = time.time()
            time_difference = current_time - last_modified_timestamp
            five_minutes = 3  # 5 * 60
            is_older_than_five_minutes = time_difference > five_minutes
            self.result_ready.emit(is_older_than_five_minutes)

        except Exception as e:
            print("Error time difference checker for modified folder:", e)
            self.result_ready.emit(False)
