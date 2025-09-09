
import os
from pprint import pprint
import sys


import random
from itertools import cycle

import carb.settings
import numpy as np
import omni.client
import omni.kit
import omni.kit.app
import omni.physx
import omni.replicator.core as rep
import omni.timeline
import omni.usd
from isaacsim.core.utils.viewports import set_camera_view    

import argparse
import json

import yaml



# Default config dict, can be updated/replaced using json/yaml config files ('--config' cli argument)
config = {
    "environments": {
        # List of background environments (list of folders or files)
        "folders": ["/Isaac/Samples/Replicator/Infinigen/dining_rooms/"],
        "files": [],
    },
    "capture": {
        # Number of captures (frames = total_captures * num_cameras)
        "total_captures": 150,
        # Number of captures per environment before running the simulation (objects in the air)
        "num_floating_captures_per_env": 0,
        # Number of captures per environment after running the simulation (objects fallen)
        "num_dropped_captures_per_env": 20,
        # Number of cameras to capture from (each camera will have a render product attached)
        "num_cameras": 6,
        # Resolution of the captured frames
        "resolution": (720, 480),
        # Disable render products throughout the piepline, enable them only when capturing the frames
        "disable_render_products": False,
        # Number of subframes to render (RayTracedLighting) to avoid temporal rendering artifacts (e.g. ghosting)
        "rt_subframes": 8,
        # Use PathTracing renderer or RayTracedLighting when capturing the frames
        "path_tracing": False,
        # Offset to avoid the images always being in the image center
        "camera_look_at_target_offset": 0.1,
        # Distance between the camera and the target object
        "camera_distance_to_target_range": (1.15, 1.45),
        # Number of scene lights to create in the working area
        "num_scene_lights": 3,
    },
    "writers": [
        {
            # Type of the writer to use (e.g. PoseWriter, BasicWriter, etc.) and the kwargs to pass to the writer init
            "type": "PoseWriter",
            "kwargs": {
                "output_dir": "_out_infinigen_posewriter",
                "format": None,
                "use_subfolders": True,
                "write_debug_images": True,
                "skip_empty_frames": False,
            },
        }
    ],
    "labeled_assets": {
        # Labeled assets with auto-labeling (e.g. 002_banana -> banana) using regex pattern replacement on the asset name
        "auto_label": {
            # Number of labeled assets to create from the given files/folders list
            "num": 2,
            # Chance to disable gravity for the labeled assets (0.0 - all the assets will fall, 1.0 - all the assets will float)
            "gravity_disabled_chance": 0,
            # List of folders and files to search for the labeled assets
            "folders": ["/Isaac/Props/YCB/Axis_Aligned/"],
            "files": ["/Isaac/Props/YCB/Axis_Aligned/036_wood_block.usd"],
            # Regex pattern to replace in the asset name (e.g. "002_banana" -> "banana")
            "regex_replace_pattern": r"^\d+_",
            "regex_replace_repl": "",
        },
        # Manually labeled assets with specific labels and properties
        "manual_label": [
            # {
            #     "url": "/Isaac/Props/YCB/Axis_Aligned/008_pudding_box.usd",
            #     "label": "pudding_box",
            #     "num": 2,
            #     "gravity_disabled_chance": 1,
            # },
            {
                "url": "/Isaac/Props/YCB/Axis_Aligned_Physics/006_mustard_bottle.usd",
                "label": "mustard_bottle",
                "num": 2,
                "gravity_disabled_chance": 0,
            },
            # {"url": "file:///home/ubuntu/lxd/usd_file/infinigen_assets/Props/YCB/Axis_Aligned/airship.usd",
            # "label": "airship",
            # "num": 1,
            # "gravity_disabled_chance": 0.25

            # }
        ],
    },
    "distractors": {
        # Shape distractors (unlabeled background assets) to drop in the scene (e.g. capsules, cones, cylinders)
        "shape_distractors": {
            # Amount of shape distractors to create
            "num": 0,
            # Chance to disable gravity for the shape distractors
            "gravity_disabled_chance": 0,
            # List of shape types to randomly choose from
            "types": ["capsule", "cone", "cylinder", "sphere", "cube"],
        },
        # Mesh distractors (unlabeled background assets) to drop in the scene
        "mesh_distractors": {
            # Amount of mesh distractors to create
            "num": 1,
            # Chance to disable gravity for the mesh distractors
            "gravity_disabled_chance": 0,
            # List of folders and files to search to randomly choose from
            "folders": [
                "/NVIDIA/Assets/DigitalTwin/Assets/Warehouse/Safety/Floor_Signs/",
                "/NVIDIA/Assets/DigitalTwin/Assets/Warehouse/Safety/Cones/",
            ],
            "files": [
                "/Isaac/Environments/Simple_Warehouse/Props/SM_CardBoxD_04_1847.usd",
                "/Isaac/Environments/Simple_Warehouse/Props/SM_CardBoxA_01_414.usd",
                "/Isaac/Environments/Simple_Warehouse/Props/S_TrafficCone.usd",
                "/Isaac/Environments/Simple_Warehouse/Props/S_WetFloorSign.usd",
                "/Isaac/Environments/Office/Props/SM_Book_03.usd",
                "/Isaac/Environments/Office/Props/SM_Book_34.usd",
                "/Isaac/Environments/Office/Props/SM_BookOpen_01.usd",
                "/Isaac/Environments/Office/Props/SM_Briefcase.usd",
                "/Isaac/Environments/Office/Props/SM_Extinguisher.usd",
                "/Isaac/Environments/Hospital/Props/SM_MedicalBag_01a.usd",
                "/Isaac/Environments/Hospital/Props/SM_MedicalBox_01g.usd",
            ],
        },
    },
    # Hide ceilling to get a top-down view of the scene, move viewport camera to the top-down view
    "debug_mode": True,
}


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


