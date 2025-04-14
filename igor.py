import copy
import math
import numpy as np
from scipy.signal import convolve2d

def get_parallel_rays(radius, pos, angle, span, num_rays):
    """
    Funkcja obliczająca współrzędne emitorów i detektorów dla zadanych parametrów

    :param radius: promień okręgu
    :param pos: środek badanego zdjęcia
    :param angle: kąt pod którym padają promienie (w równaniach oznaczany alfa)
    :param span: rozpiętość promieni (w równania oznaczana phi)
    :param num_rays: liczba emiterów oraz detektorów

    :return: ndarray współrzędnych emiterów i odpowiadających im detektorów
    """

    alpha = np.radians(angle)
    theta = np.radians(span)

    # Wektor indeksów promieni
    ray_indices = np.linspace(0, num_rays - 1, num_rays)

    # Obliczenie kątów dla detektorów i emiterów
    detector_angles = alpha - (ray_indices * theta / (num_rays - 1)) + theta / 2
    emitter_angles = alpha + np.pi - (theta / 2) + (ray_indices * theta / (num_rays - 1))

    # Obliczenie współrzędnych emiterów
    x_e = radius * np.cos(emitter_angles) + pos[0]
    y_e = radius * np.sin(emitter_angles) + pos[1]

    # Obliczenie współrzędnych detektorów
    x_d = radius * np.cos(detector_angles) + pos[0]
    y_d = radius * np.sin(detector_angles) + pos[1]

    # Łączenie współrzędnych w jedną tablicę: dla każdego promienia
    # element = [[x_det, x_em], [y_det, y_em]]
    rays = np.empty((num_rays, 2, 2))
    rays[:, 0, 0] = x_e
    rays[:, 0, 1] = x_d
    rays[:, 1, 0] = y_e
    rays[:, 1, 1] = y_d

    return rays

def get_bresenham_points(x1, x2, y1, y2):
    """
    Funkcja obliczająca współrzędne promieni na podstawie algorytmu Bresenhama

    :param x1: - współrzędne x emitera
    :param x2: - współrzędne x detektora
    :param y1: - współrzędne y emitera
    :param y2: - współrzędne y detektora

    :return: lista punktów odpowiadających wiązce
    """
    # floaty -> inty
    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
    dx = x2 - x1
    dy = y2 - y1

    # Określenie wiodącej osi
    is_steep = abs(dy) > abs(dx)

    # Jeżeli OY jest wiodąca odwracamy współrzędne inaczej dzielenie przez 0 przy kącie prostym
    if is_steep:
        x1, y1 = y1, x1
        x2, y2 = y2, x2

    # Jeżeli współrzędne są odwrócone to zamieniamy na potrzeby obliczeń
    swapped = False
    if x1 > x2:
        x1, x2 = x2, x1
        y1, y2 = y2, y1
        swapped = True

    # Obliczenie delt jeszcze raz po posprzątaniu inputu
    dx = x2 - x1
    dy = y2 - y1

    # Obliczenie błędu
    error = int(dx / 2.0)
    ystep = 1 if y1 < y2 else -1

    y = y1
    points = []
    for x in range(x1, x2 + 1):
        coord = (y, x) if is_steep else (x, y)
        points.append(coord)
        error -= abs(dy)
        if error < 0:
            y += ystep
            error += dx

    # Odwrócenie współrzędnych punktów jeżeli były w złej kolejności na potrzeby obliczeń
    if swapped:
        points.reverse()
    return points


