import omni
from pxr import UsdGeom, Gf, UsdPhysics, PhysxSchema

def create_stage():
    ctx = omni.usd.get_context()
    stage = ctx.get_stage()

    # 清空场景
    stage.DefinePrim("/World", "Xform")
    stage.SetDefaultPrim(stage.GetPrimAtPath("/World"))

    return stage

def add_ground(stage):
    """静态地面 + 碰撞体"""
    plane = stage.DefinePrim("/World/Ground", "Xform")
    UsdGeom.Mesh.Define(stage, "/World/Ground/mesh")

    # 创建可视化平面
    UsdGeom.Mesh.Get(stage, "/World/Ground/mesh").CreateExtentAttr([(-500,-500,0), (500,500,0)])
    UsdGeom.Mesh.Get(stage, "/World/Ground/mesh").CreatePointsAttr([
        (-500, -500, 0),
        (500, -500, 0),
        (500, 500, 0),
        (-500, 500, 0),
    ])
    UsdGeom.Mesh.Get(stage, "/World/Ground/mesh").CreateFaceVertexCountsAttr([4])
    UsdGeom.Mesh.Get(stage, "/World/Ground/mesh").CreateFaceVertexIndicesAttr([0,1,2,3])

    # 添加碰撞体
    UsdPhysics.CollisionAPI.Apply(plane)
    PhysxSchema.PhysxCollisionAPI.Apply(plane)

    return plane

def add_falling_box(stage):
    """动态立方体 + 碰撞体 + 刚体"""
    cube = UsdGeom.Cube.Define(stage, "/World/Box")
    cube.AddTranslateOp().Set(Gf.Vec3f(0, 0, 50))  # 放高一点让它掉落

    prim = stage.GetPrimAtPath("/World/Box")

    # 添加碰撞体
    UsdPhysics.CollisionAPI.Apply(prim)
    PhysxSchema.PhysxCollisionAPI.Apply(prim)

    # 添加刚体
    UsdPhysics.RigidBodyAPI.Apply(prim)
    UsdPhysics.MassAPI.Apply(prim)

    return prim

def enable_physics(stage):
    """创建 Physics Scene（必须有，否则不会模拟）"""

    scene = UsdPhysics.Scene.Define(stage, "/World/physicsScene")
    scene.CreateGravityDirectionAttr().Set(Gf.Vec3f(0.0, 0.0, -1.0))
    scene.CreateGravityMagnitudeAttr().Set(981.0)  # 1g = 981 cm/s^2

    # 启用 PhysX
    physxScene = PhysxSchema.PhysxSceneAPI.Apply(scene.GetPrim())
    physxScene.CreateEnableCCDAttr(True)

    return scene

def run():
    stage = create_stage()
    enable_physics(stage)
    add_ground(stage)
    add_falling_box(stage)

    print("Scene ready. Press Play in the UI to see the box drop.")

run()
