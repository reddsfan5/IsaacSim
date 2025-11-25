import omni
from pxr import UsdGeom, Gf, UsdPhysics, PhysxSchema,Sdf,Tf,UsdShade

stage = omni.usd.get_context().get_stage()
prim = stage.GetPrimAtPath('/World/boxActor')
# print(prim.GetPropertyNames())
# print(prim.GetProperties())
# print(prim.GetAttributes())
# print(prim.GetPropertiesInNamespace('xformOp'))
# print(prim.GetAttribute('physics:rigidBodyEnabled').Get())
# print(prim.HasAttribute('xformOp:translate'))
# print(prim.GetAttributes())
# print(prim.CreateAttribute('xformOp:translate11',Sdf.ValueTypeNames.Float3))
# print(prim.GetAllChildren())
# attr = prim.CreateAttribute(["xformOp", "translate"], Sdf.ValueTypeNames.Float3)
# attr.Set(Gf.Vec3f(0, 0, 10))
