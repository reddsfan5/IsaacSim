import omni.usd
from pxr import UsdGeom,Usd
from pprint import pprint
import isaacsim.core.utils.prims as prims_utils
from isaacsim.core.utils.stage import add_reference_to_stage
# too big:[GD960_JJ_50HP,]
# too small: crane # 侧翻(模型转化，up axis怎么设置)
[0.05,0.5]
max_limit = 0.5
min_limit = 0.05
target_value = 0.3
add_reference_to_stage('/home/ubuntu/lxd/usd_file/glb/bus2.usd','/World/crane')

stage = omni.usd.get_context().get_stage()


prim_path = '/World/crane'
target_prim = stage.GetPrimAtPath(prim_path)
print(target_prim)
bbox3 = UsdGeom.BBoxCache(time=Usd.TimeCode.Default(), includedPurposes=[UsdGeom.Tokens.default_]).ComputeWorldBound(target_prim)
# pprint(bbox3)
bbox_range = bbox3.ComputeAlignedRange()
# pprint(f'bbox: {bbox_range}')

min_point = bbox_range.GetMin()
max_point = bbox_range.GetMax()

print(min_point)
print(max_point)
print(max_point-min_point)
print(bbox3.GetBox().GetSize())

if (max_value:=max(max_point-min_point))>max_limit:
    scale = target_value/max_value
    if not target_prim.HasAttribute("xformOp:scale"):
        UsdGeom.Xformable(target_prim).AddScaleOp()
    ori_value = UsdGeom.Xformable(target_prim).GetScaleOp().Get()
    print(UsdGeom.Xformable(target_prim).GetScaleOp().Set(ori_value*scale))
elif (min_value:=min(max_point-min_point))<min_limit:
    scale = target_value/max_value
    if not target_prim.HasAttribute("xformOp:scale"):
        UsdGeom.Xformable(target_prim).AddScaleOp()
    ori_value = UsdGeom.Xformable(target_prim).GetScaleOp().Get()
    print(UsdGeom.Xformable(target_prim).GetScaleOp().Set(ori_value*scale))



    