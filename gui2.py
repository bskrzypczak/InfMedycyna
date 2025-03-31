import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QCheckBox, QLabel, QFrame,

)
from PyQt6.QtCore import Qt

from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox


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
    patient_labels["Imię"].setText(f"Imię: {imie}")
    patient_labels["Nazwisko"].setText(f"Nazwisko: {nazwisko}")
    patient_labels["PESEL"].setText(f"PESEL: {pesel}")
    patient_labels["Komentarz"].setText(f"Komentarz: {komentarz}")

    dialog.accept()


from PyQt6.QtWidgets import QSpinBox, QComboBox


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
    liczba_detektorow.setValue(180)

    rozpietosc = QSpinBox()
    rozpietosc.setRange(1, 360)
    rozpietosc.setValue(120)

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
    global krok_alpha, liczba_detektorow, rozpietosc, tomograph_labels

    # Zaktualizowanie ustawień tomografu
    krok_alpha = new_krok_alpha
    liczba_detektorow = new_liczba_detektorow
    rozpietosc = new_rozpietosc

    # Upewnij się, że zmienne tomograph_labels są zainicjalizowane
    if not tomograph_labels:
        tomograph_labels = {
            "Krok Δα": QLabel(f"Krok Δα: {krok_alpha}"),
            "Liczba detektorów": QLabel(f"Liczba detektorów: {liczba_detektorow}"),
            "Rozpiętość układu": QLabel(f"Rozpiętość układu: {rozpietosc}")
        }

    # Zaktualizowanie etykiet w głównym oknie
    tomograph_labels["Krok Δα"].setText(f"Krok Δα: {krok_alpha}")
    tomograph_labels["Liczba detektorów"].setText(f"Liczba detektorów: {liczba_detektorow}")
    tomograph_labels["Rozpiętość układu"].setText(f"Rozpiętość układu: {rozpietosc}")

    dialog.accept()

# Zmienna do przechowywania danych pacjenta
imie = ""
nazwisko = ""
pesel = ""
komentarz = ""

# Zmienna na etykiety
patient_labels = {}
tomograph_labels ={}

#ustawienia tomografu
krok_alpha = 10
liczba_detektorow = 256
rozpietosc = 180

def main():
    global patient_labels,tomograph_labels


    app = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("CT simulation")
    window.resize(1000, 700)

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
    btn_dodaj = QPushButton("Wczytaj obraz")
    btn_dodaj.setStyleSheet("""
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
    btn_dodaj.clicked.connect(lambda: print("Kliknięto 'Wczytaj obraz'"))
    top_buttons_layout.addWidget(btn_dodaj)

    # Przycisk "Generuj sinogram"
    btn_sinogram = QPushButton("Generuj sinogram")
    btn_sinogram.setStyleSheet("""
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
    btn_sinogram.clicked.connect(lambda: print("Kliknięto 'Generuj sinogram'"))
    top_buttons_layout.addWidget(btn_sinogram)

    # Przycisk "Rekonstruuj obraz"
    btn_rekonstrukcja = QPushButton("Rekonstruuj obraz")
    btn_rekonstrukcja.setStyleSheet("""
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
    btn_rekonstrukcja.clicked.connect(lambda: print("Kliknięto 'Rekonstruuj obraz'"))
    top_buttons_layout.addWidget(btn_rekonstrukcja)

    # Przycisk "Zapisz plik DICOM"
    btn_zapisz_dicom = QPushButton("Zapisz plik DICOM")
    btn_zapisz_dicom.setStyleSheet("""
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
    btn_zapisz_dicom.clicked.connect(lambda: print("Kliknięto 'Zapisz plik DICOM'"))
    top_buttons_layout.addWidget(btn_zapisz_dicom)
    layout.addLayout(top_buttons_layout)

    # Checkbox "Pokaż animację skanowania iteracyjnie"
    chk_animacja = QCheckBox("Pokaż animację skanowania iteracyjnie")
    chk_animacja.setStyleSheet("""
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
    chk_animacja.clicked.connect(lambda checked: print(f"Checkbox animacji: {checked}"))
    layout.addWidget(chk_animacja, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

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
    tomograph_labels = {
        "Krok Δα": QLabel(f"Krok Δα: {krok_alpha}"),
        "Liczba detektorów": QLabel(f"Liczba detektorów: {liczba_detektorow}"),
        "Rozpiętość układu": QLabel(f"Rozpiętość układu: {rozpietosc}")
    }

    # Dodajemy etykiety do layoutu, aby wyświetlić ustawienia tomografu
    for label in tomograph_labels.values():
        label.setStyleSheet("color: white; font-size: 13px;")
        tomograph_settings_layout.addWidget(label)

    # Tworzymy osobny widget do wyświetlenia ustawień tomografu
    tomograph_widget = QWidget()
    tomograph_widget.setLayout(tomograph_settings_layout)

    # --- Ramki na dane pacjenta ---
    patient_data_layout = QVBoxLayout()
    patient_labels = {
        "Imię": QLabel(f"Imię: {imie}"),
        "Nazwisko": QLabel(f"Nazwisko: {nazwisko}"),
        "PESEL": QLabel(f"PESEL: {pesel}"),
        "Komentarz": QLabel(f"Komentarz: {komentarz}")
    }

    for label in patient_labels.values():
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

    btn_dane_pacjenta = QPushButton("Zmień dane pacjenta")
    btn_dane_pacjenta.setStyleSheet("""
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
    btn_dane_pacjenta.clicked.connect(pokaz_okno_danych_pacjenta)

    btn_ustawienia = QPushButton("Zmień ustawienia tomografu")
    btn_ustawienia.setStyleSheet("""
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
    btn_ustawienia.clicked.connect(pokaz_okno_ustawien_tomografu)

    bottom_buttons_layout.addWidget(btn_dane_pacjenta)
    bottom_buttons_layout.addWidget(btn_ustawienia)

    # Linia nad dolnymi przyciskami
    line_bottom = QFrame()
    line_bottom.setFrameShape(QFrame.Shape.HLine)
    line_bottom.setStyleSheet("color: #555;")
    layout.addWidget(line_bottom)

    layout.addStretch()  # Oddziela górę od dołu
    layout.addLayout(bottom_buttons_layout)

    window.setLayout(layout)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()