import json
import math
import os
import pickle
import random
import traceback
from typing import Dict, List,Union
import cv2
import time
from datetime import datetime
import numpy as np
from lv_tools.centerpose_to_alva import add_cuboid_27, add_vfov, draw_projected_keypoints, is_ann_valid,calculate_vfov,calculate_kps_based_on_world_file
from lv_tools.cores.img_io import cv2imwrite, img_byte_to_arr
from lv_tools.cores.json_io import load_json_to_dict, save_json
from lv_tools.data_parsing.labelme_json_constructor import construct_labelme_jd,construct_one_shape
from omni.replicator.core.scripts.functional import write_image, write_json
from omni.replicator.core.annotators import AnnotatorRegistry
# from omni.replicator.core.writers import Writer
# from omni.replicator.core.writers_default import BasicWriter
from isaacsim.replicator.writers import PoseWriter
from lv_tools.dataset_io.data_saver import LmdbSaver

import PIL
import io

def construct_one_shape(label: Union[str, int], points: list, group_id: int = None, shape_type: str = None,
                        **kwargs) -> dict:
    if not shape_type:
        if len(points) == 2:
            shape_type = 'rectangle'
        else:
            shape_type = 'polygon'

    return {
        "label": label,
        "points": points,
        "group_id": group_id,
        "shape_type": shape_type,
        "flags": {
        },
        **kwargs
    }

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


def visualize_depth_gray(depth: np.ndarray, min_depth=None, max_depth=None):
    depth_vis = depth.copy()

    # 过滤无效值
    valid_mask = np.isfinite(depth_vis) & (depth_vis > 0)

    if not np.any(valid_mask):
        return np.zeros(depth_vis.shape, dtype=np.uint8)

    if min_depth is None:
        min_depth = depth_vis[valid_mask].min()
    if max_depth is None:
        max_depth = depth_vis[valid_mask].max()

    depth_vis = np.clip(depth_vis, min_depth, max_depth)
    depth_vis = (depth_vis - min_depth) / (max_depth - min_depth + 1e-8)
    depth_vis = (depth_vis * 255).astype(np.uint8)

    depth_vis[~valid_mask] = 0
    return depth_vis




class LabelRegistry:
    def __init__(self):
        self.label_to_id: Dict[str, int] = {}
        self.id_to_label: List[str] = []

    def get_or_add(self, label: str) -> int:
        if not isinstance(label, str):
            raise TypeError(f"label must be str, got {type(label)}")

        label = label.strip()

        if not label:
            raise ValueError("label cannot be empty")

        if label in self.label_to_id:
            return self.label_to_id[label]

        label_id = len(self.id_to_label)
        self.label_to_id[label] = label_id
        self.id_to_label.append(label)

        return label_id

    def get_id(self, label: str) -> int:
        return self.label_to_id[label]

    def get_label(self, label_id: int) -> str:
        return self.id_to_label[label_id]

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.id_to_label, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> "LabelRegistry":
        registry = cls()

        with open(path, "r", encoding="utf-8") as f:
            registry.id_to_label = json.load(f)

        registry.label_to_id = {
            label: idx
            for idx, label in enumerate(registry.id_to_label)
        }

        registry.validate()

        return registry

    def validate(self):
        if len(self.label_to_id) != len(self.id_to_label):
            raise ValueError("label_to_id and id_to_label size mismatch")

        for idx, label in enumerate(self.id_to_label):
            if self.label_to_id.get(label) != idx:
                raise ValueError(
                    f"Inconsistent mapping: label={label}, "
                    f"id_to_label index={idx}, "
                    f"label_to_id value={self.label_to_id.get(label)}"
                )

    def __len__(self):
        return len(self.id_to_label)

    def __repr__(self):
        return f"LabelRegistry(num_labels={len(self)})"












