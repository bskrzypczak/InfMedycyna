import copy
import math
import os
import numpy as np
from pydicom import FileDataset
from scipy.signal import convolve2d
from PIL import Image
import matplotlib.pyplot as plt
import pydicom
import datetime

def wczytanie_obrazu(sciezka, rozmiar_obrazu=(256, 256)):

    ext = os.path.splitext(sciezka)[-1].lower()

    if ext == '.dcm':
        dicom = pydicom.dcmread(sciezka)
        obraz = dicom.pixel_array.astype(np.float32)

        # Normalizacja DICOM
        obraz = obraz - np.min(obraz)
        if np.max(obraz) != 0:
            obraz = obraz / np.max(obraz)

        # Konwersja do obrazu PIL, skalowanie, potem z powrotem do numpy
        pil_img = Image.fromarray((obraz * 255).astype(np.uint8)).convert('L')
        pil_img = pil_img.resize(rozmiar_obrazu, Image.Resampling.LANCZOS)
        obraz = np.array(pil_img).astype(np.float32) / 255.0

    else:
        # Wczytanie JPG/PNG jako grayscale + skalowanie
        pil_img = Image.open(sciezka).convert('L')
        pil_img = pil_img.resize(rozmiar_obrazu, Image.Resampling.LANCZOS)
        obraz = np.array(pil_img).astype(np.float32) / 255.0

    return obraz, sciezka



def algorytm_bresenhama(x0, x1, y0, y1):
    punkty = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    x, y = int(x0), int(y0)

    if x0 > x1:
        sx = -1
    else:
        sx = 1
    if y0 > y1:
        sy = -1
    else:
        sy = 1   

    if dx > dy:
        err = dx / 2.0
        while x != int(x1):
            punkty.append((x, y))
            err -= dy
            if err < 0:
                y += sy
                err += dx
            x += sx
    else:
        err = dy / 2.0
        while y != int(y1):
            punkty.append((x, y))
            err -= dx
            if err < 0:
                x += sx
                err += dy
            y += sy
    punkty.append((int(x1), int(y1)))
    return punkty



def wyznaczenie_promieni(r, pozycja, kat, rozpietosc, liczba_promieni):
    alfa = np.radians(kat)
    theta = np.radians(rozpietosc)
    indeksy_promieni = np.linspace(0, liczba_promieni - 1, liczba_promieni)
    detektor = alfa - (indeksy_promieni * theta / (liczba_promieni - 1)) + theta / 2
    emiter = alfa + np.pi - (theta / 2) + (indeksy_promieni * theta / (liczba_promieni - 1))

    x_e = r * np.cos(emiter) + pozycja[0]
    y_e = r * np.sin(emiter) + pozycja[1]
    x_d = r * np.cos(detektor) + pozycja[0]
    y_d = r * np.sin(detektor) + pozycja[1]

    promienie = np.empty((liczba_promieni, 2, 2))
    promienie[:, 0, 0] = x_e
    promienie[:, 0, 1] = x_d
    promienie[:, 1, 0] = y_e
    promienie[:, 1, 1] = y_d

    return promienie