def add_colliders_and_rigid_body_dynamics(prim: Usd.Prim, disable_gravity: bool = False) -> None:
    """Add colliders and rigid body dynamics properties to a prim, with optional gravity setting."""
    add_colliders(prim)
    add_rigid_body_dynamics(prim, disable_gravity)


def get_random_pose_on_sphere(
    origin: tuple[float, float, float],
    radius_range: tuple[float, float],
    polar_angle_range: tuple[float, float],
    camera_forward_axis: tuple[float, float, float] = (0, 0, -1),
) -> tuple[Gf.Vec3d, Gf.Quatf]:
    """Generate a random pose on a sphere looking at the origin, with specified radius and polar angle ranges."""
    # https://docs.omniverse.nvidia.com/isaacsim/latest/reference_conventions.html
    # Convert degrees to radians for polar angles (theta)
    polar_angle_min_rad = math.radians(polar_angle_range[0])
    polar_angle_max_rad = math.radians(polar_angle_range[1])

    # Generate random spherical coordinates
    radius = random.uniform(radius_range[0], radius_range[1])
    polar_angle = random.uniform(polar_angle_min_rad, polar_angle_max_rad)
    azimuthal_angle = random.uniform(0, 2 * math.pi)

    # Convert spherical coordinates to Cartesian coordinates
    x = radius * math.sin(polar_angle) * math.cos(azimuthal_angle)
    y = radius * math.sin(polar_angle) * math.sin(azimuthal_angle)
    z = radius * math.cos(polar_angle)

    # Calculate the location in 3D space
    location = Gf.Vec3d(origin[0] + x, origin[1] + y, origin[2] + z)

    # Calculate direction vector from camera to look_at point
    direction = Gf.Vec3d(origin) - location
    direction_normalized = direction.GetNormalized()

    # Calculate rotation from forward direction (rotateFrom) to direction vector (rotateTo)
    rotation = Gf.Rotation(Gf.Vec3d(camera_forward_axis), direction_normalized)
    orientation = Gf.Quatf(rotation.GetQuat())

    return location, orientation


