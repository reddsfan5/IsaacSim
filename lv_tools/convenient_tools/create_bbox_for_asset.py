import omni.usd
from pxr import UsdGeom, Gf, Usd
import numpy as np  # 首先必须导入numpy


# 获取当前stage
stage = omni.usd.get_context().get_stage()

# 指定目标asset的路径，例如 "/World/TargetAsset"
target_asset_path = "/World/crane"

# 获取目标asset的Prim
target_prim = stage.GetPrimAtPath(target_asset_path)

# compute local bound
# bbox2 = UsdGeom.Boundable.ComputeExtentFromPlugins(UsdGeom.Boundable(target_prim), Usd.TimeCode.Default())
# print(bbox2)
# bbox2 = UsdGeom.Boundable(target_prim).ComputeExtent(Usd.TimeCode.Default())
# print(bbox2)
# bbox_cache = UsdGeom.BBoxCache(time=Usd.TimeCode.Default(), includedPurposes=[UsdGeom.Tokens.default_]).ComputeWorldBound(target_prim)
# bbox2 = bbox_cache.GetRange()


# # 计算目标asset的世界范围（边界框）
bbox3 = UsdGeom.BBoxCache(time=Usd.TimeCode.Default(), includedPurposes=[UsdGeom.Tokens.default_]).ComputeWorldBound(target_prim)
bbox_range = bbox3.ComputeAlignedRange()
print(f'bbox: {bbox_range}')

min_point = bbox_range.GetMin()
max_point = bbox_range.GetMax()

print(min_point)
print(max_point)



if not bbox_range:
    print("错误: 无法计算目标Asset的边界框")
    exit()

# 计算包围盒的中心位置和尺寸
center = (min_point + max_point) / 2.0
scale = max_point - min_point

# # 定义包围盒的Prim路径，例如在目标asset下创建
bounding_box_path = f"/World/BoundingBox"

# # 创建立方体作为包围盒
cube_prim = stage.DefinePrim(bounding_box_path, "Cube")
cube = UsdGeom.Cube(cube_prim)

# # 设置包围盒的位移、缩放和可见性等属性
cube.AddTranslateOp().Set(center)
cube.AddScaleOp().Set(scale/2) # 关键：直接将缩放设置为边界框的尺寸
cube.CreateDisplayColorAttr([(0.0, 0.0, 1.0)]) # 可选：设置为蓝色半透明

# print(f"已在 {bounding_box_path} 创建包围盒")
# print(f"中心位置: {center}")
# print(f"尺寸: {scale}")