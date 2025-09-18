# SPDX-FileCopyrightText: Copyright (c) 2024-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import math
import os
import random
import re
from itertools import chain

import omni.kit.app
import omni.kit.commands
import omni.physx
import omni.replicator.core as rep
import omni.timeline
import omni.usd
from isaacsim.core.utils.semantics import add_labels, remove_labels
from isaacsim.core.utils.stage import add_reference_to_stage
from isaacsim.storage.native import get_assets_root_path
from pxr import Gf, PhysxSchema, Sdf, Usd, UsdGeom, UsdPhysics


import math
import random
from typing import Tuple, List

def set_transform_attributes(
    prim: Usd.Prim,
    location: Gf.Vec3d | None = None,
    orientation: Gf.Quatf | None = None,
    rotation: Gf.Vec3f | None = None,
    scale: Gf.Vec3f | None = None,
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
    if rotation is not None:
        if not prim.HasAttribute("xformOp:rotateXYZ"):
            UsdGeom.Xformable(prim).AddRotateXYZOp()
        prim.GetAttribute("xformOp:rotateXYZ").Set(rotation)
    if scale is not None:
        if not prim.HasAttribute("xformOp:scale"):
            UsdGeom.Xformable(prim).AddScaleOp()
        prim.GetAttribute("xformOp:scale").Set(scale)


def add_colliders(root_prim: Usd.Prim, approximation_type: str = "convexHull") -> None:
    """Add collision attributes to mesh and geometry primitives under the root prim."""
    for desc_prim in Usd.PrimRange(root_prim):
        if desc_prim.IsA(UsdGeom.Gprim):
            if not desc_prim.HasAPI(UsdPhysics.CollisionAPI):
                collision_api = UsdPhysics.CollisionAPI.Apply(desc_prim)
            else:
                collision_api = UsdPhysics.CollisionAPI(desc_prim)
            collision_api.CreateCollisionEnabledAttr(True)

        if desc_prim.IsA(UsdGeom.Mesh):
            if not desc_prim.HasAPI(UsdPhysics.MeshCollisionAPI):
                mesh_collision_api = UsdPhysics.MeshCollisionAPI.Apply(desc_prim)
            else:
                mesh_collision_api = UsdPhysics.MeshCollisionAPI(desc_prim)
            mesh_collision_api.CreateApproximationAttr().Set(approximation_type)


def has_colliders(root_prim: Usd.Prim) -> bool:
    """Check if any descendant prims under the root prim have collision attributes."""
    for desc_prim in Usd.PrimRange(root_prim):
        if desc_prim.HasAPI(UsdPhysics.CollisionAPI):
            return True
    return False


def add_rigid_body_dynamics(prim: Usd.Prim, disable_gravity: bool = False) -> None:
    """Add rigid body dynamics properties to a prim if it has colliders, with optional gravity setting."""
    if has_colliders(prim):
        if not prim.HasAPI(UsdPhysics.RigidBodyAPI):
            rigid_body_api = UsdPhysics.RigidBodyAPI.Apply(prim)
        else:
            rigid_body_api = UsdPhysics.RigidBodyAPI(prim)
        rigid_body_api.CreateRigidBodyEnabledAttr(True)

        # Apply PhysX rigid body dynamics
        if not prim.HasAPI(PhysxSchema.PhysxRigidBodyAPI):
            physx_rigid_body_api = PhysxSchema.PhysxRigidBodyAPI.Apply(prim)
        else:
            physx_rigid_body_api = PhysxSchema.PhysxRigidBodyAPI(prim)
        physx_rigid_body_api.GetDisableGravityAttr().Set(disable_gravity)
    else:
        print(
            f"[SDG-Infinigen] Prim '{prim.GetPath()}' has no colliders. Skipping adding rigid body dynamics properties."
        )


def convert_rotated_location_to_abs(rotated_location):
    return rotated_location[0],rotated_location[2],-rotated_location[1]




def add_colliders_and_rigid_body_dynamics(prim: Usd.Prim, disable_gravity: bool = False) -> None:
    """Add colliders and rigid body dynamics properties to a prim, with optional gravity setting."""
    # add_colliders(prim)
    # add_rigid_body_dynamics(prim, disable_gravity)
    
    # do nothing
    # lock_rotation_axes(str(prim.GetPath()), lock_x=True, lock_y=False, lock_z=True)
    pass



# def get_random_pose_on_sphere(
#     origin: tuple[float, float, float],
#     radius_range: tuple[float, float],
#     polar_angle_range: tuple[float, float],
#     camera_forward_axis: tuple[float, float, float] = (0, 0, -1),
# ) -> tuple[Gf.Vec3d, Gf.Quatf]:
#     """Generate a random pose on a sphere looking at the origin, with specified radius and polar angle ranges."""
#     # https://docs.omniverse.nvidia.com/isaacsim/latest/reference_conventions.html
#     # Convert degrees to radians for polar angles (theta)
#     polar_angle_min_rad = math.radians(polar_angle_range[0])
#     polar_angle_max_rad = math.radians(polar_angle_range[1])

#     # Generate random spherical coordinates
#     radius = random.uniform(radius_range[0], radius_range[1])
#     polar_angle = random.uniform(polar_angle_min_rad, polar_angle_max_rad)
#     azimuthal_angle = random.uniform(0, 2 * math.pi)

#     # Convert spherical coordinates to Cartesian coordinates
#     x = radius * math.sin(polar_angle) * math.cos(azimuthal_angle)
#     y = radius * math.sin(polar_angle) * math.sin(azimuthal_angle)
#     z = radius * math.cos(polar_angle)

#     # Calculate the location in 3D space
#     location = Gf.Vec3d(origin[0] + x, origin[1] + y, origin[2] + z)

#     # Calculate direction vector from camera to look_at point
#     direction = Gf.Vec3d(origin) - location
#     direction_normalized = direction.GetNormalized()

#     # Calculate rotation from forward direction (rotateFrom) to direction vector (rotateTo)
#     rotation = Gf.Rotation(Gf.Vec3d(camera_forward_axis), direction_normalized)
#     orientation = Gf.Quatf(rotation.GetQuat())

#     return location, orientation


# def randomize_camera_poses(
#     cameras: list[Usd.Prim],
#     targets: list[Usd.Prim],
#     distance_range: tuple[float, float],
#     polar_angle_range: tuple[float, float] = (0, 180),
#     look_at_offset: tuple[float, float] = (-0.1, 0.1),
# ) -> None:
#     """Randomize the poses of cameras to look at random targets with adjustable distance and offset."""
#     for cam in cameras:
#         # Get a random target asset to look at
#         target_asset = random.choice(targets)

#         # Add a look_at offset so the target is not always in the center of the camera view
#         target_loc = target_asset.GetAttribute("xformOp:translate").Get()
#         target_loc = (
#             target_loc[0] + random.uniform(look_at_offset[0], look_at_offset[1]),
#             target_loc[1] + random.uniform(look_at_offset[0], look_at_offset[1]),
#             target_loc[2] + random.uniform(look_at_offset[0], look_at_offset[1]),
#         )

#         # Generate random camera pose
#         loc, quat = get_random_pose_on_sphere(target_loc, distance_range, polar_angle_range)

#         # Set the camera's transform attributes to the generated location and orientation
#         set_transform_attributes(cam, location=loc, orientation=quat)





# # Y-UP 版本
# def randomize_camera_poses(
#     cameras: list[Usd.Prim],
#     targets: list[Usd.Prim],
#     distance_range: tuple[float, float],
#     polar_angle_range: tuple[float, float] = (0, 180),
#     look_at_offset: tuple[float, float] = (-0.1, 0.1),
# ) -> None:
#     """
#     随机相机机位（Y-UP）。每个相机看向随机目标点，并在 look_at 上加少量抖动。
#     polar_angle_range: 极角 θ，单位度，0° 在 +Y，180° 在 -Y。
#     """
#     for cam in cameras:
#         target_asset = random.choice(targets)

#         # 目标点坐标，并加入轻微抖动（xyz 同范围）
#         target_loc = target_asset.GetAttribute("xformOp:translate").Get()
#         jitter = lambda: random.uniform(look_at_offset[0], look_at_offset[1])
#         target_loc = (target_loc[0] + jitter(),
#                       target_loc[1] + jitter(),
#                       target_loc[2] + jitter())

#         # 生成 Y-UP 的随机相机位姿
#         loc, quat = get_random_pose_on_sphere(
#             origin=target_loc,
#             radius_range=distance_range,
#             polar_angle_range=polar_angle_range,
#             camera_forward_axis=(0, 0, -1),  # 相机本地前向仍为 -Z
#         )

#         # 写回相机的平移与旋转（你已有的工具函数）
#         set_transform_attributes(cam, location=loc, orientation=quat)

# # Y-UP 版本
# def get_random_pose_on_sphere(
#     origin: tuple[float, float, float],
#     radius_range: tuple[float, float],
#     polar_angle_range: tuple[float, float],
#     camera_forward_axis: tuple[float, float, float] = (0, 0, -1),
# ) -> tuple[Gf.Vec3d, Gf.Quatf]:
#     """
#     生成 Y-UP 的随机机位：
#     - 极角 θ 从 +Y 量起（0°=正上方，180°=正下方）
#     - 方位角 φ 绕 Y 轴，从 +X 方向开始，右手系朝 +Z 递增
#     相机朝向 origin。
#     """
#     # 角度转弧度
#     theta_min = math.radians(polar_angle_range[0])   # 极角 θ
#     theta_max = math.radians(polar_angle_range[1])
#     theta = random.uniform(theta_min, theta_max)

#     phi = random.uniform(0.0, 2.0 * math.pi)         # 方位角 φ
#     r = random.uniform(radius_range[0], radius_range[1])

#     # Y-UP 的球坐标到笛卡尔
#     x = r * math.sin(theta) * math.cos(phi)
#     y = r * math.cos(theta)               # Y 为极轴
#     z = r * math.sin(theta) * math.sin(phi)

#     location = Gf.Vec3d(origin[0] + x, origin[1] + y, origin[2] + z)

#     # look-at 朝向
#     direction = Gf.Vec3d(origin) - location
#     direction_normalized = direction.GetNormalized()

#     # 将相机“前向向量”（默认 -Z）旋到目标方向
#     rotation = Gf.Rotation(Gf.Vec3d(camera_forward_axis), direction_normalized)
#     orientation = Gf.Quatf(rotation.GetQuat())

#     return location, orientation






# ------------------------------------------------------------
## 公共小工具
# ------------------------------------------------------------
def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def _safe_normalize(v: Gf.Vec3d) -> Gf.Vec3d:
    l = v.GetLength()
    if l < 1e-12:
        return Gf.Vec3d(0.0, 0.0, 0.0)
    return v / l

def _signed_angle_deg(a: Gf.Vec3d, b: Gf.Vec3d, axis: Gf.Vec3d) -> float:
    """返回从 a 旋到 b 围绕 axis 的有符号角度（度）。"""
    a_n = _safe_normalize(a)
    b_n = _safe_normalize(b)
    axis_n = _safe_normalize(axis)
    cross = a_n ^ b_n  # 向量叉乘（Gf 使用 ^）
    dot = _clamp01(a_n * b_n)  # 点乘（范围到 [0,1] 防数值误差）
    unsigned = math.degrees(math.atan2(_safe_normalize(cross).GetLength() * (a_n ^ b_n).GetLength(), dot)) if dot < 1.0 else 0.0
    # 符号由 right-hand rule 决定：axis · (a × b)
    sign = 1.0 if (axis_n * cross) >= 0.0 else -1.0
    return unsigned * sign

# # ------------------------------------------------------------
# # 生成机位（Y-UP）
# ------------------------------------------------------------
def get_random_pose_on_sphere(
    origin: Tuple[float, float, float],
    radius_range: Tuple[float, float],
    polar_angle_range: Tuple[float, float],
    camera_forward_axis: Tuple[float, float, float] = (0, 0, -1),
    keep_level: bool = False,
    world_up: Tuple[float, float, float] = (0, 1, 0),
) -> Tuple[Gf.Vec3d, Gf.Quatf]:
    """
    生成 Y-UP 场景中的随机相机位姿，使相机看向 origin。

    球坐标约定（Y 为极轴）：
      θ: 极角，0° 在 +Y，180° 在 -Y
      φ: 方位角，绕 Y 轴，从 +X 方向起，向 +Z 递增（右手系）

    返回: (location: Gf.Vec3d, orientation: Gf.Quatf)
    """
    # 1.calculate camera location on up-sphere
    # 角度转弧度
    theta_min = math.radians(polar_angle_range[0])
    theta_max = math.radians(polar_angle_range[1])
    theta = random.uniform(theta_min, theta_max)
    # phi = random.uniform(0.0, 2.0 * math.pi)
    phi = random.uniform(2.0*math.pi*265/360, 2.0*math.pi*275/360)

    # 半径
    r = random.uniform(radius_range[0], radius_range[1])

    # Y-UP 球坐标 -> 笛卡尔
    x = r * math.sin(theta) * math.cos(phi)  
    y = r * math.cos(theta)                 # 注意 Y 是极轴
    z = r * math.sin(theta) * math.sin(phi)

    location = Gf.Vec3d(origin[0] + x, origin[1] + y, origin[2] + z)




    # 2. calculate camera orientation
    # 目标方向（世界）：相机看向 origin
    forward_world = _safe_normalize(Gf.Vec3d(origin) - location)

    # 把“相机本地前向向量”旋到目标方向
    rot_to_target = Gf.Rotation(Gf.Vec3d(*camera_forward_axis), forward_world)
    quat = Gf.Quatf(rot_to_target.GetQuat())

    if keep_level:
        # 以世界 up（默认 (0,1,0)）来最小化滚转，使相机尽量“水平”
        world_up_v = _safe_normalize(Gf.Vec3d(*world_up))
        # 先用当前旋转把“相机本地 up”(0,1,0)变到世界，得到 current_up
        current_up = rot_to_target.TransformDir(Gf.Vec3d(0, 1, 0))
        current_up = _safe_normalize(current_up)

        # 目标 up = 在 forward_world 与 world_up_v 张成的平面上，与 forward 正交的单位向量
        right_world = _safe_normalize(forward_world ^ world_up_v)  # forward × up
        if right_world.GetLength() > 1e-6:
            desired_up = _safe_normalize(right_world ^ forward_world)  # right × forward
            # 围绕 forward 轴修正 current_up -> desired_up 的夹角
            angle = _signed_angle_deg(current_up, desired_up, forward_world)
            twist = Gf.Rotation(forward_world, angle)
            twist_quat = Gf.Quatf(twist.GetQuat())
            quat = twist_quat * quat  # 先旋到目标，再绕前向轴微调
        # 若 forward 与 world_up 几乎平行，跳过修正以避免数值不稳

    return location, quat


def randomize_camera_poses(
    cameras: List[Usd.Prim],
    targets: List[Usd.Prim],
    distance_range: Tuple[float, float],
    polar_angle_range: Tuple[float, float] = (0, 180),
    look_at_offset: Tuple[float, float] = (-0.1, 0.1),
    keep_level: bool = False,
) -> None:
    """
    为一组相机生成随机机位（Y-UP）。每台相机看向随机目标点。
      - distance_range: (近, 远)
      - polar_angle_range: (θ_min°, θ_max°)；0°= +Y，180°= -Y
      - look_at_offset: 在目标点 xyz 上加入的随机抖动范围（同一范围）
      - keep_level: True 时尽量消除滚转（保持“水平感”）
    """
    rnd = random.uniform  # 小写方便
    for cam in cameras:
        target = random.choice(targets)

        # 目标点与轻微抖动
        tgt = target.GetAttribute("xformOp:translate").Get()
        jitter = lambda: rnd(look_at_offset[0], look_at_offset[1])
        look_at = (tgt[0] + jitter(), tgt[1] + jitter(), tgt[2] + jitter())

        # 随机机位（Y-UP）
        loc, quat = get_random_pose_on_sphere(
            origin=look_at,
            radius_range=distance_range,
            polar_angle_range=polar_angle_range,
            camera_forward_axis=(0, 0, -1),   # USD 相机默认前向 -Z
            keep_level=keep_level,
            world_up=(0, 1, 0),
        )

        # 写回（此函数由isaacsim项目里提供）
        set_transform_attributes(cam, location=loc, orientation=quat)











def get_usd_paths_from_folder(
    folder_path: str, recursive: bool = True, usd_paths: list[str] = None, skip_keywords: list[str] = None
) -> list[str]:
    """Retrieve USD file paths from a folder, optionally searching recursively and filtering by keywords."""
    if usd_paths is None:
        usd_paths = []
    skip_keywords = skip_keywords or []

    # Make sure the omni.client extension is enabled
    import omni.kit.app

    ext_manager = omni.kit.app.get_app().get_extension_manager()
    if not ext_manager.is_extension_enabled("omni.client"):
        ext_manager.set_extension_enabled_immediate("omni.client", True)
    import omni.client

    result, entries = omni.client.list(folder_path)
    if result != omni.client.Result.OK:
        print(f"[SDG-Infinigen] Could not list assets in path: {folder_path}")
        return usd_paths

    for entry in entries:
        if any(keyword.lower() in entry.relative_path.lower() for keyword in skip_keywords):
            continue
        _, ext = os.path.splitext(entry.relative_path)
        if ext in [".usd", ".usda", ".usdc"]:
            path_posix = os.path.join(folder_path, entry.relative_path).replace("\\", "/")
            usd_paths.append(path_posix)
        elif recursive and entry.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN:
            sub_folder = os.path.join(folder_path, entry.relative_path).replace("\\", "/")
            get_usd_paths_from_folder(sub_folder, recursive=recursive, usd_paths=usd_paths, skip_keywords=skip_keywords)

    return usd_paths


def get_usd_paths(
    files: list[str] = None, folders: list[str] = None, skip_folder_keywords: list[str] = None
) -> list[str]:
    """Retrieve USD paths from specified files and folders, optionally filtering out specific folder keywords."""
    files = files or []
    folders = folders or []
    skip_folder_keywords = skip_folder_keywords or []

    # assets_root_path = '/home/ubuntu/lxd/usd_file/infinigen_assets'
    assets_root_path = get_assets_root_path()
    env_paths = []

    for file_path in files:
        file_path = (
            file_path
            if file_path.startswith(("omniverse://", "http://", "https://", "file://"))
            else assets_root_path + file_path
        )
        env_paths.append(file_path)

    for folder_path in folders:
        folder_path = (
            folder_path
            if folder_path.startswith(("omniverse://", "http://", "https://", "file://"))
            else assets_root_path + folder_path
        )
        env_paths.extend(get_usd_paths_from_folder(folder_path, recursive=True, skip_keywords=skip_folder_keywords))

    return env_paths


def load_env(usd_path: str, prim_path: str, remove_existing: bool = True) -> Usd.Prim:
    """Load an environment from a USD file into the stage at the specified prim path, optionally removing any existing prim."""
    stage = omni.usd.get_context().get_stage()

    # Remove existing prim if specified
    if remove_existing and stage.GetPrimAtPath(prim_path):
        omni.kit.commands.execute("DeletePrimsCommand", paths=[prim_path])

    root_prim = add_reference_to_stage(usd_path=usd_path, prim_path=prim_path)
    return root_prim


def add_colliders_to_env(root_path: str | None = None, approximation_type: str = "none") -> None:
    """Add colliders to all mesh prims within the specified root path in the stage."""
    stage = omni.usd.get_context().get_stage()
    prim = stage.GetPseudoRoot() if root_path is None else stage.GetPrimAtPath(root_path)

    for prim in Usd.PrimRange(prim):
        if prim.IsA(UsdGeom.Mesh):
            add_colliders(prim, approximation_type)


def find_matching_prims(
    match_strings: list[str], root_path: str | None = None, prim_type: str | None = None, first_match_only: bool = False
) -> Usd.Prim | list[Usd.Prim] | None:
    """Find prims matching specified strings, with optional type filtering and single match return."""
    stage = omni.usd.get_context().get_stage()
    root_prim = stage.GetPseudoRoot() if root_path is None else stage.GetPrimAtPath(root_path)

    matching_prims = []
    for prim in Usd.PrimRange(root_prim):
        if any(match in str(prim.GetPath()) for match in match_strings):
            if prim_type is None or prim.GetTypeName() == prim_type:
                if first_match_only:
                    return prim
                matching_prims.append(prim)

    return matching_prims if not first_match_only else None


def hide_matching_prims(match_strings: list[str], root_path: str | None = None, prim_type: str | None = None) -> None:
    """Set visibility of prims matching specified strings to 'invisible' within the root path."""
    stage = omni.usd.get_context().get_stage()
    root_prim = stage.GetPseudoRoot() if root_path is None else stage.GetPrimAtPath(root_path)

    for prim in Usd.PrimRange(root_prim):
        if prim_type is None or prim.GetTypeName() == prim_type:
            if any(match in str(prim.GetPath()) for match in match_strings):
                prim.GetAttribute("visibility").Set("invisible")


def setup_env(root_path: str | None = None, approximation_type: str = "none", hide_top_walls: bool = False) -> None:
    """Set up the environment with colliders, ceiling light adjustments, and optional top wall hiding."""
    # Fix ceiling lights: meshes are blocking the light and need to be set to invisible
    ceiling_light_meshes = find_matching_prims(["001_SPLIT_GLA"], root_path, "Xform")
    for light_mesh in ceiling_light_meshes:
        light_mesh.GetAttribute("visibility").Set("invisible")

    # Hide ceiling light meshes for lighting fix
    hide_matching_prims(["001_SPLIT_GLA"], root_path, "Xform")

    # Hide top walls for better debug view, if specified
    if hide_top_walls:
        hide_matching_prims(["_exterior", "_ceiling"], root_path)

    # Add colliders to the environment
    add_colliders_to_env(root_path, approximation_type)

    # Fix dining table collision by setting it to a bounding cube approximation
    table_prim = find_matching_prims(
        match_strings=["TableDining"], root_path=root_path, prim_type="Xform", first_match_only=True
    )
    if table_prim is not None:
        add_colliders(table_prim, approximation_type="boundingCube")
    else:
        print("[SDG-Infinigen] Could not find dining table prim in the environment.")


def create_shape_distractors(
    num_distractors: int, shape_types: list[str], root_path: str, gravity_disabled_chance: float
) -> tuple[list[Usd.Prim], list[Usd.Prim]]:
    """Create shape distractors with optional gravity settings, returning lists of floating and falling shapes."""
    stage = omni.usd.get_context().get_stage()
    floating_shapes = []
    falling_shapes = []
    for _ in range(num_distractors):
        rand_shape = random.choice(shape_types)
        disable_gravity = random.random() < gravity_disabled_chance
        name_prefix = "floating_" if disable_gravity else "falling_"
        prim_path = omni.usd.get_stage_next_free_path(stage, f"{root_path}/{name_prefix}{rand_shape}", False)
        prim = stage.DefinePrim(prim_path, rand_shape.capitalize())
        add_colliders_and_rigid_body_dynamics(prim, disable_gravity=disable_gravity)
        (floating_shapes if disable_gravity else falling_shapes).append(prim)
    return floating_shapes, falling_shapes


def load_shape_distractors(shape_distractors_config: dict) -> tuple[list[Usd.Prim], list[Usd.Prim]]:
    """Load shape distractors based on configuration, returning lists of floating and falling shapes."""
    num_shapes = shape_distractors_config.get("num", 0)
    shape_types = shape_distractors_config.get("shape_types", ["capsule", "cone", "cylinder", "sphere", "cube"])
    shape_gravity_disabled_chance = shape_distractors_config.get("gravity_disabled_chance", 0.0)
    return create_shape_distractors(num_shapes, shape_types, "/Distractors", shape_gravity_disabled_chance)


def create_mesh_distractors(
    num_distractors: int, mesh_urls: list[str], root_path: str, gravity_disabled_chance: float
) -> tuple[list[Usd.Prim], list[Usd.Prim]]:
    """Create mesh distractors from specified URLs with optional gravity settings."""
    stage = omni.usd.get_context().get_stage()
    floating_meshes = []
    falling_meshes = []
    for _ in range(num_distractors):
        rand_mesh_url = random.choice(mesh_urls)
        disable_gravity = random.random() < gravity_disabled_chance
        name_prefix = "floating_" if disable_gravity else "falling_"
        prim_name = os.path.basename(rand_mesh_url).split(".")[0]
        prim_path = omni.usd.get_stage_next_free_path(stage, f"{root_path}/{name_prefix}{prim_name}", False)
        try:
            prim = add_reference_to_stage(usd_path=rand_mesh_url, prim_path=prim_path)
        except Exception as e:
            print(f"[SDG-Infinigen] Failed to load mesh distractor reference {rand_mesh_url} with exception: {e}")
            continue
        add_colliders_and_rigid_body_dynamics(prim, disable_gravity=disable_gravity)
        (floating_meshes if disable_gravity else falling_meshes).append(prim)
    return floating_meshes, falling_meshes


def load_mesh_distractors(mesh_distractors_config: dict) -> tuple[list[Usd.Prim], list[Usd.Prim]]:
    """Load mesh distractors based on configuration, returning lists of floating and falling meshes."""
    num_meshes = mesh_distractors_config.get("num", 0)
    mesh_gravity_disabled_chance = mesh_distractors_config.get("gravity_disabled_chance", 0.0)
    mesh_folders = mesh_distractors_config.get("folders", [])
    mesh_files = mesh_distractors_config.get("files", [])
    mesh_urls = get_usd_paths(
        files=mesh_files, folders=mesh_folders, skip_folder_keywords=["material", "texture", ".thumbs"]
    )
    floating_meshes, falling_meshes = create_mesh_distractors(
        num_meshes, mesh_urls, "/Distractors", mesh_gravity_disabled_chance
    )
    for prim in chain(floating_meshes, falling_meshes):
        remove_labels(prim, include_descendants=True)
    return floating_meshes, falling_meshes


def create_auto_labeled_assets(
    num_assets: int,
    asset_urls: list[str],
    root_path: str,
    regex_replace_pattern: str,
    regex_replace_repl: str,
    gravity_disabled_chance: float,
) -> tuple[list[Usd.Prim], list[Usd.Prim]]:
    """Create assets with automatic labels, applying optional gravity settings."""
    stage = omni.usd.get_context().get_stage()
    floating_assets = []
    falling_assets = []
    for _ in range(num_assets):
        asset_url = random.choice(asset_urls)
        disable_gravity = random.random() < gravity_disabled_chance
        name_prefix = "floating_" if disable_gravity else "falling_"
        basename = os.path.basename(asset_url)
        name_without_ext = os.path.splitext(basename)[0]
        label = re.sub(regex_replace_pattern, regex_replace_repl, name_without_ext)
        prim_path = omni.usd.get_stage_next_free_path(stage, f"{root_path}/{name_prefix}{label}", False)
        try:
            prim = add_reference_to_stage(usd_path=asset_url, prim_path=prim_path)
        except Exception as e:
            print(f"[SDG-Infinigen] Failed to load mesh distractor reference {asset_url} with exception: {e}")
            continue
        add_colliders_and_rigid_body_dynamics(prim, disable_gravity=disable_gravity)
        remove_labels(prim, include_descendants=True)
        add_labels(prim, labels=[label], instance_name="class")
        (floating_assets if disable_gravity else falling_assets).append(prim)
    return floating_assets, falling_assets


def load_auto_labeled_assets(auto_label_config: dict) -> tuple[list[Usd.Prim], list[Usd.Prim]]:
    """Load auto-labeled assets based on configuration, returning lists of floating and falling assets."""
    num_assets = auto_label_config.get("num", 0)
    gravity_disabled_chance = auto_label_config.get("gravity_disabled_chance", 0.0)
    assets_files = auto_label_config.get("files", [])
    assets_folders = auto_label_config.get("folders", [])
    assets_urls = get_usd_paths(
        files=assets_files, folders=assets_folders, skip_folder_keywords=["material", "texture", ".thumbs"]
    )
    regex_replace_pattern = auto_label_config.get("regex_replace_pattern", "")
    regex_replace_repl = auto_label_config.get("regex_replace_repl", "")
    return create_auto_labeled_assets(
        num_assets,
        assets_urls,
        "/Assets",
        regex_replace_pattern,
        regex_replace_repl,
        gravity_disabled_chance,
    )


def create_labeled_assets(
    num_assets: int, asset_url: str, label: str, root_path: str, gravity_disabled_chance: float
) -> tuple[list[Usd.Prim], list[Usd.Prim]]:
    """Create labeled assets with optional gravity settings, returning lists of floating and falling assets."""
    stage = omni.usd.get_context().get_stage()
    assets_root_path = get_assets_root_path()
    asset_url = (
        asset_url
        if asset_url.startswith(("omniverse://", "http://", "https://", "file://"))
        else assets_root_path + asset_url
    )
    floating_assets = []
    falling_assets = []
    for _ in range(num_assets):
        disable_gravity = random.random() < gravity_disabled_chance
        name_prefix = "floating_" if disable_gravity else "falling_"
        prim_path = omni.usd.get_stage_next_free_path(stage, f"{root_path}/{name_prefix}{label}", False)

        prim = add_reference_to_stage(usd_path=asset_url, prim_path=prim_path)
        add_colliders_and_rigid_body_dynamics(prim, disable_gravity=disable_gravity)
        
        
        
        
        remove_labels(prim, include_descendants=True)
        add_labels(prim, labels=[label], instance_name="class")
        (floating_assets if disable_gravity else falling_assets).append(prim)
    return floating_assets, falling_assets


def load_manual_labeled_assets(manual_labeled_assets_config: list[dict]) -> tuple[list[Usd.Prim], list[Usd.Prim]]:
    """Load manually labeled assets based on configuration, returning lists of floating and falling assets."""
    labeled_floating_assets = []
    labeled_falling_assets = []
    for labeled_asset_config in manual_labeled_assets_config:
        asset_url = labeled_asset_config.get("url", "")
        asset_label = labeled_asset_config.get("label", "")
        num_assets = labeled_asset_config.get("num", 0)
        gravity_disabled_chance = labeled_asset_config.get("gravity_disabled_chance", 0.0)
        floating_assets, falling_assets = create_labeled_assets(
            num_assets,
            asset_url,
            asset_label,
            "/Assets",
            gravity_disabled_chance,
        )
        labeled_floating_assets.extend(floating_assets)
        labeled_falling_assets.extend(falling_assets)
    return labeled_floating_assets, labeled_falling_assets


def resolve_scale_issues_with_metrics_assembler() -> None:
    """Enable and execute metrics assembler to resolve scale issues in the stage."""
    import omni.kit.app

    ext_manager = omni.kit.app.get_app().get_extension_manager()
    if not ext_manager.is_extension_enabled("omni.usd.metrics.assembler"):
        ext_manager.set_extension_enabled_immediate("omni.usd.metrics.assembler", True)
    from omni.metrics.assembler.core import get_metrics_assembler_interface

    stage_id = omni.usd.get_context().get_stage_id()
    get_metrics_assembler_interface().resolve_stage(stage_id)


def get_matching_prim_location(match_string, root_path=None):
    prim = find_matching_prims(
        match_strings=[match_string], root_path=root_path, prim_type="Xform", first_match_only=True
    )
    if prim is None:
        print(f"[SDG-Infinigen] Could not find matching prim, returning (0, 0, 0)")
        return (0, 0, 0)
    if prim.HasAttribute("xformOp:translate"):
        return prim.GetAttribute("xformOp:translate").Get()
    elif prim.HasAttribute("xformOp:transform"):
        return prim.GetAttribute("xformOp:transform").Get().ExtractTranslation()
    else:
        print(f"[SDG-Infinigen] Could not find location attribute for '{prim.GetPath()}', returning (0, 0, 0)")
        return (0, 0, 0)


def offset_range(
    range_coords: tuple[float, float, float, float, float, float], offset: tuple[float, float, float]
) -> tuple[float, float, float, float, float, float]:
    """Offset the min and max coordinates of a range by the specified offset."""
    return (
        range_coords[0] + offset[0],  # min_x
        range_coords[1] + offset[1],  # min_y
        range_coords[2] + offset[2],  # min_z
        range_coords[3] + offset[0],  # max_x
        range_coords[4] + offset[1],  # max_y
        range_coords[5] + offset[2],  # max_z
    )


def randomize_poses(
    prims: list[Usd.Prim],
    location_range: tuple[float, float, float, float, float, float],
    rotation_range: tuple[float, float],
    scale_range: tuple[float, float],
) -> None:
    """Randomize the location, rotation, and scale of a list of prims within specified ranges."""
    for prim in prims:
        rand_loc = (
            random.uniform(location_range[0], location_range[3]),
            random.uniform(location_range[1], location_range[4]),
            random.uniform(location_range[2], location_range[5]),
        )
        rand_rot = (
            random.uniform(rotation_range[0], rotation_range[1]),
            random.uniform(rotation_range[0], rotation_range[1]),
            random.uniform(rotation_range[0], rotation_range[1]),
        )
        rand_scale = random.uniform(scale_range[0], scale_range[1])
        set_transform_attributes(prim, location=rand_loc, rotation=rand_rot, scale=(rand_scale, rand_scale, rand_scale))


def run_simulation(num_frames: int, render: bool = True) -> None:
    """Run a simulation for a specified number of frames, optionally without rendering."""
    if render:
        # Start the timeline and advance the app, this will render the physics simulation results every frame
        timeline = omni.timeline.get_timeline_interface()
        timeline.set_start_time(0)
        timeline.set_end_time(1000000)
        timeline.set_looping(False)
        timeline.play()
        for _ in range(num_frames):
            omni.kit.app.get_app().update()
        timeline.pause()
    else:
        # Run the physics simulation steps without advancing the app
        stage = omni.usd.get_context().get_stage()
        physx_scene = None

        # Search for or create a physics scene
        for prim in stage.Traverse():


            if prim.IsA(UsdPhysics.Scene):

                import ctypes
                # todo lv
                physx_scene = PhysxSchema.PhysxSceneAPI.Apply(prim)
                physx_scene.CreateGpuTempBufferCapacityAttr(2 * 1024 **3)
                # 计算4GB对应的字节数（4,294,967,296），但需确保不超过uint32上限
                heap_capacity = 4 * 1024**3  # 等同于 4294967296
                if heap_capacity <= 0xFFFFFFFF:  # 检查是否在uint32范围内
                    physx_scene.CreateGpuHeapCapacityAttr(int(heap_capacity))
                else:
                    # 动态调整为最大允许值
                    physx_scene.CreateGpuHeapCapacityAttr(0xFFFFFFFF)
                break

        if physx_scene is None:
            physics_scene = UsdPhysics.Scene.Define(stage, "/PhysicsScene")
            physx_scene = PhysxSchema.PhysxSceneAPI.Apply(stage.GetPrimAtPath("/PhysicsScene"))


        # Get simulation parameters
        physx_dt = 1 / physx_scene.GetTimeStepsPerSecondAttr().Get()
        physx_sim_interface = omni.physx.get_physx_simulation_interface()

        # Run physics simulation for each frame
        for _ in range(num_frames):
            physx_sim_interface.simulate(physx_dt, 0)
            physx_sim_interface.fetch_results()


def register_dome_light_randomizer() -> None:
    """Register a replicator graph randomizer for dome lights using various sky textures."""
    assets_root_path = get_assets_root_path()
    dome_textures = [
        assets_root_path + "/NVIDIA/Assets/Skies/Cloudy/champagne_castle_1_4k.hdr",
        assets_root_path + "/NVIDIA/Assets/Skies/Cloudy/kloofendal_48d_partly_cloudy_4k.hdr",
        assets_root_path + "/NVIDIA/Assets/Skies/Clear/evening_road_01_4k.hdr",
        assets_root_path + "/NVIDIA/Assets/Skies/Clear/mealie_road_4k.hdr",
        assets_root_path + "/NVIDIA/Assets/Skies/Clear/qwantani_4k.hdr",
        assets_root_path + "/NVIDIA/Assets/Skies/Clear/noon_grass_4k.hdr",
        assets_root_path + "/NVIDIA/Assets/Skies/Evening/evening_road_01_4k.hdr",
        assets_root_path + "/NVIDIA/Assets/Skies/Night/kloppenheim_02_4k.hdr",
        assets_root_path + "/NVIDIA/Assets/Skies/Night/moonlit_golf_4k.hdr",
    ]
    with rep.trigger.on_custom_event(event_name="randomize_dome_lights"):
        rep.create.light(light_type="Dome", texture=rep.distribution.choice(dome_textures))


def register_shape_distractors_color_randomizer(shape_distractors: list[Usd.Prim]) -> None:
    """Register a replicator graph randomizer to change colors of shape distractors."""
    with rep.trigger.on_custom_event(event_name="randomize_shape_distractor_colors"):
        shape_distractors_paths = [prim.GetPath() for prim in shape_distractors]
        shape_distractors_group = rep.create.group(shape_distractors_paths)
        with shape_distractors_group:
            rep.randomizer.color(colors=rep.distribution.uniform((0, 0, 0), (1, 1, 1)))


def randomize_lights(
    lights: list[Usd.Prim],
    location_range: tuple[float, float, float, float, float, float] | None = None,
    color_range: tuple[float, float, float, float, float, float] | None = None,
    intensity_range: tuple[float, float] | None = None,
) -> None:
    """Randomize location, color, and intensity of specified lights within given ranges."""
    for light in lights:
        # Randomize the location of the light
        if location_range is not None:
            rand_loc = (
                random.uniform(location_range[0], location_range[3]),
                random.uniform(location_range[1], location_range[4]),
                random.uniform(location_range[2], location_range[5]),
            )
            set_transform_attributes(light, location=rand_loc)

        # Randomize the color of the light
        if color_range is not None:
            rand_color = (
                random.uniform(color_range[0], color_range[3]),
                random.uniform(color_range[1], color_range[4]),
                random.uniform(color_range[2], color_range[5]),
            )
            light.GetAttribute("inputs:color").Set(rand_color)

        # Randomize the intensity of the light
        if intensity_range is not None:
            rand_intensity = random.uniform(intensity_range[0], intensity_range[1])
            light.GetAttribute("inputs:intensity").Set(rand_intensity)


def setup_writer(config: dict) -> None:
    """Setup a writer based on configuration settings, initializing with specified arguments."""
    writer_type = config.get("type", None)
    if writer_type is None:
        print("[Infinigen-SDG] No writer type specified. No writer will be used.")
        return None

    try:
        writer = rep.writers.get(writer_type)
    except Exception as e:
        print(f"[Infinigen-SDG] Writer type '{writer_type}' not found. No writer will be used. Error: {e}")
        return None

    writer_kwargs = config.get("kwargs", {})
    if out_dir := writer_kwargs.get("output_dir"):
        # If not an absolute path, make path relative to the current working directory
        if not os.path.isabs(out_dir):
            out_dir = os.path.join(os.getcwd(), out_dir)
            writer_kwargs["output_dir"] = out_dir

    writer.initialize(**writer_kwargs)
    return writer





# ---- 常量：按位标志（X/Y/Z） ----
AXIS_X = 1 << 0  # 1
AXIS_Y = 1 << 1  # 2
AXIS_Z = 1 << 2  # 4

def _get_stage():
    return omni.usd.get_context().get_stage()

def _ensure_rigid_physx_api(prim):
    # 确保挂上 RigidBody 和 PhysX 扩展属性（幂等；已存在则忽略）
    UsdPhysics.RigidBodyAPI.Apply(prim)
    PhysxSchema.PhysxRigidBodyAPI.Apply(prim)
    return PhysxSchema.PhysxRigidBodyAPI.Get(prim.GetStage(), prim.GetPath())

def lock_rotation_axes(prim_path: str, lock_x: bool, lock_y: bool, lock_z: bool):
    """
    锁定刚体的旋转轴（世界坐标系）。例如：lock_x=True, lock_y=False, lock_z=True -> 只允许绕Y旋转。
    """
    stage = _get_stage()
    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        raise RuntimeError(f"Prim 不存在: {prim_path}")

    api = _ensure_rigid_physx_api(prim)

    mask = 0
    if lock_x: mask |= AXIS_X
    if lock_y: mask |= AXIS_Y
    if lock_z: mask |= AXIS_Z

    # 写入 lockedRotAxis（int bitmask）
    api.CreateLockedRotAxisAttr().Set(mask)

def set_angular_damping(prim_path: str, damping: float):
    """
    设置角阻尼（无单位量纲，典型取值 0.05~2.0；越大旋转衰减越快）。
    """
    stage = _get_stage()
    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        raise RuntimeError(f"Prim 不存在: {prim_path}")

    api = _ensure_rigid_physx_api(prim)
    api.CreateAngularDampingAttr().Set(float(damping))

def set_max_angular_velocity(prim_path: str, max_deg_per_s: float):
    """
    限制最大角速度（单位：度/秒）。例如 360 表示每秒上限 360°。
    """
    stage = _get_stage()
    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        raise RuntimeError(f"Prim 不存在: {prim_path}")

    api = _ensure_rigid_physx_api(prim)
    api.CreateMaxAngularVelocityAttr().Set(float(max_deg_per_s))

"""
ASSET = "/World/Asset"  # 你的刚体 prim 路径

# 1) 锁定旋转：锁 X、Z，只允许绕 Y（适合 Y-up 的场景防“侧翻”）
lock_rotation_axes(ASSET, lock_x=True, lock_y=False, lock_z=True)

# 2) 提高角阻尼（更快止转）
set_angular_damping(ASSET, damping=1.0)

# 3) 限制最大角速度（避免瞬时碰撞导致夸张旋转）
set_max_angular_velocity(ASSET, max_deg_per_s=360.0)

"""