def randomize_camera_poses(
    cameras: list[Usd.Prim],
    targets: list[Usd.Prim],
    distance_range: tuple[float, float],
    polar_angle_range: tuple[float, float] = (0, 180),
    look_at_offset: tuple[float, float] = (-0.1, 0.1),
) -> None:
    """Randomize the poses of cameras to look at random targets with adjustable distance and offset."""
    for cam in cameras:
        # Get a random target asset to look at
        target_asset = random.choice(targets)

        # Add a look_at offset so the target is not always in the center of the camera view
        target_loc = target_asset.GetAttribute("xformOp:translate").Get()
        target_loc = (
            target_loc[0] + random.uniform(look_at_offset[0], look_at_offset[1]),
            target_loc[1] + random.uniform(look_at_offset[0], look_at_offset[1]),
            target_loc[2] + random.uniform(look_at_offset[0], look_at_offset[1]),
        )

        # Generate random camera pose
        loc, quat = get_random_pose_on_sphere(target_loc, distance_range, polar_angle_range)

        # Set the camera's transform attributes to the generated location and orientation
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






# Load the config parameters
env_config = config.get("environments", {})
env_urls = get_usd_paths(
    files=env_config.get("files", []), folders=env_config.get("folders", []), skip_folder_keywords=[".thumbs"]
)
capture_config = config.get("capture", {})
writers_config = config.get("writers", {})
labeled_assets_config = config.get("labeled_assets", {})
distractors_config = config.get("distractors", {})

# Create a new stage
print(f"[SDG-Infinigen] Creating a new stage")
omni.usd.get_context().new_stage()
stage = omni.usd.get_context().get_stage()
rep.orchestrator.set_capture_on_play(False)
carb.settings.get_settings().set("/physics/cooking/ujitsoCollisionCooking", True)

# Debug mode (hide ceiling, move viewport camera to the top-down view)
debug_mode = config.get("debug_mode", False)

# Create the cameras
cameras = []
num_cameras = capture_config.get("num_cameras", 0)
for i in range(num_cameras):
    cam_prim = stage.DefinePrim(f"/Cameras/cam_{i}", "Camera")
    cam_prim.GetAttribute("clippingRange").Set((0.25, 1000))
    cameras.append(cam_prim)
print(f"[SDG-Infinigen] Created {len(cameras)} cameras")

# Create the render products for the cameras
render_products = []
resolution = capture_config.get("resolution", (1280, 720))
disable_render_products = capture_config.get("disable_render_products", False)
for cam in cameras:
    rp = rep.create.render_product(cam.GetPath(), resolution, name=f"rp_{cam.GetName()}")
    if disable_render_products:
        rp.hydra_texture.set_updates_enabled(False)
    render_products.append(rp)
print(f"[SDG-Infinigen] Created {len(render_products)} render products")

# Only create the writers if there are render products to attach to
writers = []
if render_products:
    for writer_config in writers_config:
        writer = setup_writer(writer_config)
        if writer:
            writer.attach(render_products)
            writers.append(writer)
            print(f"\t {writer_config['type']}'s out dir: {writer_config.get('kwargs', {}).get('output_dir', '')}")
print(f"[SDG-Infinigen] Created {len(writers)} writers")

# Load target assets with auto-labeling (e.g. 002_banana -> banana)
auto_label_config = labeled_assets_config.get("auto_label", {})
auto_floating_assets, auto_falling_assets = load_auto_labeled_assets(auto_label_config)
print(f"[SDG-Infinigen] Loaded {len(auto_floating_assets)} floating auto-labeled assets")
print(f"[SDG-Infinigen] Loaded {len(auto_falling_assets)} falling auto-labeled assets")

# Load target assets with manual labels
manual_label_config = labeled_assets_config.get("manual_label", [])
manual_floating_assets, manual_falling_assets = load_manual_labeled_assets(manual_label_config)
print(f"[SDG-Infinigen] Loaded {len(manual_floating_assets)} floating manual-labeled assets")
print(f"[SDG-Infinigen] Loaded {len(manual_falling_assets)} falling manual-labeled assets")
target_assets = auto_floating_assets + auto_falling_assets + manual_floating_assets + manual_falling_assets

# Load the shape distractors
shape_distractors_config = distractors_config.get("shape_distractors", {})
floating_shapes, falling_shapes = load_shape_distractors(shape_distractors_config)
print(f"[SDG-Infinigen] Loaded {len(floating_shapes)} floating shape distractors")
print(f"[SDG-Infinigen] Loaded {len(falling_shapes)} falling shape distractors")
shape_distractors = floating_shapes + falling_shapes

