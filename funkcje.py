# funkcje.py

import numpy as np
import pydicom
from imageio import imread
from skimage.color import rgb2gray, gray2rgb
from skimage.draw import line_nd

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


def generuj_projekcje(obraz, liczba_katow=180, liczba_emiterow=180):
    wys, szer = obraz.shape
    promien = np.hypot(wys, szer) / 2
    srodek = (szer // 2, wys // 2)
    projekcje = []

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

def rekonstrukcja_wlasna(sinogram, liczba_katow=180, l_em=180):
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
    x = np.arange(l_em) -l_em // 2
    y = x.copy()
    X, Y = np.meshgrid(x, y)
    R = np.sqrt(X**2 + Y**2)

    for i, angle in enumerate(theta):
        t = X * np.cos(np.radians(angle)) + Y * np.sin(np.radians(angle))
        t_idx = np.round(t + num_detectors // 2).astype(int)

        valid = (t_idx >= 0) & (t_idx < num_detectors)
        reconstructed[valid] += sinogram_filtered[t_idx[valid], i]

    # Normalizacja
    reconstructed = (reconstructed - reconstructed.min()) / (reconstructed.max() - reconstructed.min())
    return reconstructed