import random
from pxr import Gf,UsdGeom,Usd,UsdPhysics
import omni.usd
from isaacsim.core.utils.semantics import add_labels
def set_transform_attributes(
    prim: Usd.Prim,
    location: Gf.Vec3d | None = None,
    orientation: Gf.Quatf | None = None,
    rotation: Gf.Vec3f | None = None,
    scale: Gf.Vec3f | None = None,
    rotate_order:str = "XYZ"
) -> None:
    """Set transformation attributes (location, orientation, rotation, scale) on a prim."""
    if location is not None:
        if not prim.HasAttribute("xformOp:translate"):
            UsdGeom.Xformable(prim).AddTranslateOp()
        prim.GetAttribute("xformOp:translate").Set(location)
    if orientation is not None:
        if not prim.HasAttribute("xformOp:orient"):
            UsdGeom.Xformable(prim).AddOrientOp()
        prim.GetAttribute("xformOp:orient").Set(orientation)
    # if rotation is not None:
    #     if not prim.HasAttribute(f"xformOp:rotate{rotate_order}"):

    #         UsdGeom.Xformable(prim).AddRotateXYZOp()
    #     prim.GetAttribute("xformOp:rotateXYZ").Set(rotation)

    if rotation is not None:
        if not prim.HasAttribute(f"xformOp:rotate{rotate_order}"):
            xfromable = UsdGeom.Xformable(prim)
            getattr(xfromable,f'AddRotate{rotate_order}Op')()
        prim.GetAttribute(f"xformOp:rotate{rotate_order}").Set(rotation)


    if scale is not None:
        if not prim.HasAttribute("xformOp:scale"):
            UsdGeom.Xformable(prim).AddScaleOp()
        prim.GetAttribute("xformOp:scale").Set(scale)



def spawn_objects(stage, asset_path, count=20,label='object'):

    objs = []
    scale = 0.3
    for i in range(count):

        prim = stage.DefinePrim(f"/World/object_{i}", "Xform")
        prim.GetReferences().AddReference(asset_path)

        x = random.uniform(-2,2)
        y = random.uniform(2,4)
        z = random.uniform(-2,2)

        # xform = UsdGeom.Xformable(prim)
        set_transform_attributes(prim, location=Gf.Vec3f(x, y, z),scale=Gf.Vec3f(scale,scale,scale))

        UsdPhysics.RigidBodyAPI.Apply(prim)
        UsdPhysics.CollisionAPI.Apply(prim)
        add_labels(prim, labels=[label], instance_name="class")
        objs.append(prim)

    return objs

stage = omni.usd.get_context().get_stage()
spawn_objects(stage, "/data2/isaacsim/assets/converted_usd/symmetric_cylinder/Gangzhu_top_003.usd", count=50)