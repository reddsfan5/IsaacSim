import omni.usd
from pxr import UsdGeom, Gf, Usd
import numpy as np  # 首先必须导入numpy


# 获取当前stage
stage = omni.usd.get_context().get_stage()

# 指定目标asset的路径，例如 "/World/TargetAsset"
target_asset_path = "/World/airship/mesh"

# 获取目标asset的Prim
target_prim = stage.GetPrimAtPath(target_asset_path)
if not target_prim:
    print(f"错误: 未在路径 {target_asset_path} 找到Asset")
    exit()

# 计算目标asset的世界范围（边界框）
bbox = UsdGeom.Boundable.ComputeExtentFromPlugins(UsdGeom.Boundable(target_prim), Usd.TimeCode.Default())
if not bbox:
    print("错误: 无法计算目标Asset的边界框")
    exit()

# bbox返回的是两个点（Gf.Vec3f）的列表，分别代表最小和最大角点
min_point = bbox[0]
max_point = bbox[1]

# 计算包围盒的中心位置和尺寸
center = (min_point + max_point) / 2.0
scale = max_point - min_point

# 定义包围盒的Prim路径，例如在目标asset下创建
bounding_box_path = f"{target_asset_path}/BoundingBox"

# 创建立方体作为包围盒
cube_prim = stage.DefinePrim(bounding_box_path, "Cube")
cube = UsdGeom.Cube(cube_prim)

# 设置包围盒的位移、缩放和可见性等属性
cube.AddTranslateOp().Set(center)
cube.AddScaleOp().Set(scale) # 关键：直接将缩放设置为边界框的尺寸
cube.CreateDisplayColorAttr([(0.0, 0.0, 1.0)]) # 可选：设置为蓝色半透明
cube_prim.CreateAttribute("primvars:displayOpacity", Usd.TypeNames.Float).Set(0.3) # 可选：设置透明度

print(f"已在 {bounding_box_path} 创建包围盒")
print(f"中心位置: {center}")
print(f"尺寸: {scale}")