from pxr import UsdGeom
import omni.usd
FALLBACK_AXIS = "Z"                      # 回退平面投影轴：'X' / 'Y' / 'Z'
UV_SET_NAME = "st"                       # 标准 UV 名

def has_valid_uv(mesh_prim, uv_name=UV_SET_NAME):
    primvars_api = UsdGeom.PrimvarsAPI(mesh_prim)
    if not primvars_api.HasPrimvar(uv_name):
        return False
    pv = primvars_api.GetPrimvar(uv_name)
    if not pv or pv.GetInterpolation() not in (UsdGeom.Tokens.vertex, UsdGeom.Tokens.varying, UsdGeom.Tokens.faceVarying):
        return False
    arr = pv.GetAttr().Get()
    return bool(arr) and len(arr) > 0


# Omniverse: auto-detect meshes without UVs and generate UVs.
# - If a built-in command for UV projection is available, use it (box/planar).
# - Otherwise, fallback to a robust planar UV projection on Z axis.
#
# Usage:
#   - Select meshes, then run => only affects selection.
#   - If没有选择，将对全场景所有 Mesh 执行。
#
# Notes:
#   - 写入 primvars:st (TexCoord2fArray, interpolation=vertex)
#   - 只在没有 UV 的 Mesh 上生成（不会覆盖已有 UV）
#   - 生成后可在材质/贴图节点直接使用（TexCoord "st"）

import carb
import omni.usd
import omni.kit.commands
from pxr import Usd, UsdGeom, Gf, Sdf, Vt

# -----------------------
# Config
# -----------------------
USE_BOX_PROJECTION_IF_AVAILABLE = True   # 如果可用命令存在，优先 Box 投影
FALLBACK_AXIS = "Z"                      # 回退平面投影轴：'X' / 'Y' / 'Z'
UV_SET_NAME = "st"                       # 标准 UV 名

# -----------------------
# Helpers
# -----------------------
def _get_stage():
    ctx = omni.usd.get_context()
    return ctx.get_stage()

def _iter_target_mesh_prims(stage, only_selection=True):
    ctx = omni.usd.get_context()
    sel = ctx.get_selection().get_selected_prim_paths()
    if only_selection and sel:
        for p in sel:
            prim = stage.GetPrimAtPath(p)
            if prim and prim.IsValid():
                for sub in Usd.PrimRange(prim):
                    if sub.IsA(UsdGeom.Mesh):
                        yield sub
    else:
        for prim in stage.Traverse():
            if prim.IsA(UsdGeom.Mesh):
                yield prim

def _has_valid_uv(mesh_prim, uv_name=UV_SET_NAME):
    primvars_api = UsdGeom.PrimvarsAPI(mesh_prim)
    if not primvars_api.HasPrimvar(uv_name):
        return False
    pv = primvars_api.GetPrimvar(uv_name)
    if not pv or pv.GetInterpolation() not in (UsdGeom.Tokens.vertex, UsdGeom.Tokens.varying, UsdGeom.Tokens.faceVarying):
        return False
    arr = pv.GetAttr().Get()
    return bool(arr) and len(arr) > 0

def _bbox_local(points):
    # points: Vt.Vec3fArray
    if not points or len(points) == 0:
        return None
    mn = Gf.Vec3f(points[0])
    mx = Gf.Vec3f(points[0])
    for p in points:
        mn[0] = min(mn[0], p[0]); mn[1] = min(mn[1], p[1]); mn[2] = min(mn[2], p[2])
        mx[0] = max(mx[0], p[0]); mx[1] = max(mx[1], p[1]); mx[2] = max(mx[2], p[2])
    return mn, mx

def _planar_uv(points, axis="Z"):
    # axis: 'X', 'Y', or 'Z' — project remaining two axes into UV
    mn, mx = _bbox_local(points)
    if mn is None:
        return Vt.Vec2fArray()

    # choose components
    if axis.upper() == "Z":
        i0, i1 = 0, 1  # (x,y) -> (u,v)
    elif axis.upper() == "Y":
        i0, i1 = 0, 2  # (x,z) -> (u,v)
    else:
        i0, i1 = 1, 2  # (y,z) -> (u,v)

    span0 = max(1e-6, mx[i0] - mn[i0])
    span1 = max(1e-6, mx[i1] - mn[i1])

    uvs = Vt.Vec2fArray(len(points))
    for idx, p in enumerate(points):
        u = (p[i0] - mn[i0]) / span0
        v = (p[i1] - mn[i1]) / span1
        uvs[idx] = Gf.Vec2f(u, v)
    return uvs

