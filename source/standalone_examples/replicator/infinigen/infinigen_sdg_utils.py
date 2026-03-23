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
import time
import pathlib
from networkx import radius
import numpy as np
import omni.kit.app
import omni.kit.commands
import omni.physx
import omni.replicator.core as rep
import omni.timeline
import omni.usd
from isaacsim.core.utils.semantics import add_labels,remove_all_semantics  # remove_labels
from isaacsim.core.utils.stage import add_reference_to_stage,is_stage_loading
from isaacsim.storage.native import get_assets_root_path

import urllib.parse
import sys


from pxr import Gf, PhysxSchema, Sdf, Usd, UsdGeom, UsdPhysics,UsdShade,UsdSemantics
from typing import Generator, Iterator, Union

import math
import random
from typing import Tuple, List

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



# def sphere_coord_to_world_loc(origin:tuple[float,float,float],polar:float,azimuth:float,radius:float):
#     '''
#     自定义球坐标约定（Y 为极轴）：
#       极角，0° 在 +Y，180° 在 -Y
#       方位角，绕 Y 轴，从 +X 方向起，向 +Z 递增（右手系）
#     '''

#     # 角度转弧度
#     polar = math.radians(polar)

#     azimuth = math.radians(azimuth)


#     # Y-UP 球坐标 -> 笛卡尔
#     x = radius * math.sin(polar) * math.cos(azimuth)  
#     y = radius * math.cos(polar) #  Y 是极轴
#     z = radius * math.sin(polar) * math.sin(azimuth)

#     # location = Gf.Vec3d(origin[0] + x, origin[1] + y, origin[2] + z)

#     return origin[0] + x, origin[1] + y, origin[2] + z



def sphere_coord_to_world_loc(origin:tuple[float,float,float],polar:float,azimuth:float,radius:float):
    '''
    自定义球坐标约定（Y 为极轴）：
      极角，0° 在 +Y，180° 在 -Y
      方位角，绕 Y 轴，从 +Z 方向起，向  递增（右手系）
    '''

    # 角度转弧度
    polar = math.radians(polar)

    azimuth = math.radians(azimuth)


    # Y-UP 球坐标 -> 笛卡尔
    x = radius * math.sin(polar) * math.sin(azimuth)  
    y = radius * math.cos(polar) #  Y 是极轴
    z = radius * math.sin(polar) * math.cos(azimuth)

    # location = Gf.Vec3d(origin[0] + x, origin[1] + y, origin[2] + z)

    return origin[0] + x, origin[1] + y, origin[2] + z




def get_random_sphere_coord(radius_range: Tuple[float, float], polar_range: Tuple[float, float], azimuth_range: Tuple[float, float]=(0,360)):
    # 角度转弧度
    polar_min = math.radians(polar_range[0])
    polar_max = math.radians(polar_range[1])

    polar = random.uniform(polar_min, polar_max)

    azimuth = random.uniform(2.0*math.pi*azimuth_range[0]/360, 2.0*math.pi*azimuth_range[1]/360)  # random.uniform(0.0, 2.0 * math.pi)

    # 半径
    r = random.uniform(radius_range[0], radius_range[1])

    return polar,azimuth,r


def get_random_location_around_target(
    origin: Tuple[float, float, float],
    radius_range: Tuple[float, float],
    polar_angle_range: Tuple[float, float],
    camera_azimuth_range: Tuple[float, float]=(0,360)
) -> Tuple[float,float,float]:

    polar,azimuth,radius = get_random_sphere_coord(radius_range,polar_angle_range,camera_azimuth_range)
    return sphere_coord_to_world_loc(origin,polar,azimuth,radius)


    
# 计算方位角（绕Y轴旋转）
def calculate_yaw(x0, z0, target_x, target_z):
    '''
    O-------------------------->  x
    |
    |
    |                  p
    |                  |
    |                  |
    |                  |
    |    q<------------O           
    |
    V
    Z

    
world coordinates w.r.t. unit circle coordinates
yaw = atan2(dq,dp) = atan2(dx,dz)


    '''
    # 计算目标点与相机位置在XOZ平面上的投影点
    dx =  x0 - target_x
    dz = z0 - target_z
    # 方位角 phi (绕 Y 轴旋转)
    yaw = math.atan2(dx, dz)  # 计算朝向的方位角（弧度）
    # print(f'yaw: {yaw / math.pi * 180}')  
    return yaw


