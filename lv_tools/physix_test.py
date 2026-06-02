import omni.usd
from pxr import Usd,UsdGeom,UsdPhysics,PhysxSchema
stage = omni.usd.get_context().get_stage()
table_top_actor_scene_prim_path = '/World/roomScene/colliders/table/tableTopActor'

# table_px = PhysxSchema.PhysxCollisionAPI.Apply(stage.GetPrimAtPath(table_top_actor_scene_prim_path))
# table_px = PhysxSchema.PhysxRigidBodyAPI.Apply(stage.GetPrimAtPath(table_top_actor_scene_prim_path))
table_px = PhysxSchema.PhysxConvexHullCollisionAPI.Apply(stage.GetPrimAtPath(table_top_actor_scene_prim_path))
print(table_px.GetSchemaAttributeNames())


# from pxr import UsdPhysics

# api = UsdPhysics.MeshCollisionAPI.Apply(stage.GetPrimAtPath(table_top_actor_scene_prim_path))
# api = UsdPhysics.CollisionAPI.Apply(stage.GetPrimAtPath(table_top_actor_scene_prim_path))

# for name in dir(api):
#     if "Attr" in name:
#         print(name)

# print(api.GetSchemaAttributeNames())      