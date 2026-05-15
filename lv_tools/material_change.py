
import omni.usd
from collections import defaultdict
from pathlib import Path
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
import carb

GLOBAL_SEED  = 4122     



class MaterialTexture:
    def __init__(self, root: str):
        self.mats = self._construct_mat_map(root)

    def _match_key_info(self, file_name: str):
        parts = {p.lower() for p in file_name.split('_')}
        keys = ("col", "rough", "nrm", "refl", "ao")

        for key in keys:
            if key in parts:
                return key

    def _filter_valid_mat_map(self, mat_map: dict):
        new_mat_map = {}
        for key, value in mat_map.items():
            # 确保至少存在 col
            if 'col' in value.keys():
                new_mat_map[key] = value
        return new_mat_map

    def _construct_mat_map(self, root: str):
        mat_map = defaultdict(dict)

        for file_path in Path(root).rglob('*'):
            if file_path.suffix.lower() in ('.jpg','.png'):
            # if file_path.suffix.lower() in ('.png'):
                key_word = self._match_key_info(file_path.name)
                if key_word:
                    rel_path = file_path.relative_to(root)
                    key = '-'.join(rel_path.parent.parts)
                    mat_map[key][key_word] = file_path.as_posix()
        mat_map = self._filter_valid_mat_map(mat_map)
        return mat_map

    def __len__(self):
        return len(self.mats)

    def choice(self):
        k = random.choice(list(self.mats.keys()))
        return k,self.mats[k]
    
    def __iter__(self):
        items = list(self.mats.items())
        random.shuffle(items)
        gener = ((k, v) for k, v in items)
        return gener

class OmniPBRPlus(OmniPBR):
    '''
    with more texture info.
    
    '''
    def set_reflectionroughness_texture(self, reflectionroughness_texture_path: str,roughness_map_influence:float=0.9) -> None:
        """[summary]

        Args:
            amount (float): [description]
        """

        if self.shaders_list[0].GetInput("reflectionroughness_texture").Get() is None:
            self.shaders_list[0].CreateInput("reflectionroughness_texture", Sdf.ValueTypeNames.Asset).Set(reflectionroughness_texture_path)
        else:
            self.shaders_list[0].GetInput("reflectionroughness_texture").Set(reflectionroughness_texture_path)
        
        if self.shaders_list[0].GetInput("reflection_roughness_texture_influence").Get() is None:
            self.shaders_list[0].CreateInput("reflection_roughness_texture_influence", Sdf.ValueTypeNames.Float).Set(roughness_map_influence)
        else:
            self.shaders_list[0].GetInput("reflection_roughness_texture_influence").Set(roughness_map_influence)
        return




    def get_reflectionroughness_texture(self) -> str:
        """[summary]

        Returns:
            str: [description]
        """
        if self.shaders_list[0].GetInput("reflectionroughness_texture").Get() is None:
            carb.log_warn("A reflectionroughness_texture attribute is not set yet")
            return None
        else:
            return self.shaders_list[0].GetInput("reflectionroughness_texture").Get()

    
    
    def set_normalmap_texture(self, normalmap_texture_path: str,bump_factor:float=0.9) -> None:
        """[summary]

        Args:
            amount (float): [description]
        """

        if self.shaders_list[0].GetInput("normalmap_texture").Get() is None:
            self.shaders_list[0].CreateInput("normalmap_texture", Sdf.ValueTypeNames.Asset).Set(normalmap_texture_path)
        else:
            self.shaders_list[0].GetInput("normalmap_texture").Set(normalmap_texture_path)

        if self.shaders_list[0].GetInput("bump_factor").Get() is None:
            self.shaders_list[0].CreateInput("bump_factor", Sdf.ValueTypeNames.Float).Set(bump_factor)
        else:
            self.shaders_list[0].GetInput("bump_factor").Set(bump_factor)
        
        return




    def get_normalmap_texture(self) -> str:
        """[summary]

        Returns:
            str: [description]
        """
        if self.shaders_list[0].GetInput("normalmap_texture").Get() is None:
            carb.log_warn("A normalmap_texture attribute is not set yet")
            return None
        else:
            return self.shaders_list[0].GetInput("normalmap_texture").Get()
    
    
    
    
    
    def set_metallic_texture(self, metallic_texture_path: str,metallic_texture_influence:float=0.9) -> None:
        """[summary]

        Args:
            amount (float): [description]
            /Look_PBR/gDmJhnqY/shader.inputs:metallic_texture
            /Look_PBR/gDmJhnqY/shader.inputs:metallic_texture_influence
        """

        if self.shaders_list[0].GetInput("metallic_texture").Get() is None:
            self.shaders_list[0].CreateInput("metallic_texture", Sdf.ValueTypeNames.Asset).Set(metallic_texture_path)
        else:
            self.shaders_list[0].GetInput("metallic_texture").Set(metallic_texture_path)

        if self.shaders_list[0].GetInput("metallic_texture_influence").Get() is None:
            self.shaders_list[0].CreateInput("metallic_texture_influence", Sdf.ValueTypeNames.Float).Set(metallic_texture_influence)
        else:
            self.shaders_list[0].GetInput("metallic_texture_influence").Set(metallic_texture_influence)
        
        return




    def get_metallic_texture(self) -> str:
        """[summary]

        Returns:
            str: [description]
        """
        if self.shaders_list[0].GetInput("metallic_texture").Get() is None:
            carb.log_warn("A metallic_texture attribute is not set yet")
            return None
        else:
            return self.shaders_list[0].GetInput("metallic_texture").Get()



               # 全局随机种子（可复现）
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

