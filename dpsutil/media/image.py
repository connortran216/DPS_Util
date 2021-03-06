import io
import os

import cv2
import numpy
from turbojpeg import TurboJPEG, TJPF_BGR

from .constant import FLIP_HORIZONTAL, FLIP_VERTICAL, FLIP_BOTH
from .constant import PX_BGR, PX_RGB, DEFAULT_QUALITY, ENCODE_PNG, ENCODE_JPEG
from .tool import hex2rgb, color_rgb2bgr, image_info, JPEG_FORMAT, JPEG2000_FORMAT

"""
This tool implement from OpenCV. Can you find more options at https://github.com/opencv/opencv
Drawing: https://docs.opencv.org/2.4/modules/core/doc/drawing_functions.html

* All method still cover (WIDTH, HEIGHT)
"""

jpeg_compressor = TurboJPEG()

M_RGB_YUV = numpy.array([
    [0.29900, -0.16874, 0.50000],
    [0.58700, -0.33126, -0.41869],
    [0.11400, 0.50000, -0.08131]
])

M_YUV_RGB = numpy.array([
    [1.0, 1.0, 1.0],
    [-0.000007154783816076815, -0.3441331386566162, 1.7720025777816772],
    [1.4019975662231445, -0.7141380310058594, 0.00001542569043522235]
])


def imencode(img, encode_type=ENCODE_JPEG, quality=DEFAULT_QUALITY, pixel_format=TJPF_BGR):
    """
    Encode image implement from OpenCV and TurboJPEG.
    Faster 2-6x at JPEG encoder. Otherwise, 1.1x.

    Parameters
    ----------
    img: numpy.ndarray
        Image's source.

    encode_type: int
        ENCODE_JPEG (default) | ENCODE_PNG.
        Output format of image.

    quality: int
        Quality of image after encode.
        From worse 0 -> 100 lossless.

    pixel_format: int
        Pixel's format of input.

    Returns
    -------
    bytes
        Buffer of image.

    References
    ------
        .. [1] PNG: https://docs.opencv.org/2.4/modules/highgui/doc/reading_and_writing_images_and_video.html#imencode
        .. [2] JPEG: https://github.com/kkroening/ffmpeg-python
    """
    if encode_type == ENCODE_JPEG:
        buffer = jpeg_compressor.encode(img, quality=quality, pixel_format=pixel_format)
    else:
        quality = max(0, min(int(quality / 10) - 1, 9))
        _, buffer = cv2.imencode(ENCODE_PNG, img, [cv2.IMWRITE_PNG_COMPRESSION, quality])
        buffer = buffer.tobytes()
    return buffer


def imdecode(buffer, pixel_format=TJPF_BGR):
    """
    Decode image implement from OpenCV and TurboJPEG.

    Parameters
    ----------
    buffer: bytes
        Buffer of image.

    pixel_format: int
        Pixel's format of output.

    Returns
    -------
    numpy.ndarray
        Numpy array of image.

    References
    ----------
        .. [1] PNG - https://docs.opencv.org/2.4/modules/highgui/doc/reading_and_writing_images_and_video.html#imdecode
        .. [2] JPEG: https://github.com/kkroening/ffmpeg-python
    """
    ext, (_, _) = image_info(buffer)

    if ext in [JPEG_FORMAT, JPEG2000_FORMAT]:
        return jpeg_compressor.decode(buffer, pixel_format)
    return cv2.imdecode(numpy.frombuffer(buffer, dtype=numpy.uint8), 1)


def imread(img_path, pixel_format=TJPF_BGR):
    """
    Read image from file to numpy.array which decode image implement from OpenCV and TurboJPEG.

    Parameters
    ----------
    img_path: str | io.BufferedReader
        Image's path.

    pixel_format: int
        Pixel's format of output.

    Returns
    -------
    numpy.ndarray
        Image's array.
    """
    assert isinstance(img_path, (str, io.BufferedReader))

    if type(img_path) is str:
        img_path = open(img_path, 'rb')

    buffer = img_path.read()
    return imdecode(buffer, pixel_format=pixel_format)


def imwrite(img, img_path, encode_type=ENCODE_JPEG, quality=95, pixel_format=TJPF_BGR, over_write=False):
    """
    Read image from file to numpy.array which encode image implement from OpenCV and TurboJPEG.
    Faster 2-6x at JPEG encoder. Otherwise, 1.1x.

    Parameters
    ----------
    img: numpy.ndarray
        Image's array

    img_path: str | io.BufferedWriter
        Image write path.

    encode_type: int
        ENCODE_JPEG (default) | ENCODE_PNG.
        Encode format of images. If extension wasn't in path. It's would be added.

    quality: int
        Quality of image after encode.
        From worse 0 -> 100 lossless.

    pixel_format: int
        Pixel's format of input.

    over_write: bool
        Over write file existed.
    """
    assert isinstance(img_path, (str, io.BufferedWriter))

    if isinstance(img_path, str):
        ext = "jpg"

        if encode_type == ENCODE_PNG:
            ext = "png"

        if not ext == img_path.split(".")[-1]:
            img_path = f"{img_path}.{ext}"

        if os.path.isfile(img_path) and not over_write:
            raise FileExistsError

        img_path = open(img_path, 'wb')

    with img_path:
        buffer = imencode(img, encode_type=encode_type, quality=quality, pixel_format=pixel_format)
        img_path.write(buffer)


