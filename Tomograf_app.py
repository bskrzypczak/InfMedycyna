from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QFileDialog, QMessageBox, QHBoxLayout
)
from PyQt6.QtGui import QPixmap, QImage
import sys
import numpy as np
import matplotlib.pyplot as plt
from main_tomograf import wczytaj_obraz, rekonstrukcja_wlasna, generuj_projekcje, wyswietl_sinogram
from skimage.color import gray2rgb
from skimage.draw import line_nd
import time

class TomografApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Symulator Tomografu")
        self.setGeometry(100, 100, 800, 600)

        # Zmienne stanu
        self.obraz = None
        self.projekcje = None
        self.rekonstrukcja = None

        # GUI
        self.layout = QVBoxLayout()

        self.label_info = QLabel("Wczytaj obraz, aby rozpocząć")
        self.layout.addWidget(self.label_info)

        self.btn_layout = QHBoxLayout()

        self.btn_wczytaj = QPushButton("Wybierz obraz")
        self.btn_wczytaj.clicked.connect(self.wczytaj_obraz)
        self.btn_layout.addWidget(self.btn_wczytaj)

        self.btn_sinogram = QPushButton("Generuj sinogram")
        self.btn_sinogram.clicked.connect(self.generuj_sinogram_z_animacja)
        self.btn_layout.addWidget(self.btn_sinogram)

        self.btn_rekonstrukcja = QPushButton("Rekonstrukcja obrazu")
        self.btn_rekonstrukcja.clicked.connect(self.rekonstrukcja_obrazu)
        self.btn_layout.addWidget(self.btn_rekonstrukcja)

        self.btn_zapisz = QPushButton("Zapisz jako DICOM")
        self.btn_zapisz.clicked.connect(self.zapisz_dicom_placeholder)
        self.btn_layout.addWidget(self.btn_zapisz)

        self.layout.addLayout(self.btn_layout)

        self.image_label = QLabel()
        self.layout.addWidget(self.image_label)

        self.setLayout(self.layout)

    def wyswietl_na_labelu(self, obraz):
        if obraz is None:
            return
        obraz = (obraz * 255).astype(np.uint8) if obraz.max() <= 1.0 else obraz.astype(np.uint8)
        if obraz.ndim == 2:
            h, w = obraz.shape
            bytes_per_line = w
            qt_image = QImage(obraz.data, w, h, bytes_per_line, QImage.Format.Format_Grayscale8)
        else:
            h, w, ch = obraz.shape
            bytes_per_line = ch * w
            qt_image = QImage(obraz.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)
        self.image_label.setPixmap(pixmap.scaled(512, 512))

    def wczytaj_obraz(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Wybierz obraz", "", "Obrazy (*.dcm *.png *.jpg *.bmp)")
        if file_path:
            self.obraz, _ = wczytaj_obraz(file_path)
            self.label_info.setText(f"Wczytano: {file_path.split('/')[-1]}")
            self.wyswietl_na_labelu(self.obraz)
            QMessageBox.information(self, "Wczytano", "Obraz został pomyślnie wczytany")

    def generuj_sinogram_z_animacja(self):
        if self.obraz is None:
            QMessageBox.warning(self, "Brak obrazu", "Najpierw wczytaj obraz.")
            return

        obraz = self.obraz
        wys, szer = obraz.shape
        liczba_katow = 180
        #liczba_emiterow = max(wys, szer)
        liczba_emiterow = 256
        promien = np.hypot(wys, szer) / 2
        srodek = (szer // 2, wys // 2)

        sinogram = []

        for kat in range(liczba_katow):
            projekcja = []
            obraz_rgb = (gray2rgb(obraz) * 255).astype(np.uint8)

            for emiter in range(liczba_emiterow):
                przesuniecie = emiter - liczba_emiterow / 2
                start_punkt = (
                    promien * np.cos(np.radians(przesuniecie + kat)) + srodek[0],
                    promien * np.sin(np.radians(przesuniecie + kat)) + srodek[1]
                )
                koniec_punkt = (
                    promien * (-np.cos(np.radians(-przesuniecie + kat))) + srodek[0],
                    promien * (-np.sin(np.radians(-przesuniecie + kat))) + srodek[1]
                )

                rr, cc = line_nd(start_punkt, koniec_punkt)
                rr = np.clip(rr, 0, wys - 1)
                cc = np.clip(cc, 0, szer - 1)

                suma = np.sum(obraz[rr, cc])
                projekcja.append(suma)

                obraz_rgb[rr, cc] = [0, 255, 0] if przesuniecie == 0 else [255, 255, 255]

            sinogram.append(projekcja)
            self.wyswietl_na_labelu(obraz_rgb)
            QApplication.processEvents()
            time.sleep(0.01)

        self.projekcje = sinogram
        wyswietl_sinogram(sinogram)
        sinogram_np = np.array(sinogram)
        self.wyswietl_na_labelu(sinogram_np / sinogram_np.max())

    def rekonstrukcja_obrazu(self):
        if self.projekcje is None:
            QMessageBox.warning(self, "Brak sinogramu", "Najpierw wygeneruj sinogram.")
            return
        rozmiar = len(self.projekcje[0])
        self.rekonstrukcja = rekonstrukcja_wlasna(self.projekcje, liczba_katow=180, rozmiar_obrazka=rozmiar)
        self.wyswietl_na_labelu(self.rekonstrukcja)

    def zapisz_dicom_placeholder(self):
        QMessageBox.information(self, "DICOM", "Tutaj będzie zapis do pliku DICOM (jeszcze niezaimplementowany)")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TomografApp()
    window.show()
    sys.exit(app.exec())
