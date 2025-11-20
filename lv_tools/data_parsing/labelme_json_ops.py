import json
import os
import re
import shutil
from os import path as osp
from pathlib import Path

import cv2
import numpy as np
from loguru import logger
from tqdm import tqdm

if __name__ == '__main__':
    __package__ = 'src.lv_tools.data_parsing'
from ..cores.file_ops import get_specific_file_paths, make_dir
from ..cores.json_io import load_json_to_dict, save_json
from ..cores.poly_ops import rectangle2points, points_resize, polygon_normalization, poly_area, Polygon4
from ..file_tools.file_ops import get_corresponding_img_path, mask_by_rec_box, single_out
from ..file_tools.renamer import filter_filename
from ..data_parsing.labelme_json_constructor import construct_one_shape, construct_labelme_jd

'''
labelme_json的几个要点：
1.shapes中shape的
    points : List[List[Union[int,float]]]
    label : str
    shape_type : 'polygon', 'rectangle', 'circle', 'line' ,'linestrip', 'point'
是三个常修改的对象。

2.图像的掩码操作。

3.imageHeight,imageWidth

4.imageData：图片读取到json 中变为 b64, 读取b64写出为图片。labelme.utils中有相关函数。
'''

JSON_SUFFIX = '.json'


def gen_empty_json_by_img(img_dir: str):
    img_paths = Path(img_dir).glob('*.jpg')
    for img_path in tqdm(img_paths):
        json_path = img_path.with_suffix('.json')
        # img_arr1 = cv2.imdecode(np.fromfile(str(img_path),dtype=np.uint8),-1) # 图像用windows右键方式旋转后，这种方式读到的img是未旋转的
        img_arr = cv2.imread(str(img_path))
        h, w = img_arr.shape[:2]
        img_name = img_path.name
        jd = construct_labelme_jd([], img_name, h, w)
        save_json(json_path, jd)


def pyramid_label_img(img_dir: str, label: str = ''):
    img_paths = [file_path for file_path in Path(img_dir).glob('**/*') if file_path.suffix in ('.png', '.jpg')]

    box_size_retio = {'min': .5, 'mid': .75, 'max': 1, 'corner': .75}
    for img_path in tqdm(img_paths):
        json_path = img_path.with_suffix(JSON_SUFFIX)
        img_arr = cv2.imread(str(img_path))
        h, w = img_arr.shape[:2]
        shapes = []
        for box_scale in ['min', 'mid', 'max']:
            box_h = h * box_size_retio[box_scale]
            box_w = w * box_size_retio[box_scale]
            xs = int(w / 2 - box_w / 2)
            ys = int(h / 2 - box_h / 2)
            points = [[xs, ys], [xs + box_w, ys + box_h]]
            shape = construct_one_shape(label, points)
            shapes.append(shape)
        imagePath = img_path.name
        imageHeight = h
        imageWidth = w
        jd = construct_labelme_jd(shapes, imagePath, imageHeight, imageWidth)

        with open(json_path, mode='w', encoding='utf8') as f:
            json.dump(jd, f)


def remove_specific_box(json_path, dst_dir, rm_label:tuple=('mask',)):
    jd = load_json_to_dict(json_path)
    new_shapes = []
    for shape in jd['shapes']:
        if shape['label'] not in rm_label:
            new_shapes.append(shape)
    jd['shapes'] = new_shapes
    save_json(osp.join(dst_dir, osp.basename(json_path)), jd)


def json_name2json_file(json_dir: str, img_suffix: str = '.png'):
    json_paths = get_specific_file_paths(json_dir, suffixs=('.json',))
    for json_path in tqdm(json_paths):
        print(json_path)
        jd = load_json_to_dict(str(json_path))
        jd['imagePath'] = json_path.with_suffix(img_suffix).name
        save_json(str(json_path), jd)


def leave_out_no_bbox_pairs(data_root: str):
    '''
    移除掉没有标注框的json
    '''
    dst_dir = data_root + '_no_bbox'
    if not os.path.exists(dst_dir):
        os.mkdir(dst_dir)
    json_paths = get_specific_file_paths(data_root, (JSON_SUFFIX,))
    for json_path in tqdm(json_paths):
        if json_path.exists() and not load_json_to_dict(str(json_path))['shapes']:
            # print(json_path)
            shutil.move(json_path, osp.join(dst_dir, json_path.name))
            img_path = json_path.with_suffix('.jpg')
            if img_path.exists():
                shutil.move(img_path, osp.join(dst_dir, img_path.name))


