import os
import sys
sys.path.append('/home/ubuntu/lxd/lxd_code/isaacsim')
from lv_tools.material_change import MaterialTexture, bind_materials_to_prims_recursively, create_pbr_with_texture, find_materials
import omni.usd
from typing import Union,Literal
from pxr import UsdShade,Usd,Sdf,UsdGeom,Gf,Vt
import random
import isaacsim.core.utils.prims as prims_utils
import random
import hashlib
import fnmatch
import numpy as np
import string
import random


from tqdm import tqdm

from omni.isaac.core.utils.stage import add_reference_to_stage

# target_asset_stage_path = '/Assets'
env_asset_stage_path = '/Environment'
target_asset_stage_path = env_asset_stage_path
# pbr_material_stage_path = '/pbr_materials'
pbr_material_stage_path = '/general_looks'
general_material_stage_path = '/general_looks'
stage = omni.usd.get_context().get_stage()
# 指定USD文件路径和期望在舞台中的根路径（Prim Path）
usd_file_path = "/home/ubuntu/lxd/usd_file/glb/general_Looks.usd"


root = r'/data2/isaacsim/materials/pbr_texture/Metal'
mat_map = MaterialTexture(root)

pbr_materials = find_materials(stage, pbr_material_stage_path)
general_materials = find_materials(stage, general_material_stage_path)


# target_prim_model = stage.GetPrimAtPath(target_asset_stage_path)
# bind_materials_to_prims_recursively(target_prim_model,general_materials,is_mesh_bind_material=True)
env_prim_model = stage.GetPrimAtPath(env_asset_stage_path)
bind_materials_to_prims_recursively(env_prim_model,pbr_materials,is_mesh_bind_material=True)