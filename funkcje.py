# funkcje.py

import numpy as np
import pydicom
from imageio import imread
from skimage.color import rgb2gray, gray2rgb
from skimage.draw import line_nd
from pydicom.dataset import Dataset, FileDataset
import datetime

def wczytaj_obraz(sciezka):
    """
    Funkcja do wczytywania obrazu (obsługuje zarówno DICOM, jak i obrazy PNG, JPG itp.).
    """
    if sciezka.lower().endswith(".dcm"):
        dicom_data = pydicom.dcmread(sciezka)
        obraz = dicom_data.pixel_array.astype(np.float32)
        obraz = (obraz - obraz.min()) / (obraz.max() - obraz.min())  # Normalizacja do [0,1]
        return obraz, dicom_data
    else:
        obraz = imread(sciezka)
        if obraz.ndim == 3:
            obraz = rgb2gray(obraz)  # Konwertowanie na obraz w skali szarości
        return obraz, None


def generuj_projekcje(obraz, krok_alpha=1, liczba_emiterow=180):
    # Oblicz liczbę projekcji na podstawie kroku α
    liczba_katow = int(180 / krok_alpha)  # 180° podzielone przez krok

    wys, szer = obraz.shape
    promien = np.hypot(wys, szer) / 2
    srodek = (szer // 2, wys // 2)
    projekcje = []

    print(f"Generowanie sinogramu z {liczba_katow} projekcjami i {liczba_emiterow} detektorami.")

    for kat in range(liczba_katow):
        projekcja = []
        kopia = (gray2rgb(obraz) * 255).astype(np.uint8)

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

            suma_pikseli = np.sum(obraz[rr, cc])
            projekcja.append(suma_pikseli)

            kopia[rr, cc] = [0, 255, 0] if przesuniecie == 0 else [255, 255, 255]

        projekcje.append(projekcja)

    return projekcje

def rekonstrukcja_wlasna(sinogram, liczba_katow, l_em):
    sinogram = np.array(sinogram).T  # shape: (num_detectors, num_angles)
    num_detectors, num_angles = sinogram.shape
    theta = np.linspace(0., 180., liczba_katow, endpoint=False)

    # 1. FILTR Ram-Lak DO USUNIECIA
    freqs = np.fft.fftfreq(num_detectors).reshape(-1, 1)
    ram_lak = 2 * np.abs(freqs)
    sinogram_fft = np.fft.fft(sinogram, axis=0)
    sinogram_filtered = np.real(np.fft.ifft(sinogram_fft * ram_lak, axis=0))

    # 2. BACK-PROJECTION
    reconstructed = np.zeros((l_em, l_em), dtype=np.float32)
    x = np.arange(l_em) - l_em // 2
    y = x.copy()
    X, Y = np.meshgrid(x, y)

    for i, angle in enumerate(theta):
        t = X * np.cos(np.radians(angle)) + Y * np.sin(np.radians(angle))
        t_idx = np.round(t + num_detectors // 2).astype(int)

        # Zapewnienie, że t_idx mieści się w odpowiednim zakresie
        t_idx = np.clip(t_idx, 0, num_detectors - 1)  # Zapobiegamy wychodzeniu poza zakres

        valid = (t_idx >= 0) & (t_idx < num_detectors)
        reconstructed[valid] += sinogram_filtered[t_idx[valid], i]

    # Normalizacja
    reconstructed = (reconstructed - reconstructed.min()) / (reconstructed.max() - reconstructed.min())
    return reconstructed

def save_dicom_image(reconstructed_array, filename, patientname, patientID, patient_comments=None):
    """
    Funkcja zapisuje zrekonstruowany obraz jako plik DICOM.
    - reconstructed_array: zrekonstruowany obraz do zapisu.
    - filename: Ścieżka, w której zapisany zostanie plik DICOM.
    - patientname: Imię pacjenta.
    - patientID: ID pacjenta.
    - patient_comments: Komentarz pacjenta (opcjonalne).
    """
    if reconstructed_array is None:
        return None

    # Tworzymy metadane DICOM
    file_meta = pydicom.Dataset()
    file_meta.MediaStorageSOPClassUID = pydicom.uid.SecondaryCaptureImageStorage
    file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
    file_meta.ImplementationClassUID = pydicom.uid.PYDICOM_IMPLEMENTATION_UID

    ds = FileDataset(filename, {}, file_meta=file_meta, preamble=b"\0" * 128)
    dt = datetime.datetime.now()
    ds.ContentDate = dt.strftime("%Y%m%d")
    ds.ContentTime = dt.strftime("%H%M%S")
    ds.Modality = "OT"  # Other (obraz medyczny "inny")
    ds.PatientName = patientname
    ds.PatientID = patientID
    ds.StudyInstanceUID = pydicom.uid.generate_uid()
    ds.SeriesInstanceUID = pydicom.uid.generate_uid()
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.SOPClassUID = file_meta.MediaStorageSOPClassUID

    # Jeśli komentarz pacjenta jest dostępny, dodajemy go do metadanych DICOM
    if patient_comments:
        ds.PatientComments = patient_comments

    # Normalizacja i konwersja obrazu do uint8
    image_array = (reconstructed_array - reconstructed_array.min()) / \
                  (reconstructed_array.max() - reconstructed_array.min()) * 255
    image_array = image_array.astype(np.uint8)

    # Ustawienia dla obrazu
    ds.Rows, ds.Columns = image_array.shape
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.SamplesPerPixel = 1
    ds.BitsAllocated = 8
    ds.BitsStored = 8
    ds.HighBit = 7
    ds.PixelRepresentation = 0
    ds.PixelData = image_array.tobytes()

    # Zapisz plik DICOM
    ds.save_as(filename, write_like_original=False)
    return filename
