from pxr import Usd, UsdGeom, Gf
import omni.usd
import random
import isaacsim.core.utils.prims as prims_utils
import sys
sys.path.append('/home/ubuntu/lxd/lxd_code/isaacsim')
from source.standalone_examples.replicator.infinigen.infinigen_sdg_utils import find_matching_prims
root_path = '/World'

table_prim = find_matching_prims(
    match_strings=["ChairFactory_6746123__spawn_asset_672237_"], root_path=root_path, prim_type="Xform", first_match_only=True
)
print(table_prim)
bbox_cache = UsdGeom.BBoxCache(time=Usd.TimeCode.Default(), includedPurposes=[UsdGeom.Tokens.default_])

table_world_bound_bbox = bbox_cache.ComputeWorldBound(table_prim)
table_world_bound_aligned_range = table_world_bound_bbox.ComputeAlignedRange()

table_size = table_world_bound_aligned_range.GetSize()
table_center = table_world_bound_aligned_range.GetMidpoint()
table_min = table_world_bound_aligned_range.GetMin()
table_max = table_world_bound_aligned_range.GetMax()

cube_path = '/World/cube_for_table'
air_cube_path = '/World/cube_for_airship'
air_path = '/World/AM114_33/mesh'


stage = omni.usd.get_context().get_stage()

air_prim = stage.GetPrimAtPath(air_path)

air_bbox = bbox_cache.ComputeWorldBound(air_prim)
air_range = air_bbox.ComputeAlignedRange()

air_size = air_range.GetSize()
air_center = air_range.GetMidpoint()





x_location = random.uniform(table_min[0], table_max[0])
z_location = random.uniform(table_min[2], table_max[2])


y_location = table_max[1] + air_size[1]/2
air_new_location = (x_location, y_location, z_location)

air_cube = UsdGeom.Cube.Define(stage, air_cube_path)

air_cube = UsdGeom.XformCommonAPI(air_cube)

print(air_new_location)
air_cube.SetTranslate(Gf.Vec3d(air_new_location),time=Usd.TimeCode.Default())
air_cube.SetScale(Gf.Vec3f(air_size/2),Usd.TimeCode.Default())
print(air_prim.GetParent())
xprim = air_prim.GetParent()


if not xprim.HasAttribute("xformOp:translate"):
    UsdGeom.Xformable(xprim).AddTranslateOp()
delta = air_center-xprim.GetAttribute("xformOp:translate").Get()

print(delta)

xprim.GetAttribute("xformOp:translate").Set(Gf.Vec3d(air_new_location)-delta)



# air_prim_xform = UsdGeom.XformCommonAPI(air_prim.GetParent())
# air_prim_xform.SetPivot(Gf.Vec3f(air_center),time=Usd.TimeCode.Default())
# air_prim_xform.SetTranslate(Gf.Vec3d(air_new_location),time=Usd.TimeCode.Default())
# air_prim_xform.SetScale(Gf.Vec3f(air_size),Usd.TimeCode.Default())

# air_cube.SetScale(Gf.Vec3f(air_size/2),Usd.TimeCode.Default())
# air_cube.AddTranslateOp().Set(air_new_location)
# air_cube.AddScaleOp().Set(air_size/2)







# air_cube = UsdGeom.Cube.Define(stage, air_cube_path)

# air_cube.AddTranslateOp().Set(air_center)
# air_cube.AddScaleOp().Set(air_size/2)





# cube = UsdGeom.Cube.Define(stage, cube_path)


# cube = stage.DefinePrim(cube_path, "Cube")

# cube = UsdGeom.Cube(cube)



# cube.AddTranslateOp().Set(center)
# cube.AddScaleOp().Set(table_size/2)