# 计算俯仰角（绕X轴旋转）
def calculate_pitch(x0, y0, z0, target_x, target_y, target_z):
    # 计算目标与相机之间的距离
    dx = target_x -x0
    dy = target_y - y0
    dz = target_z -z0
    # 计算俯仰角 theta
    distance = math.sqrt(dx ** 2 + dz ** 2)
    pitch = math.atan2(dy, distance)  # 计算朝向的俯仰角（弧度）
    # print(f'pitch: {pitch / math.pi * 180}')  
    return pitch



# 主函数，计算相机的intrinsic旋转欧拉角order->Y,X,Z,then trans to extrinsic ,order -> Z,X,Y
def calculate_camera_pitch_yaw(x0, y0, z0, target_x, target_y, target_z):
    # 计算方位角和俯仰角
    # 生成 Y-UP 场景中的随机相机位姿，使相机看向 origin。
    yaw = calculate_yaw(x0,z0, target_x, target_z)
    pitch = calculate_pitch(x0, y0, z0, target_x, target_y, target_z)
    
    return pitch/math.pi*180, yaw/math.pi*180




# 计算旋转矩阵到四元数的转换（YZX顺序）
def euler_to_quaternion(roll, pitch, yaw):
    # 计算每个旋转轴的旋转矩阵
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)

    # 计算四元数（YZX 顺序）
    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy

    # 返回Gf.Quatf（四元数类型）
    return Gf.Quatf(w, x, y, z)

def camera_prim_set(cam_prim:Usd.Prim,verticalAperture:float=24.0,
                    horizontalAperture:float=36.0,
                    focalLength:float=34.0
                    ):
    cam_prim.GetAttribute("verticalAperture").Set(verticalAperture)
    cam_prim.GetAttribute("horizontalAperture").Set(horizontalAperture)
    cam_prim.GetAttribute("focalLength").Set(focalLength)



# def randomize_camera_poses(
#     cameras: List[Usd.Prim],
#     targets: List[Usd.Prim],
#     distance_range: Tuple[float, float],
#     polar_angle_range: Tuple[float, float] = (0, 180),
#     look_at_offset: Tuple[float, float] = (0,0),
#     look_at: tuple = (0,0,0),
#     camera_loc_yaw_range: Tuple[float, float]=(0,360)
    
# ) -> None:
#     """
#     为一组相机生成随机机位（Y-UP）。每台相机看向随机目标点。
#     额外增加两个极端极角下相机出现的概率。
#       - distance_range: (近, 远)
#       - polar_angle_range: (θ_min°, θ_max°)；0°= +Y，180°= -Y
#       - look_at_offset: 在目标点 xyz 上加入的随机抖动范围（同一范围）
#     """
#     rnd = random.uniform  # 小写方便
#     for cam in cameras:
#         target = random.choice(targets)

#         # 目标点与轻微抖动
#         # tgt = target.GetAttribute("xformOp:translate").Get()
#         # tgt = look_at
#         # jitter = lambda: rnd(look_at_offset[0], look_at_offset[1])
#         # look_at = (tgt[0] + jitter(), tgt[1] + jitter(), tgt[2] + jitter())

#         # 随机机位（Y-UP）
#         roll = random.uniform(-15,15)



#         if polar_angle_range[1]==90 and polar_angle_range[0]==0:
#             if random.uniform(0,1) < 0.15:
#                 cur_polar_angle_range = (0, 15)
#                 roll = random.uniform(0,360)
#             elif random.uniform(0,1) < 0.3:
#                 cur_polar_angle_range = (75, 95)
#             else:
#                 cur_polar_angle_range = polar_angle_range

#         else:
#             cur_polar_angle_range = polar_angle_range
        

        
#         loc= get_random_location_around_target(
#             origin=look_at,
#             radius_range=distance_range,
#             polar_angle_range=cur_polar_angle_range,
#             camera_azimuth_range=camera_loc_yaw_range
#         )
        
#         pitch,yaw = calculate_camera_pitch_yaw(*loc,*look_at)
#         # 写回（此函数由isaacsim项目里提供）
#         # set_transform_attributes(cam, location=loc, orientation=euler_to_quaternion(*euler_angle))
        
#         # print(f'roll:{roll}')
        
#         set_transform_attributes(cam, location=loc, rotation=Gf.Vec3d((pitch,yaw,roll)),rotate_order="ZXY")





