
import numpy as np
import omni.usd
from pxr import Usd, UsdGeom


import numpy as np
from pxr import Usd, UsdGeom

def load_usd_mesh(prim_path):
    # 加载USD场景
    stage = omni.usd.get_context().get_stage()
    mesh_prim = stage.GetPrimAtPath(prim_path)  # 确定模型路径
    mesh = UsdGeom.Mesh(mesh_prim)
    
    # 获取网格数据
    points = mesh.GetPointsAttr().Get()
    face_indices = mesh.GetFaceVertexIndicesAttr().Get()
    
    # 转换为NumPy数组
    vertices = np.array(points)
    triangles = np.array(face_indices).reshape((-1, 3))
    
    return vertices, triangles

def apply_rotation(vertices, angle_deg, axis=(0, 0, 1)):
    # 将角度转换为弧度
    angle_rad = np.deg2rad(angle_deg)
    
    # 旋转矩阵（绕Z轴旋转）
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    rotation_matrix = np.array([
        [c + (1 - c) * axis[0] ** 2, (1 - c) * axis[0] * axis[1] - s * axis[2], (1 - c) * axis[0] * axis[2] + s * axis[1]],
        [(1 - c) * axis[1] * axis[0] + s * axis[2], c + (1 - c) * axis[1] ** 2, (1 - c) * axis[1] * axis[2] - s * axis[0]],
        [(1 - c) * axis[2] * axis[0] - s * axis[1], (1 - c) * axis[2] * axis[1] + s * axis[0], c + (1 - c) * axis[2] ** 2]
    ])
    
    # 应用旋转矩阵
    rotated_vertices = np.dot(vertices, rotation_matrix.T)
    
    return rotated_vertices

def check_rotation_symmetry(vertices):
    print(vertices)
    for angle in np.arange(0, 360, 3):  # 旋转步长
        print('begin')
        rotated_vertices = apply_rotation(vertices, angle)
        print('rotated',rotated_vertices)
        
        # 比较原始顶点和旋转后的顶点
        if np.allclose(vertices, rotated_vertices, atol=1e-8):  # 比较顶点位置
            return "Continuous rotation symmetry"
        print(vertices)
    
    return "Discrete rotation symmetry"

prim_path = r'/World/mesh'
# 加载USD文件并提取网格
vertices, triangles = load_usd_mesh(prim_path)

# 检查旋转对称性
result = check_rotation_symmetry(vertices)
print(result)





