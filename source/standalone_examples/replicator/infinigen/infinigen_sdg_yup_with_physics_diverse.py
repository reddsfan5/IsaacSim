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

"""Generate synthetic datasets using infinigen (https://infinigen.org/) generated environments.
"""


import argparse
from collections import defaultdict
import copy
from datetime import datetime
import json
import math
import os
from pathlib import Path
import shutil
import sys
from threading import local
import time
import yaml
from isaacsim import SimulationApp
import asyncio

CAMERA_LOCATION_MAP = {9000: {'polar_step_deg': 1, 'azimuth_step_min': 1}, 
            8000: {'polar_step_deg': 1, 'azimuth_step_min': 1}, 
            7000: {'polar_step_deg': 1, 'azimuth_step_min': 1}, 
            6000: {'polar_step_deg': 1, 'azimuth_step_min': 2}, 
            5000: {'polar_step_deg': 1, 'azimuth_step_min': 3}, 
            4000: {'polar_step_deg': 1, 'azimuth_step_min': 4}, 
            3000: {'polar_step_deg': 1, 'azimuth_step_min': 7}, 
            2000: {'polar_step_deg': 2, 'azimuth_step_min': 5}, 
            1000: {'polar_step_deg': 3, 'azimuth_step_min': 7},
            0: {'polar_step_deg': 80, 'azimuth_step_min': 250}}



# Check if there are any config files (yaml or json) are passed as arguments
parser = argparse.ArgumentParser()
parser.add_argument("--config", required=True, help="Yaml include specific config parameters")
parser.add_argument(
    "--close-on-completion", action="store_true", help="Ensure the app closes on completion even in debug mode"
)

parser.add_argument("--task_id", required=True, help="Subforder name")
parser.add_argument("--remote_save_root", type=str, help='The remote root folder to save the generated dataset')
parser.add_argument("--local_glb_path",help='Local path to the glb files',nargs='+',type=str)
parser.add_argument("--camera_azimuth",help='Camera azimuth angle range',nargs=2,default=[-180,180],type=float,metavar=('azimuth_min','azimuth_max'))
parser.add_argument("--camera_latitude",help='Camera latitude angle range',nargs=2,default=[-90,90],type=float,metavar=('polar_min','polar_max'))
parser.add_argument("--data_num",help='max data num',type=int)
parser.add_argument("--add_angle",help='angle compliment',type=str)
parser.add_argument("--gpu",help='gpu select',type=int,default=1)
parser.add_argument("--val_num",help='val num between (1000,10000)',type=int,default=8000)
print("Received args:", sys.argv)
 

if sys.argv[1:]:
    args, unknown = parser.parse_known_args()
else:
    args_list = [
             "--config", "source/standalone_examples/replicator/infinigen/config/infinigen_multi_writers_with_container.yaml",
             "--task_id", "symmetric_cylinder_multi_obj_v12_same_env_60_obj_v3", 
            #  "--local_glb_path", "/data2/isaacsim/assets/glb/Gangzhu_top_003.glb",
            #  "--local_glb_path", "/data2/isaacsim/assets/glb/3dModels/fadongji1125.glb","/data2/isaacsim/assets/glb/Gangzhu_top_003.glb",  
            "--local_glb_path", 
            "/data2/isaacsim/assets/glb/Gangzhu_top_003.glb",
            "/data2/isaacsim/assets/glb/3dModels/fadongji1125.glb",
            "/data2/isaacsim/assets/glb/moto-02.usd",
            "/data2/isaacsim/assets/glb/729-disk.usd",
            # "/data2/isaacsim/assets/glb/airship.usd",
            "/data2/isaacsim/assets/glb/AM114_33.glb",
            # "/data2/isaacsim/assets/glb/benTian.glb",
            # "/data2/isaacsim/assets/glb/bus.glb",
            # "/data2/isaacsim/assets/glb/bulldozer.glb",
            # "/data2/isaacsim/assets/glb/crane.glb",
            # "/data2/isaacsim/assets/glb/excavator.glb"  
             "--camera_azimuth", "0","360", 
             "--camera_latitude", "10","90", 
             "--data_num", "20",
             '--gpu','0',
             "--val_num",'0']
    
    args, unknown = parser.parse_known_args(args_list)

args_config = {}
if args.config and os.path.isfile(args.config):
    with open(args.config, "r") as f:
        if args.config.endswith(".json"):
            args_config = json.load(f)
        elif args.config.endswith(".yaml"):
            args_config = yaml.safe_load(f)
        else:
            print(f"[SDG-Infinigen] Config file {args.config} is not json or yaml, will use default config")