def randomize_camera_poses(
    cameras: List[Usd.Prim],
    pose_gener:Iterator,
    look_at: tuple = (0,0,0),  
    roll_range:tuple = (-15,15),
    distance_scale:float = 1
) -> None:

    for cam in cameras:

        # 随机机位（Y-UP）
        roll = random.uniform(*roll_range)
        polar,azimuth,radius = next(pose_gener)
        radius *= distance_scale
        # too close may cause exception
        radius = max(.4,radius)
        

        print(f'polar:{polar},azimuth:{azimuth},radius:{radius}')

        loc = sphere_coord_to_world_loc(look_at,polar,azimuth,radius)  

        pitch,yaw = calculate_camera_pitch_yaw(*loc,*look_at)
        # 写回（此函数由isaacsim项目里提供）
        # set_transform_attributes(cam, location=loc, orientation=euler_to_quaternion(*euler_angle))
        
        set_transform_attributes(cam, location=loc, rotation=Gf.Vec3d((pitch,yaw,roll)),rotate_order="ZXY")











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
    
    # need internet access
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


def load_env(usd_path: str, prim_path: str,simulation_app, remove_existing: bool = True) -> Usd.Prim:
    """Load an environment from a USD file into the stage at the specified prim path, optionally removing any existing prim."""
    stage = omni.usd.get_context().get_stage()

    # Remove existing prim if specified
    if remove_existing and stage.GetPrimAtPath(prim_path):
        omni.kit.commands.execute("DeletePrimsCommand", paths=[prim_path])

    for _ in range(30):
        simulation_app.update()
    root_prim = add_reference_to_stage(usd_path=usd_path, prim_path=prim_path)
     # 3) 至少先 update 一帧，让 reference 提交
    simulation_app.update()

    # 4) 等到 stage 不再 loading
    wait_count = 0
    while is_stage_loading():
        simulation_app.update()
        wait_count += 1

    # 5) 再额外 warmup 几帧，避免刚结束 loading 就采到过渡帧
    for _ in range(3):
        simulation_app.update()
    return root_prim

def remove_prim(prim_path: str,simulation_app):
    stage = omni.usd.get_context().get_stage()

    # Remove existing prim if specified
    if stage.GetPrimAtPath(prim_path):
        omni.kit.commands.execute("DeletePrimsCommand", paths=[prim_path])
    for _ in range(30):
        simulation_app.update()


def add_static_collider(container_stage_path: str):
    """
    将 container_stage_path 设为静态碰撞体：
    - 不加 RigidBodyAPI
    - 只加 CollisionAPI
    - 若自身已有 RigidBodyAPI，则移除
    """
    stage = omni.usd.get_context().get_stage()
    prim = stage.GetPrimAtPath(container_stage_path)

    if not prim or not prim.IsValid():
        raise ValueError(f"Invalid prim path: {container_stage_path}")

    # 1) 如果 prim 自身带有 RigidBodyAPI，移除它
    if prim.HasAPI(UsdPhysics.RigidBodyAPI):
        prim.RemoveAPI(UsdPhysics.RigidBodyAPI)

    # 2) 如果 prim 自身带有 MassAPI，也建议移除，避免误导
    if prim.HasAPI(UsdPhysics.MassAPI):
        prim.RemoveAPI(UsdPhysics.MassAPI)

    # 3) 添加 CollisionAPI
    if not prim.HasAPI(UsdPhysics.CollisionAPI):
        UsdPhysics.CollisionAPI.Apply(prim)

    return prim



def add_colliders_to_env(root_path: str | None = None, approximation_type: str = "none") -> None:
    """Add colliders to all mesh prims within the specified root path in the stage."""
    stage = omni.usd.get_context().get_stage()
    prim = stage.GetPseudoRoot() if root_path is None else stage.GetPrimAtPath(root_path)

    for prim in Usd.PrimRange(prim):
        if prim.IsA(UsdGeom.Mesh):
            add_colliders(prim, approximation_type)


