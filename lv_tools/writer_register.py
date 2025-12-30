import json
import math
import os
import pickle
import random
import traceback
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
    def _xyzr_to_thetaphi(x, y, z, r):
        if r <= 0:
            raise ValueError("r must be > 0")

        # theta
        c = y / r
        c = max(-1.0, min(1.0, c))           # clamp for numeric safety
        theta = math.acos(c)

        # phi
        s = math.sin(theta)
        if abs(s) < 1e-12:                   # pole: phi undefined
            phi = 0.0
        else:
            phi = math.atan2(z, x)           # [-pi, pi]
            if phi < 0:
                phi += 2 * math.pi           # [0, 2pi) if you want

        return theta, phi


    def camera_loc_on_sphere(self,center_target:tuple,camera_view_transform:np.ndarray):


        V = np.array(camera_view_transform).reshape(4,4)
        camera_loc = np.linalg.inv(V)[3, :3]   # 相机世界坐标（行向量约定）
        r = math.sqrt(sum([(camera_loc[i]-center_target[i])**2 for i in range(3)]))
        polar,yaw = self._xyzr_to_thetaphi(camera_loc[0]-center_target[0],camera_loc[1]-center_target[1],camera_loc[2]-center_target[2],r)
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
            polar,yaw,r = self.camera_loc_on_sphere(center_target,camera_view_transform)

            print(f'写入角度参数：polar:{round(polar,2)},azimuth:{round(yaw,2)},radius:{round(r,2)}')

            data_dict['camera_polar_yaw'] = (int(polar),int(yaw))
            data_dict['camera_r'] = round(r,3)
            
            
            add_cuboid_27(self._frame_data)
            add_vfov(self._frame_data)
            img_bin = img_arr_to_bytes(rgb_data)

            data_dict['img'] = img_bin

            
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
                    
                    img_ori_path = os.path.join(show_dir,str(self._frame_id).zfill(10)+'.jpg')
                    img_draw_path = os.path.join(show_dir,str(self._frame_id).zfill(10)+'_overlay.jpg')
                    img_seg_path = os.path.join(show_dir,str(self._frame_id).zfill(10)+'_seg.jpg')
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



if __name__ == '__main__':
    print(LMDBWriter.__name__)