# Load the mesh distractors
mesh_distractors_config = distractors_config.get("mesh_distractors", {})
floating_meshes, falling_meshes = load_mesh_distractors(mesh_distractors_config)
print(f"[SDG-Infinigen] Loaded {len(floating_meshes)} floating mesh distractors")
print(f"[SDG-Infinigen] Loaded {len(falling_meshes)} falling mesh distractors")
mesh_distractors = floating_meshes + falling_meshes

# Resolve any centimeter-meter scale issues of the assets
resolve_scale_issues_with_metrics_assembler()



 # Create lights to randomize in the working area
scene_lights = []
num_scene_lights = capture_config.get("num_scene_lights", 0)
for i in range(num_scene_lights):
    light_prim = stage.DefinePrim(f"/Lights/SphereLight_scene_{i}", "SphereLight")
    scene_lights.append(light_prim)
print(f"[SDG-Infinigen] Created {len(scene_lights)} scene lights")

# Register replicator randomizers and trigger them once
print(f"[SDG-Infinigen] Registering replicator graph randomizers")
register_dome_light_randomizer()
register_shape_distractors_color_randomizer(shape_distractors)

# Check if the render mode needs to be switched to path tracing for the capture (by default: RayTracedLighting)
use_path_tracing = capture_config.get("path_tracing", False)

# Capture detail using subframes (https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/subframes_examples.html)
rt_subframes = capture_config.get("rt_subframes", 3)

# Min and max distance between the camera and the target object
camera_distance_to_target_range = capture_config.get("camera_distance_to_target_range", (0.5, 1.5))

# Number of captures (frames = total_captures * num_cameras)
# NOTE: if captured frames have no labeled data, they can be skipped (e.g. PoseWriter with skip_empty_frames=True)
total_captures = capture_config.get("total_captures", 0)

# Number of captures per environment with the objects in the air or dropped
num_floating_captures_per_env = capture_config.get("num_floating_captures_per_env", 0)
num_dropped_captures_per_env = capture_config.get("num_dropped_captures_per_env", 0)

# Start the SDG loop
env_cycle = cycle(env_urls)
capture_counter = 0



