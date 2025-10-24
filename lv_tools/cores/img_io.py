'''
【b64】,【bytes】,【arr】,【PIL】 数据形式转换。 labelme 的utils模块都有实现。
'''
import base64
import io

import PIL.Image
import PIL.ImageOps
import cv2
import numpy as np


def cv2imread(img_path:str)->np.ndarray:
    '''
    可读取中文等特殊命名的图片文件，且图片不存在时，会报异常。
    '''
    return cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), -1)


def cv2imwrite(img_path:str, img:np.ndarray):
    '''
    可写出path中带有中文等特殊字符的文件。
    '''
    cv2.imencode('.jpg', img)[1].tofile(img_path)


def img_byte_to_pil(img_data: bytes)->PIL.Image.Image:
    with io.BytesIO() as f:
        f.write(img_data)
        img_pil = PIL.Image.open(f)
        img_pil.load()  # 强制加载数据到内存
    return img_pil


def img_byte_to_arr(img_data: bytes)->np.ndarray:
    img_pil = img_byte_to_pil(img_data)
    img_arr = np.array(img_pil)
    return img_arr


def img_b64_to_arr(img_b64: str) -> np.ndarray:
    img_data = base64.b64decode(img_b64)
    img_arr = img_byte_to_arr(img_data)
    return img_arr


def img_pil_to_byte(img_pil: PIL.Image,format='JPEG') -> bytes:
    f = io.BytesIO()
    img_pil.save(f, format=format)
    img_data = f.getvalue()
    return img_data


def img_arr_to_b64(img_arr: np.ndarray,format='JPEG')->bytes:
    img_pil = PIL.Image.fromarray(img_arr)
    f = io.BytesIO()
    img_pil.save(f, format=format)
    img_bin = f.getvalue()
    if hasattr(base64, "encodebytes"):
        img_b64 = base64.encodebytes(img_bin)
    else:
        img_b64 = base64.encodestring(img_bin)
    return img_b64


def img_byte_to_png_data(img_data: bytes,format='JPEG'):
    with io.BytesIO() as f:
        f.write(img_data)
        img = PIL.Image.open(f)

        with io.BytesIO() as f:
            img.save(f, format=format)
            f.seek(0)
            return f.read()
