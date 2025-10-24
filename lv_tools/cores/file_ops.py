import os
import shutil
from pathlib import Path
from typing import Tuple, Generator, Union, Iterator

'''
原则上，cores里的模块，不依赖项目中的其它模块，也就无需导入项目中的其它模块。（避免循环依赖） -》 只有上下级安排导入，同级不安排导入，在设计上就避免了循环依赖。
'''


def get_specific_file_paths(root: Union[str, Path], suffixs: Tuple[str, ...] = None) -> Iterator[Path]:
    '''
    递归查找目录下特定后缀的文件，返回Path对象列表
    此处返回生成器存在无限递归的风险，如果在root下创建目录树，就会导致无限递归。
    '''
    if not root:
        return (x for x in [])
    root = Path(root)

    if suffixs:
        file_paths = (file_path for file_path in root.glob('**/*') if file_path.suffix in suffixs)
    else:
        file_paths = (file_path for file_path in root.glob('**/*'))
    return file_paths


def make_dir(dir_path: Union[str, Path]):
    dir_path = Path(dir_path)
    if not dir_path.exists():
        dir_path.mkdir(parents=True, exist_ok=True)


def copy_folder(source_folder, destination_folder, exclude_folders=[]):
    '''
    保持目录结构的同时，选择性拷贝root下的内容。使用exclude_folders排除某些文件夹。

    :param source_folder:
    :param destination_folder:
    :param exclude_folders:
    :return:
    '''
    # 确保目标文件夹存在
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)

    # 遍历源文件夹下的所有内容
    for item in os.listdir(source_folder):
        source_item = os.path.join(source_folder, item)
        destination_item = os.path.join(destination_folder, item)

        # 如果是文件夹，递归调用自身
        if os.path.isdir(source_item):
            # 检查是否需要排除该文件夹
            if item in exclude_folders:
                continue
            copy_folder(source_item, destination_item, exclude_folders)
        else:
            # 如果是文件，复制到目标文件夹
            shutil.copy2(source_item, destination_folder)

def get_sub_root(root,root_names=('ori_img', 'final_alva_json')) -> list:
    '''
    基于识别目录结构的统一性规范性，进行有条件的高效率递归。
    * 由于目录中，图像数据，json数据不会与sub_root在同一个层级，所以在某层级发现图像或者json时，及终止对该文件夹的递归遍历。避免对于大量图像json文件的遍历。
    *
    :param root:
    :param root_names:
    :return:
    '''
    if not os.path.isdir(root):
        raise FileNotFoundError(f'{root}不是有效文件夹')
    sub_files = os.listdir(root)
    if not any(sub_file.endswith('.json') or sub_file.endswith('.jpg') for sub_file in sub_files):
        if all(root_name in sub_files for root_name in root_names):
            return [root]
        sub_roots = []
        for sub_file in sub_files:
            if os.path.isdir(sub_dir := os.path.join(root, sub_file)):
                if ret := get_sub_root(sub_dir):
                    sub_roots.extend(ret)
        return sub_roots
    
    
if __name__ == '__main__':
    # 示例用法
    source_folder = r'D:\dataset\merge_data\ImageAlign'
    destination_folder = r'D:\dataset\merge_data\dst'
    exclude_folders = ['splitResult']
    copy_folder(source_folder, destination_folder, exclude_folders)