def crop(img, box=(0, 0, 0, 0)) -> numpy.ndarray:
    """
    Crop media with margin.

    box = (x, y, width, height). (x, y) are location top-left of box.

    :return: cropped media
    """
    if not numpy.any(box):
        return img

    (max_height, max_width, _) = img.shape
    (x, y, w, h) = box

    x = int(round(max(x, 0)))
    y = int(round(max(y, 0)))
    w = x + int(round(min(w, max_width)))
    h = y + int(round(min(h, max_width)))
    return img[y:h, x:w]


def crop_margin(img: numpy.ndarray, margin_size: float, box=(0, 0, 0, 0)) -> numpy.ndarray:
    x, y, w, h = box
    w = w + margin_size
    h = h + margin_size
    x = x - margin_size
    y = y - margin_size
    return crop(img, (x, y, w, h))


# Todo: https://stackoverflow.com/questions/60029431/how-to-pad-an-array-of-images-with-a-given-color-without-a-for-loop
# torchvision.functional.pad
# def pad(img, pad_value, method="constant"):
#     pass


def crop_center(img, crop_size) -> numpy.ndarray:
    """
    Crop center of image with crop_size

    :raise ValueError. if crop_size > image's size
    """
    height, width = img.shape[:2]
    width_crop, height_crop = crop_size

    if width_crop >= width or height_crop >= height:
        raise ValueError(f"crop_size must be smaller than image's size! {width_crop, height_crop} >= {width, height}")

    x = int(round((width - width_crop) / 2.))
    y = int(round((height - height_crop) / 2.))
    return crop(img, (x, y, width_crop, height_crop))


def resize(img, width=None, height=None, interpolation=None):
    """
    This function resize with keep ratio supported. Auto downscale or upscale fit with image's height.
    """
    assert isinstance(img, numpy.ndarray)

    # check any width or height parameters was filled.
    if (width is None and height is None) or not ((not width or width > 0) or (not height or height > 0)):
        return img

    old_h, old_w, _ = img.shape
    if not width or width <= 0:
        width = height / old_h * old_w

    if not height or height <= 0:
        height = width / old_w * old_h
    return cv2.resize(img, (int(width), int(height)), interpolation=interpolation)


def flip(img, flip_mode):
    if flip_mode == FLIP_VERTICAL:
        axis = 0
    elif flip_mode == FLIP_HORIZONTAL:
        axis = 1
    elif flip_mode == FLIP_BOTH:
        axis = (0, 1)
    else:
        raise ValueError(f"Mode '{flip_mode}' isn't supported. Only: FLIP_VERTICAL, FLIP_HORIZONTAL or FLIP_BOTH")
    return numpy.flip(img, axis=axis)


