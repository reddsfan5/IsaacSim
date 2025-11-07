import omni.kit.material.library as matlib
import omni.usd
import omni.kit
from pxr import Sdf,UsdShade
def iterate_shaders(prim):
    prims = []
    
    """递归迭代 prim 下的所有 Shader prim"""
    if prim.IsA(UsdShade.Shader):
        return [prim]
    
    for child in prim.GetChildren():
        prims.extend(iterate_shaders(child))
    return prims
    

# 从根 prim 开始遍历
root = stage.GetPrimAtPath("/general_Looks/Looks")

stage = omni.usd.get_context().get_stage()

# /home/ubuntu/lxd/usd_file/Automotive_Materials_NVD@10011/Automotive_Materials_NVD@10011/Materials/2023_1/Automotive/Carbon_Fiber/Carbon_Fiber_ANI_01_Clearcoat.mdl

prim = stage.GetPrimAtPath('/general_Looks/Looks')
for sub_prim in iterate_shaders(root):
    if sub_prim.IsA(UsdShade.Shader):

        asset_path_attr = sub_prim.GetAttribute("info:mdl:sourceAsset")
        ori_asset_path = asset_path_attr.Get()
        print(ori_asset_path)
        target_value = str(ori_asset_path).replace('/home/ubuntu/lxd/usd_file/Automotive_Materials_NVD@10011/Automotive_Materials_NVD@10011','/data2/isaacsim/materials/Automotive_Materials_NVD@10011')
        target_value = str(target_value.strip('@'))
        print(target_value)
        asset_path_attr.Set(Sdf.AssetPath(target_value))
        print(str(asset_path_attr.Get()))
