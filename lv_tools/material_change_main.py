import os
import sys
sys.path.append('/home/ubuntu/lxd/lxd_code/isaacsim')
from lv_tools.material_change import bind_materials_to_prims_recursively, create_pbr_with_texture, find_materials
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



prim_path = '/Root/material_test/Scope'
# # print(prims_utils.get_prim_attribute_names(prim_path=prim_path))
# stage = omni.usd.get_context().get_stage()
# # print(stage)
# random_material(prim_path)
stage = omni.usd.get_context().get_stage()

from omni.isaac.core.utils.stage import add_reference_to_stage

# 指定USD文件路径和期望在舞台中的根路径（Prim Path）
usd_file_path = "/home/ubuntu/lxd/usd_file/glb/general_Looks.usd"
# prim_path = "/general_looks"
# 将USD文件作为引用添加到当前舞台
# add_reference_to_stage(usd_path=usd_file_path, prim_path=prim_path)
# material = stage.GetPrimAtPath(prim_path)
# value = prims_utils.get_prim_attribute_names(prim_path=prim_path)

# '''
# material change

# '''
# alpha = 0.5
# beta = 2
# color = np.random.uniform(0,1,3)
# metallic_constant = random.uniform(.1,.99)
# reflection_roughness = random.uniform(.01,1)
# texture_scale = np.random.beta(alpha,beta,1)*10
# translate = random.randint(2,20)
# texture_root = '/home/ubuntu/lxd/usd_file/pbr_data/RustPlain030/4k'
# texture_path = os.path.join(texture_root,'RustPlain030_COL_4K.jpg')
# normal_texture_path = os.path.join(texture_root,'RustPlain030_NRM_4K.jpg')
# roughness_texture_path = os.path.join(texture_root,'MetalFineGold001_GLOSS_4K_SPECULAR.jpg')
# metallic_texture_path = os.path.join(texture_root,'RustPlain030_REFL_4K.jpg')
# project_uvw=True
# scale = 1
# rand_str = ''.join(random.choices(string.ascii_letters,k=8))
# material_prim_path = f'/Look_PBR/{rand_str}'
# prim_path_model = '/World'
# prim_path = prim_path_model
# omni_pbr_material = create_pbr_with_texture(material_prim_path,texture_path,metallic_constant,reflection_roughness,scale,translate,project_uvw,
#                                             normalmap_texture_path=normal_texture_path,
#                                             metallic_texture_path=metallic_texture_path,
#                                             reflectionroughness_texture_path=roughness_texture_path)
# materials = [omni_pbr_material]
materials = find_materials(stage, "/Root/general_looks/Looks")
# # materials.extend([omni_pbr_material]*20)




prim_model = stage.GetPrimAtPath(prim_path)
bind_materials_to_prims_recursively(prim_model,materials,is_mesh_bind_material=False)
