usd_root = '/home/ubuntu/lxd/lxd_code/isaacsim_dev/IsaacSim/usd_tutorial/usd_data'
from pxr import Usd,UsdGeom,Gf,UsdLux,Sdf,UsdShade
import math
import os
import time
from datetime import datetime

timestemp = datetime.now().strftime('%d%m%Y-%H%M%S')
file_path = f"{usd_root}/relationships_{timestemp}.usda"

stage = Usd.Stage.CreateNew(file_path)


# A root transform group we will move and rotate
world = UsdGeom.Xform.Define(stage, "/World")
parent = UsdGeom.Xform.Define(stage, world.GetPath().AppendPath("Parent_Prim"))

# Parent Translate, Rotate, Scale using XformCommonAPI
parent_xform_api = UsdGeom.XformCommonAPI(parent)
parent_xform_api.SetTranslate(Gf.Vec3d(5, 0, 3))
parent_xform_api.SetRotate(Gf.Vec3f(90, 0, 0))
parent_xform_api.SetScale(Gf.Vec3f(3.0, 3.0, 3.0))


child_translation = Gf.Vec3d(2, 0, 0)

# Child A - inherits parent transforms
child_a_cone = UsdGeom.Cone.Define(stage, parent.GetPath().AppendChild("Child_A"))
child_a_xform_api = UsdGeom.XformCommonAPI(child_a_cone)
child_a_xform_api.SetTranslate(child_translation)  # Parent_Prim transform + local placement
# Child B - "/World/Alt_Parent/Child_B" does NOT inherit Parent_Prim transforms
alt_parent = UsdGeom.Xform.Define(stage, world.GetPath().AppendChild("Alt_Parent"))
child_b_cone = UsdGeom.Cone.Define(stage, alt_parent.GetPath().AppendChild("Child_B"))
child_b_xform_api = UsdGeom.XformCommonAPI(child_b_cone)
child_b_xform_api.SetTranslate(child_translation)  # local placement only

# Inspect the authored Xform Operation Order
print("Parent xformOpOrder:", UsdGeom.Xformable(parent).GetXformOpOrderAttr().Get())
print("Alt_Parent xformOpOrder:", UsdGeom.Xformable(alt_parent).GetXformOpOrderAttr().Get())
print("Child A xformOpOrder:", UsdGeom.Xformable(child_a_cone).GetXformOpOrderAttr().Get())
print("Child B xformOpOrder:", UsdGeom.Xformable(child_b_cone).GetXformOpOrderAttr().Get())

stage.Save()


