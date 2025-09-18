from pxr import Usd, UsdGeom, Gf
import omni.usd

# 设置路径
airship_path = r'/home/ubuntu/lxd/usd_file/glb/airship.usd'

# 获取当前的 stage
stage: Usd.Stage = omni.usd.get_context().get_stage()

# 获取飞机模型的 Prim
airship_prim = stage.GetPrimAtPath('/World/Cone_Xform')
print(airship_prim.IsA(UsdGeom.Xform))

if airship_prim and airship_prim.IsA(UsdGeom.Xform):
    # 获取该 Prim 下的几何体
    geom = UsdGeom.Xform(airship_prim)
    
    # 查找其子 Prim（如果存在 Mesh）
    for child in airship_prim.GetChildren():
        if child.IsA(UsdGeom.Mesh):
            mesh = UsdGeom.Mesh(child)
            
            # 计算几何体的包围盒
            bbox = mesh.ComputeWorldBound(Usd.TimeCode.Default())  # 默认时间
            print("Bounding Box:", bbox)
            break  # 找到第一个 Mesh 后跳出

else:
    print("未找到有效的 Xform 或路径错误")
