import pydicom

# Wczytanie pliku DICOM
dicom_file_path = "h.dcm"  # Zmień na rzeczywistą ścieżkę do pliku
dicom_data = pydicom.dcmread(dicom_file_path)

# Wyświetlenie wszystkich metadanych w pliku DICOM
for elem in dicom_data.iterall():
    print(f"{elem.tag}: {elem.name} = {elem.value}")