def _write_uv(mesh_prim, uv_array, uv_name=UV_SET_NAME, interpolation=UsdGeom.Tokens.vertex):
    primvars_api = UsdGeom.PrimvarsAPI(mesh_prim)
    pv = primvars_api.CreatePrimvar(uv_name, Sdf.ValueTypeNames.TexCoord2fArray, interpolation)
    pv.Set(uv_array)

def _generate_uv_fallback_planar(mesh_prim, axis=FALLBACK_AXIS):
    mesh = UsdGeom.Mesh(mesh_prim)
    pts = mesh.GetPointsAttr().Get()
    if not pts:
        carb.log_warn(f"[UV Gen] {mesh_prim.GetPath()} 无顶点，跳过")
        return False
    uvs = _planar_uv(pts, axis)
    _write_uv(mesh_prim, uvs, UV_SET_NAME, UsdGeom.Tokens.vertex)
    return True

def _try_builtin_uv_projection(mesh_prim):
    """
    尝试调用可用的 UV 投影命令（若扩展支持）。
    不同版本/扩展里命令名可能不同，这里做几种常见名称的探测。
    """
    cmd_candidates = [
        # 假设存在的命令名（不同版本可能不一致）
        ("omni.kit.mesh.clip_uv_box", {"prim_path": str(mesh_prim.GetPath())}),
        ("omni.kit.mesh.create_box_uv", {"prim_path": str(mesh_prim.GetPath())}),
        ("omni.kit.commands.CreateUVs", {"prim_path": str(mesh_prim.GetPath()), "projection": "box"}),
        ("omni.kit.commands.CreateUVProjection", {"prim_path": str(mesh_prim.GetPath()), "mode": "box"}),
    ]

    for cmd, kwargs in cmd_candidates:
        try:
            if hasattr(omni.kit.commands, "has_command") and omni.kit.commands.has_command(cmd):
                omni.kit.commands.execute(cmd, **kwargs)
                return True
            # 某些环境没有 has_command，就直接硬试一次
            omni.kit.commands.execute(cmd, **kwargs)
            return True
        except Exception:
            continue
    return False

# -----------------------
# Main
# -----------------------
def run(only_selection=True):
    stage = _get_stage()
    if not stage:
        carb.log_error("[UV Gen] 无有效 Stage")
        return

    total = 0
    created = 0
    skipped_has_uv = 0
    failed = 0

    for mesh_prim in _iter_target_mesh_prims(stage, only_selection=only_selection):
        total += 1
        path = str(mesh_prim.GetPath())

        try:
            if _has_valid_uv(mesh_prim, UV_SET_NAME):
                skipped_has_uv += 1
                continue

            # 优先尝试内置投影命令
            used_builtin = False
            # if USE_BOX_PROJECTION_IF_AVAILABLE:
            #     used_builtin = _try_builtin_uv_projection(mesh_prim)

            if not used_builtin:
                # 回退到平面投影
                if not _generate_uv_fallback_planar(mesh_prim, FALLBACK_AXIS):
                    failed += 1
                    carb.log_warn(f"[UV Gen] 生成 UV 失败: {path}")
                    continue

            created += 1
            carb.log_info(f"[UV Gen] 已为 {path} 生成 UV （{'Box投影' if used_builtin else f'Planar-{FALLBACK_AXIS}'}）")

        except Exception as e:
            failed += 1
            carb.log_error(f"[UV Gen] 处理 {path} 出错: {e}")

    carb.log_info(f"[UV Gen] 完成 | 总计: {total} | 新增UV: {created} | 已有UV跳过: {skipped_has_uv} | 失败: {failed}")

# 执行：
# - 若当前有选择，将仅处理选中层级；
# - 若无选择，将处理全场景 Mesh。
run(only_selection=False)



# stage = omni.usd.get_context().get_stage()

# # mesh_prim = stage.GetPrimAtPath('/World/JJ_2_no_base/mesh')
# mesh_prim = stage.GetPrimAtPath('/World/_29_disk2_01/Mesh_0')
# print(has_valid_uv(mesh_prim))