def tworzenie_sinogramu(obraz, kroki, rozpietosc, liczba_promieni, max_kat):
    sinogram = np.zeros((kroki, liczba_promieni))
    
    for idx in range(kroki):
        kat = idx * (max_kat / kroki)
        promienie = wyznaczenie_promieni(
            np.hypot(obraz.shape[0] // 2, obraz.shape[1] // 2),
            (obraz.shape[0] // 2, obraz.shape[1] // 2), kat, rozpietosc, liczba_promieni)
        
        for promien_idx, promien in enumerate(promienie):
            punkty = algorytm_bresenhama(promien[0][0], promien[0][1], promien[1][0], promien[1][1])
            sinogram[idx, promien_idx] = sum(
                obraz[p[1], p[0]] for p in punkty if 0 <= p[0] < obraz.shape[1] and 0 <= p[1] < obraz.shape[0])
    
    return sinogram


def transforma_radona(wymiary_obrazu, sinogram, kroki, rozpietosc, liczba_promieni, max_kat, zwroc_klatki=False):
    obraz_wynikowy = np.zeros(wymiary_obrazu)
    klatki = [] if zwroc_klatki else None

    for idx in range(kroki):
        kat = idx * (max_kat / kroki)
        promienie = wyznaczenie_promieni(
            np.hypot(wymiary_obrazu[0] // 2, wymiary_obrazu[1] // 2),
            (wymiary_obrazu[0] // 2, wymiary_obrazu[1] // 2),
            kat, rozpietosc, liczba_promieni
        )

        for promien_idx, promien in enumerate(promienie):
            punkty = algorytm_bresenhama(promien[0][0], promien[0][1], promien[1][0], promien[1][1])

            for p in punkty:
                if 0 <= p[0] < wymiary_obrazu[1] and 0 <= p[1] < wymiary_obrazu[0]:
                    obraz_wynikowy[p[1], p[0]] += sinogram[idx, promien_idx]

        if klatki is not None:
            klatki.append(np.copy(obraz_wynikowy))

    obraz_wynikowy = normalizacja(obraz_wynikowy)

    if klatki is not None:
        klatki = [normalizacja(k) for k in klatki]
        return obraz_wynikowy, klatki

    return obraz_wynikowy



def normalizacja(obraz):
    return (obraz - obraz.min()) / (obraz.max() - obraz.min())



def filter_sinogram(sinogram, typ_filtru='ram-lak'):
    liczba_projekcji, liczba_detektorow = sinogram.shape

    czestotliwosci = np.fft.fftfreq(liczba_detektorow).reshape(1, -1)
    omega = 2 * np.pi * czestotliwosci

    ram_lak = 2 * np.abs(czestotliwosci)

    # Inne filtry jako modyfikacja Ram-Laka
    if typ_filtru == 'ram-lak':
        krzywa_filtru = ram_lak
    elif typ_filtru == 'shepp-logan':
        sinc = np.sinc(czestotliwosci / 2)
        krzywa_filtru = ram_lak * sinc
    elif typ_filtru == 'cosine':
        krzywa_filtru = ram_lak * np.cos(np.pi * czestotliwosci / 2)
    elif typ_filtru == 'hamming':
        window = 0.54 + 0.46 * np.cos(omega)
        krzywa_filtru = ram_lak * window
    elif typ_filtru == 'hann':
        window = 0.5 + 0.5 * np.cos(omega)
        krzywa_filtru = ram_lak * window
    else:
        raise ValueError(f"Nieznany typ filtra: {typ_filtru}")

    sino_czest = np.fft.fft(sinogram, axis=1)
    sino_czest_filtrowany= sino_czest * krzywa_filtru
    sinogram_filtrowany = np.real(np.fft.ifft(sino_czest_filtrowany, axis=1))

    return sinogram_filtrowany

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


def obliczenie_bledu(obraz1, obraz2):
    return np.sqrt(np.mean(np.square(obraz1 - obraz2)))



def main():
    sciezka_pliku = "saddle_pe.jpg"
    obraz, dane_dicom = wczytanie_obrazu(sciezka_pliku)

    kroki = 360
    liczba_promieni = 360
    rozpietosc = 180
    max_kat = 180

    sinogram = tworzenie_sinogramu(obraz, kroki, rozpietosc, liczba_promieni, max_kat)
    sinogram_filtrowany = filter_sinogram(sinogram, "hann")

    odtworzony_obraz = transforma_radona(obraz.shape, sinogram, kroki, rozpietosc, liczba_promieni, max_kat)
    odtworzony_obraz_filtrowany = transforma_radona(obraz.shape, sinogram_filtrowany, kroki, rozpietosc, liczba_promieni, max_kat)

    # Analiza statystyczna — obliczanie RMSE
    blad_bez_filtru = obliczenie_bledu(obraz, odtworzony_obraz)
    blad_z_filtrem = obliczenie_bledu(obraz, odtworzony_obraz_filtrowany)

    print(f"RMSE bez filtra: {blad_bez_filtru:.4f}")
    print(f"RMSE z filtrem: {blad_z_filtrem:.4f}")

    fig, axs = plt.subplots(1, 4, figsize=(20, 5))
    axs[0].imshow(obraz, cmap='gray')
    axs[0].set_title("Obraz wejściowy")
    axs[1].imshow(sinogram.T, cmap='gray', aspect='auto')
    axs[1].set_title("Sinogram")
    axs[2].imshow(odtworzony_obraz, cmap='gray')
    axs[2].set_title("Rekonstrukcja bez filtra")
    axs[3].imshow(odtworzony_obraz_filtrowany, cmap='gray')
    axs[3].set_title("Rekonstrukcja z filtrem")
    for ax in axs:
        ax.axis('off')
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()