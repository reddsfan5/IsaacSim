
import omni.usd
from typing import Union,Literal
from pxr import UsdShade,Usd,Sdf,UsdGeom,Gf,Vt
import random
import isaacsim.core.utils.prims as prims_utils
import random
import hashlib
import fnmatch
from isaacsim.core.api.materials import OmniPBR
import numpy as np
import string

GLOBAL_SEED  = 4122                    # 全局随机种子（可复现）
def _stable_seed(s: str) -> int:
    return int(hashlib.md5(s.encode("utf-8")).hexdigest()[:8], 16)

def set_prim_attr(prim_path,attribute_name,value):
    if prims_utils.get_prim_attribute_value(prim_path=prim_path, attribute_name=attribute_name)!= None:
        prims_utils.set_prim_attribute_value(prim_path=prim_path, attribute_name=attribute_name, value=value)


def random_pbr_material(root_prim_path,color_range=(0,1),metallic_range=(0.94,.99),roughness_range=(0.01,0.05)):

    print(root_prim_path)
    child_prims = prims_utils.get_all_matching_child_prims(prim_path=root_prim_path)
    for material in child_prims:
        # print(material.GetPath())
        if material.IsA(UsdShade.Shader):
            # print(prims_utils.get_prim_attribute_names(prim_path=material.GetPath()))

            set_prim_attr(prim_path=material.GetPath(), attribute_name='inputs:base_color_factor', value=(random.uniform(*color_range),random.uniform(*color_range),random.uniform(*color_range)))
            set_prim_attr(prim_path=material.GetPath(), attribute_name='inputs:metallic_factor', value=(random.uniform(*metallic_range)))
            set_prim_attr(prim_path=material.GetPath(), attribute_name='inputs:roughness_factor', value=(random.uniform(*roughness_range)))



def rand_pbr(asset_prim_path:str):
    try:
        rep_items = rep.get.shader(prim_path)
        color_dis = rep.distribution.uniform((0.2,0.2,0.2),(1,1,1))
        # pdb.set_trace()
        metallic_dis = rep.distribution.uniform((.1,),(0.9,))
        roughness_dis = rep.distribution.uniform((.1,),(0.9,))
        with rep_items:

            rep.modify.attribute('inputs:base_color_factor',color_dis)
            rep.modify.attribute('inputs:metallic_factor',metallic_dis)
            rep.modify.attribute('inputs:roughness_factor',roughness_dis) 
    except:
        pass


def random_gprim_color(prim:UsdGeom.Gprim):
    # print(prim)
    if prim.IsA(UsdGeom.Gprim):
        # 随机颜色（也可从你的调色板里抽样）
        color = Vt.Vec3fArray((random.random(), random.random(), random.random()))
        pv_api = UsdGeom.PrimvarsAPI(prim)
        pv = pv_api.CreatePrimvar("displayColor",
                                Sdf.ValueTypeNames.Color3f,
                                UsdGeom.Tokens.constant)
        pv.Set(color)

def find_materials(stage:Usd.Stage, looks_root:Union[str,Sdf.Path])->list[UsdShade.Material]:
    root = stage.GetPrimAtPath(looks_root)
    if not root:
        return []
    mats = []
    for p in Usd.PrimRange(root):
        if p.IsA(UsdShade.Material):
            m = UsdShade.Material(p)
            mats.append(m)
    return mats

def bind_material_to_prim_with_seed_randomly(prim:UsdGeom.Gprim, mats:list[UsdShade.Material]):
    # 按 prim 路径生成稳定 RNG；再叠加全局种子
    rng = random.Random((_stable_seed(prim.GetPath().pathString) ^ GLOBAL_SEED) & 0xFFFFFFFF)
    choices = mats
    weights = None
    m = rng.choices(choices, weights=weights, k=1)[0] if weights else rng.choice(choices)
    bind_material_to_prim(prim,m)

def bind_material_to_prim_randomly(prim:UsdGeom.Gprim, mats:list[UsdShade.Material]):
    m = random.choice(mats)
    bind_material_to_prim(prim,m)