def bind_material_to_prim_randomly(prim:UsdGeom.Gprim, mats:list[UsdShade.Material],bindingStrength:str=UsdShade.Tokens.weakerThanDescendants):
    bind_material = random.choice(mats)
    bind_material_to_prim(prim,bind_material,bindingStrength=bindingStrength)
    # print(f"----Infinigen-SDG----- [[[Bound material]]] '{bind_material.GetPath().pathString}' to prim '{prim.GetPath().pathString}'")


def bind_material_to_prim(model_prim:Union[UsdGeom.Gprim,UsdGeom.Subset],material:UsdShade.Material,bindingStrength:str=UsdShade.Tokens.weakerThanDescendants,subdivision_scheme:Literal['catmullClark','loop','bilinear','none']='catmullClark'):

    UsdShade.MaterialBindingAPI(model_prim).Bind(material,bindingStrength=bindingStrength)
    if model_prim.IsA(UsdGeom.Mesh):
        model_mesh = UsdGeom.Mesh(model_prim)
        model_mesh.CreateSubdivisionSchemeAttr(subdivision_scheme) # loop catmullClark
    

# def bind_materials_to_assets(target_assets:list[Usd.Prim],materials:list[UsdShade.Material],is_maintain_material_structure:bool=True,usd_materials_num:int=None):
#     if usd_materials_num:
#         materials = random.sample(materials,usd_materials_num)
    
#     for target_asset in target_assets:

#         for prim in Usd.PrimRange(target_asset):
#             try:
#                 if prim.IsA(UsdGeom.Gprim):
#                     if is_maintain_material_structure:
#                         bind_material_to_prim_randomly(prim,materials)

#                     random_gprim_color(target_asset)


#                 elif prim.IsA(UsdGeom.Subset):
#                     bind_material_to_prim_randomly(prim,materials)
#             except:
#                 continue


def bind_materials_to_assets(target_assets:list[Usd.Prim],materials:list[UsdShade.Material],is_maintain_material_structure:bool=True,usd_materials_num:int=None):
    if usd_materials_num:
        materials = random.sample(materials,usd_materials_num)
    
    for target_asset in target_assets:

        for prim in Usd.PrimRange(target_asset):
            try:
                if prim.IsA(UsdGeom.Gprim):
                    binding_strength = UsdShade.Tokens.strongerThanDescendants if is_maintain_material_structure else UsdShade.Tokens.weakerThanDescendants
                    bind_material_to_prim_randomly(prim,materials,bindingStrength=binding_strength)
                    random_gprim_color(target_asset)

                elif prim.IsA(UsdGeom.Subset):
                    bind_material_to_prim_randomly(prim,materials)
            except:
                continue



def bind_material_to_subset(prim: UsdGeom.Subset, materials: list[UsdShade.Material]):
    if prim.IsA(UsdGeom.Subset):
        # print(prim)
        bind_material_to_prim_randomly(prim, materials)


def bind_materials_to_prims_recursively(root_prim:Union[Usd.Prim,Sdf.Path],materials: list[UsdShade.Material],is_mesh_bind_material:bool=False,bindingStrength:str=UsdShade.Tokens.weakerThanDescendants):
    for prim in Usd.PrimRange(root_prim):
        if prim.IsA(UsdGeom.Gprim):
            # print(f'binding:{prim.GetPath()}')
            if is_mesh_bind_material:
                bind_material_to_prim(prim,random.choice(materials),bindingStrength=bindingStrength)
            random_gprim_color(prim)
            
        elif prim.IsA(UsdGeom.Subset):
            bind_material_to_subset(prim,materials)
    

def create_pbr_with_texture(material_prim_path:str,
                            texture_path:str,
                            metallic_constant:float,
                            reflection_roughness:float,
                            scale:float,
                            translate:int,
                            project_uvw:bool=True,
                            color:np.ndarray=np.array([1,0,0]),
                            normalmap_texture_path:str=None,
                            metallic_texture_path:str=None,
                            reflectionroughness_texture_path:str=None
                            ):
    
    
    omni_pbr = OmniPBRPlus(prim_path=material_prim_path,
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
    if normalmap_texture_path:
        omni_pbr.set_normalmap_texture(normalmap_texture_path=normalmap_texture_path)
    if metallic_texture_path:
        omni_pbr.set_metallic_texture(metallic_texture_path=metallic_texture_path)
    if reflectionroughness_texture_path:
        omni_pbr.set_reflectionroughness_texture(reflectionroughness_texture_path=reflectionroughness_texture_path)

    # 确保材质生效
    omni_pbr.set_project_uvw(flag=project_uvw)
    
    
    return omni_pbr.material


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