else:
    print(f"[SDG-Infinigen] Config file {args.config} does not exist, will use default config")

#  Update the default config dict with the external one
config = args_config
lmdb_output_dir  = os.path.join(config['writers'][0]['kwargs']['output_dir'],str(args.task_id)) 

config['writers'][0]['kwargs']['output_dir'] = lmdb_output_dir











simulation_app = SimulationApp(launch_config={
    "headless": config.get("headless", False),
    "renderer": "RealTimePathTracing",  # 选择 RT 2.0 的渲染模式
    "active_gpu":args.gpu,
    "physics_gpu":args.gpu,
    "multi_gpu":False
})



import random
from itertools import cycle
import carb
import carb.settings

import numpy as np
import omni.kit.app
import omni.replicator.core as rep

import omni.usd
from isaacsim.core.utils.viewports import set_camera_view

from pxr import UsdGeom,Gf,Usd,UsdShade,UsdPhysics
from omni.isaac.core.utils.stage import add_reference_to_stage
from omni.replicator.core import WriterRegistry
import omni.kit.asset_converter as converter
from omni.kit.asset_converter import AssetConverterContext

from isaacsim.core.utils.semantics import get_labels,add_labels,remove_labels
import omni.client
import omni.kit
import omni.physx
import omni.timeline

_cur_file_path = Path(__file__).resolve()
_custom_sys_path ='/'.join(_cur_file_path.parts[:_cur_file_path.parts.index("source")]).replace('//','/')
sys.path.append(_custom_sys_path)

import infinigen_sdg_utils as infinigen_utils
from source.standalone_examples.replicator.infinigen.location_on_sphere import IterPatchSampler,RandomUniformSphereCoord,RandomQuotaSphereCoord,PatchSampler, SpherePatch, latitude_range_to_polar_range, polar_range_to_latitude_range
from lv_tools.material_change import MaterialTexture, bind_materials_to_prims_recursively, create_pbr_with_texture,bind_materials_to_assets

from lv_tools.writer_register import LMDBWriterMultiAssets

