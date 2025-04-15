import sys
import time

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QCheckBox, QLabel, QFrame, QFileDialog, QSpinBox, QMessageBox, QInputDialog,QSizePolicy,QComboBox

)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QImage, qRgb
from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox

from dzialaj import wczytanie_obrazu, tworzenie_sinogramu, filter_sinogram, transforma_radona,save_dicom_image
import numpy as np

from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtGui import QImage, QPixmap
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

sinogram_label = None
reconstructed_image_label = None
zrekonstruowany_obraz = None
saved_dicom_path = None
combo_filtr = None
dicom_viewer_window = None
def wczytaj_i_pokaz_obraz():
    global obraz, input_image_frame

    sciezka, _ = QFileDialog.getOpenFileName(
        None, "Wybierz obraz", "", "Wszystkie pliki (*);;Obrazy (*.png *.jpg *.jpeg *.bmp *.dcm)"
    )

    if sciezka:
        obraz, _ = wczytanie_obrazu(sciezka, rozmiar_obrazu=(256, 256))  # zmiana tutaj na funkcję z dzialaj.py

        if obraz is not None:
            print("Obraz wczytany poprawnie!")

            # upewnienie się, że obraz jest w zakresie 0-255
            obraz_display = (obraz * 255).astype(np.uint8)

            # Konwertowanie obrazu na QImage
            try:
                height, width = obraz_display.shape
                bytes_per_line = width
                q_image = QImage(obraz_display.data, width, height, bytes_per_line, QImage.Format.Format_Grayscale8)

                pixmap = QPixmap.fromImage(q_image).scaled(
                    input_image_frame.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )

                layout = input_image_frame.layout()
                if layout is None:
                    layout = QVBoxLayout()
                    input_image_frame.setLayout(layout)

                # Usunięcie starego obrazu
                for i in reversed(range(layout.count())):
                    widget = layout.itemAt(i).widget()
                    if widget is not None:
                        widget.deleteLater()

                label = QLabel()
                label.setPixmap(pixmap)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(label)

                print("Obraz wyświetlony.")
            except Exception as e:
                print(f"Błąd przy konwersji obrazu: {e}")
                QMessageBox.critical(None, "Błąd", "Wystąpił błąd podczas konwersji obrazu.")
        else:
            print("Błąd podczas wczytywania obrazu")
            QMessageBox.critical(None, "Błąd", "Nie udało się wczytać obrazu.")