def json_rec_2_poly(root):
    json_file_paths = get_specific_file_paths(root, (JSON_SUFFIX,))
    for json_file_path in json_file_paths:
        jd = load_json_to_dict(str(json_file_path))
        new_shapes = []
        for shape in jd['shapes']:
            if shape['shape_type'] == 'rectangle':
                shape['points'] = rectangle2points(shape['points'])
                shape['shape_type'] = 'polygon'
                new_shapes.append(shape)
            else:
                new_shapes.append(shape)
        jd['shapes'] = new_shapes
        with open(json_file_path, mode='w', encoding='utf8') as f:
            json.dump(jd, f)


def labelme_shapes_merge(src_dir1, src_dir2, dst_dir):
    json_paths1 = list(Path(src_dir1).glob('**/*.json'))
    json_paths2 = list(Path(src_dir2).glob('**/*.json'))
    if not osp.exists(dst_dir):
        os.mkdir(dst_dir)
    for json_path in tqdm(json_paths1):
        jd1 = load_json_to_dict(str(json_path))
        if (json_path2 := Path(src_dir2) / json_path.name) in json_paths2:
            json_paths2.remove(json_path2)
            jd2 = load_json_to_dict(json_path2)
            jd1['shapes'].extend(jd2['shapes'])
        with open(osp.join(dst_dir, json_path.name), mode='w', encoding='utf8') as f:
            json.dump(jd1, f)
    for json_path in json_paths2:
        shutil.copy(str(json_path), osp.join(dst_dir, json_path.name))


def find_out_json_without_group_id(root: str, dst_dir: str):
    # 直接搜索所有.json文件
    json_paths = Path(root).rglob('*.json')
    dst_path = Path(dst_dir)

    for json_path in json_paths:
        jd = load_json_to_dict(str(json_path))
        # 使用any来判断是否所有shapes都没有group_id
        if not any(shape['group_id'] for shape in jd.get('shapes', [])):
            shutil.move(json_path, dst_path / json_path.name)
            jpg_path = json_path.with_suffix('.jpg')
            shutil.move(jpg_path, dst_path / jpg_path.name)


def remove_box_around_white_space(root):
    json_paths = [json_path for json_path in Path(root).glob('**/*.json')]
    for json_path in tqdm(json_paths):
        jd = load_json_to_dict(str(json_path))
        img_path = get_corresponding_img_path(json_path)
        if not img_path:
            continue
        img_arr = cv2.imdecode(np.fromfile(str(img_path), dtype=np.uint8), 1)
        new_shapes = []
        for shape in jd['shapes']:

            points = shape['points']
            rect = cv2.minAreaRect(np.array(points).astype(np.float32).reshape((-1, 1, 2)))
            points = cv2.boxPoints(rect)
            if len(points) < 4:
                continue
            dst = [[0, 0], [200, 0], [200, 200], [0, 200]]
            M = cv2.getPerspectiveTransform(np.array(points, dtype=np.float32), np.array(dst, dtype=np.float32))

            distorted = cv2.warpPerspective(img_arr, M, (200, 200))
            count = np.bincount(distorted[..., 0].flatten())
            if len(count) > 255 and count[-1] / sum(count) > .6:
                logger.info(f'发现白色框：{json_path}')
            else:
                new_shapes.append(shape)
        jd['shapes'] = new_shapes
        with open(str(json_path), mode='w', encoding='utf8') as f:
            json.dump(jd, f)


def processing_manu_labeled_data(ori, dst):
    '''
    1.mask涂抹
    2.移除mask覆盖的标注框和mask
    4.移走单独的json或单独的img

    :return:
    '''

    mask_by_rec_box(ori)
    remove_box_around_white_space(ori + '_with_mask')
    single_out(ori, dst)

def rm_small_bbox(jd:dict,min_area=2000):
    if not jd.get('shapes'):
        return jd
    new_shapes = []
    for shape in jd['shapes']:
        points = shape['points']
        if len(points) <4:
            continue
        if poly_area(points) > min_area:
            new_shapes.append(shape)
    jd['shapes'] = new_shapes
    return jd