def _get_val_patams(val_num:int):
    val_num = max(1000,min(val_num//1000*1000,9000))
    return CAMERA_LOCATION_MAP[val_num]



def _get_time_str():
    return datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H')

def progress_callback(current_step: int, total: int):
    # Show progress
    print(f"{current_step} of {total}")


async def convert_asset_to_usd(input_asset_path, output_asset_path):
    asset_converter_obj = AssetConverterContext()
    asset_converter_obj.single_mesh = True
    # asset_converter_obj.use_meter_as_world_unit = True
    asset_converter_obj.merge_all_meshes = True
    asset_converter_obj.convert_stage_up_z = False
    asset_converter_obj.bake_mdl_material = True
    asset_converter_obj.embed_mdl_in_usd = True  # Deprecated.

    task_manager = converter.get_instance()
    task = task_manager.create_converter_task(input_asset_path, output_asset_path, progress_callback,asset_converter_obj)
    
    success = await task.wait_until_finished()
    if not success:
        # detailed_status_code = task.get_status()
        detailed_status_error_string = task.get_error_message()
        carb.log_error(detailed_status_error_string)



def generate_pbr_materials(materials_control_config:dict,stage:Usd.Stage,mat_map:dict)->list[UsdShade.Material]:

    '''
    耦合当前配置文件的业务逻辑函数
    
    '''
    texture_paths = [img_path for img_path in Path(materials_control_config['pbr']['texture_bg']).rglob('*') if img_path.suffix.lower() in ['.png','.jpg']]
    


    omni_pbr_materials = []
    for _ in range(materials_control_config['pbr']['num']):
        mat_name,material_cur = mat_map.choice()
        
        # texture_path = random.choice([material_cur.get('col'),str(random.choice(texture_paths))])
        texture_path = material_cur.get('col')
        normal_texture_path = material_cur.get('nrm')
        roughness_texture_path = material_cur.get('rough')
        metallic_texture_path = material_cur.get('refl')

        project_uvw = random.choice([True, False])
        pbr_base_name = f"omni_pbr_{mat_name.replace('-','_')}"
        metallic_constant = random.uniform(*materials_control_config['pbr']['metallic_constant'])
        reflection_roughness = random.uniform(*materials_control_config['pbr']['reflection_roughness'])
        scale = random.uniform(*materials_control_config['pbr']['texture_scale'])
    
        translate = random.randint(*materials_control_config['pbr']['translate'])
        
        pbr_material_prim_path = omni.usd.get_stage_next_free_path(stage,os.path.join(materials_control_config['pbr']['materials_root'],pbr_base_name),False)
        omni_pbr_material = create_pbr_with_texture(pbr_material_prim_path,
                                                    texture_path,
                                                    metallic_constant,
                                                    reflection_roughness,
                                                    scale,
                                                    translate,
                                                    project_uvw,
                                                    normalmap_texture_path=normal_texture_path,
                                                    metallic_texture_path=metallic_texture_path,
                                                    reflectionroughness_texture_path=roughness_texture_path)
        omni_pbr_materials.append(omni_pbr_material)
    return omni_pbr_materials



def capture_one_frame(rt_subframes: int, delta_time: float, pause_timeline: bool, wait_after: bool):
    rep.orchestrator.step(rt_subframes=max(1, rt_subframes), delta_time=delta_time, pause_timeline=pause_timeline)
    if wait_after:
        rep.orchestrator.wait_until_complete()



def writers_init(writers_config,render_products,mode='train'):
    writers = []
    for writer_config in writers_config:
        writer_config = copy.deepcopy(writer_config)
        writer_config['kwargs']['task_id'] = args.task_id
        output_root = writer_config['kwargs']['output_dir']
        writer_config['kwargs']['output_dir'] =  output_root +f'/{os.path.basename(output_root)}_{_get_time_str()}_{mode}_lmdb'
        writer = infinigen_utils.setup_writer(writer_config)
        if writer:
            writer.attach(render_products)
            writers.append(writer)
            print(f"\t {writer_config['type']}'s out dir: {writer_config.get('kwargs', {}).get('output_dir', '')}")
    print(f"[SDG-Infinigen] Created {len(writers)} writers")
    return writers


def spawn_objects(stage, asset_path, x_range=(-2,2),y_range=(1,3),z_range=(-2,2),scale=1,count=20,label='object'):

    objs = []
    for i in range(count):

        prim = stage.DefinePrim(f"/World/object_{i}", "Xform")
        prim.GetReferences().AddReference(asset_path)

        x = random.uniform(*x_range)
        y = random.uniform(*y_range)
        z = random.uniform(*z_range)

        infinigen_utils.set_transform_attributes(prim, location=Gf.Vec3f(x, y, z),scale=Gf.Vec3f(scale,scale,scale))

        UsdPhysics.RigidBodyAPI.Apply(prim)
        UsdPhysics.CollisionAPI.Apply(prim)
        add_labels(prim, labels=[label], instance_name="class")
        objs.append(prim)

    return objs

# Run the SDG pipeline on the scenarios
def run_sdg(config,args):

    # ⭐加载配置⭐
    # Load the config parameters
    env_config = config.get("environments", {})
    env_urls = infinigen_utils.get_usd_paths(
        files=env_config.get("files", []), folders=env_config.get("folders", []), skip_folder_keywords=[".thumbs"]
    )
    capture_config = config.get("capture", {})
    writers_config = config.get("writers", {})
    distractors_config = config.get("distractors", {})
    materials_control_config = config.get("materials_control",{})

    container_config = config.get("containers", {})
    container_urls = infinigen_utils.get_usd_paths(
        files=container_config.get("files", []), folders=container_config.get("folders", []), skip_folder_keywords=[".thumbs"]
    )


    if args.data_num:
        capture_config['total_captures'] = args.data_num

    # ⭐asset格式转换，并存放到预期路径下，给出存放后的路径位置 。⭐
    # 二次转换
        # 第一次是glb->usd，无法实现彻底的mesh合并，导致bbox计算错误。
        # 第二次是 usd->usd,可以实现彻底的mesh合并，bbox计算正确。
    labeled_assets_config = defaultdict(list)
    for input_path in args.local_glb_path:
        if input_path and os.path.isfile(input_path):
            usd_asset_dir = Path(config['global']['usd_asset_root'] + f'/{args.task_id}')
            usd_mediate_dir = Path(config['global']['usd_asset_root'] + f'/{args.task_id}_tem')
            if not usd_asset_dir.exists():
                usd_asset_dir.mkdir(exist_ok=True,parents=True)

            if not usd_mediate_dir.exists():
                usd_mediate_dir.mkdir(exist_ok=True,parents=True)

            mediate_asset_path = str(usd_mediate_dir / f"{Path(input_path).stem}.usd")
            output_path = str(usd_asset_dir / f"{Path(input_path).stem}.usd")

            asyncio.get_event_loop().run_until_complete(convert_asset_to_usd(input_path, mediate_asset_path))
            asyncio.get_event_loop().run_until_complete(convert_asset_to_usd(mediate_asset_path, output_path))




            labeled_assets_config["manual_label"].append({"url": infinigen_utils.path_to_file_uri(output_path),
                                    "label": infinigen_utils.valid_stage_name(str(Path(input_path).stem)),
                                    "num": 10,
                                    "gravity_disabled_chance": 0})


        else:
            # 如果提供的目标asset无效，则直接退出，避免后续流程报错
            return


    mat_map = MaterialTexture(materials_control_config['pbr']['texture_poliigon'])

    # ⭐创建stage，并设置向上轴⭐
    # Create a new stage
    
    

    stage = omni.usd.get_context().get_stage()
    # Set stage Up axis
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    print(f"[SDG-Infinigen] Creating a new stage")
    
    
    # Disable capture on play
    rep.orchestrator.set_capture_on_play(False)

    # Disable UJITSO cooking ([Warning] [omni.ujitso] UJITSO : Build storage validation failed)

    # optimize collide geometry
    '''
    Collision Cooking refers to the preprocessing of collision geometry in physics engines. 
    It optimizes raw mesh data into efficient collision shapes (e.g., convex hulls) for real-time simulations.
    '''
    carb.settings.get_settings().set("/physics/cooking/ujitsoCollisionCooking", True)

    # Debug mode (hide ceiling, move viewport camera to the top-down view)
    debug_mode = config.get("debug_mode", False)

    
    
    # ⭐相机创建⭐
    # Create the cameras
    cameras = []
    num_cameras = capture_config.get("num_cameras", 0)
    focalLengths = capture_config.get('focal_lengths',[15,24,28,35,50])
    for i in range(num_cameras):
        cam_prim = stage.DefinePrim(f"/Cameras/cam_{i}", "Camera")
        cam_prim.GetAttribute("focalLength").Set(focalLengths[i%len(focalLengths)])
        cam_prim.GetAttribute("clippingRange").Set((0.25, 1000))
        cameras.append(cam_prim)
    print(f"[SDG-Infinigen] Created {len(cameras)} cameras")

    # Create the render products for the cameras
    render_products = []
    resolution = capture_config.get("resolution", (1280, 720))
    disable_render_products = capture_config.get("disable_render_products", False)
    for cam in cameras:
        # camera: Union[ReplicatorItem, str, List[str], Sdf.Path, List[Sdf.Path], usdrt.Usd.Prim, List[usdrt.Usd.Prim]]
        rp = rep.create.render_product(cam.GetPath(), resolution, name=f"rp_{cam.GetName()}")
        if disable_render_products:
            rp.hydra_texture.set_updates_enabled(False)
        render_products.append(rp)
    print(f"[SDG-Infinigen] Created {len(render_products)} render products")

    
    
    # ⭐加载干扰物⭐
    # Load the shape distractors
    shape_distractors_config = distractors_config.get("shape_distractors", {})
    floating_shapes, falling_shapes = infinigen_utils.load_shape_distractors(shape_distractors_config)
    print(f"[SDG-Infinigen] Loaded {len(floating_shapes)} floating shape distractors")
    print(f"[SDG-Infinigen] Loaded {len(falling_shapes)} falling shape distractors")
    shape_distractors = floating_shapes + falling_shapes
    # Load the mesh distractors
    mesh_distractors_config = distractors_config.get("mesh_distractors", {})
    floating_meshes, falling_meshes = infinigen_utils.load_mesh_distractors(mesh_distractors_config)
    
    print(f"[SDG-Infinigen] Loaded {len(floating_meshes)} floating mesh distractors")
    print(f"[SDG-Infinigen] Loaded {len(falling_meshes)} falling mesh distractors")
    mesh_distractors = floating_meshes + falling_meshes



    # ⭐asset 尺度自动适配⭐
    # Resolve any centimeter-meter scale issues of the assets
    infinigen_utils.resolve_scale_issues_with_metrics_assembler()

    # ⭐加载灯光⭐
    # Create lights to randomize in the working area
    scene_lights = []
    num_scene_lights = capture_config.get("num_scene_lights", 0)
    for i in range(num_scene_lights):
        light_prim = stage.DefinePrim(f"/Lights/SphereLight_scene_{i}", "SphereLight")
        scene_lights.append(light_prim)
    print(f"[SDG-Infinigen] Created {len(scene_lights)} scene lights")

    # Register replicator randomizers and trigger them once
    print(f"[SDG-Infinigen] Registering replicator graph randomizers")
    infinigen_utils.register_dome_light_randomizer()

    # infinigen_utils.register_shape_distractors_color_randomizer(shape_distractors)

   
   
    # ⭐数据捕获的一些配置⭐
   
    # Check if the render mode needs to be switched to path tracing for the capture (by default: RayTracedLighting)
    use_path_tracing = capture_config.get("path_tracing", False)

    # Capture detail using subframes (https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/subframes_examples.html)
    rt_subframes = capture_config.get("rt_subframes", 3)

    # Min and max distance between the camera and the target object
    camera_distance_to_target_range = capture_config.get("camera_distance_to_target_range", (0.5, 2.))

    # Number of captures (frames = total_captures * num_cameras)
    # NOTE: if captured frames have no labeled data, they can be skipped (e.g. PoseWriter with skip_empty_frames=True)
    total_captures = capture_config.get("total_captures", 0)

    # Number of captures per environment with the objects in the air or dropped
    num_floating_captures_per_env = capture_config.get("num_floating_captures_per_env", 0)
    num_dropped_captures_per_env = capture_config.get("num_dropped_captures_per_env", 0)

    

    step_delta_time = float(capture_config.get("step_delta_time", 0.0))
    wait_after_each_capture = bool(capture_config.get("wait_after_each_capture", True))
    
    materials = []


    # # 将材质USD文件作为引用添加到当前舞台
    usd_file_path = materials_control_config['classic_materials']['usd_file_path']
    classic_materials_prim_path = materials_control_config['classic_materials']['scope_path']
    add_reference_to_stage(usd_path=usd_file_path, prim_path=classic_materials_prim_path)
    classic_materials = infinigen_utils.find_materials(stage, f"{classic_materials_prim_path}")
    materials.extend(classic_materials)


    omni_pbr_materials = generate_pbr_materials(materials_control_config,stage,mat_map=mat_map)
    materials.extend(omni_pbr_materials)
    
    # ⭐⭐⭐循环场景，开始捕获数据⭐⭐⭐
    # Start the SDG loop
    env_cycle = cycle(env_urls)
    container_cycle = cycle(container_urls)
    
    
    capture_counter = 0
    
    # Gradually increase the number of distractors
    env_count = 0

    json_str = args.add_angle

    data_gen_list = []


    roll_range = (-15,15)
    azimuth_range = args.camera_azimuth
    distance_range = camera_distance_to_target_range # (1.5,1.5)

    if not json_str:

        polar_range = latitude_range_to_polar_range(args.camera_latitude)

        

        patches = [SpherePatch(
                polar_range=polar_range,
                azimuth_range=azimuth_range,
            )]

        train_dict = {'gener':RandomUniformSphereCoord(
                patches=patches,total_samples=capture_config.get("total_captures", 0)),
        'writers_init':lambda : writers_init(writers_config,render_products,mode='train')}

        data_gen_list.append(train_dict)

    
    
    # load env
    env_url = next(env_cycle)
    # env_url = next(env_cycle)
    # env_url = next(env_cycle)
    # env_url = next(env_cycle)
    # Load the new environment
    print(f"[SDG-Infinigen] Loading environment: {env_url}")
    infinigen_utils.load_env(env_url, prim_path="/Environment",simulation_app=simulation_app)

    # simulation_app.update()

    # Setup the environment (add collision, fix lights, etc.) and update the app once to apply the changes
    print(f"[SDG-Infinigen] Setting up the environment")
    infinigen_utils.setup_env(root_path="/Environment", hide_top_walls=debug_mode)
    infinigen_utils.run_simulation(num_frames=3000, render=False)  
    simulation_app.update()

    
    for data_gener in data_gen_list:
        writers = data_gener['writers_init']()
        gener = iter(data_gener['gener'])



        while True:
            if any(exit_file for exit_file in Path(lmdb_output_dir).iterdir() if exit_file.is_file() and exit_file.suffix == ".exit"):
                break




            # Load the next environment
            
            infinigen_utils.remove_prim('/Assets',simulation_app)


            # Load container
            container_url = next(container_cycle)
            infinigen_utils.remove_prim('/Container',simulation_app)

            container_stage_path = '/Container'
            container_asset = infinigen_utils.load_env(container_url, prim_path=container_stage_path,simulation_app=simulation_app)

            infinigen_utils.add_colliders_to_env(container_stage_path, approximation_type = "boundingCube")
            
            # infinigen_utils.add_static_collider(container_stage_path)
            infinigen_utils.set_transform_attributes(container_asset, location=Gf.Vec3d([0,0,0]), rotation=Gf.Vec3f([0,0,0]), scale=Gf.Vec3f([3,random.uniform(.1,.2),3]))
            # infinigen_utils.asset_size_adaptive(container_asset,max_limit=0.8,min_limit=0.1,target_value=random.uniform(0.3,0.6))

            bind_materials_to_assets(
                [container_asset],classic_materials,
                is_maintain_material_structure=False,usd_materials_num=10)
            
            target_assets = []
            
            manual_label_config = labeled_assets_config.get("manual_label", [])
            original_label_config = labeled_assets_config.get("original_label", [])
            
            
            
            if manual_label_config:
                manual_floating_assets, manual_falling_assets = infinigen_utils.load_manual_labeled_assets(manual_label_config)
                target_assets.extend(manual_falling_assets)

                for asset_prim in manual_falling_assets:
                    infinigen_utils.add_colliders_and_rigid_body_dynamics(asset_prim, disable_gravity=False)



            if original_label_config:
                original_assets = infinigen_utils.load_original_labeled_assets(original_label_config)
                target_assets.extend(original_assets)
            
            bind_materials_to_assets(
                target_assets,classic_materials,
                is_maintain_material_structure=False,usd_materials_num=10)



            infinigen_utils.run_simulation(num_frames=3000, render=False)  



            simulation_app.update()

            


            #Get the plane prim 
            match_string = random.choice(["TableDining"])
            # match_string = random.choice(["TableDining",'floor'])
            root_path= '/Environment'

            plane_prims = infinigen_utils.find_matching_prims(
                match_strings=[match_string], root_path=root_path, prim_type="Xform", first_match_only=False,exception_prim_strings=[
                '/Environment/TableDiningFactory_3810673__spawn_asset_8768607__001',    # dining_room_4
                '/Environment/TableDiningFactory_6160158__spawn_asset_9053640__001',     # dining_room_5
                '/Environment/TableDiningFactory_5756319__spawn_asset_664843__001',     # dining_room_6
                '/Environment/TableDiningFactory_8694695__spawn_asset_1032784__001_SPLIT_GLAS',   # dining_room_8
                ] 
            )

            # random asset plain
            for plane_prim in plane_prims:
                infinigen_utils.add_colliders_to_env(plane_prim.GetPath(), approximation_type = "boundingCube")
            bind_materials_to_assets(plane_prims,materials,is_maintain_material_structure=True)
            plane_prim = random.choice(plane_prims)



            working_area_loc_abs = (0,0,0)

            target_loc_range = infinigen_utils.offset_range((-0.5,0.2,-0.5,.5,0.8,.5), working_area_loc_abs)
            infinigen_utils.randomize_poses(
                target_assets,
                location_range=target_loc_range,
                rotation_range=(0, 25),
                scale_range=[.8,1],
            )

            for asset_to_adapt in target_assets:
                
                # todo tem
                rotation = Gf.Vec3f([180,0,0])
                #rotation = Gf.Vec3f([0,0,0])


                # infinigen_utils.set_transform_attributes(asset_to_adapt, location=Gf.Vec3d([0,0,0]), rotation=rotation, scale=Gf.Vec3f([1,1,1]))
                infinigen_utils.asset_size_adaptive(asset_to_adapt,max_limit=.15,min_limit=0.05,target_value=0.1)
                # infinigen_utils.add_colliders_and_rigid_body_dynamics(asset_to_adapt, disable_gravity=0)
            
            # translate the env location to make the plane under target prim
            # infinigen_utils.translate_env_under_target_asset(plane_prim,target_assets[0],(0,0,0))  # (0,-0.12,0) for disk
            infinigen_utils.translate_env_under_target_asset(plane_prim,container_asset,(0,0,0))  # (0,-0.12,0) for disk


            # ⭐⭐我们的主体asset的位置⭐⭐
            # Get the spawn areas as offseted location ranges from the working area (min_x, min_y, min_z, max_x, max_y, max_z)
            print(f"\tRandomizing {len(target_assets)} target assets around the working area")

            # ⭐视窗相机位置和角度设置⭐
            
            if debug_mode:
                camera_loc = (working_area_loc_abs[0], working_area_loc_abs[1]+5, working_area_loc_abs[2]+3)
                print(f"相机位置:{camera_loc}")
                set_camera_view(eye=np.array(camera_loc), target=np.array(working_area_loc_abs))




            
            # Mesh distractors
            print(f"\tRandomizing {len(mesh_distractors)} mesh distractors around the working area")

            mesh_loc_x0,mesh_loc_x1 = distractors_config['mesh_distractors']['location_range']['x']
            mesh_loc_y0,mesh_loc_y1 = distractors_config['mesh_distractors']['location_range']['y']
            mesh_loc_z0,mesh_loc_z1 = distractors_config['mesh_distractors']['location_range']['z']
            mesh_dis_scale_range = distractors_config['mesh_distractors']['scale_range']
            mesh_loc_range = infinigen_utils.offset_range((mesh_loc_x0,mesh_loc_y0,mesh_loc_z0,mesh_loc_x1,mesh_loc_y1,mesh_loc_z1), working_area_loc_abs)
            infinigen_utils.randomize_poses(
                mesh_distractors,
                location_range=mesh_loc_range,
                rotation_range=(0, 25),
                scale_range=mesh_dis_scale_range,
            )

            # Shape distractors
            print(f"\tRandomizing {len(shape_distractors)} shape distractors around the working area")

            shape_loc_x0,shape_loc_x1 = distractors_config['shape_distractors']['location_range']['x']
            shape_loc_y0,shape_loc_y1 = distractors_config['shape_distractors']['location_range']['y']
            shape_loc_z0,shape_loc_z1 = distractors_config['shape_distractors']['location_range']['z']
            shape_dis_scale_range = distractors_config['shape_distractors']['scale_range']

            shape_loc_range = infinigen_utils.offset_range((shape_loc_x0,shape_loc_y0,shape_loc_z0,shape_loc_x1,shape_loc_y1,shape_loc_z1), working_area_loc_abs)
            infinigen_utils.randomize_poses(
                shape_distractors,
                location_range=shape_loc_range,
                rotation_range=(0, 25),
                scale_range=shape_dis_scale_range,
            )
            
            # simulation_app.update()

            print(f"\tRandomizing {len(scene_lights)} scene lights properties and locations around the working area")
            # lights_loc_range = infinigen_utils.offset_range(capture_config.get('lights_offset_range',(-1.5, -0.1, -1.5, 1.5, 0.8, 1.5)), working_area_loc_abs)
            lights_loc_range = infinigen_utils.offset_range(capture_config.get('lights_offset_range',(-0.15, 0.6, -0.15, 0.15, 1.1, 0.15)), working_area_loc_abs)
            infinigen_utils.randomize_lights(
                scene_lights,
                location_range=lights_loc_range,
                intensity_range=capture_config.get('lights_intensity_range',(4000, 5000)),
                color_range=capture_config.get('lights_color_range',(0.1, 0.1, 0.1, 0.9, 0.9, 0.9)),
            )


            print(f"\tRandomizing dome lights")
            rep.utils.send_og_event(event_name="randomize_dome_lights")

            print(f"\tRandomizing shape distractor colors")
            rep.utils.send_og_event(event_name="randomize_shape_distractor_colors")

            # Run the physics simulation for a few frames to solve any collisions
            # # 先用一些仿真帧稳定落位/碰撞
            print(f"\tFixing collisions through physics simulation")
            simulation_app.update()
            infinigen_utils.run_simulation(num_frames=100, render=True)        
            

            # Check if the render products need to be enabled for the capture
            if disable_render_products:
                for rp in render_products:
                    rp.hydra_texture.set_updates_enabled(True)

            # Check if the render mode needs to be switched to path tracing for the capture
            if use_path_tracing:
                carb.settings.get_settings().set("/rtx/rendermode", "PathTracing")
            try:


                for i in range(num_dropped_captures_per_env):
                    # Check if the total captures have been reached
                    # if capture_counter >= total_captures:
                    #     break

                    if any(exit_file for exit_file in Path(lmdb_output_dir).iterdir() if exit_file.is_file() and exit_file.suffix == ".exit"):
                        break
                    # Spawn the cameras with a smaller polar angle to have mostly a top-down view of the objects
                    print(f"\tRandomizing camera poses")

                    target_asset_centers = [infinigen_utils.calculate_asset_world_center(target_asset) for target_asset in target_assets]
                    target_asset_centers = [target_asset_center for target_asset_center in target_asset_centers if target_asset_center[1] > 0]
                    if not target_asset_centers:
                        continue

                    print('[[middle]]',tuple(target_asset_centers))
                    infinigen_utils.randomize_camera_poses(
                        cameras, gener,look_at=tuple(random.choice(target_asset_centers)),roll_range=roll_range,distance_range=distance_range
                    )

                    distractors = stage.GetPrimAtPath('/Distractors')

                    # if random.uniform(0,1) < materials_control_config['pbr']['pbr_prob']:
                    bind_materials_to_prims_recursively(plane_prim,omni_pbr_materials,is_mesh_bind_material=True)
                    bind_materials_to_prims_recursively(distractors,materials,is_mesh_bind_material=True)
                    
                    # todo random visibility ,may result in unexpected exit
                    # if i%20 == 0:
                    #     infinigen_utils.random_visibility("/Distractors")
                        
                    # 取余 纬度转极角
                    # latitude_range = [90-polar for polar in args.camera_latitude]
                    # latitude_range.sort()
                    



                    # print(
                    #     f"\tCapturing dropped assets {i+1}/{num_dropped_captures_per_env}; total captures: {capture_counter+1}/{total_captures};"
                    # )
                    simulation_app.update()
                    capture_one_frame(rt_subframes,step_delta_time,pause_timeline=True,wait_after=wait_after_each_capture)
                    capture_counter += 1   
            except StopIteration:
                break


                
 

            # Check if the render products need to be disabled until the next capture
            if disable_render_products:
                for rp in render_products:
                    rp.hydra_texture.set_updates_enabled(False)

            # Check if the render mode needs to be switched back to raytracing until the next capture
            if use_path_tracing:
                carb.settings.get_settings().set("/rtx/rendermode", "RayTracedLighting")

            env_count += 1


        #todo 跑一段物理（掉落阶段）
        print(f"\tRunning the simulation (drop phase)")
        infinigen_utils.run_simulation(num_frames=200, render=False)
            
        
        
        # Wait until the data is written to the disk
        rep.orchestrator.wait_until_complete()
        
        # for cur_asset in target_assets:
        #     from isaacsim.core.utils.semantics import get_labels
        #     label = get_labels(cur_asset)
        #     print(label)

        # Detach the writers
        print(f"[SDG-Infinigen] Detaching writers")
        for writer in writers:
            writer.detach()


    # Destroy render products
    print(f"[SDG-Infinigen] Destroying render products")
    for rp in render_products:
        rp.destroy()

    print(f"[SDG-Infinigen] SDG Finished, captured {capture_counter * num_cameras} frames..")


def o3d_syn_data_copy_to_local(remoteip, username, passdword, syn_data_dir, target_data_dir, copy_status=False):
    """
    o3d合成数据迁移
    """
    import time
    import subprocess
    from subprocess import Popen
    def copy_syn_data_to_train_server_command(syn_data_dir, target_data_dir):
        """ 拷贝合成数据到训练机器的目标地址 """
        command = rf"sshpass -p {passdword} scp -r {syn_data_dir}/* {username}@{remoteip}:{target_data_dir} "
        return command
    def copy_syn_data_status_to_train_server_command(syn_data_dir, target_data_dir):
        """ 拷贝合成数据到训练机器的目标地址 """
        command = rf"plink -pw {passdword} scp -r {syn_data_dir} {username}@{remoteip}:{target_data_dir} "
        return command
    print(f"o3dGenDataInfo: -----数据拷贝到训练服务器-----")
    if copy_status:
        gen_common = copy_syn_data_status_to_train_server_command(
            syn_data_dir=syn_data_dir, 
            target_data_dir=target_data_dir,
        )
    else:
        gen_common = copy_syn_data_to_train_server_command(
            syn_data_dir=syn_data_dir, 
            target_data_dir=target_data_dir,
        )
    print(f"o3dGenDataInfo: 执行命令如下\n\t{gen_common}")
    start_time = time.time()
    p = Popen(
        gen_common,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
    )

    time.sleep(3)
    print(f"o3dGenDataInfo: 生成数据迁移中......")

    if p.wait():
        end_time = time.time()
        print("o3dGenDataInfo: 结束的时间：【{}】".format(
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(end_time))))
        count_time = end_time - start_time
        print(f"o3dGenDataInfo: 所用的时间：【{count_time}】")
    time.sleep(2)


def main():

    # WriterRegistry.register(LMDBWriter)
    # (
    # WriterRegistry._default_writers.append("LMDBWriter")
    #     if "LMDBWriter" not in WriterRegistry._default_writers
    #     else None)
    
    WriterRegistry.register(LMDBWriterMultiAssets)
    (
    WriterRegistry._default_writers.append("LMDBWriterMultiAssets")
        if "LMDBWriterMultiAssets" not in WriterRegistry._default_writers
        else None)

    # WriterRegistry.register(KPSWriter)
    # (
    # WriterRegistry._default_writers.append("KPSWriter")
    #     if "KPSWriter" not in WriterRegistry._default_writers
    #     else None)

    # Check if debug mode is enabled
    debug_mode = config.get("debug_mode", False)

    # if debug_mode:
    #     np.random.seed(11)
    #     random.seed(11)
    #     rep.set_global_seed(11)

    # Start the SDG pipeline
    print(f"[SDG-Infinigen] Starting the SDG pipeline.")
    run_sdg(config,args)
    print(f"[SDG-Infinigen] SDG pipeline finished.")


    # Make sure the app closes on completion even if in debug mode
    if args.close_on_completion:
        simulation_app.close()

    # In debug mode, keep the app running until manually closed
    if debug_mode:
        while simulation_app.is_running():
            simulation_app.update()

    simulation_app.close()


if __name__ == "__main__":
    main()


