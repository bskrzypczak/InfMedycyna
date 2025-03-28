from imageio import imread
import matplotlib.pyplot as plt
import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from datetime import datetime
from skimage.color import gray2rgb, rgb2gray
from skimage.draw import line_nd
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

def generuj_projekcje(obraz, liczba_katow=381, liczba_emiterow=180):
    wys, szer = obraz.shape
    promien = np.hypot(wys, szer) / 2
    srodek = (szer // 2, wys // 2)
    projekcje = []
    
    for kat in range(liczba_katow):
        projekcja = []
        kopia = gray2rgb(obraz)
        
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

def wyswietl_linie(obraz, kat):
    plt.imshow(obraz, cmap='gray')
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

def zapisz_dicom(projekcje, sciezka_wyj):
    # Stwórz obiekt DICOM Dataset
    ds = Dataset()

    # Dodaj podstawowe metadane o pacjencie
    ds.PatientName = "Anonimowy Pacjent"
    ds.PatientID = "000000"
    ds.StudyDate = datetime.now().strftime('%Y%m%d')
    ds.Modality = "CT"
    ds.SeriesDescription = "Wygenerowany sinogram"
    ds.ImageComments = "Sinogram utworzony z obrazu wejściowego"

    # Przygotuj dane FileMetaDataset - nagłówek DICOM
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = pydicom.uid.ImplicitVRLittleEndian
    file_meta.MediaStorageSOPInstanceUID = pydicom.uid.generate_uid()
    file_meta.TransferSyntaxUID = pydicom.uid.ExplicitVRLittleEndian
    file_meta.FileMetaInformationGroupLength = 0
    file_meta.FileMetaInformationVersion = b'\x00\x01'

    # Przypisz do ds obiekt FileMetaDataset
    ds.file_meta = file_meta

    # Dodaj wymagane atrybuty związane z obrazem:
    ds.Rows, ds.Columns = np.array(projekcje).shape
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15  # 16-bitowe obrazy mają wysoki bit na pozycji 15
    ds.PixelRepresentation = 0  # 0 - wartości nieskatalogowane, 1 - wartości ze znakami
    ds.PixelData = np.array(projekcje, dtype=np.uint16).tobytes()

    # Zapisz DICOM do pliku
    ds.save_as(sciezka_wyj)
    print(f"Plik DICOM zapisany: {sciezka_wyj}")

# Wczytanie obrazu
droga_do_pliku = "CT_ScoutView.dcm"  # Można podać plik DCM lub standardowy obraz
obraz, dicom_metadata = wczytaj_obraz(droga_do_pliku)

# Generowanie projekcji
projekcje = generuj_projekcje(obraz)

# Wyświetlenie sinogramu
wyswietl_sinogram(projekcje)

# Zapis do DICOM
zapisz_dicom(projekcje, "sinogram_output.dcm")