def rename_pairs_by_labels(json_dir: str, dst_dir: str):
    if not os.path.exists(dst_dir):
        os.mkdir(dst_dir)
    json_files = Path(json_dir).rglob('*.json')
    for json_file_path in tqdm(json_files):
        img_file_path = json_file_path.with_suffix('.jpg')
        if not img_file_path.exists():
            continue
        jd = load_json_to_dict(json_file_path)
        if not jd.get('shapes'):
            continue
        # print([shape['label'] for shape in jd['shapes']])
        label_str = '_'.join([filter_filename(shape['label']) for shape in jd['shapes']])
        # 将连续的多个下划线替换为一个下划线
        label_str = re.sub(r'_+', '_', label_str)
        # 如果下划线出现在文件名的开头或结尾，移除它们
        label_str = label_str.strip('_')
        if not (dst_sub := Path(os.path.join(dst_dir, img_file_path.parent.name))).exists():
            dst_sub.mkdir(parents=True, exist_ok=True)

        shutil.copy(img_file_path, dst_sub / (label_str + '.jpg'))
        shutil.copy(json_file_path, dst_sub / (label_str + '.json'))

def get_boxes(json_path):
    jd = load_json_to_dict(json_path)
    boxes = [shape['points'] for shape in jd['shapes']]

    return boxes

def json_points_resize(template_jd: dict,dst_hw:tuple):
    h, w = template_jd['imageHeight'], template_jd['imageWidth']
    # ⭐对目标书籍的大小进行限制，并修改对应json相关信息,掠过索书号，给下一阶段去贴
    bg_h,bg_w = dst_hw
    h_ratio, w_ratio = bg_h / h, bg_w / w
    new_shapes = []
    for info_index in range(len(template_jd['shapes'])):
        shape = template_jd['shapes'][info_index]
        shape['points'] = points_resize(shape['points'], (w_ratio, h_ratio))
        new_shapes.append(shape)
    template_jd['shapes'] = new_shapes
    template_jd['imageHeight'], template_jd['imageWidth'] = bg_h, bg_w


def mark_exception_group_id_for_textinfo_class(root: str, legal_group_id=(
'0主标题', '1副标题', '2分辑号', '3版本', '4丛书项', '5作者', '6出版社', '7索书号',
'8杂项')):
    json_paths = Path(root).glob('*.json')
    for json_path in tqdm(json_paths):
        jd = load_json_to_dict(json_path)
        if not jd.get('shapes'):
            continue
        for shape in jd['shapes']:
            if shape['group_id'] not in legal_group_id:
                shape['group_id'] = '*' * 10
        save_json(json_path, jd)


def json_points_order_rectify(json_root:str):
    json_paths = Path(json_root).rglob('*.json')
    for json_path in tqdm(json_paths):
        jd = load_json_to_dict(str(json_path))
        for shape in jd['shapes']:
            shape['points'] = polygon_normalization(shape['points'])
        save_json(str(json_path),jd)


def rm_small_box_batch(json_root:str):
    for json_path in tqdm(Path(json_root).rglob('*.json')):
    #
        jd = load_json_to_dict(json_path)
        jd = rm_small_bbox(jd,min_area=10000)
        save_json(json_path,jd)




def rm_bbox_with_low_score(json_root:str, rm_label_score_threshold:float=.9,rm_bbox_score_threshold:float=.82):
    for json_path in tqdm(Path(json_root).rglob('*.json')):
        jd = load_json_to_dict(json_path)
        new_shapes = []
        for shape in jd['shapes']:
            if shape['group_id'] < rm_bbox_score_threshold:
                continue
            if shape['group_id'] < rm_label_score_threshold:
                shape['label'] = 'bar'
            new_shapes.append(shape)

        jd['shapes'] = new_shapes
        save_json(json_path,jd)

def low_avg_score(jd:dict,threshold:float = .5):
    count = 0
    scores = []
    for shape in jd['shapes']:
        group_id = 0 if shape.get('group_id') is None else shape.get('group_id')
        if group_id < threshold:
            count +=1
        scores.append(group_id)
    avg_score = sum(scores)/(len(scores)+1e-8)
    return count,avg_score






