import json
import os
import traceback
from multiprocessing import Lock
from pathlib import Path
from typing import Literal
from typing import Union

import cv2
import lmdb
import numpy as np
from PIL import Image

if __name__ == '__main__':
    __package__ = 'src.lv_tools.dataset_io'
from ..cores.str_utils import rand_str
from ..cores.img_io import img_pil_to_byte
from ..cores.json_io import save_json


class LmdbSaver:
    num_key = 'num-samples'

    def __init__(self, lmdb_path: Union[str, Path], cache_capacity: int = 1000, map_size: int = 10 ** 9):

        self.path = lmdb_path
        self._env = self._open_lmdb(lmdb_path, map_size=map_size)
        self._lock = Lock()
        self._cnt = self._init_cnt()
        self._cache = dict()
        self._cache_capacity = cache_capacity

    def __len__(self):
        return self._cnt
    
    @staticmethod
    def _open_lmdb(lmdb_path: Union[Path, str], map_size: int = 100 * 1024 * 1024):
        lmdb_path = Path(lmdb_path)
        base_folder = lmdb_path.parent
        if not base_folder.exists():
            base_folder.mkdir(parents=True, exist_ok=True)
        if (lmdb_path / "data.mdb").exists():
            print("Open lmdb {}".format(str(lmdb_path)))
        else:
            print("Create lmdb {}".format(str(lmdb_path)))
        return lmdb.open(str(lmdb_path), map_size=map_size)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _add_map_size(self, adder_size: int = 1024 * 1024 * 1024):
        self._lock.acquire()
        map_size = self._env.info()['map_size']
        map_size += adder_size
        self._env.set_mapsize(map_size)
        self._lock.release()

    def _init_cnt(self):
        txn = self._env.begin()
        # num_samples = txn.get(self.num_key.encode("utf-8"), b'0')
        num_samples = txn.stat()['entries']
        return int(num_samples)

    def _get_cnt(self):
        self._lock.acquire()
        cnt = self._cnt
        self._cnt += 1
        self._lock.release()
        return cnt

    def _write_cache(self):
        self._update_global_info()
        self._lock.acquire()

        txn = self._env.begin(write=True)

        for k, v in self._cache.items():
            try:
                txn.put(k, v)

            except lmdb.MapFullError:
                txn.abort()  # 如果内存满，回滚事务
                self._lock.release()
                return False  # 返回False表示需要扩展映射空间
            except:
                print('unkonw error {}'.format(traceback.extract_stack(limit=2)))
                self._lock.release()
                return True  # 返回True表示其他异常，不扩展映射空间
        try:
            stat = txn.stat()  # txn 每 put一次，txn.stat()都会返回一个新字典，['entries']同步变化。
            num_entries = stat['entries']
            
            self._cnt = num_entries - 1
            txn.put(self.num_key.encode('utf8'), str(self._cnt).encode('utf8'))

            txn.commit()
        except lmdb.MapFullError:
            txn.abort()
            self._lock.release()
            return False
        except:
            print('unkonw error {}'.format(traceback.extract_stack(limit=2)))

        self._lock.release()
        return True

    def show_samples(self):
        raise NotImplementedError

    def key_exists(self, key: bytes):
        # with self.env.begin() as txn:
        #     if txn.get(key) is None:
        #         return False
        #     return True

        with self._env.begin() as txn:
            cursor = txn.cursor()
            return cursor.set_key(key)  # Returns True if key exists, False otherwise

    def put(self, key: bytes, value: bytes):
        '''
        append() 是用于 列表 的方法，向列表末尾添加单个元素。
        add()   是用于 集合 的方法，向集合中添加一个元素（集合自动处理重复元素）。
        put()  主要用于 队列 或线程安全的数据结构，插入数据到队列中，通常不用于字典，字典操作中使用的是 key = value 语法。

        :param key:
        :param value:
        :return:
        '''
        self._cache[key] = value
        self._end_a_item()

    def close(self):
        print('begin to close {}...'.format(self.path))
        if self._env is None:
            return
        idx = 0
        while idx < 100:  # 防止无限扩充,确保可以正常关闭数据库，代价就是可能存在一些末尾数据无法写入的问题。
            if self._write_cache():
                break
            else:
                self._add_map_size()
            idx += 1
        self._env.close()
        self._env = None
        print('{} have {} samples'.format(self.path, self._cnt))

    def _update_global_info(self):
        self._cache["num-samples".encode("utf-8")] = str(self._cnt).encode("utf-8")

    def __del__(self):
        self.close()

    def _end_a_item(self):
        if len(self._cache) >= self._cache_capacity:
            while True:
                if self._write_cache():
                    break
                else:
                    self._add_map_size()
            self._cache = dict()