def find_matching_prims(
    match_strings: list[str], root_path: str | None = None, prim_type: str | None = None, first_match_only: bool = False,
    exception_prim_strings: list[str] = []
) -> Usd.Prim | list[Usd.Prim] | None:
    """Find prims matching specified strings, with optional type filtering and single match return."""
    stage = omni.usd.get_context().get_stage()
    root_prim = stage.GetPseudoRoot() if root_path is None else stage.GetPrimAtPath(root_path)

    matching_prims = []
    print(root_prim)
    for prim in Usd.PrimRange(root_prim):
        # print(str(prim.GetPath()))
        # print(str(prim.GetPath()))
        if os.path.basename(str(prim.GetPath())) in [os.path.basename(str(exp_prim_str)) for exp_prim_str in exception_prim_strings]:
            print(f"*************************移除标记好的可疑prim：{prim}***********************")
            continue
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
    ceiling_light_meshes = find_matching_prims(["001_SPLIT_GLA","PointLamp"], root_path, "Xform")

    for light_mesh in ceiling_light_meshes:
        light_mesh.GetAttribute("visibility").Set("invisible")

    # Hide ceiling light meshes for lighting fix
    hide_matching_prims(["001_SPLIT_GLA"], root_path, "Xform")

    # Hide top walls for better debug view, if specified
    if hide_top_walls:
        hide_matching_prims(["_exterior", "_ceiling"], root_path)

    # Add colliders to the environment,# todo lvxiaodng 


    
    # add_colliders_to_env(root_path, approximation_type)

    # Fix dining table collision by setting it to a bounding cube approximation
    # table_prim = find_matching_prims(
    #     match_strings=["TableDining"], root_path=root_path, prim_type="Xform", first_match_only=True
    # )
    # if table_prim is not None:
    #     add_colliders(table_prim, approximation_type="boundingCube")
    # else:
    #     print("[SDG-Infinigen] Could not find dining table prim in the environment.")


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
        remove_old_labels(prim, include_descendants=True)
        remove_new_labels(prim,include_descendants=True)
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
        remove_old_labels(prim, include_descendants=True)
        remove_new_labels(prim,include_descendants=True)
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

def valid_stage_name(name:str):
    '''
    stage path will add falling/droping to the name,so no need to add underline beforehead.
    '''
    name = name.replace("-", "_")
    valid_str = "".join(ch for ch in name if ch.isascii() and (ch.isalnum() or ch == "_"))
    return valid_str

    


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
        
        
        
        
        remove_old_labels(prim, include_descendants=True)
        remove_new_labels(prim,include_descendants=True)
        add_labels(prim, labels=[label], instance_name="class")
        (floating_assets if disable_gravity else falling_assets).append(prim)
    return floating_assets, falling_assets

def create_original_assets(
    num_assets: int, asset_url: str, label: str, root_path: str, gravity_disabled_chance: float
) -> list[Usd.Prim]:
    """Create labeled assets with optional gravity settings, returning lists of floating and falling assets."""
    stage = omni.usd.get_context().get_stage()
    assets_root_path = get_assets_root_path()
    asset_url = (
        asset_url
        if asset_url.startswith(("omniverse://", "http://", "https://", "file://"))
        else assets_root_path + asset_url
    )
    falling_assets = []
    for _ in range(num_assets):
        disable_gravity = random.random() < gravity_disabled_chance
        name_prefix = "falling_"
        prim_path = omni.usd.get_stage_next_free_path(stage, f"{root_path}/{name_prefix}{label}", False)

        prim = add_reference_to_stage(usd_path=asset_url, prim_path=prim_path)
        add_colliders_and_rigid_body_dynamics(prim, disable_gravity=disable_gravity)
        

        falling_assets.append(prim)
    return falling_assets

def load_manual_labeled_assets(manual_labeled_assets_config: list[dict]) -> tuple[list[Usd.Prim], list[Usd.Prim]]:
    """Load manually labeled assets based on configuration, returning lists of floating and falling assets."""
    labeled_floating_assets = []
    labeled_falling_assets = []
    for labeled_asset_config in manual_labeled_assets_config:
        if not labeled_asset_config:
            continue

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


def load_original_labeled_assets(original_labeled_assets_config: list[dict]) -> list[Usd.Prim]:
    """Load manually labeled assets based on configuration, returning lists of floating and falling assets."""

    labeled_assets = []
    for labeled_asset_config in original_labeled_assets_config:
        if not labeled_asset_config:
            continue
        asset_url = labeled_asset_config.get("url", "")
        asset_label = labeled_asset_config.get("label", "")
        num_assets = labeled_asset_config.get("num", 0)
        gravity_disabled_chance = labeled_asset_config.get("gravity_disabled_chance", 0.0)
        falling_assets = create_original_assets(
            num_assets,
            asset_url,
            asset_label,
            "/Assets",
            gravity_disabled_chance,
        )

        labeled_assets.extend(falling_assets)
    return labeled_assets



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
        timeline.set_end_time(100000000)
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
    radius_range: tuple[float, float] | None = None
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
        
        if radius_range is not None:
            rand_radius = random.uniform(radius_range[0], radius_range[1])
            light.GetAttribute("inputs:radius").Set(rand_radius)


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



