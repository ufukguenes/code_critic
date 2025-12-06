import sys
from PyQt6.QtWidgets import QApplication, QLabel, QWidget, QMenu
from PyQt6.QtGui import QMovie
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
import subprocess
import re

GIF_HAPPY = "/home/ufuk/Downloads/pika_happy.gif"
GIF_SAD = "/home/ufuk/Downloads/pika_sad.gif"
GIF_PANIC = "/home/ufuk/Downloads/pika_sad.gif"
PROJECT_PATH = "/home/ufuk/Documents/Programming/kuh-handel"
WINDOW_WIDTH = 100
WINDOW_HEIGHT = 100


class CodeQualityChecker(QThread):
    result_ready = pyqtSignal((int, int))

    def run(self):
        try:
            cmd = ["cargo", "check"]
            result = subprocess.run(
                cmd, cwd=PROJECT_PATH, capture_output=True, text=True
            )
            output = result.stderr + result.stdout
            warnings_count = self.count_occurrences(output, "warning:")
            errors_count = self.count_occurrences(output, "error:")

            self.result_ready.emit(warnings_count, errors_count)

        except Exception as e:
            print("Error running cargo check:", e)
            self.result_ready.emit(0)

    def count_occurrences(self, text, pattern):
        occurrences = [match.start() for match in re.finditer(pattern, text)]
        return len(occurrences)


class Character(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.BypassWindowManagerHint
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.label = QLabel(self)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.movie = QMovie(GIF_HAPPY)
        self.label.setMovie(self.movie)
        self.movie.start()

        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.movie.setScaledSize(self.size())
        self.label.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        screen = app.primaryScreen()
        rect = screen.availableGeometry()  # type: ignore
        bottom_right_x = rect.right() - self.width()
        bottom_right_y = rect.bottom() - self.height() - 30
        self.move(bottom_right_x, bottom_right_y)

        self.drag_position = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.run_code_check)
        self.timer.start(1000)

    def run_code_check(self):
        self.worker = CodeQualityChecker()
        self.worker.result_ready.connect(self.update_gif)
        self.worker.start()

    def update_gif(self, warnings_count, errors_count):
        if errors_count > 0:
            self.movie.stop()
            self.movie.setFileName(GIF_PANIC)
            self.movie.start()
        elif warnings_count > 100:
            self.movie.stop()
            self.movie.setFileName(GIF_SAD)
            self.movie.start()
        else:
            self.movie.stop()
            self.movie.setFileName(GIF_HAPPY)
            self.movie.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint()

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
