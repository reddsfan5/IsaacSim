from pxr import Usd, UsdGeom, Gf
import omni.usd
# Create a new stage and define a cube:
stage = omni.usd.get_context().get_stage()

# Create a second file path and stage, define a world and a sphere:
asset_xform = UsdGeom.Xform.Define(stage, "/asset")
asset_usd_path = '/data2/isaacsim/assets/converted_usd/symmetric_cylinder_rotate_0_no_resize_smaller_rich_env-normal-test_tem/TuopanS_Mask_blue_unBottom_003.usd'
# Define a reference prim and set its translation:
reference_prim = stage.DefinePrim(asset_xform.GetPath().AppendPath("Cube_Ref"))

# Add a reference to the "cube.usda" file:
reference_prim.GetReferences().AddReference(asset_usd_path)
# Position the cube
UsdGeom.XformCommonAPI(reference_prim).SetTranslate(Gf.Vec3d(0, 0, 0))

stage.Save()