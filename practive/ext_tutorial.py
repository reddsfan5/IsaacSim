import numpy as np



from isaacsim.core.api.objects.ground_plane import GroundPlane
import omni.usd
from pxr import Sdf,UsdLux

from isaacsim.core.api.objects import VisualCuboid,DynamicCuboid
from isaacsim.core.prims import XFormPrim
# 1.Ground Plane
# GroundPlane(prim_path="/World/ground_plane")
# stage = omni.usd.get_context().get_stage()
# distantLight = UsdLux.DistantLight.Define(stage, Sdf.Path("/DistantLight"))
# distantLight.createIntensityAttr(300)




#2. visual cuboid
# VisualCuboid(prim_path='/visual_cube', 
#              name='visual_cube', 
#              position=np.array([0, 0.5, 0.5]), 
#              size=0.3, 
#              color=np.array([255, 255, 0]))
# VisualCuboid(prim_path='/test_cube',name='test_cube', position=np.array([0, -0.5, 0.5]), size=0.3, color=np.array([0, 255, 255]))


# ori method

# from pxr import UsdPhysics, PhysxSchema, Gf, PhysicsSchemaTools, UsdGeom
# import omni

# # USD api for getting the stage
# stage = omni.usd.get_context().get_stage()

# # Adding a Cube
# path = "/visual_cube_usd"
# cubeGeom = UsdGeom.Cube.Define(stage, path)
# cubePrim = stage.GetPrimAtPath(path)
# size = 0.5
# offset = Gf.Vec3f(1.5,-0.2,1.0)
# cubeGeom.CreateSizeAttr(size)
# if not cubePrim.HasAttribute("xformOp:translate"):
#   UsdGeom.Xformable(cubePrim).AddTranslateOp().Set(offset)
# else:
#   cubePrim.GetAttribute("xformOp:translate").Set(offset)




# DynamicCuboid(
#    prim_path="/dynamic_cube",
#    name="dynamic_cube",
#    position=np.array([0, -1.0, 1.0]),
#    scale=np.array([0.6, 0.5, 0.2]),
#    size=1.0,
#    color=np.array([255, 0, 0]),
# )

# from isaacsim.core.prims import RigidPrim
# RigidPrim("/test_cube")

# from isaacsim.core.prims import GeometryPrim
# prim = GeometryPrim("/test_cube")
# prim.apply_collision_apis()




translate_offset = np.array([[1.6,1.2,1.0]])
orientation_offset = np.array([[0.7,0.7,0,1]])     # note this is in radians
scale = np.array([[1,1.5,0.2]])

# stage = omni.usd.get_context().get_stage()
cube_in_coreapi = XFormPrim(prim_paths_expr="/test_cube")
cube_in_coreapi.set_world_poses(translate_offset, orientation_offset)
cube_in_coreapi.set_local_scales(scale)