def colorize_segmentation(seg: np.ndarray, id_to_color=None):
    """
    seg: HxW, 整型分割图
    return: HxWx3, uint8 彩色图
    """
    seg = np.asarray(seg)
    assert seg.ndim == 2, f"seg shape must be HxW, got {seg.shape}"

    h, w = seg.shape
    color_img = np.zeros((h, w, 3), dtype=np.uint8)

    ids = np.unique(seg)

    if id_to_color is None:
        rng = np.random.default_rng(12345)  # 固定随机种子，保证颜色稳定
        id_to_color = {}
        for i in ids:
            if i == 0:
                id_to_color[i] = (0, 0, 0)   # 背景黑色
            else:
                id_to_color[i] = tuple(rng.integers(0, 256, size=3).tolist())

    for i in ids:
        color_img[seg == i] = id_to_color[i]

    return color_img


def mask_to_rotated_box(mask: np.ndarray):
    """
    单实例 mask -> 最小外接旋转矩形
    返回:
        rect: ((cx, cy), (w, h), angle)
        box:  (4, 2) 四点
    """
    ys, xs = np.where(mask > 0)
    if len(xs) < 3:
        return None, None

    pts = np.stack([xs, ys], axis=1).astype(np.float32)
    rect = cv2.minAreaRect(pts)
    box = cv2.boxPoints(rect)
    # box = order_box_points_clockwise(box)
    return rect, box