if __name__ == '__main__':


    # json_paths = get_specific_file_paths(root,
    #                                      suffixs=('.json',))

    # single_out(root)
    dst_dir = r'D:\lxd_code\bar_dm\dm_bar_base\indoorCVPR_09\Images_bbox_text'
    # make_dir(dst_dir)
    # for json_path in json_paths:
    #     jd = load_json_to_dict(json_path)
    #     if jd.get('shapes') and any(shape['label'] for shape in jd.get('shapes')):
    #         shutil.move(json_path,os.path.join(dst_dir,json_path.name))

    json_root = r'F:\dataset\OCR\1.book_det\horizontal'
    # json_points_order_rectify(json_root)

    #     new_shapes = []
    #     for shape in jd['shapes']:
    #         shape['label'] = 'BAR'
    #         new_shapes.append(shape)
    #     jd['shapes'] = new_shapes
    #     save_json(str(json_path), jd)


    # rename_pairs_by_labels(r'F:\dataset\OCR\3.text_rec\need_multi_core_rec\1_1_PhoneScan_Normalization\zhongkeda_phoneScan_norm\book_info_classes_2024-09-12\book_info_classes_zhongkeda',
    #                        r'F:\dataset\OCR\3.text_rec\need_multi_core_rec\1_1_PhoneScan_Normalization\zhongkeda_phoneScan_norm\book_info_classes_2024-09-12_renamed')

    # single_out(r'F:\dataset\OCR\2.text_det\20250603_220000_6f70_check_data\v2\ori_img')
    # leave_out_no_bbox_pairs(r'D:\lxd_code\OCR\OCR_SOURCE\bg\bg_ori')
    json_name2json_file(r'\\192.168.1.183\数维_内部\吕晓东\orbbec\1113_checked_from_problem',img_suffix='.jpg')
    # empty_json_by_qimg(r'D:\dataset\layer_board_det\3_robot\close_up_data_jintan\qiye_jintan\qiye_1_4\1_4\0314_no_ver_sampled_per_8')
    dst = r'F:\dataset\OCR\1.book_det\rotate\20250618-tongjidaxue_horizontal_data-single'
    # processing_manu_labeled_data(ori,dst)

    # json_root = r'F:\dataset\OCR\1.book_det\rotate\tongjidaxue_book_det\xbot10b-241112-001-010\0618_v1_check_data\p2'
    # rm_small_box_batch(json_root)
    # json_points_order_rectify(r'F:\dataset\OCR\1.book_det\test_on_train_data\test')

    # json_paths = Path(r'F:\dataset\OCR\3.text_rec\foreign_language\korean\korean').rglob('*.json')
    # for json_path in json_paths:
    #
    #     remove_specific_box(str(json_path),
    #                         dst_dir = r'F:\dataset\OCR\3.text_rec\foreign_language\korean\dst',
    #                         rm_label=('bar',))

    # remove_specific_box(r'F:\dataset\OCR\3.text_rec\foreign_language\korean\test\33fe2a0513b2650a4b26f416bc1710f.json',dst_dir=r'F:\dataset\OCR\3.text_rec\foreign_language\korean\test\ret',
    #                     rm_label=('',' '))
    # rm_bbox_with_low_score(r'F:\dataset\OCR\3.text_rec\foreign_language\korean\250731',rm_bbox_score_threshold=.82)

    # json_root = r'F:\dataset\OCR\2.text_det\manu_done\shujutang\shujutang_zoubo_detbox_check\shujutang_train_new\v6'
    # dst_root = Path(json_root).parent
    #
    # for json_path in Path(json_root).rglob('*.json'):
    #     jd = load_json_to_dict(json_path)
    #     low_num,avg = low_avg_score(jd,.5)
    #     sub_base = low_num//10*10
    #     dst_dir = dst_root / str(sub_base)
    #     if not dst_dir.exists():
    #         dst_dir.mkdir(parents=True,exist_ok=True)
    #     if sub_base>30:
    #         shutil.move(json_path,dst_dir/json_path.name)
    #         shutil.move(json_path.with_suffix('.jpg'),dst_dir/json_path.with_suffix('.jpg').name)
    #
    #     print(f'{json_path.stem}-----,{low_num}-----,{avg}')
