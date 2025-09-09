
import omni.usd
from pxr import UsdShade
import random
import isaacsim.core.utils.prims as prims_utils
prim_path = '/World/excavator'
stage = omni.usd.get_context().get_stage()

prim = stage.GetPrimAtPath(prim_path)

# child_prim = prim.GetChild("Looks")

# value = child_prim.GetAttribute("attribute_name").Get()

# value = prims_utils.get_all_matching_child_prims(prim_path=prim_path)
# child_prims = prims_utils.get_prim_children(prim=child_prim)


# def set_prim_attr(prim_path,attribute_name,value):
#     if prims_utils.get_prim_attribute_value(prim_path=prim_path, attribute_name=attribute_name)!= None:
#         prims_utils.set_prim_attribute_value(prim_path=prim_path, attribute_name=attribute_name, value=value)


# def random_material(root_prim_path,color_range=(0,1),metallic_range=(0,.95),roughness_range=(0.1,.95)):

#     child_prims = prims_utils.get_all_matching_child_prims(prim_path=root_prim_path)
#     for material in child_prims:
#         if material.IsA(UsdShade.Shader):
#             # value = prims_utils.get_prim_property(prim_path=material.GetPath(), property_name=property_name)
#             # print(prims_utils.get_prim_attribute_names(prim_path=material.GetPath()))

#             set_prim_attr(prim_path=material.GetPath(), attribute_name='inputs:base_color_factor', value=(random.uniform(*color_range),random.uniform(*color_range),random.uniform(*color_range)))
#             set_prim_attr(prim_path=material.GetPath(), attribute_name='inputs:metallic_factor', value=(random.uniform(*metallic_range)))
#             set_prim_attr(prim_path=material.GetPath(), attribute_name='inputs:roughness_factor', value=(random.uniform(*roughness_range)))




import omni.replicator.core as rep

def random_material(root_prim_path,color_range=(0,1),metallic_range=(0,.95),roughness_range=(0.1,.95)):

    rep_items = rep.get.shader(root_prim_path)
    color_dis = rep.distribution.uniform((0,0,0),(1,1,1))
    with rep_items:
        rep.modify.attribute('inputs:base_color_factor',color_dis)
    # for rep_item in rep_items:

    #     set_prim_attr(prim_path=material.GetPath(), attribute_name='inputs:base_color_factor', value=(random.uniform(*color_range),random.uniform(*color_range),random.uniform(*color_range)))
    #     set_prim_attr(prim_path=material.GetPath(), attribute_name='inputs:metallic_factor', value=(random.uniform(*metallic_range)))
    #     set_prim_attr(prim_path=material.GetPath(), attribute_name='inputs:roughness_factor', value=(random.uniform(*roughness_range)))



# # if __name__ == '__main__':
prim_path = '/World/airship'

# random_material(prim_path)


# asset_prim_path = str(target_asset.GetPath())
try:
    rep_items = rep.get.shader(prim_path)
    color_dis = rep.distribution.uniform((0.2,0.2,0.2),(1,1,1))
    metallic_dis = rep.distribution.uniform((.1,),(0.9,))
    roughness_dis = rep.distribution.uniform((.1,),(0.9,))
    with rep_items:
        rep.modify.attribute('inputs:base_color_factor',color_dis)
        rep.modify.attribute('inputs:metallic_factor',metallic_dis)
        rep.modify.attribute('inputs:roughness_factor',roughness_dis) 
except:
    pass