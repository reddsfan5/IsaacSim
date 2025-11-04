# coding=utf-8
import json
import os
import random
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

import cv2
import lmdb
import numpy as np
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type, retry_if_result
import sys

sys.path.append('/home/ubuntu/lxd/lxd_code/isaacsim')

if __name__ == '__main__':
    __package__ = 'lv_tools.dataset_io'
        
   
from ..cores.img_io import img_byte_to_arr
from ..cores.json_io import load_json_to_dict


class ImgArrayJDLoader(ABC):
    '''
    数据来源不确定，无法保证字典数据对于某些字段的完备性。
    因此，对于关键字段需要进行检查更新。
    比如：
    1. 对于image_path字段，需要检查是否存在，不存在则基于对应的实现类的逻辑进行补充。

    我们可以使用文档字符串的方式提醒开发，对对应的字典进行检查，但这样缺乏强制性。
    可使用容器类对关键字检查。

    jd 应该携带便于追踪的一些信息，比如：来源，所用字体等。

    '''

    @abstractmethod
    def __iter__(self):
        pass

    @abstractmethod
    def __len__(self):
        pass

    # @abstractmethod
    # def __next__(self) -> tuple[np.ndarray, dict]:
    #     '''
    #     :return:   (np.ndarray:【BGR】,jd)'''
    #     pass

    @abstractmethod
    def choice(self) -> tuple[np.ndarray, dict]:
        '''
        :return:   (np.ndarray:【BGR】,jd)
        '''
        pass


class LmdbLoader:
    def __init__(self, lmdb_path: Union[Path, str]):
        self.env = self._open_lmdb(str(lmdb_path))
        self.txn = self.env.begin(write=False)
        self.num_samples = self._get_num_samples()

    def _open_lmdb(self, lmdb_path: str):
        if not os.path.exists(lmdb_path):
            raise FileExistsError(lmdb_path)
        if not os.path.exists(os.path.join(lmdb_path, "data.mdb")):
            raise FileExistsError(os.path.join(lmdb_path, "data.mdb"))
        env = lmdb.open(lmdb_path, max_readers=32, readonly=True, lock=False, readahead=False, meminit=False)
        return env

    def _get_num_samples(self):
        num_samples = self.txn.get("num-samples".encode("utf-8"))
        num_samples = int(num_samples.decode("utf-8")) if num_samples is not None else self.txn.stat()['entries']

        return num_samples

    def __len__(self):
        return self.num_samples

    def __getitem__(self, key: str):
        '''
        只负责取出来，不做额外逻辑
        '''
        if isinstance(key, str):
            key = key.encode("utf-8")
        elif not isinstance(key, bytes):
            raise TypeError(f'key should be str or byte,but accept type: {type(key)}')
        return self.txn.get(key)

    def get(self, key: str):  # 只是为了兼容之前基于此逻辑的代码，现已用__getitem__()取代。
        return self[key]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.env.close()

    def __iter__(self):
        return iter(self.txn.cursor())
    def iter_keys(self):
        return iter(self.txn.cursor().iternext(keys=True,values=False))

class JsonLLoader:
    def __init__(self, jsonl_path: Union[Path, str]):
        self.json_lines: list[str] = self._get_json_lines(jsonl_path)
        self._index = 0

    def _get_json_lines(self, jsonl_path: Union[Path, str]):
        with open(str(jsonl_path), "r", encoding='utf8') as f:
            lines = f.readlines()
        return lines

    def choice(self) -> dict:
        jsonl = random.choice(self.json_lines).strip()
        return json.loads(jsonl)

    def __iter__(self):
        return self

    def __next__(self):
        if self._index >= len(self.json_lines):
            raise StopIteration
        else:
            value = self.json_lines[self._index].strip()
            jd = json.loads(value)
            self._index += 1
            return jd

    def __len__(self):
        return len(self.json_lines)

    def __getitem__(self, index: int):
        jsonl = self.json_lines[index].strip()
        return json.loads(jsonl)
    
    
        
    


