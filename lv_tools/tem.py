import omni.usd
from pxr import UsdGeom,Usd
from isaacsim.core.utils.stage import add_reference_to_stage
# too big:[GD960_JJ_50HP,]
# too small: crane # 侧翻(模型转化，up axis怎么设置)

max_limit = 0.5
min_limit = 0.1
target_value = 0.35

stage = omni.usd.get_context().get_stage()

prim_path = '/World/crane'
target_prim = stage.GetPrimAtPath(prim_path)
bbox3 = UsdGeom.BBoxCache(time=Usd.TimeCode.Default(), includedPurposes=[UsdGeom.Tokens.default_]).ComputeWorldBound(target_prim)
bbox_range = bbox3.ComputeAlignedRange()

min_point = bbox_range.GetMin()
max_point = bbox_range.GetMax()

if (test_value:=max(max_point-min_point))>max_limit or test_value<min_limit:
    scale = target_value/test_value
    if not target_prim.HasAttribute("xformOp:scale"):
        UsdGeom.Xformable(target_prim).AddScaleOp()
    ori_value = UsdGeom.Xformable(target_prim).GetScaleOp().Get()
    UsdGeom.Xformable(target_prim).GetScaleOp().Set(ori_value*scale)

def asset_size_adaptive(target_prim:Usd.Prim,max_limit:float=0.5,min_limit:float=0.1,target_value:float=0.35):

    bbox3 = UsdGeom.BBoxCache(time=Usd.TimeCode.Default(), includedPurposes=[UsdGeom.Tokens.default_]).ComputeWorldBound(target_prim)
    bbox_range = bbox3.ComputeAlignedRange()

    min_point = bbox_range.GetMin()
    max_point = bbox_range.GetMax()

    if (test_value:=max(max_point-min_point))>max_limit or test_value<min_limit:
        scale = target_value/test_value
        if not target_prim.HasAttribute("xformOp:scale"):
            UsdGeom.Xformable(target_prim).AddScaleOp()
        ori_value = UsdGeom.Xformable(target_prim).GetScaleOp().Get()
        UsdGeom.Xformable(target_prim).GetScaleOp().Set(ori_value*scale)


    