def zoom(img: numpy.ndarray, zoom_level: float, center=None) -> numpy.ndarray:
    """
    Zoom image at position.

    Parameters
    ----------
    img: numpy.ndarray
        Image's array

    zoom_level: int
        Level of zoom. Example: 1x == 1, 1.5x==1.5, 2x == 2...

    center: tuple of int
        Center of image's zoomed. Default: center old image.
    """
    assert isinstance(img, numpy.ndarray)
    assert type(center) in [type(None), tuple]

    if zoom_level == 1:
        return img

    (h, w) = img.shape[:2]

    if type(center) is tuple:
        assert len(center) == 2
        assert 0 <= center[0] <= w and 0 <= center[1] <= h, "Out of image's length"
    else:
        center = (w // 2, h // 2)

    rotate_matrix = cv2.getRotationMatrix2D(center, 0, float(zoom_level))
    return cv2.warpAffine(img, rotate_matrix, (w, h))


def crop_scale(img, box=(0, 0, 0, 0), output_size=None):
    """Crop image and scale to output_size if it's set"""
    if not numpy.any(box):
        box = (0, 0, *img.shape[:2][::-1])

    img = crop(img, box)

    if output_size:
        return resize(img, output_size)
    return img


def rotate_bound(img, angle) -> numpy.ndarray:
    """
    Rote image without crop image.
    """
    (h, w) = img.shape[:2]
    (cX, cY) = (w // 2, h // 2)

    rotate_matix = cv2.getRotationMatrix2D((cX, cY), -angle, 1.0)
    cos = numpy.abs(rotate_matix[0, 0])
    sin = numpy.abs(rotate_matix[0, 1])

    new_w = int((h * sin) + (w * cos))
    new_h = int((h * cos) + (w * sin))

    rotate_matix[0, 2] += (new_w / 2) - cX
    rotate_matix[1, 2] += (new_h / 2) - cY
    return cv2.warpAffine(img, rotate_matix, (new_w, new_h))


def rotate_crop(img, angle, center=None) -> numpy.ndarray:
    """
    Rotate image and crop part out of size.
    """
    assert type(center) in [type(None), tuple]

    (h, w) = img.shape[:2]

    if type(center) is tuple:
        assert len(center) == 2
        assert 0 <= center[0] <= w and 0 <= center[1] <= h, "Out of image's length"
    else:
        center = (w // 2, h // 2)

    rotate_matix = cv2.getRotationMatrix2D(center, -angle, 1.0)
    return cv2.warpAffine(img, rotate_matix, (h, w))


def draw_text(img, label, position, color=(0, 0, 255), scale_factor=1, thickness=1,
              font=cv2.FONT_HERSHEY_DUPLEX, wrap_text=False) -> numpy.ndarray:
    """
    Draw text at position in image.
    - position: top-left of text
    - color: support tuple and hex_color
    :return:
    """
    if not isinstance(position, tuple):
        position = tuple(position)

    if isinstance(color, str):
        color = hex2rgb(color)
        color = color_rgb2bgr(color)

    if wrap_text:
        for i, line in enumerate(label.split('\n')):
            text_size = cv2.getTextSize(line, fontFace=font, fontScale=scale_factor, thickness=thickness)[0]

            gap = text_size[1] + 10

            y = int((img.shape[0] + text_size[1]) / 2) + i * gap
            x = int((img.shape[1] - text_size[0]) / 2)

            cv2.putText(img, line, (x, y),
                        fontFace=font,
                        color=color,
                        fontScale=scale_factor,
                        thickness=thickness,
                        lineType=cv2.LINE_AA)
    else:
        cv2.putText(img, label, position,
                    fontFace=cv2.FONT_HERSHEY_DUPLEX, fontScale=scale_factor, color=color, thickness=thickness)
    return img


def draw_square(img, position, color=(0, 255, 0), thickness=1, line_type=None, shift=None) -> numpy.ndarray:
    """
    Draw text at position in image.
    - position: top-left, bottom-right of square
    - color: support tuple and hex_color
    :return:
    """
    if not isinstance(position, tuple):
        position = tuple(position)

    if isinstance(color, str):
        color = hex2rgb(color)
        color = color_rgb2bgr(color)

    return cv2.rectangle(img, position[0:2], position[2:4], color, thickness=thickness, lineType=line_type, shift=shift)


def normalize(img, mean, std):
    assert isinstance(img, numpy.ndarray)

    img = img.astype(numpy.float32) / 255

    mean = numpy.asarray(mean, dtype=numpy.float32)
    std = numpy.asarray(std, dtype=numpy.float32)
    return (img - mean[None, None, :]) / std[None, None, :]


def RGB2YUV(rgb_image):
    """
    Convert image's array in RGB -> YUV

    Parameter
    ---------
    rgb_image: numpy.ndarray
        Image's array is RGB numpy array with shape (height,width,3),
        can be uint,int, float or double, values expected in the range 0..255

    Returns
    -------
    numpy.ndarray
        Image's array is a double YUV numpy array with shape (height,width,3), values in the range 0..255
    """
    yuv_image = numpy.dot(rgb_image, M_RGB_YUV)
    yuv_image[:, :, 1:] += 128.0
    return yuv_image.astype(numpy.uint8)


def YUV2RGB(yuv_image):
    """
    Convert image's array in YUV -> RGB color-space

    Parameter
    ---------
    rgb_image: numpy.ndarray
        Image's array is YUV numpy array with shape (height,width,3),
        can be uint,int, float or double, values expected in the range 0..255

    Returns
    -------
    numpy.ndarray
        Image's array is a double RGB numpy array with shape (height,width,3), values in the range 0..255
    """

    rgb_image = numpy.dot(yuv_image, M_YUV_RGB)
    rgb_image[:, :, 0] -= 179.45477266423404
    rgb_image[:, :, 1] += 135.45870971679688
    rgb_image[:, :, 2] -= 226.8183044444304
    return rgb_image.astype(numpy.uint8)


__all__ = ['imencode', 'imdecode', 'imread', 'imwrite', 'crop', 'resize', 'zoom', 'rotate_bound', 'rotate_crop',
           'draw_text', 'draw_square', 'RGB2YUV', 'YUV2RGB', 'ENCODE_PNG', 'ENCODE_JPEG', 'PX_BGR',
           'PX_RGB', 'crop_scale', 'flip', 'crop_margin', 'crop_center']