def calculate_sinogram(img, steps, span, num_rays, max_angle, intermediate=False):
    """
    Funkcja obliczająca sinogram obrazu wejściowego

    :param img: - ndarray obrazu wejściowego
    :param steps: - ilość kroków (emiterów oraz detektorów)
    :param span: - zakres promieni
    :param num_rays: - liczba promieni
    :param max_angle: - maksymalny kąt
    :param intermediate: możliwość uzyskania wyników pośrednich jeżeli True

    :return ndarray odpowiadający sinogramowi
    """
    # Pusty ndarray wypełniany dalej sinogramem (czarny obraz)
    sinogram = np.zeros((steps, num_rays))
    if intermediate:
        iterations = []

    for idx in range(steps):
        # Kąt padania promieni i współrzędne emiterów oraz detektorów
        angle = idx * (max_angle/steps)
        rays = get_parallel_rays(max(img.shape[0]//2, img.shape[1]//2) * np.sqrt(2),
                                 (img.shape[0]//2, img.shape[1]//2), angle, span, num_rays)
        for ray_idx, ray in enumerate(rays):
            # Współrzędne wiązek z emiterów
            emitter_value = 0
            points = get_bresenham_points(ray[0][0], ray[0][1], ray[1][0], ray[1][1])
            for point in points:
                # Rozświetlanie pikseli w granicach obrazu
                if (0 <= point[0] < img.shape[0]) and (0 <= point[1] < img.shape[1]):
                    emitter_value += img[point[0]][point[1]]
            sinogram[idx][ray_idx] = emitter_value
        if intermediate:
            iterations.append(copy.deepcopy(sinogram))

    # By wyświetlić prawidłowo trezeba transponować ponieważ format odpowiada formatowi
    # danych zbieranych przez rzeczywisty tomograf (każdy wiersz to wyniki uzyskane
    # dla danego kąta), który powodowałby błędne wykreślenie sinogramu
    if intermediate:
        return iterations
    else:
        return sinogram

def reverse_radon_transform(img, sinogram, steps, span, num_rays, max_angle, intermediate=False):
    """
    Funkcja uzyskująca rekonstrukcję oryginalnego obrazu na podstawie sinogramu używając
    odwróconej transformaty Radona

    :param img: - ndarray obrazu wejściowego
    :param sinogram: - sinogram wejściowy
    :param steps: - ilość kroków (emiterów oraz detektorów)
    :param span: - zakres promieni
    :param num_rays: - liczba promieni
    :param max_angle: - maksymalny kąt
    :param intermediate: możliwość uzyskania wyników pośrednich jeżeli True

    :return: ndarray przedstawiąjący zrekonstruowany obraz wejściowy
    """
    out_image = np.zeros((img.shape[0], img.shape[1]))
    if intermediate:
        iterations = []

    for idx in range(steps):
        angle = idx * max_angle / steps
        rays = get_parallel_rays(max(img.shape[0] // 2, img.shape[1] // 2) * np.sqrt(2),
                                 (img.shape[0] // 2, img.shape[1] // 2), angle, span, num_rays)
        for ray_idx, ray in enumerate(rays):
            points = get_bresenham_points(ray[0][0], ray[0][1], ray[1][0], ray[1][1])
            for point in points:
                # Tylko dla punktów zawierających się w sinogramie
                if (0 <= point[0] < img.shape[0]) and (0 <= point[1] < img.shape[1]):
                    out_image[point[0]][point[1]] += sinogram[idx][ray_idx]
                    if intermediate:
                        iterations.append(copy.deepcopy(out_image))

    if intermediate:
        return iterations
    else:
        return normalize(out_image)

def normalize(img):
    return (img - img.min()) / (img.max() - img.min())

def __create_kernel(size, kernel_type):
    """
    Tworzy dwuwymiarowy kernel (jądro filtra) na podstawie podanego rozmiaru i typu.
    Dostępne typy: 'ramp' (Ram-Lak), 'shepp-logan', 'cosine', 'hamming', 'hanning'

    :param size: rozmiar kwadratowego kernela (np. 51 oznacza kernel 51x51)
    :param kernel_type: typ kernela (jeden z dopuszczalnych ciągów znaków)
    :return: 2D ndarray o wymiarach (size, size) reprezentujący jądro filtra
    """
    one_d = np.zeros(size, dtype=np.float64)
    center = size // 2

    for i in range(size):
        if i == center:
            one_d[i] = 1.0
        elif i % 2 == 0:
            one_d[i] = 0.0
        else:
            dist = i - center
            if kernel_type == 'ramp':
                one_d[i] = (-4.0 / (math.pi ** 2)) / (dist ** 2)
            elif kernel_type == 'shepp-logan':
                # Unikanie dzielenia przez zero przy obliczeniach sinc
                sinc = math.sin(math.pi * dist / (2 * center)) / (math.pi * dist / (2 * center))
                one_d[i] = (-4.0 / (math.pi ** 2)) / (dist ** 2) * sinc
            elif kernel_type == 'hamming':
                window = 0.54 - 0.46 * math.cos(2 * math.pi * i / (size - 1))
                one_d[i] = (-4.0 / (math.pi ** 2)) / (dist ** 2) * window
            elif kernel_type == 'hanning':
                window = 0.5 * (1 - math.cos(2 * math.pi * i / (size - 1)))
                one_d[i] = (-4.0 / (math.pi ** 2)) / (dist ** 2) * window
            elif kernel_type == 'cosine':
                window = math.cos(math.pi * dist / (2 * center))
                one_d[i] = (-4.0 / (math.pi ** 2)) / (dist ** 2) * window
            else:
                raise ValueError(
                    "Niepoprawny typ kernela. Dozwolone typy: 'ramp', 'shepp-logan', 'cosine', 'hamming', 'hanning'")

    # Tworzymy kernel 2D jako produkt zewnętrzny jądra jednowymiarowego
    kernel = np.outer(one_d, one_d)
    return kernel


def create_shepp_logan_kernel(size):
    kernel_1d = np.zeros(size, dtype=np.float64)
    center = size // 2

    for i in range(size):
        if i == center:
            kernel_1d[i] = 1.0
        elif i % 2 == 0:
            kernel_1d[i] = 0.0
        else:
            dist = i - center
            arg = math.pi * dist / (2 * center)
            sinc = math.sin(arg) / arg if arg != 0 else 1.0
            kernel_1d[i] = (-4.0 / (math.pi ** 2)) / (dist ** 2) * sinc

    kernel_2d = np.outer(kernel_1d, kernel_1d)
    return kernel_2d

def filter_sinogram(sinogram, kernel):
    """
    Dokonuje dwuwymiarowego splotu sinogramu z podanym 2D kernelem.

    :param sinogram: macierz sinogramu (2D ndarray)
    :param kernel: dwuwymiarowy jądro filtra (2D ndarray)
    :return: ndarray przefiltrowanego sinogramu o tych samych wymiarach co wejściowy
    """
    # Wykonywany jest splot 2D z trybem 'same', który zapewnia, że wynik ma te same wymiary co macierz wejściowa.
    filtered = convolve2d(sinogram, kernel, mode='same', boundary='fill', fillvalue=0)
    return filtered


def rmse(img1, img2):
    return np.sqrt(np.mean(np.square(img1 - img2)))