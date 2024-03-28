import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QGraphicsView, QGraphicsScene, QMessageBox
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QGraphicsVideoItem
from PyQt5.QtCore import QTimer, QUrl, Qt, QSizeF
from PyQt5.QtGui import QImage, QPainter
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class VideoPlayerApp(QMainWindow):
    def __init__(self):
        super().__init__()
    
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.scene = QGraphicsScene(self)
        self.scene.setBackgroundBrush(Qt.transparent)

        QTimer.singleShot(100, lambda: self.resizeEvent(None))
        self.setupUI()
        self.showFullScreen()

    def setupUI(self):
        self.imageWidgets = []
        audio_base_path = os.path.join(BASE_DIR, "tones")
        image_base_path = os.path.join(BASE_DIR, "vg")
        self.audioFiles = [(os.path.join(audio_base_path, f"{i}L.wav"), os.path.join(audio_base_path, f"{i}R.wav")) for i in range(1, 9)]
        
        self.positions_left = {0: (40, 80), 1: (100, 580), 2: (200, 140), 3: (80, 460), 4: (90, 550), 5: (10, 720), 6: (100, 740), 7: (300, 760)}
        self.display_on_right = False
        
        for i, audio_paths in enumerate(self.audioFiles, start=1):
            image_path = os.path.join(image_base_path, f"{i}.png")
            widget = TransparentImageWidget(image_path, audio_paths)
            widget.hide()
            proxy = self.scene.addWidget(widget)
            proxy.setZValue(1)
            self.imageWidgets.append(widget)

        self.videoItem = QGraphicsVideoItem()
        self.videoItem.setZValue(0)
        self.scene.addItem(self.videoItem)
        
        self.view = QGraphicsView(self.scene, self)
        self.view.setStyleSheet("background: transparent")
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setCentralWidget(self.view)

        self.player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.player.setVideoOutput(self.videoItem)
        video_path = os.path.join(image_base_path, "BackgroundVideo.mp4")
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))
        self.player.play()
        self.player.stateChanged.connect(self.checkVideoState)

        self.calculateMirroredPositions()

    def calculateMirroredPositions(self):
        self.positions_right = {}
        window_width = self.view.width()
        for index, (x, y) in self.positions_left.items():
            mirrored_x = window_width - x - 100
            self.positions_right[index] = (mirrored_x, y)

    def toggleImage(self, index):
        self.calculateMirroredPositions()
        widget = self.imageWidgets[index]
        side = 'right' if self.display_on_right else 'left'
        position = self.positions_right[index] if side == 'right' else self.positions_left[index]
        
        x, y = position
        widget.move(x, y)
        widget.setVisible(not widget.isVisible())  # Toggle visibility
        if widget.isVisible():
            widget.playAudio(side)
            widget.setSide(side)  # Update image based on side
        else:
            widget.stopAudio()
        widget.raise_()

    def toggle_side(self):
        self.display_on_right = not self.display_on_right
        for widget in self.imageWidgets:
            side = 'right' if self.display_on_right else 'left'
            if widget.isVisible():
                widget.stopAudio()
                widget.playAudio(side)
                widget.setSide(side)  # Update image based on side
                widget.raise_()

    def checkVideoState(self, state):
        if state == QMediaPlayer.StoppedState:
            self.player.play()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.confirmExit()
        elif event.key() == Qt.Key_M:
            self.player.setMuted(not self.player.isMuted())
        elif event.key() in (Qt.Key_F, Qt.Key_G):
            self.toggle_side()
        else:
            index = event.key() - Qt.Key_1
            if 0 <= index < len(self.imageWidgets):
                self.toggleImage(index)

    def confirmExit(self):
        reply = QMessageBox.question(self, 'Exit Confirmation', 'Are you sure you want to exit?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            QApplication.instance().exit()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.videoItem.setSize(QSizeF(self.view.width(), self.view.height()))
        self.calculateMirroredPositions()  # Update positions on resize

class TransparentImageWidget(QWidget):
    def __init__(self, image_path, audio_paths, parent=None):
        super().__init__(parent)
        self.original_image = QImage(image_path)
        self.mirrored_image = self.original_image.mirrored(True, False)  # Horizontal mirroring
        self.current_image = self.original_image  # Start with the original image
        
        if not self.original_image.isNull():
            self.setFixedSize(self.original_image.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation).size())
        else:
            print(f"Failed to load image at {image_path}")

        self.audioPlayer = QMediaPlayer()
        self.audioPaths = audio_paths
        self.audioPlayer.mediaStatusChanged.connect(self.checkMediaStatus)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

    def paintEvent(self, event):
        painter = QPainter(self)
        scaled_img = self.current_image.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter.drawImage(self.rect(), scaled_img)

    def playAudio(self, side):
        audio_path = self.audioPaths[0] if side == 'left' else self.audioPaths[1]
        self.audioPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(audio_path)))
        self.audioPlayer.play()

    def setSide(self, side):
        # If the widget is to be displayed on the right, use the mirrored image
        self.current_image = self.mirrored_image if side == 'right' else self.original_image
        self.update()  # Trigger a repaint to show the updated image

    def stopAudio(self):
        self.audioPlayer.stop()

    def checkMediaStatus(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.audioPlayer.setPosition(0)
            self.audioPlayer.play()

def main():
    app = QApplication(sys.argv)
    mainWindow = VideoPlayerApp()
    mainWindow.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
