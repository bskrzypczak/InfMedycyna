import numpy as np
import cv2
import pydicom
import matplotlib.pyplot as plt
from scipy.ndimage import rotate
from skimage.transform import iradon
import tkinter as tk
from tkinter import filedialog

# Funkcja obliczająca współrzędne emitera i detektorów
def compute_emitter_and_detectors(radius, alpha, phi, num_detectors):
    x_E = radius * np.cos(np.radians(alpha))
    y_E = radius * np.sin(np.radians(alpha))
    emitter = (x_E, y_E)
    
    detectors = []
    for i in range(num_detectors):
        theta = alpha + 180 - (phi / 2) + i * (phi / (num_detectors - 1))
        x_D = radius * np.cos(np.radians(theta))
        y_D = radius * np.sin(np.radians(theta))
        detectors.append((x_D, y_D))
    
    return emitter, detectors

# Algorytm Bresenhama
def bresenham(x0, y0, x1, y1):
    points = []
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    
    while True:
        points.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
    
    return points

# Obliczanie sinogramu
def calculate_sinogram(image, steps=180, span=120, num_rays=250):
    h, w = image.shape
    sinogram = np.zeros((steps, num_rays))
    radius = max(h, w) // 2
    center = (w // 2, h // 2)
    
    for step in range(steps):
        angle = step * (360 / steps)
        emitter, detectors = compute_emitter_and_detectors(radius, angle, span, num_rays)
        
        for i, (dx, dy) in enumerate(detectors):
            points = bresenham(int(emitter[0] + center[0]), int(emitter[1] + center[1]), int(dx + center[0]), int(dy + center[1]))
            sinogram[step, i] = sum(image[y, x] for x, y in points if 0 <= x < w and 0 <= y < h)
    
    return sinogram

# Odtwarzanie obrazu
def reconstruct_image(sinogram, steps=180):
    return iradon(sinogram.T, theta=np.linspace(0, 180, steps, endpoint=False), filter_name='ramp')

# Funkcja główna aplikacji
def main():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(title='Wybierz obraz', filetypes=[('Obrazy', '*.png;*.jpg;*.bmp')])
    
    if not file_path:
        print("Nie wybrano pliku.")
        return
    
    image = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
    sinogram = calculate_sinogram(image)
    reconstructed = reconstruct_image(sinogram)
    
    plt.figure(figsize=(12, 4))
    plt.subplot(1, 3, 1)
    plt.title("Obraz oryginalny")
    plt.imshow(image, cmap='gray')
    
    plt.subplot(1, 3, 2)
    plt.title("Sinogram")
    plt.imshow(sinogram, cmap='gray', aspect='auto')
    
    plt.subplot(1, 3, 3)
    plt.title("Obraz po rekonstrukcji")
    plt.imshow(reconstructed, cmap='gray')
    
    plt.show()

if __name__ == "__main__":
    main()