class LmdbJsonLLoader(ImgArrayJDLoader):
    def __init__(self, lmdb_root: str, jsonl_paths: Union[str, Path, list[Union[Path, str]]]):
        '''
        文件结构，需要一些约束，就像各种训练数据集需要特定结构一样，这有利于程序快速运行，而不需要多余的没必要的判断和遍历。
        这里约束：凡是基于lmdb和Jsonl对儿进行数据加载的文件目录结构都应该只有如下两种：
        1. lmdb放在根目录下。
        2. lmdb放在次级目录下，且其parent需与jsonl中image_path的parent对应。
        '''
        self._lmdb_loader_map = self._load_lmdbs(self._find_lmdb_dirs(lmdb_root))
        self._jsonl_loader_list = self._load_jsonls(jsonl_paths)

    def _find_lmdb_dirs(self, lmdb_root: Union[Path, str]):
        lmdb_dirs = [mdb_path.parent for mdb_path in Path(lmdb_root).rglob('*data.mdb')]
        return lmdb_dirs

    def _load_lmdbs(self, lmdb_dirs: list[Path]):
        lmdb_loader_map = {}
        for lmdb_dir in lmdb_dirs:
            lmdb_loader_map[lmdb_dir.name] = LmdbLoader(str(lmdb_dir))
        return lmdb_loader_map

    def _load_jsonls(self, jsonl_paths: Union[str, Path, list[Union[Path, str]]]):
        jsonl_loader_list = []
        if isinstance(jsonl_paths, list):

            for jsonl_path in jsonl_paths:
                if (jsonl_path := Path(jsonl_path)).suffix == '.jsonl' and jsonl_path.exists():
                    jsonl_loader_list.append(JsonLLoader(jsonl_path))
        elif (jsonl_path := Path(jsonl_paths)).suffix == '.jsonl':
            jsonl_loader_list.append(JsonLLoader(jsonl_path))

        return jsonl_loader_list

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type(ValueError)  # 仅在抛出 ValueError 时才重试
    )
    def choice(self):
        '''
        jsonl都是用我们的程序生成的，必然会有image_path字段。
        :return:
        '''

        jsonl_loader = random.choice(self._jsonl_loader_list)

        jd = jsonl_loader.choice()
        img_arr = self._get_img_arr(jd)
        return img_arr, jd

    def _get_img_arr(self, jd: dict):
        if not jd:
            raise ValueError("Failed to get jsonl data")
        img_name = jd.get('image_path')
        img_map_k = os.path.dirname(img_name)
        if img_map_k not in self._lmdb_loader_map:
            raise KeyError(f"the lmdb dir named {img_map_k} doesn't exist")

        img_byte = self._lmdb_loader_map[img_map_k].get(img_name)

        if not img_byte:
            raise ValueError(f"Failed to get image from lmdb {img_map_k}")
        img_arr = img_byte_to_arr(img_byte)
        img_arr = cv2.cvtColor(img_arr, cv2.COLOR_RGB2BGR)  # cv2写出时，就不用再转换了。

        return img_arr

    def __len__(self):
        jsons_len = sum([len(jsonl_loader) for jsonl_loader in self._jsonl_loader_list])
        lmdb_data_len = sum([len(lmdb_loader) for lmdb_loader in self._lmdb_loader_map.values()])

        return min(jsons_len, lmdb_data_len)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type(ValueError)  # 仅在抛出 ValueError 时才重试
    )
    def __iter__(self):
        for jsonl_loader in self._jsonl_loader_list:
            for jd in jsonl_loader:
                try:
                    img_arr = self._get_img_arr(jd)
                except:
                    continue

                yield img_arr, jd