def calculate_asset_world_center(prim:Usd.Prim):
    bbox_cache = UsdGeom.BBoxCache(time=Usd.TimeCode.Default(), includedPurposes=[UsdGeom.Tokens.default_])
    asset_world_bound_bbox = bbox_cache.ComputeWorldBound(prim)
    asset_world_bound_aligned_range = asset_world_bound_bbox.ComputeAlignedRange()
    asset_world_center = asset_world_bound_aligned_range.GetMidpoint()
    return asset_world_center


def translate_env_under_target_asset(plain_prim:Usd.Prim,target_prim:Usd.Prim,plain_prim_offset:tuple[float,float,float]=(0,0,0)):
    print(f'******************进入环境基于桌面移动的函数{plain_prim}**************************')

    bbox_cache = UsdGeom.BBoxCache(time=Usd.TimeCode.Default(), includedPurposes=[UsdGeom.Tokens.default_])

    table_world_bound_bbox = bbox_cache.ComputeWorldBound(plain_prim)
    table_world_bound_aligned_range = table_world_bound_bbox.ComputeAlignedRange()

    table_size = table_world_bound_aligned_range.GetSize()
    table_center = table_world_bound_aligned_range.GetMidpoint()


    target_world_bbox = bbox_cache.ComputeWorldBound(target_prim)
    target_world_range = target_world_bbox.ComputeAlignedRange()

    target_asset_size = target_world_range.GetSize()
    target_asset_min = target_world_range.GetMin()
    # target_asset_max = target_world_range.GetMax()

    target_asset_center = target_world_range.GetMidpoint()
    # print(table_size)

    ## 求出target_asset 在桌面上的可移动范围：
    x_padding = table_size[0]*.1
    z_padding = table_size[2]*.1
    x_delta = (table_size[0]-target_asset_size[0] - x_padding) / 2
    z_delta = (table_size[2]-target_asset_size[2]- z_padding) / 2

    x_location = random.uniform(target_asset_center[0]-x_delta, target_asset_center[0]+x_delta) + plain_prim_offset[0]
    z_location = random.uniform(target_asset_center[2]-z_delta, target_asset_center[2]+z_delta) + plain_prim_offset[2]
    y_location = target_asset_min[1] - table_size[1]/2 + plain_prim_offset[1]

    table_center_target_location = (x_location, y_location, z_location)


    target_origin_delta = Gf.Vec3d(table_center_target_location)-Gf.Vec3d(table_center)

    dinning_room_xform = plain_prim.GetParent()

    
    dinning_room_ori_location = dinning_room_xform.GetAttribute("xformOp:translate").Get()
    dinning_room_xform.GetAttribute("xformOp:translate").Set(dinning_room_ori_location+target_origin_delta)
    print(f'dst_location:{dinning_room_ori_location+target_origin_delta}')

def find_materials(stage:Usd.Stage, looks_root:Union[str,Sdf.Path])->list[UsdShade.Material]:
    root = stage.GetPrimAtPath(looks_root)
    if not root:
        return []
    mats = []
    for p in Usd.PrimRange(root):
        if p.IsA(UsdShade.Material):
            m = UsdShade.Material(p) # only been wraped can be binding to mesh.
            mats.append(m)
    return mats


def remove_old_labels(prim: Usd.Prim, include_descendants: bool = False) -> None:
    """Removes semantic labels from a prim.

    Args:
        prim (Usd.Prim): Prim to remove labels from.
        include_descendants (bool, optional): Also traverse children and remove labels recursively. Defaults to False.
    """

    if include_descendants:
        for p in Usd.PrimRange(prim):
            remove_all_semantics(p)
    else:
        remove_all_semantics(prim)

def remove_new_labels(prim: Usd.Prim, instance_name: str | None = None, include_descendants: bool = False) -> None:
    """Removes semantic labels (UsdSemantics.LabelsAPI) from a prim.

    Args:
        prim (Usd.Prim): Prim to remove labels from.
        instance_name (str | None, optional): Specific instance name to remove.
                                              If None (default), removes *all* LabelsAPI instances.
        include_descendants (bool, optional): Also traverse children and remove labels recursively. Defaults to False.
    """

    def remove_single_prim_labels(target_prim: Usd.Prim):
        schemas_to_remove = []
        for schema_name in target_prim.GetAppliedSchemas():
            if schema_name.startswith("SemanticsLabelsAPI:") or schema_name.startswith("SemanticsAPI:"):
                current_instance = schema_name.split(":", 1)[1]
                if instance_name is None or current_instance == instance_name:
                    schemas_to_remove.append(current_instance)

        for inst_to_remove in schemas_to_remove:
            target_prim.RemoveAPI(UsdSemantics.LabelsAPI, inst_to_remove)

    if include_descendants:
        for p in Usd.PrimRange(prim):
            remove_single_prim_labels(p)
    else:
        remove_single_prim_labels(prim)



