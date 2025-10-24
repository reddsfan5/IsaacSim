import json
import os
import pickle
import traceback

import numpy as np
from lv_tools.centerpose_to_alva import add_cuboid_27, add_vfov, draw_projected_keypoints, is_ann_valid
from lv_tools.cores.img_io import cv2imwrite
from omni.replicator.core import WriterRegistry
from omni.replicator.core.writers import Writer
from omni.replicator.core.annotators import AnnotatorRegistry
from omni.replicator.core.writers_default import BasicWriter
from isaacsim.replicator.writers import PoseWriter
from lv_tools.dataset_io.data_saver import LmdbSaver
from pprint import pprint
import PIL
import io

class BasicDataCollector(BasicWriter):
    def write(self,data:dict):
        print('B'*20)
        pprint(data)


class PoseDataCollector(PoseWriter):
    def write(self,data:dict):
        print('P'*20)
        pprint(data)

class LMDBWriter(PoseWriter):
    BOUNDING_BOX_2D = 'bounding_box_2d_tight_fast'
    SEMANTIC_SEGMENTATION = 'semantic_segmentation'





    def __init__(self,cache_capacity:int=10,*args,**kwargs):
        # rgb = kwargs.pop('rgb',False)
        self._output_dir = kwargs.get('output_dir','')
        _lmdb_path = self._output_dir+f'/{os.path.basename(self._output_dir)}_lmdb'
        self._saver = LmdbSaver(_lmdb_path,cache_capacity)
        self._show_bin = kwargs.pop('show_bin',1000)


        semantic_segmentation = kwargs.pop('semantic_segmentation',False)
        bounding_box_2d_tight = kwargs.pop('bounding_box_2d_tight',False)

        self.colorize_semantic_segmentation = kwargs.pop('colorize_semantic_segmentation',True)

        super().__init__(*args,**kwargs)

        if bounding_box_2d_tight:
            self.annotators.append(self.BOUNDING_BOX_2D)
        
        # Semantic Segmentation
        if semantic_segmentation:
            self.annotators.append(
                AnnotatorRegistry.get_annotator(
                    self.SEMANTIC_SEGMENTATION, init_params={"colorize": self.colorize_semantic_segmentation}
                )
            )

    def _get_init_info(self,label:str,points_27:list):
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
                "isProportionalSize": False
                    }
                },
                "ProjectName": ""
                }
        return init_info




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


            if not is_ann_valid(self._frame_data, truncation_ratio=.5, visibility_ratio=.65,rotate_threshold=90):
                return 
            add_cuboid_27(self._frame_data)
            add_vfov(self._frame_data)


            data_dict = {'img':rgb_data,
                         'label':self._frame_data
                         }
            pickle_bytes = pickle.dumps(data_dict)



            self._saver.put(str(self._frame_id).zfill(10).encode('utf8'),pickle_bytes)




            # show samples

            if int(self._frame_id)%self._show_bin==0:
                try:
            
                    show_dir = os.path.join(self._output_dir,'samples')
                    if not os.path.exists(show_dir):
                        os.mkdir(show_dir)
                    
                    img_ori_path = os.path.join(show_dir,str(self._frame_id).zfill(10)+'.jpg')
                    img_draw_path = os.path.join(show_dir,str(self._frame_id).zfill(10)+'_overlay.jpg')
                    pil_img = PIL.Image.fromarray(rgb_data)
                    draw = PIL.ImageDraw.Draw(pil_img)

                    keypoints = self._frame_data['objects'][0]['cuboid_keypoints_projected']
                    draw_projected_keypoints(draw,keypoints)
                    cv2imwrite(img_ori_path,rgb_data)
                    cv2imwrite(img_draw_path,np.array(pil_img))
                except:
                    traceback.print_exc()

            init_config_file_path = os.path.join(self._output_dir,'config.json')

            label = self._frame_data['objects'][0]['label']
            points_27 = self._frame_data['objects'][0]['cuboid_27_world']

            init_info = self._get_init_info(label,points_27)
            if not os.path.exists(init_config_file_path):
                with open(init_config_file_path,mode='w',encoding='utf8') as f:
                    json.dump(init_info,f)






            # If render products are NOT separated into subfolders increment the frame id after processing each render product
            if not self._use_subfolders:
                self._frame_id += 1

        # If render products are separated into subfolders increment the frame id after processing all render products
        if self._use_subfolders:
            self._frame_id += 1



WriterRegistry.register(BasicDataCollector)
(
    WriterRegistry._default_writers.append("BasicDataCollector")
    if "BasicDataCollector" not in WriterRegistry._default_writers
    else None
)

WriterRegistry.register(PoseDataCollector)
(
    WriterRegistry._default_writers.append("PoseDataCollector")
    if "PoseDataCollector" not in WriterRegistry._default_writers
    else None)


WriterRegistry.register(LMDBWriter)
(
    WriterRegistry._default_writers.append("LMDBWriter")
    if "LMDBWriter" not in WriterRegistry._default_writers
    else None)




# PoseWriter
# WriterRegistry.register(PoseWriter)
# (
#     WriterRegistry._default_writers.append("PoseWriter")
#     if "PoseWriter" not in WriterRegistry._default_writers
#     else None
# )


'''

from omni.replicator.core import WriterRegistry
from isaacsim.replicator.writers import PoseWriter

# PoseWriter
WriterRegistry.register(PoseWriter)
(
    WriterRegistry._default_writers.append("PoseWriter")
    if "PoseWriter" not in WriterRegistry._default_writers
    else None
)

'''