def bind_material_to_prim(model_prim:Union[UsdGeom.Gprim,UsdGeom.Subset],material:UsdShade.Material,bindingStrength:str=UsdShade.Tokens.strongerThanDescendants,subdivision_scheme:Literal['catmullClark','loop','bilinear','none']='catmullClark'):

    UsdShade.MaterialBindingAPI(model_prim).Bind(material,bindingStrength=bindingStrength)
    if model_prim.IsA(UsdGeom.Mesh):
        model_mesh = UsdGeom.Mesh(model_prim)
        model_mesh.CreateSubdivisionSchemeAttr(subdivision_scheme) # loop catmullClark
    




def bind_material_to_subset(prim: UsdGeom.Subset, materials: list[UsdShade.Material]):
    if prim.IsA(UsdGeom.Subset):
        # print(prim)
        bind_material_to_prim_randomly(prim, materials)


def bind_materials_to_prims_recursively(root_prim:Union[Usd.Prim,Sdf.Path],materials: list[UsdShade.Material],is_mesh_bind_material:bool=False):
    for prim in Usd.PrimRange(root_prim):
        if prim.IsA(UsdGeom.Gprim):
            if is_mesh_bind_material:
                bind_material_to_prim(prim,random.choice(materials))
            random_gprim_color(prim)
            
        elif prim.IsA(UsdGeom.Subset):
            bind_material_to_subset(prim,materials)
    

def create_pbr_with_texture(material_prim_path:str,texture_path:str,metallic_constant:float,reflection_roughness:float,scale:int,translate:int,project_uvw:bool=True,color:np.ndarray=np.array([1,0,0])):
    
    
    omni_pbr = OmniPBR(prim_path=material_prim_path,
            texture_path=texture_path,
            texture_scale=np.array([scale,scale]),
            texture_translate=np.array([translate,translate]),
            color=color
        )

    # 防止金属度过高，导致渲染异常。（阴影处异常死黑和物体异常消失）
    safe_metallic_constant = min(metallic_constant,.9)
    safe_reflection_roughness = max(.1,reflection_roughness)
    omni_pbr.set_metallic_constant(amount=safe_metallic_constant)
    omni_pbr.set_reflection_roughness(amount=safe_reflection_roughness)

    # 确保材质生效
    omni_pbr.set_project_uvw(flag=project_uvw)
    return omni_pbr.material








# if __name__ == '__main__':



prim_path = '/World/JJ_2_no_base/mesh'
# # print(prims_utils.get_prim_attribute_names(prim_path=prim_path))
# stage = omni.usd.get_context().get_stage()
# # print(stage)
# random_material(prim_path)
stage = omni.usd.get_context().get_stage()

from omni.isaac.core.utils.stage import add_reference_to_stage

# 指定USD文件路径和期望在舞台中的根路径（Prim Path）
usd_file_path = "/home/ubuntu/lxd/usd_file/glb/general_Looks.usd"
prim_path = "/World/general_looks"
# 将USD文件作为引用添加到当前舞台
# add_reference_to_stage(usd_path=usd_file_path, prim_path=prim_path)
# material = stage.GetPrimAtPath(prim_path)
# value = prims_utils.get_prim_attribute_names(prim_path=prim_path)

# '''
# material change

# '''

color = np.random.uniform(0,1,3)
metallic_constant = random.uniform(.1,.99)
reflection_roughness = random.uniform(.01,1)
scale = random.choice([random.uniform(.01,1),random.randint(1,10)])
translate = random.randint(2,20)
texture_path = '/home/ubuntu/lxd/usd_file/imgs/71q9Ii6lj3L._AC_.jpg'
project_uvw=True

rand_str = ''.join(random.choices(string.ascii_letters,k=8))
material_prim_path = f'/Look_PBR/{rand_str}'
prim_path_model = '/World'
prim_path = prim_path_model
omni_pbr_material = create_pbr_with_texture(material_prim_path,texture_path,metallic_constant,reflection_roughness,scale,translate,project_uvw)
# materials = [omni_pbr_material]
materials = find_materials(stage, "/general_looks/Looks")
materials.extend([omni_pbr_material]*20)




prim_model = stage.GetPrimAtPath(prim_path_model)
bind_materials_to_prims_recursively(prim_model,materials,is_mesh_bind_material=True)