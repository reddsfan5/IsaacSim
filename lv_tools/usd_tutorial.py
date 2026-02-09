usd_root = '/home/ubuntu/lxd/lxd_code/isaacsim_dev/IsaacSim/usd_tutorial/usd_data'
ref_path = '/data2/isaacsim/assets/converted_usd/007/C919.usd'
ref_path2 = '/home/ubuntu/lxd/lxd_code/isaacsim_dev/IsaacSim/usd_tutorial/usd_data/relationships_29012026-145455.usda'
from pxr import Usd,UsdGeom,Gf,UsdLux,Sdf,UsdShade,Kind
import math
import os
import time
import random
from datetime import datetime
from omni import usd

timestemp = datetime.now().strftime('%d%m%Y-%H%M%S')
file_path = f"{usd_root}/relationships_{timestemp}.usda"
stage = usd.get_context().get_stage()
# stage = Usd.Stage.CreateNew(file_path)
world_xform = UsdGeom.Xform.Define(stage, "/World")
# Make /World a group so children can be models
Usd.ModelAPI(world_xform.GetPrim()).SetKind(Kind.Tokens.group)

# Non-model branch: Markers (utility geometry, no kind)
markers = UsdGeom.Scope.Define(stage, world_xform.GetPath().AppendChild("Markers"))

points = {
    "PointA": Gf.Vec3d(-3, 0, -3), "PointB": Gf.Vec3d(-3, 0, 3),
    "PointC": Gf.Vec3d(3, 0, -3), "PointD": Gf.Vec3d(3, 0, 3)
    }
for name, pos in points.items():
    cone = UsdGeom.Cone.Define(stage, markers.GetPath().AppendChild(name))
    cone.CreateAxisAttr(UsdGeom.Tokens.z)
    UsdGeom.XformCommonAPI(cone).SetTranslate(pos)
    cone.CreateDisplayColorPrimvar().Set([Gf.Vec3f(1.0, 0.85, 0.2)])

# Model branch: a Component we want to place as a unit
component = UsdGeom.Xform.Define(stage, world_xform.GetPath().AppendChild("Component"))
Usd.ModelAPI(component.GetPrim()).SetKind(Kind.Tokens.component)
body = UsdGeom.Cube.Define(stage, component.GetPath().AppendChild("Body"))
body.CreateDisplayColorPrimvar().Set([(0.25, 0.55, 0.85)])
UsdGeom.XformCommonAPI(body).SetScale((3.0, 1.0, 3.0))

# Model-only traversal: affect models, ignore markers
for prim in Usd.PrimRange(stage.GetPseudoRoot(), predicate=Usd.PrimIsModel):
    if prim.IsComponent():
        xformable = UsdGeom.Xformable(prim)
        if xformable:
            UsdGeom.XformCommonAPI(xformable).SetTranslate((0.0, 2.0, 0.0))

# Show which prims were considered models
model_paths = [p.GetPath().pathString for p in Usd.PrimRange(stage.GetPseudoRoot(), predicate=Usd.PrimIsModel)]
print("Model prims seen by traversal:", model_paths)



# print("\n\nStage contents AFTER deactivating:")
# for prim in stage.Traverse():
#     print(prim.GetPath())







# Save the stage
stage.Save()










# # A root transform group we will move and rotate
# world = stage.GetPseudoRoot()
# parent = UsdGeom.Xform.Define(stage, world.GetPath().AppendPath("Parent_Prim1"))

# # Parent Translate, Rotate, Scale using XformCommonAPI
# parent_xform_api = UsdGeom.XformCommonAPI(parent)
# parent_xform_api.SetTranslate(Gf.Vec3d(5, 0, 3))
# parent_xform_api.SetRotate(Gf.Vec3f(90, 0, 0))
# parent_xform_api.SetScale(Gf.Vec3f(3.0, 3.0, 3.0))


# child_translation = Gf.Vec3d(2, 0, 0)

# # Child A - inherits parent transforms
# child_a_cone = UsdGeom.Cone.Define(stage, parent.GetPath().AppendChild("Child_A"))
# child_a_xform_api = UsdGeom.XformCommonAPI(child_a_cone)
# child_a_xform_api.SetTranslate(child_translation)  # Parent_Prim transform + local placement
# # Child B - "/World/Alt_Parent/Child_B" does NOT inherit Parent_Prim transforms
# alt_parent = UsdGeom.Xform.Define(stage, world.GetPath().AppendChild("Alt_Parent1"))
# child_b_cone = UsdGeom.Cone.Define(stage, alt_parent.GetPath().AppendChild("Child_B"))
# child_b_xform_api = UsdGeom.XformCommonAPI(child_b_cone)
# child_b_xform_api.SetTranslate(child_translation)  # local placement only

# # Inspect the authored Xform Operation Order
# print("Parent xformOpOrder:", UsdGeom.Xformable(parent).GetXformOpOrderAttr().Get())
# print("Alt_Parent xformOpOrder:", UsdGeom.Xformable(alt_parent).GetXformOpOrderAttr().Get())
# print("Child A xformOpOrder:", UsdGeom.Xformable(child_a_cone).GetXformOpOrderAttr().Get())
# print("Child B xformOpOrder:", UsdGeom.Xformable(child_b_cone).GetXformOpOrderAttr().Get())

# ref_prim_path = world.GetPath().AppendChild('C919999')
# if not (ref_prim:=stage.GetPrimAtPath(ref_prim_path)).IsValid():
#     ref_prim = stage.DefinePrim(ref_prim_path)
# ref_prim.GetReferences().AddReference(ref_path)


# stage.SetDefaultPrim(ref_prim)




# stage.Save()