while capture_counter < total_captures:
    # Load the next environment
    env_url = next(env_cycle)

    # Load the new environment
    print(f"[SDG-Infinigen] Loading environment: {env_url}")
    load_env(env_url, prim_path="/Environment")

    # Setup the environment (add collision, fix lights, etc.) and update the app once to apply the changes
    print(f"[SDG-Infinigen] Setting up the environment")
    setup_env(root_path="/Environment", hide_top_walls=debug_mode)

    # Get the location of the prim above which the assets will be randomized
    working_area_loc = get_matching_prim_location(
        match_string="TableDining", root_path="/Environment"
    )

    # Move viewport above the working area to get a top-down view of the scene
    if debug_mode:
        camera_loc = (working_area_loc[0], working_area_loc[1], working_area_loc[2] + 10)
        set_camera_view(eye=np.array(camera_loc), target=np.array(working_area_loc))

    # Get the spawn areas as offseted location ranges from the working area (min_x, min_y, min_z, max_x, max_y, max_z)
    print(f"\tRandomizing {len(target_assets)} target assets around the working area")
    target_loc_range = offset_range((-0.5, -0.5, 1, 0.5, 0.5, 1.5), working_area_loc)
    randomize_poses(
        target_assets,
        location_range=target_loc_range,
        rotation_range=(0, 360),
        scale_range=(0.95, 1.15),
    )

    # Mesh distractors
    print(f"\tRandomizing {len(mesh_distractors)} mesh distractors around the working area")
    mesh_loc_range = offset_range((-1, -1, 1, 1, 1, 2), working_area_loc)
    randomize_poses(
        mesh_distractors,
        location_range=mesh_loc_range,
        rotation_range=(0, 360),
        scale_range=(0.3, 1.0),
    )

    # Shape distractors
    print(f"\tRandomizing {len(shape_distractors)} shape distractors around the working area")
    shape_loc_range = offset_range((-1.5, -1.5, 1, 1.5, 1.5, 2), working_area_loc)
    randomize_poses(
        shape_distractors,
        location_range=shape_loc_range,
        rotation_range=(0, 360),
        scale_range=(0.01, 0.1),
    )

    print(f"\tRandomizing {len(scene_lights)} scene lights properties and locations around the working area")
    lights_loc_range = offset_range((-2, -2, 1, 2, 2, 3), working_area_loc)
    randomize_lights(
        scene_lights,
        location_range=lights_loc_range,
        intensity_range=(500, 2500),
        color_range=(0.1, 0.1, 0.1, 0.9, 0.9, 0.9),
    )

    print(f"\tRandomizing dome lights")
    rep.utils.send_og_event(event_name="randomize_dome_lights")

    print(f"\tRandomizing shape distractor colors")
    rep.utils.send_og_event(event_name="randomize_shape_distractor_colors")

    # Run the physics simulation for a few frames to solve any collisions
    print(f"\tFixing collisions through physics simulation")
    run_simulation(num_frames=4, render=True)

    # Check if the render products need to be enabled for the capture
    if disable_render_products:
        for rp in render_products:
            rp.hydra_texture.set_updates_enabled(True)

    # Check if the render mode needs to be switched to path tracing for the capture
    if use_path_tracing:
        print(f"\tSwitching to PathTracing render mode")
        carb.settings.get_settings().set("/rtx/rendermode", "PathTracing")

    # Capture frames with the objects in the air
    for i in range(num_floating_captures_per_env):
        # Check if the total captures have been reached
        if capture_counter >= total_captures:
            break
        # Randomize the camera poses
        print(f"\tRandomizing {len(cameras)} camera poses")
        randomize_camera_poses(
            cameras, target_assets, camera_distance_to_target_range, polar_angle_range=(0, 75)
        )
        print(
            f"\tCapturing floating assets {i+1}/{num_floating_captures_per_env}; total captures: {capture_counter+1}/{total_captures};"
        )
        rep.orchestrator.step(rt_subframes=rt_subframes, delta_time=0.0)
        capture_counter += 1

    # Check if the render products need to be disabled until the next capture
    if disable_render_products:
        for rp in render_products:
            rp.hydra_texture.set_updates_enabled(False)

    # Check if the render mode needs to be switched back to raytracing until the next capture
    if use_path_tracing:
        carb.settings.get_settings().set("/rtx/rendermode", "RayTracedLighting")

    print(f"\tRunning the simulation")
    run_simulation(num_frames=200, render=False)

    # Check if the render products need to be enabled for the capture
    if disable_render_products:
        for rp in render_products:
            rp.hydra_texture.set_updates_enabled(True)

    # Check if the render mode needs to be switched to path tracing for the capture
    if use_path_tracing:
        carb.settings.get_settings().set("/rtx/rendermode", "PathTracing")

    for i in range(num_dropped_captures_per_env):
        # Check if the total captures have been reached
        if capture_counter >= total_captures:
            break
        # Spawn the cameras with a smaller polar angle to have mostly a top-down view of the objects
        print(f"\tRandomizing camera poses")
        randomize_camera_poses(
            cameras, target_assets, distance_range=camera_distance_to_target_range, polar_angle_range=(0, 45)
        )
        print(
            f"\tCapturing dropped assets {i+1}/{num_dropped_captures_per_env}; total captures: {capture_counter+1}/{total_captures};"
        )
        rep.orchestrator.step(rt_subframes=rt_subframes, delta_time=0.0)
        capture_counter += 1

    # Check if the render products need to be disabled until the next capture
    if disable_render_products:
        for rp in render_products:
            rp.hydra_texture.set_updates_enabled(False)

    # Check if the render mode needs to be switched back to raytracing until the next capture
    if use_path_tracing:
        carb.settings.get_settings().set("/rtx/rendermode", "RayTracedLighting")

# Wait until the data is written to the disk
rep.orchestrator.wait_until_complete()
# Detach the writers
print(f"[SDG-Infinigen] Detaching writers")
for writer in writers:
    writer.detach()

# Destroy render products
print(f"[SDG-Infinigen] Destroying render products")
for rp in render_products:
    rp.destroy()

print(f"[SDG-Infinigen] SDG Finished, captured {capture_counter * num_cameras} frames..")