
from pxr import UsdGeom,Gf
import random
import omni.usd
from isaacsim.core.utils.stage import add_reference_to_stage


asset_usd_path = '/data2/isaacsim/assets/converted_usd/symmetric_cylinder_rotate_0_no_resize_smaller_rich_env-normal-test111/SAM4030.usd'
# env_usd_path = '/data2/isaacsim/scene/dining_rooms/dining_room_6/dining_room_6.usdc'
env_usd_path = '/data2/isaacsim/scene/Office/office_no_building_no_ceil.usdc'
# material_usd_path = '/data2/isaacsim/materials/material_aggregation_usd/poliigon_city.usd'
name = asset_usd_path.split('/')[-1].split('.')[0]

stage = omni.usd.get_context().get_stage()
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
UsdGeom.SetStageMetersPerUnit(stage, 1)
UsdGeom.Scope.Define(stage, '/Assets')
# add_reference_to_stage(asset_usd_path, f'/Assets/{name}')
# add_reference_to_stage(env_usd_path, '/Environment')
add_reference_to_stage(material_usd_path, '/general_looks')
prim_path = f'/Assets/{name}'

root_prim = stage.GetPrimAtPath(prim_path)
xf = UsdGeom.Xformable(root_prim)
# UsdGeom.XformCommonAPI(root_prim).SetRotate(Gf.Vec3f(180, 0, 0))


rotate_order = 'XYZ'
rotation = Gf.Vec3f(0, 0, 0)
if not root_prim.HasAttribute(f"xformOp:rotate{rotate_order}"):

    UsdGeom.Xformable(root_prim).AddRotateXYZOp()
root_prim.GetAttribute("xformOp:rotateXYZ").Set(rotation)
