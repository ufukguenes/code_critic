import sys
from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QMenu
from PyQt6.QtGui import QMovie
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
import subprocess
import re
from enum import Enum
import time

from sleep_worker import ModifiedTimeDiffChecker

PROJECT_PATH = "/home/ufuk/Documents/Programming/kuh-handel"
WINDOW_WIDTH = 200
WINDOW_HEIGHT = 200


class CharacterStates(Enum):
    HAPPY = "/home/ufuk/Nextcloud/Photos/rust_gifs/crab_walk.GIF"
    EXCITED = "/home/ufuk/Nextcloud/Photos/rust_gifs/crab_excited.gif"
    WARNING = "/home/ufuk/Nextcloud/Photos/rust_gifs/crab_warning.gif"
    PANIC = "/home/ufuk/Nextcloud/Photos/rust_gifs/crab_panic.gif"
    SLEEP = "/home/ufuk/Nextcloud/Photos/rust_gifs/crab_sleep.gif"


class CodeQualityChecker(QThread):
    result_ready = pyqtSignal((int, int))

    def __init__(self, project_path, parent=None):
        super().__init__(parent)
        self.project_path = project_path

    def run(self):
        try:
            cmd = ["cargo", "check"]
            result = subprocess.run(
                cmd, cwd=self.project_path, capture_output=True, text=True
            )
            output = result.stderr + result.stdout

            # r"^" for matching only at beginning of line
            warnings_count = self.count_occurrences(output, r"^warning:")
            errors_count = self.count_occurrences(output, r"^error:")

            self.result_ready.emit(warnings_count, errors_count)

        except Exception as e:
            print("Error running cargo check:", e)
            self.result_ready.emit(0)

    def count_occurrences(self, text, pattern):
        occurrences = [
            match.start() for match in re.finditer(pattern, text, re.MULTILINE)
        ]
        return len(occurrences)


class Character(QWidget):
    def __init__(self):
        super().__init__()

        self.current_state = CharacterStates.HAPPY

        self.excited_cool_down = 5  # secs
        self.excited_time_stamp = 0

        self.max_move_steps = 20
        self.current_move_step = 0
        self.move_offset = 5
        self.increase_offset = False

        self.default_pacing_interval = 100  # milliseconds
        self.code_check_interval = 1000  # milliseconds
        self.sleep_check_interval = 1000  # milliseconds

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.BypassWindowManagerHint
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.label = QLabel(self)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.movie = QMovie(self.current_state.value)
        self.label.setMovie(self.movie)
        self.movie.start()

        self.default_speed = self.movie.speed()

        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.movie.setScaledSize(self.size())
        self.label.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        self.move_to_start_pos()

        self.drag_position = None

        self.code_check_timer = QTimer(self)
        self.code_check_timer.timeout.connect(self.run_code_check)
        self.code_check_timer.start(self.code_check_interval)

        self.pacing_timer = QTimer(self)
        self.pacing_timer.timeout.connect(self.character_pacing)
        self.pacing_timer.start(self.default_pacing_interval)

        self.sleep_timer = QTimer(self)
        self.sleep_timer.timeout.connect(self.sleep_check)
        self.sleep_timer.start(self.sleep_check_interval)

    def move_to_start_pos(self):
        screen = app.primaryScreen()
        rect = screen.availableGeometry()  # type: ignore
        bottom_right_x = rect.right() - self.width()
        bottom_right_y = rect.bottom() - self.height()
        self.move(bottom_right_x, bottom_right_y)

    def run_code_check(self):
        self.code_check_worker = CodeQualityChecker(PROJECT_PATH)
        self.code_check_worker.result_ready.connect(self.update_code_quality)
        self.code_check_worker.start()

    def sleep_check(self):
        self.sleep_check_worker = ModifiedTimeDiffChecker(PROJECT_PATH)
        self.sleep_check_worker.result_ready.connect(self.update_sleep)
        self.sleep_check_worker.start()

    def update_sleep(self, is_older_than_timeout):
        if is_older_than_timeout:
            self.update_state(CharacterStates.SLEEP)
            self.pacing_timer.stop()
        elif self.current_state == CharacterStates.SLEEP:
            self.update_state(CharacterStates.HAPPY)
            self.pacing_timer.start(self.default_pacing_interval)

    def update_code_quality(self, warnings_count, errors_count):
        if self.current_state == CharacterStates.SLEEP:
            return

        if errors_count > 0:
            new_state = CharacterStates.PANIC
            self.pacing_timer.stop()

        elif warnings_count > 10:
            new_state = CharacterStates.WARNING
            new_speed = self.default_speed + warnings_count
            self.movie.setSpeed(new_speed)

            new_pacing_time = int(self.default_pacing_interval - warnings_count)
            new_pacing_time = max(20, new_pacing_time)
            new_pacing_time = min(100, new_pacing_time)
            self.update_pacing_timer(new_pacing_time)

        else:
            self.update_pacing_timer(self.default_pacing_interval)
            self.current_move_offset = 5
            new_state = CharacterStates.HAPPY

        self.update_state(new_state)

    def update_pacing_timer(self, interval):
        if self.current_state != CharacterStates.EXCITED:
            self.pacing_timer.start(interval)

    def update_state(self, new_state):
        prev_state = self.current_state

        if self.current_state != new_state:
            if (
                time.time() - self.excited_time_stamp > self.excited_cool_down
                or new_state == CharacterStates.EXCITED
            ):
                self.current_state = new_state
                self.movie.setSpeed(self.default_speed)
                self.movie.stop()
                self.movie.setFileName(self.current_state.value)
                self.movie.start()

            if prev_state != CharacterStates.EXCITED:
                self.movie.setSpeed(self.default_speed)
                self.movie.stop()
                self.movie.setFileName(self.current_state.value)
                self.movie.start()

    def character_pacing(self):
        if self.current_state != CharacterStates.PANIC:
            current_pos = self.pos()

            if self.current_move_step >= self.max_move_steps:
                self.increase_offset = False
                self.move_offset *= -1
            elif self.current_move_step <= 0:
                self.increase_offset = True
                self.move_offset *= -1

            if self.increase_offset:
                self.current_move_step += 1
            else:
                self.current_move_step -= 1

            new_x = current_pos.x() + self.move_offset
            self.move(new_x, current_pos.y())

    def excite_character(self):
        self.excited_time_stamp = time.time()
        self.update_state(CharacterStates.EXCITED)
        self.pacing_timer.stop()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint()
            self.excite_character()

    def mouseMoveEvent(self, event):
        if self.drag_position:
            delta = event.globalPosition().toPoint() - self.drag_position
            self.move(self.pos() + delta)
            self.drag_position = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.drag_position = None

    def contextMenuEvent(self, event):
        menu = QMenu(self)

        quit_action = menu.addAction("Quit")
        action = menu.exec(event.globalPos())

        if action == quit_action:
            QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = Character()
    window.show()

    sys.exit(app.exec())