class ImgJsonLoader(ImgArrayJDLoader):
    def __init__(self, root: Union[Path, str], img_parent: str = '', json_parent: str = ''):
        '''
        img与json最常见的两种结构：
            一种是它们放在同一个目录下 -> img_base为空字符串即可
            一种是它们的父级在同一个root下->需提供img_base
        :param root:
        :param img_parent:
        '''
        self.root = root
        self.img_parent = img_parent
        self.json_parent = json_parent
        self.json_paths = self._get_json_paths()
        self._index = 0
        self.cur_json_path = None

    def _get_sub_root(self, root: str) -> list:
        '''
        基于识别目录结构的统一性规范性，进行有条件的高效率递归。
        * 由于目录中，图像数据，json数据不会与sub_root在同一个层级，所以在某层级发现图像或者json时，及终止对该文件夹的递归遍历。避免对于大量图像json文件的遍历。
        *
        :param root:
        :param basenames:
        :return:
        '''

        basenames = (self.img_parent, self.json_parent)
        if not os.path.isdir(root):
            raise FileNotFoundError(f'{root}不是有效文件夹')
        sub_files = os.listdir(root)
        if not any(sub_file.endswith('.json') or sub_file.endswith('.jpg') for sub_file in sub_files):
            if all(root_name in sub_files for root_name in basenames):
                return [root]
            sub_roots = []
            for sub_file in sub_files:
                if os.path.isdir(sub_dir := os.path.join(root, sub_file)):
                    if ret := self._get_sub_root(sub_dir):
                        sub_roots.extend(ret)
            return sub_roots

    def _get_json_paths_recursive(self, sub_roots: list) -> list[Path]:
        '''
        确保图像和json一一对应。
        '''
        json_paths = []
        for sub_root in sub_roots:
            img_path_stems = {img_path.stem for img_path in (Path(sub_root) / self.img_parent).glob('*.jpg')}

            sub_json_paths = [json_path for json_path in (Path(sub_root) / self.json_parent).glob('*.json') if
                              json_path.stem in img_path_stems]
            json_paths.extend(sub_json_paths)

            print(f'{"/".join(Path(sub_root).parts[-3:])}---图像读取完毕,成对数据量：{len(sub_json_paths)}')
        return json_paths

    def _get_json_paths_iter(self):
        img_path_stems = {img_path.stem for img_path in Path(self.root).glob('*.jpg')}

        json_paths = [json_path for json_path in Path(self.root).glob('*.json') if
                      json_path.stem in img_path_stems]

        print(f'{"/".join(Path(self.root).parts[-3:])}---图像读取完毕,成对数据量：{len(json_paths)}')
        return json_paths

    def _get_img_path_by_json_path(self, json_path: Union[str, Path]) -> Path:
        json_path = Path(json_path)
        if self.img_parent:
            img_path = json_path.parent.with_stem(self.img_parent) / json_path.with_suffix('.jpg').name
        else:
            img_path = json_path.with_suffix('.jpg')
        return img_path

    def _get_json_paths(self) -> list:
        if self.img_parent and self.json_parent:

            sub_roots = self._get_sub_root(self.root)
            json_paths = self._get_json_paths_recursive(sub_roots)
        else:
            json_paths = self._get_json_paths_iter()
        return json_paths

    def _get_img_jd_by_json_path(self, json_path: Union[str, Path]):
        img_path = self._get_img_path_by_json_path(json_path)
        img_arr = cv2.imread(str(img_path))
        jd = load_json_to_dict(json_path)
        jd['image_path'] = os.path.basename(img_path)
        self.cur_json_path = json_path
        return img_arr, jd

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_result(lambda e: e[0] is None)
    )
    def choice(self):
        json_path = random.choice(self.json_paths)
        img_arr, jd = self._get_img_jd_by_json_path(json_path)

        return img_arr, jd

    def __iter__(self):
        return self

    def __next__(self):
        if self._index >= len(self.json_paths):
            raise StopIteration
        json_path = self.json_paths[self._index]
        img_arr, jd = self._get_img_jd_by_json_path(json_path)

        self._index += 1
        return img_arr, jd

    def __len__(self):
        return len(self.json_paths)


def lmdb_size_info(lmdb_path: str):
    with lmdb.open(lmdb_path, map_size=1) as env:
        cur_mapsize = env.info()['map_size']
        print('初始map_size', cur_mapsize)
        cur_mapsize += 10 ** 9
        env.set_mapsize(cur_mapsize)
        # 获取数据库的当前统计数据
        stats = env.stat()
        print("当前数据库统计信息:", stats)

        # 获取最大和已用数据库大小
        # 已使用大小应该包括叶子页、分支页和溢出页的总和
        used_size = stats['psize'] * (stats['branch_pages'] + stats['leaf_pages'] + stats['overflow_pages'])

        max_size = env.info()['map_size']  # 最大映射大小

        print("已使用大小 (bytes):", used_size)
        print("最大大小 (bytes):", max_size)

        # 计算剩余空间
        remaining_size = max_size - used_size
        print("剩余空间 (bytes):", remaining_size)


def lmdb_2_min_size(lmdb_path: str):
    # 以极小的尺寸打开，即可使文件大小变为刚好包裹数据的大小。
    with lmdb.open(lmdb_path, map_size=1):
        pass



if __name__ == '__main__':

    import pickle
    
    lmdbloader = LmdbLoader('/data2/data/_out_infinigen_posewriter_lv_1103_jj_with_base_multi_focal_length/_out_infinigen_posewriter_lv_1103_jj_with_base_multi_focal_length_train_lmdb')
    print(len(lmdbloader))
    for i in lmdbloader.iter_keys():
        print(i)

    # for i in lmdbloader:
    #     from matplotlib import pyplot as plt
    #     print(i[0])
    #     if i[0].decode()=='num-samples':
    #         print(i[1].decode())
        # else:
        #     s = pickle.loads(i[1])
            

        #     img_arr = img_byte_to_arr(s['img'])
        #     plt.imshow(img_arr)
        #     plt.show()
