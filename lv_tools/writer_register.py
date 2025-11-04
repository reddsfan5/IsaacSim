import json
import os
import pickle
import random
import traceback
import cv2

import numpy as np
from lv_tools.centerpose_to_alva import add_cuboid_27, add_vfov, draw_projected_keypoints, is_ann_valid,calculate_vfov
from lv_tools.cores.img_io import cv2imwrite
from lv_tools.cores.json_io import save_json

from omni.replicator.core.writers import Writer
from omni.replicator.core.annotators import AnnotatorRegistry
from omni.replicator.core.writers_default import BasicWriter
from isaacsim.replicator.writers import PoseWriter
from lv_tools.dataset_io.data_saver import LmdbSaver
from pprint import pprint
import PIL
import io


def normalize_bbox(img_h, img_w, xmin, ymin, xmax, ymax):
    """
    将边界框的像素坐标转换为归一化参数（xcenter, ycenter, box_w, box_h）。
    
    返回:
        tuple: 归一化后的参数 (xcenter, ycenter, box_w, box_h)，均为float类型。
    """
    # 计算归一化中心点坐标
    xcenter = (xmin + xmax) / (2 * img_w)
    ycenter = (ymin + ymax) / (2 * img_h)
    
    # 计算归一化边界框宽高
    box_w = (xmax - xmin) / img_w
    box_h = (ymax - ymin) / img_h
    
    return (xcenter, ycenter, box_w, box_h)


def img_arr_to_bytes(img_arr:np.ndarray):

    img_pil = PIL.Image.fromarray(img_arr)
    img_pil = img_pil.convert('RGB')
    f = io.BytesIO()
    img_pil.save(f, format='JPEG',quality=90)
    img_bin = f.getvalue()
    return img_bin


