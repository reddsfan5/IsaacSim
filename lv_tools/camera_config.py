import omni.usd
import isaacsim.core.utils.prims as prims_utils

stage = omni.usd.get_context().get_stage()
cam_prim = stage.DefinePrim(f"/Cameras/cam_1", "Camera")
print(cam_prim.GetPath())
# cam_prim.GetAttribute("clippingRange").Set((0.25, 1000))
value = prims_utils.get_prim_attribute_names(prim_path=cam_prim.GetPath())
print(value)
value = prims_utils.get_prim_attribute_value(prim_path=cam_prim.GetPath(), attribute_name='horizontalAperture')
cam_prim.GetAttribute("verticalAperture").Set(24.0)
cam_prim.GetAttribute("horizontalAperture").Set(36.0)
cam_prim.GetAttribute("focalLength").Set(34.0)



# cam_prim.GetAttribute("clippingRange").Set((0.25, 1000))


# cam_prim.GetFocalLengthAttr().Set(24.0)