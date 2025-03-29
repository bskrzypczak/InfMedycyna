from imageio import imread
import matplotlib.pyplot as plt
import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from datetime import datetime
from skimage.color import gray2rgb, rgb2gray
from skimage.draw import line_nd
import scipy.fftpack
import os

def wczytaj_obraz(sciezka):
    if sciezka.lower().endswith(".dcm"):
        dicom_data = pydicom.dcmread(sciezka)
        obraz = dicom_data.pixel_array.astype(np.float32)
        obraz = (obraz - obraz.min()) / (obraz.max() - obraz.min())  # Normalizacja do [0,1]
        return obraz, dicom_data
    else:
        obraz = imread(sciezka)
        if obraz.ndim == 3:
            obraz = rgb2gray(obraz)
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
        
        wyswietl_linie(kopia, kat)
        projekcje.append(projekcja)
    
    return projekcje

def rekonstrukcja_wlasna(sinogram, liczba_katow, rozmiar_obrazka):
    sinogram = np.array(sinogram).T  # shape: (num_detectors, num_angles)
    num_detectors, num_angles = sinogram.shape
    theta = np.linspace(0., 180., liczba_katow, endpoint=False)

    # 1. FILTR Ram-Lak DO USUNIECIA
    freqs = np.fft.fftfreq(num_detectors).reshape(-1, 1)
    ram_lak = 2 * np.abs(freqs)
    sinogram_fft = np.fft.fft(sinogram, axis=0)
    sinogram_filtered = np.real(np.fft.ifft(sinogram_fft * ram_lak, axis=0))

    # 2. BACK-PROJECTION
    reconstructed = np.zeros((rozmiar_obrazka, rozmiar_obrazka), dtype=np.float32)
    x = np.arange(rozmiar_obrazka) - rozmiar_obrazka // 2
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

def wyswietl_linie(obraz, kat):
    if obraz.dtype != np.uint8:
        obraz = np.clip(obraz, 0, 255).astype(np.uint8)
    plt.imshow(obraz)  # bez cmap, bo RGB
    plt.title(f"Linia dla kąta {kat}")
    plt.axis('off')
    plt.pause(0.01)
    plt.clf()

def wyswietl_sinogram(projekcje):
    plt.figure(figsize=(10, 5))
    plt.imshow(projekcje, cmap='gray', aspect='auto', origin='lower')
    plt.title("Sinogram")
    plt.xlabel("Kąt (stopnie)")
    plt.ylabel("Pozycja detektora")
    plt.colorbar(label="Suma wartości pikseli")
    plt.show()

def zapisz_dicom_obraz(obraz, sciezka_wyj):
    ds = Dataset()
    ds.PatientName = "Anonimowy Pacjent"
    ds.PatientID = "000000"
    ds.StudyDate = datetime.now().strftime('%Y%m%d')
    ds.Modality = "CT"
    ds.SeriesDescription = "Rekonstrukcja obrazu"
    ds.ImageComments = "Odtworzony obraz z sinogramu (FBP)"

    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = pydicom.uid.ImplicitVRLittleEndian
    file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
    file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
    file_meta.FileMetaInformationGroupLength = 0
    file_meta.FileMetaInformationVersion = b'\x00\x01'
    ds.file_meta = file_meta

    obraz_norm = (obraz - obraz.min()) / (obraz.max() - obraz.min()) * 65535
    obraz_uint16 = obraz_norm.astype(np.uint16)

    ds.Rows, ds.Columns = obraz_uint16.shape
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.PixelData = obraz_uint16.tobytes()

    ds.save_as(sciezka_wyj)
    print(f"Plik DICOM (rekonstrukcja) zapisany: {sciezka_wyj}")
    return

# Wczytanie obrazu
droga_do_pliku = "shepp_logan.dcm"  # lub np. 'obrazy/test.png'
obraz, dicom_metadata = wczytaj_obraz(droga_do_pliku)

# Liczba emiterów = liczba detektorów
liczba_katow = 180
liczba_emiterow = 256  # Możesz też dać: liczba_emiterow = max(obraz.shape)

# Generowanie projekcji (sinogramu)
projekcje = generuj_projekcje(obraz, liczba_katow=liczba_katow, liczba_emiterow=liczba_emiterow)

# Wyświetlenie sinogramu
wyswietl_sinogram(projekcje)

# Rekonstrukcja obrazu z sinogramu (FBP)

rekonstruowany_obraz = rekonstrukcja_wlasna(projekcje, liczba_katow=liczba_katow, rozmiar_obrazka=liczba_emiterow)



# Wyświetlenie rekonstrukcji
plt.imshow(rekonstruowany_obraz, cmap='gray')
plt.title("Obraz po rekonstrukcji (FBP)")
plt.axis('off')
plt.show()

# Zapis obrazu po rekonstrukcji jako DICOM
zapisz_dicom_obraz(rekonstruowany_obraz, "rekonstrukcja_output.dcm")