class JsonLSaver:
    def __init__(self, jsonl_path: str, mode: Literal['w', 'a'] = 'w', cache_capacity: int = 1000):
        self._jsonl_path = jsonl_path
        self._mode = mode
        self._write_file = open(self._jsonl_path, mode=self._mode, encoding='utf8')
        self._cache = []
        self._cache_capacity = cache_capacity

    def put(self, jd: dict):
        json_string = json.dumps(jd, ensure_ascii=False)
        self._cache.append(f'{json_string}\n')
        self._end_a_item()

        # self.write_file.write(f'{json_string}\n')

    def _end_a_item(self):
        if len(self._cache) > self._cache_capacity:
            self._write_cache()

    def __enter__(self):

        return self

    def _write_cache(self):
        self._write_file.writelines(self._cache)
        self._write_file.flush()
        self._cache = []

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._write_file.close()

    def close(self):
        if self._cache:
            self._write_cache()
        self._write_file.close()


class LmdbJsonLSaver:
    def __init__(self, lmdb_saver: LmdbSaver, jsonl_saver: JsonLSaver):
        self._lmdb_saver = lmdb_saver
        self._jsonl_saver = jsonl_saver

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self._lmdb_saver.close()
        self._jsonl_saver.close()

    def _get_image_stem(self, jd: dict):
        if img_path := jd.get('image_path'):
            image_path_stem = Path(img_path).stem
        elif img_path := jd.get('imagePath'):
            image_path_stem = Path(img_path).stem
        else:
            raise ValueError('image_path or imagePath not found in jd')
        return image_path_stem

    def _gen_img_save_key(self, jd: dict):
        lmdb_dir_name = Path(self._lmdb_saver.path).name
        image_path_stem = self._get_image_stem(jd)
        image_path_stem += f'_{rand_str(5)}'
        image_path_name = image_path_stem.lower() + '.jpg'

        return f'{lmdb_dir_name}/{image_path_name}'

    def _img_arr_to_bytes(self, img_arr: np.ndarray) -> bytes:
        img_pil = Image.fromarray(img_arr)
        img_bytes = img_pil_to_byte(img_pil)
        return img_bytes

    def _ensure_img_path(self, jd: dict):
        jd['image_path'] = self._gen_img_save_key(jd)

    def _compatible_with_labelme(self, jd: dict):

        jd['imagePath'] = Path(jd['image_path']).name

    def put(self, img_arr: np.ndarray, jd: dict):
        '''
        # put 承担了过多职责，应该将其拆分。 image_path 的生成，应该单独的方法。但是目前有太多依赖于这个方法的代码，所以暂时不拆分。
        :value 直接接收img_arr，因为lmdb-jsonl的模式，已确定为img_arr和jd的存储形式，不太可能存储别的python类型。
        而Jd，一定是个json_dict。
        '''

        self._ensure_img_path(jd)

        self._compatible_with_labelme(jd)

        key = jd['image_path'].encode('utf-8')
        img_arr = cv2.cvtColor(img_arr, cv2.COLOR_BGR2RGB)
        img_bytes = self._img_arr_to_bytes(img_arr)

        self._lmdb_saver.put(key, img_bytes)
        self._jsonl_saver.put(jd)

    def close(self):
        self._lmdb_saver.close()
        self._jsonl_saver.close()


class JpgJsonSaver:
    def __init__(self, dst_dir: Union[Path, str], json_style: Literal['alva', 'labelme'] = 'labelme'):
        self._dst_dir = dst_dir
        # 有多种版本的JpgJsonSAver，之后应该不会再有碎文件生成了，所以该类只是简单实现一下。
        # ①可以使用继承实现多个版本
        # ②也可以使用组成的方式封装多版本变化
        # ③也可以像这里的实现一样用开关切换。（开关的缺点是，会削弱内聚性）
        self._json_style = json_style

    def _get_image_path(self, jd: dict):
        image_path_name = Path(jd.get('image_path')).name if jd.get('image_path') else rand_str(8) + '.jpg'

        return image_path_name

    def put(self, img_arr: np.ndarray, jd: dict):
        '''
        需要知道进来的img_arr是BGR模式还是RBG模式。-> 如何巧妙统一cv2和PIL来源的图像数组的存储，当前设计是：

        确保所有加载进来的img_arr是BGR模式，
        * 写出到jpg时，使用cv2直接写出。
        * 写出到lmdb时，转为RBG再将bytes格式的图像写出。

        '''

        if not os.path.exists(self._dst_dir):
            os.mkdir(self._dst_dir)

        img_name = self._get_image_path(jd)
        jd['imagePath'] = jd['image_path'] = img_name
        json_path = os.path.join(self._dst_dir, img_name[:-4] + '.json')
        cv2.imwrite(os.path.join(self._dst_dir, img_name), img_arr)

        save_json(json_path, jd)


if __name__ == '__main__':
    print(Path('image_path/dsfsaaaddd').name.strip('sfdd'))