class LMDBWriter(PoseWriter):
    BOUNDING_BOX_2D = 'bounding_box_2d_tight_fast'
    SEMANTIC_SEGMENTATION = 'semantic_segmentation'


    def __init__(self,cache_capacity:int=10,
                 truncation_ratio:float=.5,
                 visibility_ratio:float=.5,
                 rotate_threshold:float=90,
                 show_bin:int=1000,
                 *args,**kwargs):
        self._output_dir = kwargs.get('output_dir','')
        _train_lmdb_path = self._output_dir+f'/{os.path.basename(self._output_dir)}_train_lmdb'
        _val_lmdb_path = self._output_dir+f'/{os.path.basename(self._output_dir)}_val_lmdb'
        self._truncation_ratio = truncation_ratio
        self._visibility_ratio = visibility_ratio
        self._rotate_threshold = rotate_threshold

        self._train_saver = LmdbSaver(_train_lmdb_path,cache_capacity)
        self._val_saver = LmdbSaver(_val_lmdb_path,cache_capacity)
        self._show_bin = show_bin
        self._val_count = 0
        self._train_count = 0


        # semantic_segmentation = kwargs.pop('semantic_segmentation',False)
        # bounding_box_2d_tight = kwargs.pop('bounding_box_2d_tight',False)

        # self.colorize_semantic_segmentation = kwargs.pop('colorize_semantic_segmentation',True)

        super().__init__(*args,**kwargs)

        # if bounding_box_2d_tight:
        self.annotators.append(self.BOUNDING_BOX_2D)
        
        # Semantic Segmentation
        # if semantic_segmentation:
        self.annotators.append(
            AnnotatorRegistry.get_annotator(
                self.SEMANTIC_SEGMENTATION, init_params={"colorize": False}
            )
        )

    def _get_init_info(self,label:str,points_27:list,scale:float=1):
        init_info = {
            # 当前批次数据类别列表
            "classNames": [label],
            "classLabels": {
            # 类别数据信息
            label: {
                # 类别id -- id序列与类别列表顺序一致
                "Label": 0,
                # 3d模型初始位姿的第0 和26 个点坐标
                "ModelBox": [*points_27[0],*points_27[-1]],
                "Scale": scale,
                # 3d 模型初始位姿
                "Point3Ds": points_27,
                # 3d模型初始位姿视图矩阵 -- 默认单位制 -- 一般不需要改
                "Views": [
                [
                    1.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    1.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    1.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    1.0
                ]
                ],
                "ModelType": "",
                # 是否为等比模型
                "equalPhysicalSize": False,
                "ModelPath": "",
                "isProportionalSize": False if scale == 1 else True,
                    }
                },
                "ProjectName": ""
                }
        return init_info


    def _get_idToLabels(self,idToLabels_ori:dict):
        idToLabels = {}
        for k,v in idToLabels_ori.items():
            idToLabels[k] = v['class']

        return idToLabels
    

    def _cal_labelToIds(self,idToLabels:dict):
        labelToIds = {}
        for k,v in idToLabels.items():
            labelToIds[v] = k
        return labelToIds




    def write(self,data:dict):
                # Iterate over the render products
        for rp_name, annotators_data in data["renderProducts"].items():

            # Process the frame data of the current render product
            bounding_box_3d_data = annotators_data[self.BB3D_ANNOT_NAME]
            camera_params_data = annotators_data[self.CAM_PARAMS_ANNOT_NAME]
            num_objs = self._process_frame_data(bounding_box_3d_data, camera_params_data)
            
            bounding_box_2d_data = annotators_data[self.BOUNDING_BOX_2D]
            self._frame_data[self.BOUNDING_BOX_2D] = bounding_box_2d_data

            semantic_seg_data = annotators_data[self.SEMANTIC_SEGMENTATION]
            self._frame_data[self.SEMANTIC_SEGMENTATION] = semantic_seg_data


            # Early exist if empty frames should not be written
            if self._skip_empty_frames and num_objs == 0:
                continue

            # Create render product name subfolder if data should be separated for each render product
            rp_subfolder = f"{rp_name}/" if self._use_subfolders else ""
            
            rgb_data = annotators_data[self.RGB_ANNOT_NAME]["data"]


            if not is_ann_valid(self._frame_data, truncation_ratio=self._truncation_ratio, visibility_ratio=self._visibility_ratio,rotate_threshold=self._rotate_threshold):
                continue 
            add_cuboid_27(self._frame_data)
            add_vfov(self._frame_data)
            img_bin = img_arr_to_bytes(rgb_data)

            data_dict = {'img':img_bin}


            # bbox 2d
            seg_id_to_labels = self._get_idToLabels(semantic_seg_data['idToLabels'])
            seg_label_to_ids = self._cal_labelToIds(seg_id_to_labels)


            data_dict['label']=seg_label_to_ids

            box_2d_id_to_labels = self._get_idToLabels(bounding_box_2d_data['idToLabels'])

            
            bboxs_2d_normed = []
            
            for bbox in bounding_box_2d_data['data'].tolist():
                id_box = int(seg_label_to_ids[box_2d_id_to_labels[bbox[0]]])
                
                img_w,img_h = self._frame_data['camera_data']['resolution']
                bbox_normalized = normalize_bbox(img_h,img_w,*bbox[1:-1])
                bboxs_2d_normed.append([id_box,*bbox_normalized])

            data_dict['bounding_box_2d_tight_fast'] = bboxs_2d_normed


            # seg data
            seg_arr = semantic_seg_data['data']
            seg_bin = img_arr_to_bytes(seg_arr)

            data_dict['semantic_segmentation'] = seg_bin



            # bbox 3d

            bbox_3ds = []

            for obj in self._frame_data['objects']:
                label_id = seg_label_to_ids[obj['label']]
                bbox_3ds.append([int(label_id),*obj['cuboid_27_screen']])

            data_dict['cuboid_27_screen'] = bbox_3ds



            pickle_bytes = pickle.dumps(data_dict)

            if self._val_count<30 and random.uniform(0,1)<0.01:
                self._val_saver.put(str(self._val_count).zfill(10).encode('utf8'),pickle_bytes)
                self._val_count += 1
            else:

                self._train_saver.put(str(self._train_count).zfill(10).encode('utf8'),pickle_bytes)
                self._train_count += 1
            




            # show samples

            if int(self._frame_id)%self._show_bin==0:
                try:
            
                    show_dir = os.path.join(self._output_dir,'samples')
                    if not os.path.exists(show_dir):
                        os.mkdir(show_dir)
                    
                    img_ori_path = os.path.join(show_dir,str(self._frame_id).zfill(10)+'.jpg')
                    img_draw_path = os.path.join(show_dir,str(self._frame_id).zfill(10)+'_overlay.jpg')
                    bgr_data = cv2.cvtColor(rgb_data,cv2.COLOR_RGB2BGR)
                    pil_img = PIL.Image.fromarray(bgr_data)
                    draw = PIL.ImageDraw.Draw(pil_img)

                    keypoints = self._frame_data['objects'][0]['cuboid_keypoints_projected']
                    draw_projected_keypoints(draw,keypoints)
                    cv2imwrite(img_ori_path,bgr_data)
                    cv2imwrite(img_draw_path,np.array(pil_img))


                    data_dict['rotation_matrix_camera_frame'] = self._frame_data['objects'][0]['rotation_matrix_camera_frame']
                    data_dict['rotation_matrix_world_frame'] = self._frame_data['objects'][0]['rotation_matrix_world_frame']
                    data_dict['location_camera_frame'] = self._frame_data['objects'][0]['location_camera_frame']
                    data_dict['size'] = self._frame_data['objects'][0]['size']

                    data_dict['vfov'] = self._frame_data['camera_data']['vfov']

                    data_dict.pop('img')
                    data_dict.pop('semantic_segmentation')

                    save_json(img_ori_path[:-4]+'.json',data_dict)
                except:
                    traceback.print_exc()
            
            
            self._frame_id += 1
            
            
            init_config_file_path = os.path.join(self._output_dir,'config.json')
            if not os.path.exists(init_config_file_path):

                label = self._frame_data['objects'][0]['label']
                points_27 = self._frame_data['objects'][0]['cuboid_27_world']
                scale = self._frame_data['objects'][0]['local_to_world_transform'][0][0]
                init_info = self._get_init_info(label,points_27,scale)

                
                # placeholder for deploy: 我们的项目依赖这个配置
                init_info['vfov'] = round(self._frame_data['camera_data']['vfov'], 2)

            
                with open(init_config_file_path,mode='w',encoding='utf8') as f:
                    json.dump(init_info,f)

                