def instance_seg_to_rotated_boxes(
    instance_seg: np.ndarray,
    min_mask_area: int = 50,
    min_fill_ratio: float = 0.2,
    max_aspect_ratio: float = 20.0,
    morph_open_kernel: int = 0,
    seg_id_occlusion:dict = {}
):
    """
    将实例分割图转为四点旋转框。

    参数:
        instance_seg: HxW, 每个像素是 instance id
        min_mask_area: 最小可见像素面积
        min_fill_ratio: mask_area / rotated_rect_area 的最小阈值
        max_aspect_ratio: 允许的最大长宽比，过细通常是严重遮挡/碎片
        morph_open_kernel: >0 时先做开运算去噪
    """
    seg = np.asarray(instance_seg)
    if seg.ndim == 3 and seg.shape[2] == 1:
        seg = seg[..., 0]

    if not seg_id_occlusion:

        unique_ids = np.unique(seg)
        unique_ids = {id:0 for id in unique_ids}

    else:
        unique_ids = seg_id_occlusion

    shapes = []

    for inst_id,occlusion in unique_ids.items():
        if inst_id == 0:
            continue  # 默认把 0 当背景

        mask = (seg == inst_id).astype(np.uint8)
        mask_area = int(mask.sum())

        if mask_area < min_mask_area:
            continue

        if morph_open_kernel > 0:
            kernel = np.ones((morph_open_kernel, morph_open_kernel), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask_area = int(mask.sum())
            if mask_area < min_mask_area:
                continue

        rect, box = mask_to_rotated_box(mask)
        if rect is None:
            continue

        (_, _), (w, h), angle = rect
        w = float(w)
        h = float(h)

        if w < 1e-6 or h < 1e-6:
            continue

        rect_area = w * h
        fill_ratio = mask_area / (rect_area + 1e-6)

        aspect_ratio = max(w, h) / (min(w, h) + 1e-6)

        # 近似过滤“严重遮挡/碎片”
        if fill_ratio < min_fill_ratio:
            continue
        if aspect_ratio > max_aspect_ratio:
            continue
        shapes.append(construct_one_shape(str(inst_id),box.tolist(),fill_ratio=float(fill_ratio),occlusion=occlusion,group_id=occlusion))

    return shapes














class LMDBWriter(PoseWriter):

    RGB_ANNOT_NAME = "rgb"
    CAM_PARAMS_ANNOT_NAME = "camera_params"
    CUBOID_KEYPOINTS_ORDER_DEFAULT = ["Center", "LDB", "LDF", "LUB", "LUF", "RDB", "RDF", "RUB", "RUF"]
    CUBOID_KEYPOINT_COLORS = ["white", "red", "green", "blue", "yellow", "cyan", "magenta", "orange", "purple"]
    CUBOID_EDGE_COLORS = {"front": "red", "back": "blue", "connecting": "green"}



    BB3D_ANNOT_NAME = "bounding_box_3d_fast"
    BOUNDING_BOX_2D = 'bounding_box_2d_tight_fast'
    SEMANTIC_SEGMENTATION = 'semantic_segmentation'


    def __init__(self,cache_capacity:int=10,
                 truncation_ratio:float=.5,
                 visibility_ratio:float=.5,
                 rotate_threshold:float=90,
                 show_bin:int=1000,
                 expect_data_num:int=10000,
                 task_id:str= '0000',
                 *args,**kwargs):
 
        self._output_dir = kwargs.get('output_dir','')
        self._truncation_ratio = truncation_ratio
        self._visibility_ratio = visibility_ratio
        self._rotate_threshold = rotate_threshold
        self._data_saver = LmdbSaver(self._output_dir,cache_capacity)
        self._show_bin = show_bin
        self._val_count = 0
        self._data_count = 0

        super().__init__(*args,**kwargs)

        self.annotators.append(self.BOUNDING_BOX_2D)
        
        self.annotators.append(
            AnnotatorRegistry.get_annotator(
                self.SEMANTIC_SEGMENTATION, init_params={"colorize": False}
            )
        )

    def _get_time_str(self):
        return datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H')


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


    @staticmethod
    def _xyz_to_thetaphi(x, y, z):
        '''
        Docstring for _xyz_to_thetaphi
        按照右手系，从+z到+x.
        X
        ↑
        |
        |
        |                  
        |                  
        O------------->Z


        '''

        r = math.sqrt(x*x + y*y + z*z)
        if r <= 0:
            raise ValueError("r must be > 0")

        # 极角 θ：与 +Y 轴夹角
        c = y / r
        c = max(-1.0, min(1.0, c))
        theta = math.acos(c)

        # 方位角 φ：绕 +Y，从 +Z向 +X
        s = math.sin(theta)
        if abs(s) < 1e-12:
            phi = 0.0
        else:
            phi = math.atan2(x, z)

        return theta, phi





    def camera_loc_on_sphere(self,center_target:tuple,camera_view_transform:np.ndarray):


        V = np.array(camera_view_transform).reshape(4,4)
        camera_loc = np.linalg.inv(V)[3, :3]   # 相机世界坐标（行向量约定）
        r = math.sqrt(sum([(camera_loc[i]-center_target[i])**2 for i in range(3)]))
        polar,yaw = self._xyz_to_thetaphi(camera_loc[0]-center_target[0],camera_loc[1]-center_target[1],camera_loc[2]-center_target[2])
        polar_deg = polar * 180 / math.pi
        yaw_deg = yaw * 180 / math.pi
        return polar_deg,yaw_deg,r


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
            data_dict = {}
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
            
            
            camera_view_transform = camera_params_data['cameraViewTransform']
            # bbox_3d_info = bounding_box_3d_data['data'][0]
            center_target = self._frame_data['objects'][0]['cuboid_keypoints_world_frame'][0]
            polar,azimuth,r = self.camera_loc_on_sphere(center_target,camera_view_transform)

            print(f'写入角度参数：polar:{round(polar,2)},azimuth:{round(azimuth,2)},radius:{round(r,2)}')

            latitude = 90-int(polar)

            # data_dict['camera_latitude_azimuth'] = (latitude,90-int(azimuth))
            data_dict['camera_latitude_azimuth'] = (latitude,int(azimuth))
            data_dict['camera_r'] = round(r,3)
            
            
            add_cuboid_27(self._frame_data)
            add_vfov(self._frame_data)
            img_bin = img_arr_to_bytes(rgb_data)

            data_dict['img'] = img_bin

            
            # bbox 2d
            normalized_id_to_labels = self._get_idToLabels(semantic_seg_data['idToLabels'])
            seg_label_to_ids = self._cal_labelToIds(normalized_id_to_labels)


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


            self._data_saver.put(str(self._data_count).zfill(10).encode('utf8'),pickle_bytes)
            self._data_count += 1
            if self._data_count%10==0:
                print(f'current training data num:[ {self._data_count}]')

            

            # show samples

            if int(self._frame_id)%self._show_bin==0:
                try:
            
                    show_dir = os.path.join(os.path.dirname(self._output_dir),'samples')
                    if not os.path.exists(show_dir):
                        os.mkdir(show_dir)
                    stem = str(int(azimuth))+"_"+str(self._frame_id).zfill(10)
                    img_ori_path = os.path.join(show_dir,stem+'.jpg')
                    img_draw_path = os.path.join(show_dir,stem+'_overlay.jpg')
                    # img_seg_path = os.path.join(show_dir,stem+'_seg.jpg')
                    bgr_data = cv2.cvtColor(rgb_data,cv2.COLOR_RGB2BGR)
                    pil_img = PIL.Image.fromarray(bgr_data)
                    draw = PIL.ImageDraw.Draw(pil_img)

                    keypoints = self._frame_data['objects'][0]['cuboid_keypoints_projected']

                    draw_projected_keypoints(draw,keypoints)


                    # seg = img_byte_to_arr(s['semantic_segmentation'])
                    # seg = np.where(seg==2,255,0).astype(np.uint8)
                    # ret = cv2.addWeighted(bgr_data, 0.5, seg, 0.5,0)

                    cv2imwrite(img_ori_path,bgr_data)
                    cv2imwrite(img_draw_path,np.array(pil_img))

                    # cv2imwrite(img_seg_path,ret)



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
            
            
            init_config_file_path = os.path.join(os.path.dirname(self._output_dir),'config.json')
            if not os.path.exists(init_config_file_path):

                label = self._frame_data['objects'][0]['label']
                points_27 = self._frame_data['objects'][0]['cuboid_27_world']
                scale = self._frame_data['objects'][0]['local_to_world_transform'][0][0]

                # 尺寸还原到初始尺寸，而不是场景中使用的尺寸。json中的scale只用作记录，不再用作还原
                # points_27 = (np.array(points_27)/scale).tolist()


                init_info = self._get_init_info(label,points_27,scale)

                
                # placeholder for deploy: 我们的项目依赖vfov
                init_info['vfov'] = round(self._frame_data['camera_data']['vfov'], 2)

            
                with open(init_config_file_path,mode='w',encoding='utf8') as f:
                    json.dump(init_info,f)

                

class KPSWriter(PoseWriter):
    def __init__(self,world_frame_kps_file_path,prifix,*args,**kwargs):
        self.kps_jd = load_json_to_dict(world_frame_kps_file_path)
        self.prifix = prifix
        super().__init__(*args,**kwargs)





    def write(self, data: dict):
        # Iterate over the render products
        for rp_name, annotators_data in data["renderProducts"].items():

            # Process the frame data of the current render product
            bounding_box_3d_data = annotators_data[self.BB3D_ANNOT_NAME]
            camera_params_data = annotators_data[self.CAM_PARAMS_ANNOT_NAME]
            # 确保主体存在
            num_objs = self._process_frame_data(bounding_box_3d_data, camera_params_data)

            # Early exist if empty frames should not be written
            if self._skip_empty_frames and num_objs == 0:
                continue

            # Create render product name subfolder if data should be separated for each render product
            rp_subfolder = f"{rp_name}/" if self._use_subfolders else ""

            
            
            shapes = []
            # save_center_from_posewriter_data(jd,dst_json_path)
            camera_jd = self._frame_data['camera_data']
            kps_screen = calculate_kps_based_on_world_file(camera_jd,self.kps_jd)
            for k,v in kps_screen.items():
                shapes.append(construct_one_shape(**{
                    'label':k,
                    'points':[v],
                    'shape_type':'point',
                }))

            shapes.sort(key=lambda x: int(x['label']))
            
            points = np.array([shape['points'][0] for shape in shapes])
            offset = 25

            x0,y0 = points[:,0].min()-offset,points[:,1].min()-offset
            x1,y1 = points[:,0].max()+offset,points[:,1].max()+offset

            shapes.append(construct_one_shape(label='bbox',points=[[int(x0),int(y0)],[int(x1),int(y1)]]))


            w,h = camera_jd["resolution"]
            # dst_json_path = os.path.join(dst_json_dir,os.path.basename(target_json_path))
            self._frame_data = construct_labelme_jd(shapes,'',h,w)
            
            
            
            
            # Write frame data to disk
            rgb_data = annotators_data[self.RGB_ANNOT_NAME]["data"]
            
            
            
            
            
            self._write_frame_data(rgb_data, rp_subfolder)
            if self._write_debug_images:
                self._write_debug_data(rgb_data, rp_subfolder)

            # If render products are NOT separated into subfolders increment the frame id after processing each render product
            if not self._use_subfolders:
                self._frame_id += 1

        # If render products are separated into subfolders increment the frame id after processing all render products
        if self._use_subfolders:
            self._frame_id += 1


    
    
    def _write_frame_data(self, rgb_data: dict, render_product_subfolder: str = ""):

        time_prefix = datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H')
        

        # Write image to disk
        rgb_file_path = f"{self.prifix}{render_product_subfolder}{time_prefix}{self._frame_id:0{self._frame_padding}}.jpg"
        self.backend.schedule(write_image, path=rgb_file_path, data=rgb_data)

        # Write frame data to as a JSON file
        file_path_json = rgb_file_path[:-4] + '.json'
        self._frame_data['imagePath'] = os.path.basename(rgb_file_path)
        
        self.backend.schedule(write_json, path=file_path_json, data=self._frame_data, indent=2)




class LMDBWriterMultiAssets(PoseWriter):

    RGB_ANNOT_NAME = "rgb"
    CAM_PARAMS_ANNOT_NAME = "camera_params"
    CUBOID_KEYPOINTS_ORDER_DEFAULT = ["Center", "LDB", "LDF", "LUB", "LUF", "RDB", "RDF", "RUB", "RUF"]
    CUBOID_KEYPOINT_COLORS = ["white", "red", "green", "blue", "yellow", "cyan", "magenta", "orange", "purple"]
    CUBOID_EDGE_COLORS = {"front": "red", "back": "blue", "connecting": "green"}



    BB3D_ANNOT_NAME = "bounding_box_3d_fast"
    BOUNDING_BOX_2D = 'bounding_box_2d_tight_fast'
    SEGMENTATION = 'instance_segmentation'
    DISTANCE_TO_IMAGE_PLANE = 'distance_to_image_plane'
    MORPH_POEN_KERNEL = 9




    def __init__(self,cache_capacity:int=10,
                 truncation_ratio:float=.5,
                 visibility_ratio:float=.5,
                 rotate_threshold:float=90,
                 show_bin:int=1000,
                 occlusion_threshold:float=0.5,
                 is_save_seg_info:bool=False,
                 task_id:str= '0000',
                 *args,**kwargs):
 
        self._label_registry = LabelRegistry()
        self._output_dir = kwargs.get('output_dir','')
        self._truncation_ratio = truncation_ratio
        self._visibility_ratio = visibility_ratio
        self._rotate_threshold = rotate_threshold
        self._occlusion_threshold = occlusion_threshold
        self._data_saver = LmdbSaver(self._output_dir,cache_capacity)
        self._is_save_seg_info = is_save_seg_info
        self._show_bin = show_bin
        self._val_count = 0
        self._data_count = 0


        self._init_info = {
        "classNames": [],
        "classLabels": {},
        "ProjectName": "",
}

        

        super().__init__(*args,**kwargs)

        self.annotators.append(self.BOUNDING_BOX_2D)
        self.annotators.append(self.DISTANCE_TO_IMAGE_PLANE)
        
        self.annotators.append(
            AnnotatorRegistry.get_annotator(
                self.SEGMENTATION, init_params={"colorize": False}
            )
        )

    def _get_time_str(self):
        return datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H')


    # def _get_init_info(self,label:str,points_27:list,scale:float=1):
        


    #     init_info = {
    #         # 当前批次数据类别列表
    #         "classNames": [label],
    #         "classLabels": {
    #         # 类别数据信息
    #         label: {
    #             # 类别id -- id序列与类别列表顺序一致
    #             "Label": 0,
    #             # 3d模型初始位姿的第0 和26 个点坐标
    #             "ModelBox": [*points_27[0],*points_27[-1]],
    #             "Scale": scale,
    #             # 3d 模型初始位姿
    #             "Point3Ds": points_27,
    #             # 3d模型初始位姿视图矩阵 -- 默认单位制 -- 一般不需要改
    #             "Views": [
    #             [
    #                 1.0,
    #                 0.0,
    #                 0.0,
    #                 0.0,
    #                 0.0,
    #                 1.0,
    #                 0.0,
    #                 0.0,
    #                 0.0,
    #                 0.0,
    #                 1.0,
    #                 0.0,
    #                 0.0,
    #                 0.0,
    #                 0.0,
    #                 1.0
    #             ]
    #             ],
    #             "ModelType": "",
    #             # 是否为等比模型
    #             "equalPhysicalSize": False,
    #             "ModelPath": "",
    #             "isProportionalSize": False if scale == 1 else True,
    #                 }
    #             },
    #             "ProjectName": ""
    #             }
    #     return init_info

    def _construct_label_info(self,label:str,points_27:list,views=[]):
        return {
                # 类别id -- id序列与类别列表顺序一致
                "Label": self._label_registry.get_or_add(label),
                # 3d模型初始位姿的第0 和26 个点坐标
                "ModelBox": [*points_27[0],*points_27[-1]],
                # "Scale": scale,
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
                ] if not views else views,
                "ModelType": "",
                # 是否为等比模型
                "equalPhysicalSize": False,
                "ModelPath": "",
                "isProportionalSize": False,
                    }



    def _get_init_info(self,label:str,points_27:list,scale:float=1,views=[]):
        

        


        init_info = {
            # 当前批次数据类别列表
            "classNames": self._label_registry.id_to_label,
            "classLabels": {
            # 类别数据信息
            label: {
                # 类别id -- id序列与类别列表顺序一致
                "Label": self._label_registry.get_or_add(label),
                # 3d模型初始位姿的第0 和26 个点坐标
                "ModelBox": [*points_27[0],*points_27[-1]],
                # "Scale": scale,
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
                ] if not views else views,
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


    @staticmethod
    def _xyz_to_thetaphi(x, y, z):
        '''
        Docstring for _xyz_to_thetaphi
        按照右手系，从+z到+x.
        X
        ↑
        |
        |
        |                  
        |                  
        O------------->Z


        '''

        r = math.sqrt(x*x + y*y + z*z)
        if r <= 0:
            raise ValueError("r must be > 0")

        # 极角 θ：与 +Y 轴夹角
        c = y / r
        c = max(-1.0, min(1.0, c))
        theta = math.acos(c)

        # 方位角 φ：绕 +Y，从 +Z向 +X
        s = math.sin(theta)
        if abs(s) < 1e-12:
            phi = 0.0
        else:
            phi = math.atan2(x, z)

        return theta, phi





    def camera_loc_on_sphere(self,center_target:tuple,camera_view_transform:np.ndarray):


        V = np.array(camera_view_transform).reshape(4,4)
        camera_loc = np.linalg.inv(V)[3, :3]   # 相机世界坐标（行向量约定）
        r = math.sqrt(sum([(camera_loc[i]-center_target[i])**2 for i in range(3)]))
        polar,yaw = self._xyz_to_thetaphi(camera_loc[0]-center_target[0],camera_loc[1]-center_target[1],camera_loc[2]-center_target[2])
        polar_deg = polar * 180 / math.pi
        yaw_deg = yaw * 180 / math.pi
        return polar_deg,yaw_deg,r


    def _get_idToLabels(self,idToLabels_ori:dict):
        idToLabels = {}
        for k,v in idToLabels_ori.items():
            idToLabels[k] = v['class']

        return idToLabels
    

    def _exchange_k_v(self,idToLabels:dict):
        
        return {v:k for k,v in idToLabels.items()}




    def write(self,data:dict):
                # Iterate over the render products
        for rp_name, annotators_data in data["renderProducts"].items():
            data_dict = {}
            # Process the frame data of the current render product
            bounding_box_3d_data = annotators_data[self.BB3D_ANNOT_NAME]
            camera_params_data = annotators_data[self.CAM_PARAMS_ANNOT_NAME]
            num_objs = self._process_frame_data(bounding_box_3d_data, camera_params_data)
            
            bounding_box_2d_data = annotators_data[self.BOUNDING_BOX_2D]
            self._frame_data[self.BOUNDING_BOX_2D] = bounding_box_2d_data

            seg_data = annotators_data[self.SEGMENTATION]
            self._frame_data[self.SEGMENTATION] = seg_data

            distancer_data = annotators_data[self.DISTANCE_TO_IMAGE_PLANE]
            self._frame_data[self.DISTANCE_TO_IMAGE_PLANE] = distancer_data
            with open('/data2/logs/log/log.txt', 'a') as f:

                f.write(f'[bounding_box_2d]---{bounding_box_2d_data["idToLabels"]}\n')
                f.write(f'[bounding_box_3d]---{bounding_box_3d_data["idToLabels"]}\n')
                f.write(f'[seg_data]---{seg_data["idToSemantics"]}\n')


            # Early exist if empty frames should not be written
            if self._skip_empty_frames and num_objs == 0:
                continue

            # Create render product name subfolder if data should be separated for each render product
            rp_subfolder = f"{rp_name}/" if self._use_subfolders else ""
            
            rgb_data = annotators_data[self.RGB_ANNOT_NAME]["data"]

            
            add_cuboid_27(self._frame_data)
            add_vfov(self._frame_data)




            img_bin = img_arr_to_bytes(rgb_data)

            data_dict['img'] = img_bin



            normalized_id_to_labels = self._get_idToLabels(seg_data['idToSemantics'])
            print(f"【{seg_data['idToSemantics']}】")
            
            
            ## bbox 2d

            seg_label_to_ids = self._exchange_k_v(normalized_id_to_labels)
            data_dict['label']=seg_label_to_ids

            box_2d_id_to_labels = self._get_idToLabels(bounding_box_2d_data['idToLabels'])

            
            bboxs_2d_normed = []
            
            for bbox in bounding_box_2d_data['data'].tolist():
                # filter occlusion
                if bbox[-1]>self._occlusion_threshold:
                    continue


                id_box = int(seg_label_to_ids[box_2d_id_to_labels[bbox[0]]])
                
                img_w,img_h = self._frame_data['camera_data']['resolution']
                # bbox_normalized = normalize_bbox(img_h,img_w,*bbox[1:-1])

                bbox_normalized = normalize_bbox(img_h,img_w,*bbox[1:-1])
                bboxs_2d_normed.append([id_box,*bbox_normalized])

            data_dict['bounding_box_2d_tight_fast'] = bboxs_2d_normed


            # seg data
            seg_arr = seg_data['data']

            if self._is_save_seg_info:

                seg_dict = {'seg_bytes':seg_arr.tobytes(),
                                'seg_shape':seg_arr.shape,
                                'seg_dtype':str(seg_arr.dtype)}
                

                data_dict['segmentation'] = seg_dict


            # distancer
            distancer_arr = distancer_data['data']
            distancer_arr = (distancer_arr*100).astype(np.uint16)

            # compatable with orbbec, distancer data type is uint16,unit is mm.

            distancer_dict = {'depth_bytes':distancer_arr.tobytes(),
                              'depth_shape':distancer_arr.shape,
                              'depth_dtype':str(distancer_arr.dtype)}

            data_dict['distancer'] = distancer_dict

            data_dict['occlusion_ratio'] =  {prim_path:data[-1] for prim_path,data in zip(bounding_box_2d_data['primPaths'],bounding_box_2d_data['data'].tolist())}




            # bbox 3d

            bbox_3ds = []

            for obj in self._frame_data['objects']:
                label_id = seg_label_to_ids[obj['label']]
                bbox_3ds.append([int(label_id),*obj['cuboid_27_screen']])

            data_dict['cuboid_27_screen'] = bbox_3ds
            
            data_dict['id_to_label'] = normalized_id_to_labels
            data_dict['prim_path_to_id'] = self._exchange_k_v(seg_data['idToLabels'])

            

            # data to 2D Polygon, point order irrelevant

            # 1.pop occlusion info and move out occlusion data

            occlusion_ratio_map = data_dict.pop('occlusion_ratio')
            prim_path_to_id = data_dict.pop('prim_path_to_id')
            seg_id_occlusion = {}
            for prim_path,occlusion_ratio in occlusion_ratio_map.items():
                if occlusion_ratio<self._occlusion_threshold:
                    seg_id_occlusion[int(prim_path_to_id[prim_path])] = occlusion_ratio


            # 2.pop segmentation info, process seg data and seg to polygon

            shapes = instance_seg_to_rotated_boxes(seg_arr,morph_open_kernel=self.MORPH_POEN_KERNEL,seg_id_occlusion=seg_id_occlusion)

            
            # 3.save seg to data_dict
            data_dict['shapes'] = shapes



            # write data to lmdb

            pickle_bytes = pickle.dumps(data_dict)


            self._data_saver.put(str(self._data_count).zfill(10).encode('utf8'),pickle_bytes)
            self._data_count += 1
            if self._data_count%10==0:
                print(f'current training data num:[ {self._data_count}]')

            

            # show samples

            if int(self._frame_id)%self._show_bin==0:
                try:
            
                    show_dir = os.path.join(os.path.dirname(self._output_dir),'samples')
                    if not os.path.exists(show_dir):
                        os.mkdir(show_dir)
                    stem = str(self._frame_id).zfill(10)
                    img_ori_path = os.path.join(show_dir,stem+'.jpg')
                    img_draw_path = os.path.join(show_dir,stem+'_overlay.jpg')
                    img_depth_path = os.path.join(show_dir,stem+'_depth.jpg')
                    img_seg_path = os.path.join(show_dir,stem+'_seg.jpg')

                    bgr_data = cv2.cvtColor(rgb_data,cv2.COLOR_RGB2BGR)

                    seg = seg_arr

                    cv2imwrite(img_ori_path,bgr_data)
                    # cv2imwrite(img_draw_path,np.array(pil_img))
                    cv2imwrite(img_depth_path,visualize_depth_gray(distancer_arr))

                    cv2imwrite(img_seg_path,colorize_segmentation(seg))



                    data_dict['rotation_matrix_camera_frame'] = self._frame_data['objects'][0]['rotation_matrix_camera_frame']
                    data_dict['rotation_matrix_world_frame'] = self._frame_data['objects'][0]['rotation_matrix_world_frame']
                    data_dict['location_camera_frame'] = self._frame_data['objects'][0]['location_camera_frame']
                    data_dict['size'] = self._frame_data['objects'][0]['size']

                    data_dict['vfov'] = self._frame_data['camera_data']['vfov']
                   
                    data_dict.pop('img')
                    data_dict.pop('distancer')

                    save_json(img_ori_path[:-4]+'.json',data_dict)
                except:
                    traceback.print_exc()
            
            
            self._frame_id += 1
            
            
            init_config_file_path = os.path.join(os.path.dirname(self._output_dir),'config.json')
            # update init config
            # if not os.path.exists(init_config_file_path):

            for target_asset in self._frame_data['objects']:

                label = target_asset['label']
                points_27 = target_asset['cuboid_27_world']

                scale = target_asset['local_to_world_transform'][0][0]

                # 尺寸还原到初始尺寸，而不是场景中使用的尺寸。json中的scale只用作记录，不再用作还原
                points_27 = (np.array(points_27)/scale).tolist()

                class_label_block = self._construct_label_info(label,points_27)

                self._init_info['classNames'] = self._label_registry.id_to_label
                self._init_info['classLabels'][label] = class_label_block


                # init_info = self._get_init_info(label,points_27,scale)

            
            # placeholder for deploy: 我们的项目依赖vfov
            self._init_info['vfov'] = round(self._frame_data['camera_data']['vfov'], 2)

        
            with open(init_config_file_path,mode='w',encoding='utf8') as f:
                json.dump(self._init_info,f)




if __name__ == '__main__':
    print(LMDBWriter.__name__)