def asset_size_adaptive(target_prim:Usd.Prim,max_limit:float=0.5,min_limit:float=0.1,target_value:float=0.35):
    '''
    max_limit:float=0.5,
    min_limit:float=0.1,
    target_value:float=0.35
    '''

    bbox3 = UsdGeom.BBoxCache(time=Usd.TimeCode.Default(), includedPurposes=[UsdGeom.Tokens.default_]).ComputeWorldBound(target_prim)
    bbox_range = bbox3.ComputeAlignedRange()

    min_point = bbox_range.GetMin()
    max_point = bbox_range.GetMax()
    scale = 1
    if (test_value:=max(max_point-min_point))>max_limit or test_value<min_limit:
        scale = target_value/test_value
        if not target_prim.HasAttribute("xformOp:scale"):
            UsdGeom.Xformable(target_prim).AddScaleOp()

        ori_value = target_prim.GetAttribute("xformOp:scale").Get()

    

        target_prim.GetAttribute("xformOp:scale").Set(ori_value*scale)
        # ori_value = UsdGeom.Xformable(target_prim).GetScaleOp().Get()
        # UsdGeom.Xformable(target_prim).GetScaleOp().Set(ori_value*scale)

    return scale


def calculate_env_adaptive_ratio(target_prim:Usd.Prim,max_limit:float=0.5,min_limit:float=0.1,target_value:float=0.35):
    '''
    max_limit:float=0.5,
    min_limit:float=0.1,
    target_value:float=0.35
    '''

    bbox3 = UsdGeom.BBoxCache(time=Usd.TimeCode.Default(), includedPurposes=[UsdGeom.Tokens.default_]).ComputeWorldBound(target_prim)
    bbox_range = bbox3.ComputeAlignedRange()

    min_point = bbox_range.GetMin()
    max_point = bbox_range.GetMax()
    scale = 1
    if (test_value:=max(max_point-min_point))>max_limit or test_value<min_limit:
        scale = test_value/target_value
        if not target_prim.HasAttribute("xformOp:scale"):
            UsdGeom.Xformable(target_prim).AddScaleOp()

    return scale



def random_visibility(parent="/Distractors"):
    stage = omni.usd.get_context().get_stage()
    root = stage.GetPrimAtPath(parent)
    children = root.GetChildren()
    
    
    # Step 1: 全部显示
    for p in children:
        UsdGeom.Imageable(p).MakeVisible()

    # Step 2: 随机隐藏
    hide_count = random.randint(0,len(children))
    print(hide_count)
    to_hide = random.sample(children, hide_count)
    for p in to_hide:
        UsdGeom.Imageable(p).MakeInvisible()

    print(f"保持 {len(children)-hide_count} 个，隐藏 {hide_count} 个")



def path_to_file_uri(path: str) -> str:
    """
    Convert a local filesystem path to a file:/// resource URI.
    Works on Windows, Linux, macOS.
    """
    p = pathlib.Path(path).absolute()
    # Convert to URI (pathlib automatically handles slashes and drive letters)
    uri = p.as_uri()
    return uri



def file_uri_to_path(uri: str) -> str:
    """
    Convert file:/// URI to local filesystem path.
    Works on Windows, Linux, macOS.
    """
    if not uri.lower().startswith("file://"):
        raise ValueError("Not a file URI: " + uri)

    parsed = urllib.parse.urlparse(uri)

    # Network path: file://server/share/file
    if parsed.netloc and parsed.netloc != "localhost":
        # UNC path
        path = f"//{parsed.netloc}{parsed.path}"
    else:
        # Local path
        path = parsed.path

    # URL decode (%20 → space)
    path = urllib.parse.unquote(path)

    # Windows: strip leading slash /C:/...
    if sys.platform.startswith("win") and path.startswith("/"):
        path = path[1:]

    # Convert slashes for Windows
    return os.path.normpath(path)










