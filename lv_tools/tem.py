from pxr import Usd, UsdGeom, Gf
import omni.usd
import omni.kit.material.library as matlib
def create_cylindrical_skybox(
    prim_path="/World/SkyCylinder",
    radius=500.0,
    height=1000.0,
):
    stage = omni.usd.get_context().get_stage()

    # 创建 Cylinder
    cylinder = UsdGeom.Cylinder.Define(stage, prim_path)
    cylinder.CreateRadiusAttr(radius)
    cylinder.CreateHeightAttr(height)
    cylinder.CreateAxisAttr(UsdGeom.Tokens.y)

    # Xform（居中）
    xform = UsdGeom.Xformable(cylinder)
    xform.AddTranslateOp().Set(Gf.Vec3f(0.0, 0.0, 0.0))

    # 🔑 法线反转：让“内侧可见”
    cylinder.CreateOrientationAttr().Set(UsdGeom.Tokens.leftHanded)

    # 双面渲染，防止法线错误导致不可见
    prim = cylinder.GetPrim()
    prim.CreateAttribute("doubleSided", UsdGeom.Tokens.bool).Set(True)

    return prim
from pxr import UsdPhysics

def disable_physics_and_shadows(prim):
    # 不参与物理
    if not UsdPhysics.RigidBodyAPI(prim):
        UsdPhysics.RigidBodyAPI.Apply(prim)
    UsdPhysics.RigidBodyAPI(prim).CreateRigidBodyEnabledAttr(False)

    # 禁用碰撞
    if not UsdPhysics.CollisionAPI(prim):
        UsdPhysics.CollisionAPI.Apply(prim)
    UsdPhysics.CollisionAPI(prim).CreateCollisionEnabledAttr(False)

    # 禁用阴影
    prim.CreateAttribute(
        "primvars:doNotCastShadows",
        UsdGeom.Tokens.bool
    ).Set(True)


def bind_unlit_material(
    prim,
    color=(1.0, 1.0, 1.0),
    intensity=1.0,
):
    stage = omni.usd.get_context().get_stage()

    material_path = "/World/Looks/SkyUnlit"
    material = matlib.create_material(
        stage,
        material_path,
        matlib.MaterialTypes.UNLIT,
    )

    shader = matlib.get_shader_from_material(material)
    shader.GetInput("color").Set(color)
    shader.GetInput("intensity").Set(intensity)

    UsdGeom.MaterialBindingAPI(prim).Bind(material)
def setup_sky_cylinder():
    prim = create_cylindrical_skybox(
        radius=800.0,
        height=1600.0,
    )
    disable_physics_and_shadows(prim)
    bind_unlit_material(
        prim,
        color=(0.6, 0.7, 0.9),  # 天空色
        intensity=1.0,
    )
    print("Sky cylinder ready.")
setup_sky_cylinder()