def generuj_sinogram():
    global obraz, sinogram, krok_alpha, rozpietosc, liczba_detektorow
    global chk_scan_animation, sinogram_frame, sinogram_label

    if obraz is not None:
        try:
            # Wyciąganie wartości z QSpinBox, jeśli trzeba
            krok_alpha_val = krok_alpha.value() if isinstance(krok_alpha, QSpinBox) else krok_alpha
            rozpietosc_val = rozpietosc.value() if isinstance(rozpietosc, QSpinBox) else rozpietosc
            liczba_detektorow_val = liczba_detektorow.value() if isinstance(liczba_detektorow, QSpinBox) else liczba_detektorow

            kroki = int(180 / krok_alpha_val)

            # Tworzenie sinogramu z dzialaj.py
            sinogram = tworzenie_sinogramu(
                obraz=obraz,
                kroki=kroki,
                rozpietosc=rozpietosc_val,
                liczba_promieni=liczba_detektorow_val,
                max_kat=180
            )
            wybrany_filtr = combo_filtr.currentText()
            if wybrany_filtr != "brak":
                sinogram = filter_sinogram(sinogram, typ_filtru=wybrany_filtr)

            # Tylko do wyświetlenia
            sinogram_display = np.clip(sinogram, 0, np.max(sinogram))
            sinogram_display = (sinogram_display / np.max(sinogram_display) * 255).astype(np.uint8)
            sinogram_display = sinogram_display.T  # żeby był poziomo

            layout = sinogram_frame.layout()
            if layout is None:
                layout = QVBoxLayout()
                sinogram_frame.setLayout(layout)

            if sinogram_label is None:
                sinogram_label = QLabel()
                sinogram_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                sinogram_label.setMaximumSize(sinogram_frame.size())
                layout.addWidget(sinogram_label)

            if chk_scan_animation.isChecked():
                for i in range(1, sinogram_display.shape[1] + 1):
                    current_sinogram = sinogram_display[:, :i]
                    q_image = QImage(current_sinogram.tobytes(), current_sinogram.shape[1], current_sinogram.shape[0],
                                     current_sinogram.shape[1], QImage.Format.Format_Grayscale8)
                    pixmap = QPixmap.fromImage(q_image).scaled(
                        sinogram_frame.size(), Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation)

                    sinogram_label.setPixmap(pixmap)
                    QApplication.processEvents()
                    time.sleep(0.05)
            else:
                q_image = QImage(sinogram_display.tobytes(), sinogram_display.shape[1], sinogram_display.shape[0],
                                 sinogram_display.shape[1], QImage.Format.Format_Grayscale8)
                pixmap = QPixmap.fromImage(q_image).scaled(
                    sinogram_frame.size(), Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)

                sinogram_label.setPixmap(pixmap)

            print(f"Sinogram wygenerowany. Shape: {sinogram.shape}")

        except Exception as e:
            print(f"Błąd przy generowaniu sinogramu: {e}")
            QMessageBox.critical(None, "Błąd", "Wystąpił błąd podczas generowania sinogramu.")
    else:
        QMessageBox.warning(None, "Błąd", "Najpierw wczytaj obraz przed generowaniem sinogramu.")

