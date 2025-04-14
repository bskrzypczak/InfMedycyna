import copy
import math
import numpy as np
from scipy.signal import convolve2d
from PIL import Image
import matplotlib.pyplot as plt


def load_image(file_path, target_size=(256, 256)):
    img = Image.open(file_path).convert('L')
    img = img.resize(target_size, Image.Resampling.LANCZOS)
    return np.array(img) / 255.0


def get_parallel_rays(radius, pos, angle, span, num_rays):
    alpha = np.radians(angle)
    theta = np.radians(span)
    ray_indices = np.linspace(0, num_rays - 1, num_rays)
    detector_angles = alpha - (ray_indices * theta / (num_rays - 1)) + theta / 2
    emitter_angles = alpha + np.pi - (theta / 2) + (ray_indices * theta / (num_rays - 1))
    x_e = radius * np.cos(emitter_angles) + pos[0]
    y_e = radius * np.sin(emitter_angles) + pos[1]
    x_d = radius * np.cos(detector_angles) + pos[0]
    y_d = radius * np.sin(detector_angles) + pos[1]
    rays = np.empty((num_rays, 2, 2))
    rays[:, 0, 0] = x_e
    rays[:, 0, 1] = x_d
    rays[:, 1, 0] = y_e
    rays[:, 1, 1] = y_d
    return rays


def get_bresenham_points(x0, y0, x1, y1):
    points = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    x, y = int(x0), int(y0)
    sx = -1 if x0 > x1 else 1
    sy = -1 if y0 > y1 else 1

    if dx > dy:
        err = dx / 2.0
        while x != int(x1):
            points.append((x, y))
            err -= dy
            if err < 0:
                y += sy
                err += dx
            x += sx
    else:
        err = dy / 2.0
        while y != int(y1):
            points.append((x, y))
            err -= dx
            if err < 0:
                x += sx
                err += dy
            y += sy
    points.append((int(x1), int(y1)))
    return points


def calculate_sinogram(img, steps, span, num_rays, max_angle):
    sinogram = np.zeros((steps, num_rays))
    for idx in range(steps):
        angle = idx * (max_angle / steps)
        rays = get_parallel_rays(max(img.shape[0] // 2, img.shape[1] // 2) * np.sqrt(2),
                                 (img.shape[0] // 2, img.shape[1] // 2), angle, span, num_rays)
        for ray_idx, ray in enumerate(rays):
            points = get_bresenham_points(ray[0][0], ray[1][0], ray[0][1], ray[1][1])
            sinogram[idx][ray_idx] = sum(img[p[1], p[0]] for p in points if 0 <= p[0] < img.shape[1] and 0 <= p[1] < img.shape[0])
    return sinogram


def reverse_radon_transform(img_shape, sinogram, steps, span, num_rays, max_angle):
    out_image = np.zeros(img_shape)
    for idx in range(steps):
        angle = idx * max_angle / steps
        rays = get_parallel_rays(max(img_shape[0] // 2, img_shape[1] // 2) * np.sqrt(2),
                                 (img_shape[0] // 2, img_shape[1] // 2), angle, span, num_rays)
        for ray_idx, ray in enumerate(rays):
            points = get_bresenham_points(ray[0][0], ray[1][0], ray[0][1], ray[1][1])
            for p in points:
                if 0 <= p[0] < img_shape[1] and 0 <= p[1] < img_shape[0]:
                    out_image[p[1], p[0]] += sinogram[idx][ray_idx]
    return normalize(out_image)


def normalize(img):
    return (img - img.min()) / (img.max() - img.min())


def create_kernel(size, kernel_type):
    one_d = np.zeros(size, dtype=np.float64)
    center = size // 2
    for i in range(size):
        if i == center:
            one_d[i] = 1.0
        elif i % 2 == 0:
            one_d[i] = 0.0
        else:
            dist = i - center
            base = (-4.0 / (math.pi ** 2)) / (dist ** 2)
            if kernel_type == 'ramp':
                one_d[i] = base
            elif kernel_type == 'shepp-logan':
                arg = math.pi * dist / (2 * center)
                sinc = math.sin(arg) / arg if arg != 0 else 1.0
                one_d[i] = base * sinc
            elif kernel_type == 'hamming':
                window = 0.54 - 0.46 * math.cos(2 * math.pi * i / (size - 1))
                one_d[i] = base * window
            elif kernel_type == 'hanning':
                window = 0.5 * (1 - math.cos(2 * math.pi * i / (size - 1)))
                one_d[i] = base * window
            elif kernel_type == 'cosine':
                window = math.cos(math.pi * dist / (2 * center))
                one_d[i] = base * window
            else:
                raise ValueError("Niepoprawny typ kernela.")
    return np.outer(one_d, one_d)


def filter_sinogram(sinogram):
    n_proj, n_detectors = sinogram.shape
    filtered_sino = np.zeros_like(sinogram)

    # Filtr Ram-Lak
    freqs = np.fft.fftfreq(n_detectors).reshape(-1, 1)
    ram_lak = 2 * np.abs(freqs)  # Filtr Ram-Lak

    sinogram_fft = np.fft.fft(sinogram, axis=0)
    sinogram_filtered = np.real(np.fft.ifft(sinogram_fft * ram_lak, axis=0))

    return sinogram_filtered


def rmse(img1, img2):
    return np.sqrt(np.mean(np.square(img1 - img2)))


def main():
    file_path = "shepp_logan.jpg"
    image = load_image(file_path)

    steps = 360
    num_rays = 360
    span = 180
    max_angle = 180

    sinogram = calculate_sinogram(image, steps, span, num_rays, max_angle)
    kernel = create_kernel(351, 'hamming')
    sinogram_filtered = filter_sinogram(sinogram)

    recon_image = reverse_radon_transform(image.shape, sinogram, steps, span, num_rays, max_angle)
    recon_image_filtered = reverse_radon_transform(image.shape, sinogram_filtered, steps, span, num_rays, max_angle)

    fig, axs = plt.subplots(1, 4, figsize=(20, 5))
    axs[0].imshow(image, cmap='gray')
    axs[0].set_title("Obraz wejściowy")
    axs[1].imshow(sinogram.T, cmap='gray', aspect='auto')
    axs[1].set_title("Sinogram")
    axs[2].imshow(recon_image, cmap='gray')
    axs[2].set_title("Rekonstrukcja bez filtra")
    axs[3].imshow(recon_image_filtered, cmap='gray')
    axs[3].set_title("Rekonstrukcja z filtrem")
    for ax in axs:
        ax.axis('off')
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()