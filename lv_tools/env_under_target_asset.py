# from pxr import Usd, UsdGeom, Gf
# import omni.usd
import random
import sys
sys.path.append('/home/ubuntu/lxd/lxd_code/isaacsim')
# from source.standalone_examples.replicator.infinigen.infinigen_sdg_utils import find_matching_prims
# root_path = '/World'

# table_prim = find_matching_prims(
#     match_strings=["floor"], root_path=root_path, prim_type="Xform", first_match_only=True
# )



# bbox_cache = UsdGeom.BBoxCache(time=Usd.TimeCode.Default(), includedPurposes=[UsdGeom.Tokens.default_])

# table_world_bound_bbox = bbox_cache.ComputeWorldBound(table_prim)
# table_world_bound_aligned_range = table_world_bound_bbox.ComputeAlignedRange()

# table_size = table_world_bound_aligned_range.GetSize()
# table_center = table_world_bound_aligned_range.GetMidpoint()
# table_min = table_world_bound_aligned_range.GetMin()
# table_max = table_world_bound_aligned_range.GetMax()


# target_mesh_path = '/World/AM114_33/mesh'


# stage = omni.usd.get_context().get_stage()

# target_prim = stage.GetPrimAtPath(target_mesh_path)

# target_world_bbox = bbox_cache.ComputeWorldBound(target_prim)
# target_world_range = target_world_bbox.ComputeAlignedRange()

# target_asset_size = target_world_range.GetSize()
# target_asset_min = target_world_range.GetMin()
# target_asset_max = target_world_range.GetMax()

# target_asset_center = target_world_range.GetMidpoint()
# # print(table_size)
# x_delta = (table_size[0]-target_asset_size[0])/2
# z_delta = (table_size[2]-target_asset_size[2])/2

# x_location = random.uniform(target_asset_center[0]-x_delta, target_asset_center[0]+x_delta)
# z_location = random.uniform(target_asset_center[2]-z_delta, target_asset_center[2]+z_delta)
# y_location = target_asset_min[1] - table_size[1]/2



# table_center_target_location = (x_location, y_location, z_location)


# target_origin_delta = Gf.Vec3d(table_center_target_location)-Gf.Vec3d(table_center)

# dinning_room_xform = table_prim.GetParent()

# dinning_room_ori_location = dinning_room_xform.GetAttribute("xformOp:translate").Get()

# dinning_room_xform.GetAttribute("xformOp:translate").Set(dinning_room_ori_location+target_origin_delta)


import omni.usd
from source.standalone_examples.replicator.infinigen.infinigen_sdg_utils import translate_env_under_target_asset,find_matching_prims

root_path = '/World'


# 指定USD文件路径和期望在舞台中的根路径（Prim Path）
# usd_file_path = "/home/ubuntu/lxd/usd_file/glb/general_Looks.usd"
# prim_path = "/World/general_looks"

# 将USD文件作为引用添加到当前舞台
# add_reference_to_stage(usd_path=usd_file_path, prim_path=prim_path)

stage = omni.usd.get_context().get_stage()

# Get the plane prim 

match_string = "TableDining"
# match_string = "bedroom_1_0_floor"
# root_path= '/Environment'
plane_prims = find_matching_prims(
    match_strings=[match_string], root_path=root_path, prim_type="Xform", first_match_only=False,exception_prim_strings=[
    '/World/dining_room_4/TableDiningFactory_3810673__spawn_asset_8768607__001',
    '/World/dining_room_5/TableDiningFactory_6160158__spawn_asset_9053640__001'
    '/World/dining_room_6/TableDiningFactory_5756319__spawn_asset_664843__001',
    '/World/dining_room_8/TableDiningFactory_8694695__spawn_asset_1032784__001_SPLIT_GLAS']
)

table_prim = random.choice(plane_prims)



target_prim = stage.GetPrimAtPath('/World/airship')

print(table_prim)
print(target_prim)

translate_env_under_target_asset(table_prim,target_prim)