def rekonstruuj_obraz():
    global sinogram, obraz, krok_alpha, liczba_detektorow, rozpietosc
    global reconstructed_image_frame, reconstructed_image_label, zrekonstruowany_obraz

    if sinogram is None or obraz is None:
        QMessageBox.warning(None, "Błąd", "Najpierw wczytaj obraz i wygeneruj sinogram.")
        return

    try:
        krok_alpha_val = krok_alpha.value() if isinstance(krok_alpha, QSpinBox) else krok_alpha
        liczba_detektorow_val = liczba_detektorow.value() if isinstance(liczba_detektorow, QSpinBox) else liczba_detektorow
        rozpietosc_val = rozpietosc.value() if isinstance(rozpietosc, QSpinBox) else rozpietosc

        liczba_katow = int(180 / krok_alpha_val)

        if chk_scan_animation.isChecked():
            animuj_rekonstrukcje()
            return

        reconstructed = transforma_radona(
            obraz.shape,
            sinogram,
            liczba_katow,
            rozpietosc_val,
            liczba_detektorow_val,
            180
        )

        zrekonstruowany_obraz = reconstructed  # zapisz do globalnej zmiennej

        reconstructed = np.clip(reconstructed, 0, 1)
        reconstructed_display = (reconstructed * 255).astype(np.uint8)

        height, width = reconstructed_display.shape
        bytes_per_line = width
        q_image = QImage(reconstructed_display.tobytes(), width, height, bytes_per_line, QImage.Format.Format_Grayscale8)
        pixmap = QPixmap.fromImage(q_image).scaled(
            reconstructed_image_frame.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        layout = reconstructed_image_frame.layout()
        if layout is None:
            layout = QVBoxLayout()
            reconstructed_image_frame.setLayout(layout)

        if reconstructed_image_label is None:
            reconstructed_image_label = QLabel()
            reconstructed_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            reconstructed_image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
            layout.addWidget(reconstructed_image_label)
        else:
            reconstructed_image_label.clear()

        reconstructed_image_label.setPixmap(pixmap)

        print(f"Rekonstrukcja zakończona. Shape: {reconstructed.shape}")

    except Exception as e:
        print(f"Błąd przy rekonstrukcji: {e}")
        QMessageBox.critical(None, "Błąd", "Wystąpił błąd podczas rekonstrukcji obrazu.")

def animuj_rekonstrukcje():
    global sinogram, obraz, krok_alpha, liczba_detektorow, rozpietosc
    global reconstructed_image_frame, reconstructed_image_label, zrekonstruowany_obraz

    try:
        krok_alpha_val = krok_alpha.value() if isinstance(krok_alpha, QSpinBox) else krok_alpha
        liczba_detektorow_val = liczba_detektorow.value() if isinstance(liczba_detektorow, QSpinBox) else liczba_detektorow
        rozpietosc_val = rozpietosc.value() if isinstance(rozpietosc, QSpinBox) else rozpietosc

        liczba_katow = int(180 / krok_alpha_val)
        shape_obraz = obraz.shape

        # Wywołanie transforma_radona z zapisem wszystkich etapów
        print("Generowanie klatek rekonstrukcji...")
        zrekonstruowany_obraz, klatki = transforma_radona(
            shape_obraz,
            sinogram,
            liczba_katow,
            rozpietosc_val,
            liczba_detektorow_val,
            180,
            zwroc_klatki=True
        )

        print(f"Wygenerowano {len(klatki)} klatek. Rozpoczynanie animacji...")

        # Ustawienie layoutu i QLabel jeśli potrzeba
        layout = reconstructed_image_frame.layout()
        if layout is None:
            layout = QVBoxLayout()
            reconstructed_image_frame.setLayout(layout)

        if reconstructed_image_label is None:
            reconstructed_image_label = QLabel()
            reconstructed_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            reconstructed_image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
            layout.addWidget(reconstructed_image_label)
        else:
            reconstructed_image_label.clear()

        # Wyświetlanie klatek
        for frame in klatki:
            frame_display = (frame * 255).astype(np.uint8)
            height, width = frame_display.shape
            bytes_per_line = width
            q_image = QImage(frame_display.tobytes(), width, height, bytes_per_line, QImage.Format.Format_Grayscale8)
            pixmap = QPixmap.fromImage(q_image).scaled(
                reconstructed_image_frame.size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            reconstructed_image_label.setPixmap(pixmap)
            QApplication.processEvents()
            time.sleep(0.03)

        print("Animacja zakończona.")

    except Exception as e:
        print(f"Błąd przy animacji z bufora: {e}")
        QMessageBox.critical(None, "Błąd", "Wystąpił błąd podczas animacji rekonstrukcji.")


def save_dicom_file():
    global zrekonstruowany_obraz, imie, nazwisko, pesel, komentarz

    if zrekonstruowany_obraz is None:
        QMessageBox.warning(None, "Błąd", "Najpierw wykonaj rekonstrukcję obrazu.")
        return

    try:
        # Okno zapisu pliku
        filename, _ = QFileDialog.getSaveFileName(None, "Zapisz plik DICOM", "", "DICOM files (*.dcm)")
        if not filename:
            return

        # Sprawdzenie danych pacjenta
        if not imie or not nazwisko or not pesel:
            QMessageBox.warning(None, "Błąd", "Dane pacjenta muszą być wprowadzone.")
            return

        patientname = f"{imie} {nazwisko}"
        patientID = pesel
        patient_comments = komentarz

        # Przygotowanie obrazu do zapisu
        reconstructed_to_save = (np.clip(zrekonstruowany_obraz, 0, 1) * 255).astype(np.uint8)

        # Zapis pliku
        saved_filename = save_dicom_image(reconstructed_to_save, filename, patientname, patientID, patient_comments)

        if saved_filename:
            QMessageBox.information(None, "DICOM", f"Plik DICOM został zapisany jako:\n{saved_filename}")
            global saved_dicom_path, btn_show_saved_dicom
            saved_dicom_path = saved_filename
            btn_show_saved_dicom.setVisible(True)
        else:
            QMessageBox.critical(None, "Błąd", "Nie udało się zapisać pliku DICOM.")

        print("Plik DICOM zapisany pomyślnie.")

    except Exception as e:
        print(f"Błąd przy zapisie DICOM: {e}")
        QMessageBox.critical(None, "Błąd", "Wystąpił błąd podczas zapisu pliku DICOM.")



def pokaz_okno_danych_pacjenta():
    global imie, nazwisko, pesel, komentarz  # Używamy zmiennych globalnych

    dialog = QDialog()
    dialog.setStyleSheet("background-color: #2A2A2A; color: white; font-size: 14px;")
    dialog.setWindowTitle("Dane pacjenta")

    layout = QFormLayout()

    # Wstawiamy obecne dane pacjenta do formularza
    imie_edit = QLineEdit(imie)
    nazwisko_edit = QLineEdit(nazwisko)
    pesel_edit = QLineEdit(pesel)
    komentarz_edit = QLineEdit(komentarz)

    layout.addRow("Imię:", imie_edit)
    layout.addRow("Nazwisko:", nazwisko_edit)
    layout.addRow("PESEL:", pesel_edit)
    layout.addRow("Komentarz:", komentarz_edit)

    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons.setStyleSheet("""
    QDialogButtonBox QPushButton {
        font-size: 14px;
        background-color: #007BFF;
        color: white;
        border-radius: 8px;
        padding: 6px 12px;
    }
    QDialogButtonBox QPushButton:hover {
        background-color: #168FFF;
    }
    """)

    buttons.accepted.connect(
        lambda: zapisz_dane(imie_edit.text(), nazwisko_edit.text(), pesel_edit.text(), komentarz_edit.text(), dialog))
    buttons.rejected.connect(dialog.reject)

    layout.addRow(buttons)
    dialog.setLayout(layout)

    dialog.exec()


def zapisz_dane(new_imie, new_nazwisko, new_pesel, new_komentarz, dialog):
    global imie, nazwisko, pesel, komentarz  # Używamy zmiennych globalnych

    # Zaktualizowanie danych pacjenta
    imie = new_imie
    nazwisko = new_nazwisko
    pesel = new_pesel
    komentarz = new_komentarz

    # Zaktualizowanie etykiet w głównym oknie
    patient_info_labels["Imię"].setText(f"Imię: {imie}")
    patient_info_labels["Nazwisko"].setText(f"Nazwisko: {nazwisko}")
    patient_info_labels["PESEL"].setText(f"PESEL: {pesel}")
    patient_info_labels["Komentarz"].setText(f"Komentarz: {komentarz}")

    dialog.accept()





def pokaz_okno_ustawien_tomografu():
    global krok_alpha, rozpietosc, liczba_detektorow  # Używamy zmiennych globalnych

    dialog = QDialog()
    dialog.setWindowTitle("Ustawienia tomografu")
    dialog.setStyleSheet("background-color: #2A2A2A; color: white; font-size: 14px;")

    layout = QFormLayout()

    # Tworzymy QSpinBox dla ustawień tomografu
    krok_alpha = QSpinBox()
    krok_alpha.setRange(1, 360)
    krok_alpha.setValue(1)

    liczba_detektorow = QSpinBox()
    liczba_detektorow.setRange(10, 1000)
    liczba_detektorow.setValue(256)

    rozpietosc = QSpinBox()
    rozpietosc.setRange(1, 360)
    rozpietosc.setValue(180)

    # Dodanie do layoutu
    layout.addRow("Krok Δα:", krok_alpha)
    layout.addRow("Liczba detektorów:", liczba_detektorow)
    layout.addRow("Rozpiętość układu:", rozpietosc)

    # Przycisk OK i Cancel
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons.setStyleSheet("""
    QDialogButtonBox QPushButton {
        font-size: 14px;
        background-color: #007BFF;
        color: white;
        border-radius: 8px;
        padding: 6px 12px;
    }
    QDialogButtonBox QPushButton:hover {
        background-color: #168FFF;
    }
    """)
    # Zapisz dane po kliknięciu OK
    buttons.accepted.connect(
        lambda: zapisz_ustawienia(krok_alpha.value(), liczba_detektorow.value(), rozpietosc.value(), dialog))
    buttons.rejected.connect(dialog.reject)

    layout.addRow(buttons)
    dialog.setLayout(layout)

    dialog.exec()


def zapisz_ustawienia(new_krok_alpha, new_liczba_detektorow, new_rozpietosc, dialog):
    global krok_alpha, liczba_detektorow, rozpietosc, tomograph_settings_labels

    # Zaktualizowanie ustawień tomografu
    krok_alpha = new_krok_alpha
    liczba_detektorow = new_liczba_detektorow
    rozpietosc = new_rozpietosc

    # Upewnij się, że zmienne tomograph_settings_labels są zainicjalizowane
    if not tomograph_settings_labels:
        tomograph_settings_labels = {
            "Krok Δα": QLabel(f"Krok Δα: {krok_alpha}"),
            "Liczba detektorów": QLabel(f"Liczba detektorów: {liczba_detektorow}"),
            "Rozpiętość układu": QLabel(f"Rozpiętość układu: {rozpietosc}")
        }

    # Zaktualizowanie etykiet w głównym oknie
    tomograph_settings_labels["Krok Δα"].setText(f"Krok Δα: {krok_alpha}")
    tomograph_settings_labels["Liczba detektorów"].setText(f"Liczba detektorów: {liczba_detektorow}")
    tomograph_settings_labels["Rozpiętość układu"].setText(f"Rozpiętość układu: {rozpietosc}")

    dialog.accept()

def pokaz_zapisany_dicom():
    global saved_dicom_path, dicom_viewer_window

    if not saved_dicom_path:
        QMessageBox.warning(None, "Błąd", "Brak zapisanego pliku DICOM.")
        return

    try:
        from pydicom import dcmread

        ds = dcmread(saved_dicom_path)
        img = ds.pixel_array

        dicom_viewer_window = QWidget()
        window = dicom_viewer_window
        window.setWindowTitle("Zapisany plik DICOM")
        window.resize(600, 700)
        layout = QVBoxLayout()

        image_label = QLabel()
        height, width = img.shape
        q_image = QImage((img / img.max() * 255).astype(np.uint8).tobytes(), width, height, width, QImage.Format.Format_Grayscale8)
        pixmap = QPixmap.fromImage(q_image).scaled(500, 500, Qt.AspectRatioMode.KeepAspectRatio)
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(image_label)

        # Metadane
        meta_label = QLabel()
        meta_label.setStyleSheet("color: white; font-size: 13px;")
        meta_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        data = ds.get("ContentDate", "Brak daty")
        czas = ds.get("ContentTime", "Brak czasu")

        # Formatowanie daty i czasu jeśli są dostępne
        if data != "Brak daty" and len(data) == 8:
            data = f"{data[:4]}-{data[4:6]}-{data[6:]}"
        if czas != "Brak czasu" and len(czas) >= 6:
            czas = f"{czas[:2]}:{czas[2:4]}:{czas[4:6]}"

        meta_label.setText(
            f"Pacjent: {ds.PatientName}\n"
            f"PESEL (Patient ID): {ds.PatientID}\n"
            f"Data: {data} {czas}\n"
            f"Komentarz: {ds.get('PatientComments', '-')}"
        )
        layout.addWidget(meta_label)

        window.setStyleSheet("background-color: #2A2A2A; color: white;")
        window.setLayout(layout)
        window.show()

    except Exception as e:
        QMessageBox.critical(None, "Błąd", f"Nie udało się otworzyć pliku:\n{e}")

# Zmienna do przechowywania danych pacjenta
imie = ""
nazwisko = ""
pesel = ""
komentarz = ""

# Zmienna na etykiety
patient_info_labels = {}
tomograph_settings_labels ={}

#ustawienia tomografu
krok_alpha = 1
liczba_detektorow = 256
rozpietosc = 180

chk_scan_animation = None
def main():
    global patient_info_labels,tomograph_settings_labels
    global frames,chk_scan_animation
    global input_image_frame, sinogram_frame, reconstructed_image_frame
    global combo_filtr
    global btn_show_saved_dicom
    app = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("CT simulation")
    window.resize(1200, 900)

    # Tło okna
    window.setStyleSheet("background-color: #3A3A3A;")

    # Layout pionowy
    layout = QVBoxLayout()

    # Żeby przycisk był w lewym górnym rogu, zerujemy marginesy i ustalamy wyrównanie do góry
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    # Tytuł aplikacji
    title_label = QLabel("CT simulation")
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title_label.setStyleSheet("font-size: 24px; color: white; padding: 10px;")
    layout.addWidget(title_label)

    # Linia pod tytułem
    line1 = QFrame()
    line1.setFrameShape(QFrame.Shape.HLine)
    line1.setStyleSheet("color: #555;")
    layout.addWidget(line1)

    # Layout poziomy dla górnych przycisków
    top_buttons_layout = QHBoxLayout()
    top_buttons_layout.setContentsMargins(10, 10, 10, 0)
    top_buttons_layout.setSpacing(10)

    # Przycisk "Wczytaj obraz"
    btn_load_image = QPushButton("Wczytaj obraz")
    btn_load_image.setStyleSheet("""
QPushButton {
    font-size: 16px;
    background-color: #007BFF;
    color: white;
    border-radius: 10px;
    padding: 5px;
}
QPushButton:hover {
    background-color: #168FFF;
}
""")
    btn_load_image.clicked.connect(wczytaj_i_pokaz_obraz)
    top_buttons_layout.addWidget(btn_load_image)

    # Przycisk "Generuj sinogram"
    btn_generate_sinogram = QPushButton("Generuj sinogram")
    btn_generate_sinogram.setStyleSheet("""
QPushButton {
    font-size: 16px;
    background-color: #007BFF;
    color: white;
    border-radius: 10px;
    padding: 5px;
}
QPushButton:hover {
    background-color: #168FFF;
}
""")
    btn_generate_sinogram.clicked.connect(generuj_sinogram)
    top_buttons_layout.addWidget(btn_generate_sinogram)

    # Przycisk "Rekonstruuj obraz"
    btn_reconstruct_image = QPushButton("Rekonstruuj obraz")
    btn_reconstruct_image.setStyleSheet("""
QPushButton {
    font-size: 16px;
    background-color: #007BFF;
    color: white;
    border-radius: 10px;
    padding: 5px;
}
QPushButton:hover {
    background-color: #168FFF;
}
""")
    btn_reconstruct_image.clicked.connect(rekonstruuj_obraz)
    top_buttons_layout.addWidget(btn_reconstruct_image)

    # Przycisk "Zapisz plik DICOM"
    btn_save_dicom = QPushButton("Zapisz plik DICOM")
    btn_save_dicom.setStyleSheet("""
    QPushButton {
        font-size: 16px;
        background-color: #007BFF;
        color: white;
        border-radius: 10px;
        padding: 5px;
    }
    QPushButton:hover {
        background-color: #168FFF;
    }
    """)
    btn_save_dicom.clicked.connect(save_dicom_file)  # Wywołanie funkcji zapisu DICOM
    top_buttons_layout.addWidget(btn_save_dicom)
    layout.addLayout(top_buttons_layout)

    # Layout poziomy: checkbox + combo filtr w jednej linii
    filters_and_options_layout = QHBoxLayout()
    filters_and_options_layout.setContentsMargins(10, 5, 10, 0)
    filters_and_options_layout.setSpacing(20)

    chk_scan_animation = QCheckBox("Pokaż animację skanowania iteracyjnie")
    chk_scan_animation.setStyleSheet("""
        QCheckBox {
            font-size: 16px;
            color: white;
            padding: 5px;
        }
        QCheckBox::indicator {
            width: 20px;
            height: 20px;
        }
    """)
    chk_scan_animation.clicked.connect(lambda checked: None)

    filtr_label = QLabel("Filtr:")
    filtr_label.setStyleSheet("font-size: 16px; color: white;")

    combo_filtr = QComboBox()
    combo_filtr.addItems(["brak", "ram-lak", "shepp-logan", "cosine", "hamming", "hann"])
    combo_filtr.setStyleSheet("""
        QComboBox {
            font-size: 16px;
            min-width: 160px;
            color: white;
        }
        QComboBox QAbstractItemView {
        background-color: #2A2A2A;
        color: white;
        selection-color: white;
    }
    """)

    filters_and_options_layout.addWidget(chk_scan_animation)
    filters_and_options_layout.addSpacing(50)
    filters_and_options_layout.addWidget(filtr_label)
    filters_and_options_layout.addWidget(combo_filtr)

    settings_widget = QWidget()
    settings_widget.setLayout(filters_and_options_layout)
    layout.addWidget(settings_widget, alignment=Qt.AlignmentFlag.AlignHCenter)

    # Linia pod checkboxem
    line_checkbox = QFrame()
    line_checkbox.setFrameShape(QFrame.Shape.HLine)
    line_checkbox.setStyleSheet("color: #555;")
    layout.addWidget(line_checkbox)

    # Środkowa sekcja z 3 ramkami
    image_display_layout = QHBoxLayout()
    image_display_layout.setContentsMargins(10, 20, 10, 10)
    image_display_layout.setSpacing(20)

    for label_text in ["Obraz wejściowy", "Sinogram", "Obraz po rekonstrukcji"]:
        container = QVBoxLayout()
        label = QLabel(label_text)
        label.setStyleSheet("color: white; font-size: 14px; padding: 4px;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #2A2A2A;
                border: 2px solid #555;
                border-radius: 8px;
                min-width: 250px;
                min-height: 250px;
            }
        """)
        container.addWidget(label)
        container.addWidget(frame)

        if label_text == "Obraz wejściowy":
            input_image_frame = frame
        elif label_text == "Sinogram":
            sinogram_frame = frame
        elif label_text == "Obraz po rekonstrukcji":
            reconstructed_image_frame = frame

        wrapper = QWidget()
        wrapper.setLayout(container)
        image_display_layout.addWidget(wrapper)
    layout.addLayout(image_display_layout)

    # Linia pod ramkami obrazów
    line4 = QFrame()
    line4.setFrameShape(QFrame.Shape.HLine)
    line4.setStyleSheet("color: #555;")
    layout.addWidget(line4)

    # Ramki na dane pacjenta i ustawienia tomografu
    info_frames_layout = QHBoxLayout()
    info_frames_layout.setContentsMargins(10, 10, 10, 10)
    info_frames_layout.setSpacing(20)

    for title in ["Dane pacjenta", "Ustawienia tomografu"]:
        container = QVBoxLayout()
        label = QLabel(title)
        label.setStyleSheet("color: white; font-size: 14px; padding: 4px;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        container.addWidget(label)

        wrapper = QWidget()
        wrapper.setLayout(container)
        info_frames_layout.addWidget(wrapper)

    layout.addLayout(info_frames_layout)




    # --- Ustawienia tomografu - etykiety dynamiczne ---
    tomograph_settings_layout = QVBoxLayout()
    tomograph_settings_labels = {
        "Krok Δα": QLabel(f"Krok Δα: {krok_alpha}"),
        "Liczba detektorów": QLabel(f"Liczba detektorów: {liczba_detektorow}"),
        "Rozpiętość układu": QLabel(f"Rozpiętość układu: {rozpietosc}")
    }

    # Dodajemy etykiety do layoutu, aby wyświetlić ustawienia tomografu
    for label in tomograph_settings_labels.values():
        label.setStyleSheet("color: white; font-size: 13px;")
        tomograph_settings_layout.addWidget(label)

    # Tworzymy osobny widget do wyświetlenia ustawień tomografu
    tomograph_widget = QWidget()
    tomograph_widget.setLayout(tomograph_settings_layout)

    # --- Ramki na dane pacjenta ---
    patient_data_layout = QVBoxLayout()
    patient_info_labels = {
        "Imię": QLabel(f"Imię: {imie}"),
        "Nazwisko": QLabel(f"Nazwisko: {nazwisko}"),
        "PESEL": QLabel(f"PESEL: {pesel}"),
        "Komentarz": QLabel(f"Komentarz: {komentarz}")
    }

    for label in patient_info_labels.values():
        label.setStyleSheet("color: white; font-size: 13px;")
        patient_data_layout.addWidget(label)

    # Tworzymy osobny widget do wyświetlenia danych pacjenta
    patient_widget = QWidget()
    patient_widget.setLayout(patient_data_layout)

    # Layout dla obu sekcji: dane pacjenta i ustawienia tomografu
    info_frames_layout = QHBoxLayout()
    info_frames_layout.setContentsMargins(10, 10, 10, 10)
    info_frames_layout.setSpacing(20)

    # Dodajemy widgety do layoutu
    info_frames_layout.addWidget(patient_widget)
    info_frames_layout.addWidget(tomograph_widget)

    # Na koniec dodajemy info_frames_layout do głównego layoutu
    layout.addLayout(info_frames_layout)



    # Przyciski dolne: "Zmień dane pacjenta" i "Zmień ustawienia tomografu"
    bottom_buttons_layout = QHBoxLayout()
    bottom_buttons_layout.setContentsMargins(10, 20, 10, 10)
    bottom_buttons_layout.setSpacing(10)

    btn_edit_patient_data = QPushButton("Zmień dane pacjenta")
    btn_edit_patient_data.setStyleSheet("""
QPushButton {
    font-size: 16px;
    background-color: #007BFF;
    color: white;
    border-radius: 10px;
    padding: 5px;
}
QPushButton:hover {
    background-color: #168FFF;
}
""")
    btn_edit_patient_data.clicked.connect(pokaz_okno_danych_pacjenta)

    btn_edit_tomograph_settings = QPushButton("Zmień ustawienia tomografu")
    btn_edit_tomograph_settings.setStyleSheet("""
QPushButton {
    font-size: 16px;
    background-color: #007BFF;
    color: white;
    border-radius: 10px;
    padding: 5px;
}
QPushButton:hover {
    background-color: #168FFF;
}
""")
    btn_edit_tomograph_settings.clicked.connect(pokaz_okno_ustawien_tomografu)

    bottom_buttons_layout.addWidget(btn_edit_patient_data)
    bottom_buttons_layout.addWidget(btn_edit_tomograph_settings)

    # Linia nad dolnymi przyciskami
    line_bottom = QFrame()
    line_bottom.setFrameShape(QFrame.Shape.HLine)
    line_bottom.setStyleSheet("color: #555;")
    layout.addWidget(line_bottom)

    btn_show_saved_dicom = QPushButton("Wyświetl zapisany plik DICOM")
    btn_show_saved_dicom.setStyleSheet("""
        QPushButton {
            font-size: 16px;
            background-color: #555;
            color: white;
            border-radius: 8px;
            padding: 10px 20px;
            min-width: 250px;
        }
        QPushButton:hover {
            background-color: #777;
        }
    """)
    btn_show_saved_dicom.setVisible(False)
    btn_show_saved_dicom.clicked.connect(pokaz_zapisany_dicom)
    dicom_button_wrapper = QVBoxLayout()
    dicom_button_wrapper.setContentsMargins(0, 30, 0, 0)  # 15px górnego marginesu
    dicom_button_wrapper.addWidget(btn_show_saved_dicom, alignment=Qt.AlignmentFlag.AlignHCenter)
    layout.addLayout(dicom_button_wrapper)

    layout.addStretch()  # Oddziela górę od dołu
    layout.addLayout(bottom_buttons_layout)

    window.setLayout(layout)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()