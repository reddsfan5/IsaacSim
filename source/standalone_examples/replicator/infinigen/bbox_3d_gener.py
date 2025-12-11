import argparse
import json
import math
import os
import shutil
import sys
import asyncio
import random
import queue
import threading
import time
from itertools import cycle
from threading import local
from pathlib import Path

import numpy as np
import yaml
from fastapi import FastAPI
from pydantic import BaseModel
import uuid



from fastapi import FastAPI, Request


app = FastAPI()
# 最大并行任务数
MAX_RUNNING = 2

# 任务队列: 等待中的任务
task_queue = queue.Queue()

# 正在运行的任务 {task_id: TaskInfo}
running_tasks = {}





class TaskStatus:
    WAITING = "waiting"
    RUNNING = "running"
    FINISHED = "finished"
    CANCELLED = "cancelled"
    FAILED = "failed"

# 任务对象
class TaskInfo:
    def __init__(self, task_id:str, remote_save_root:str,local_glb_path:str,
                 camera_yaw:tuple=(0,360),
                 camera_polar:tuple=(0,90),
                 data_num:int=20000):
        self.task_id = task_id
        self.remote_save_root = remote_save_root
        self.local_glb_path = local_glb_path
        self.camera_yaw = camera_yaw
        self.camera_polar = camera_polar
        self.data_num = data_num


        self.status = TaskStatus.WAITING
        self.cancel_event = threading.Event()


# 用户提交数据格式
class TaskRequest(BaseModel):
    task_id: str
    remote_save_root: str
    local_glb_path: str
    camera_yaw: tuple
    camera_polar: tuple
    data_num: int




def synthesize_data(task:TaskInfo):
    '''
    app的生命周期需由该函数所在的线程控制，所以其实例化先写在这里。

    又由于很多插件的导入依赖于app的启动加载，而相关函数的定义依赖于这些导入的插件接口，所以，将相关的
    导入和函数定义都放在该函数内。

    该函数负责一个完整的数据生产流程。
    '''

    YAML_CONFIG_PATH = './config/infinigen_multi_writers_pt_lv.yaml'


    if not os.path.isfile(YAML_CONFIG_PATH):
        raise FileNotFoundError(f"[SDG-Infinigen] Config file {YAML_CONFIG_PATH} does not exist")

    with open(YAML_CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)

    task.status = TaskStatus.RUNNING
    print(f"[TASK {task.task_id}] 开始执行...")
    
    from isaacsim import SimulationApp
    simulation_app = SimulationApp(launch_config={
        "headless": config.get("headless", True),
        "renderer": "RealTimePathTracing"  # 选择 RT 2.0 的渲染模式
    })


    import infinigen_sdg_utils as infinigen_utils
    from pxr import UsdGeom,Gf,Usd,UsdShade
    import carb
    import carb.settings
    import omni.client
    import omni.kit
    import omni.kit.app
    import omni.physx
    import omni.replicator.core as rep
    import omni.timeline
    import omni.usd
    from isaacsim.core.utils.viewports import set_camera_view
    from isaacsim.core.utils.semantics import get_labels
    from omni.isaac.core.utils.stage import add_reference_to_stage
    from omni.replicator.core import WriterRegistry
    import omni.kit.asset_converter as converter
    from omni.kit.asset_converter import AssetConverterContext


    sys.path.append('/home/ubuntu/lxd/lxd_code/isaacsim')
    from lv_tools.material_change import MaterialTexture, bind_materials_to_prims_recursively, create_pbr_with_texture,bind_materials_to_assets
    from lv_tools.writer_register import LMDBWriter,KPSWriter


    WriterRegistry.register(LMDBWriter)
    (
        WriterRegistry._default_writers.append("LMDBWriter")
        if "LMDBWriter" not in WriterRegistry._default_writers
        else None)

    WriterRegistry.register(KPSWriter)
    (
        WriterRegistry._default_writers.append("KPSWriter")
        if "KPSWriter" not in WriterRegistry._default_writers
        else None)



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


    # Run the SDG pipeline on the scenarios
    def run_sdg(config,task):

        # ⭐命令行调整配置⭐

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

        # ⭐创建stage，并设置向上轴⭐
        # Create a new stage
        print(f"[SDG-Infinigen] Creating a new stage")


        if task.data_num:
            capture_config['total_captures'] = task.data_num


        # asset格式转换，并存放到预期路径下，给出存放后的路径位置 。


        if (input_path:=task.local_glb_path) and os.path.isfile(input_path):
            usd_asset_dir = Path(config['global']['usd_asset_root'] + f'/{task.task_id}')
            if not usd_asset_dir.exists():
                usd_asset_dir.mkdir(exist_ok=True,parents=True)

            output_path = str(usd_asset_dir / f"{Path(input_path).stem}.usd")

            asyncio.get_event_loop().run_until_complete(convert_asset_to_usd(input_path, output_path))
            # simulation_app.close()

            labeled_assets_config = {"manual_label":[{"url": infinigen_utils.path_to_file_uri(output_path),
                                    "label": infinigen_utils.valid_stage_name(str(task.task_id)),
                                    "num": 1,
                                    "gravity_disabled_chance": 0}]}


        else:
            labeled_assets_config = config.get("labeled_assets", {})


        mat_map = MaterialTexture(materials_control_config['pbr']['texture_poliigon'])

        
        

        stage = omni.usd.get_context().get_stage()
        # Set stage Up axis
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)

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
            rp = rep.create.render_product(cam.GetPath(), resolution, name=f"rp_{cam.GetName()}")
            if disable_render_products:
                rp.hydra_texture.set_updates_enabled(False)
            render_products.append(rp)
        print(f"[SDG-Infinigen] Created {len(render_products)} render products")

        # Only create the writers if there are render products to attach to
        writers = []
        if render_products:
            for writer_config in writers_config:
                writer_config['kwargs']['task_id'] = task.task_id

                writer = infinigen_utils.setup_writer(writer_config)
                if writer:
                    writer.attach(render_products)
                    writers.append(writer)
                    print(f"\t {writer_config['type']}'s out dir: {writer_config.get('kwargs', {}).get('output_dir', '')}")
        print(f"[SDG-Infinigen] Created {len(writers)} writers")

        
        
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
        camera_distance_to_target_range = capture_config.get("camera_distance_to_target_range", (0.5, 1.5))

        # Number of captures (frames = total_captures * num_cameras)
        # NOTE: if captured frames have no labeled data, they can be skipped (e.g. PoseWriter with skip_empty_frames=True)
        total_captures = capture_config.get("total_captures", 0)

        # Number of captures per environment with the objects in the air or dropped
        num_floating_captures_per_env = capture_config.get("num_floating_captures_per_env", 0)
        num_dropped_captures_per_env = capture_config.get("num_dropped_captures_per_env", 0)

        
        
        # todo warmup

        # warmup_updates = int(capture_config.get("warmup_updates", 3))
        # warmup_dummy_steps = int(capture_config.get("warmup_dummy_steps", 1))
        step_delta_time = float(capture_config.get("step_delta_time", 0.0))
        wait_after_each_capture = bool(capture_config.get("wait_after_each_capture", True))
        
        materials = []


        # # 将USD文件作为引用添加到当前舞台
        usd_file_path = materials_control_config['classic_materials']['usd_file_path']
        classic_materials_prim_path = materials_control_config['classic_materials']['scope_path']
        add_reference_to_stage(usd_path=usd_file_path, prim_path=classic_materials_prim_path)
        classic_materials = infinigen_utils.find_materials(stage, f"{classic_materials_prim_path}/Looks")
        materials.extend(classic_materials)


        omni_pbr_materials = generate_pbr_materials(materials_control_config,stage,mat_map=mat_map)
        materials.extend(omni_pbr_materials)

        # bind_materials_to_assets(target_assets,materials,is_maintain_material_structure=True)


        
        # ⭐⭐⭐循环场景，开始捕获数据⭐⭐⭐
        # Start the SDG loop
        env_cycle = cycle(env_urls)
        
        
        capture_counter = 0
        
        # Gradually increase the number of distractors
        env_count = 0


        while capture_counter < total_captures:




            # Load the next environment
            env_url = next(env_cycle)


            infinigen_utils.remove_prim('/Assets',simulation_app)
            
            target_assets = []
            
            manual_label_config = labeled_assets_config.get("manual_label", [])
            original_label_config = labeled_assets_config.get("original_label", [])
            
            
            
            if manual_label_config:
                manual_floating_assets, manual_falling_assets = infinigen_utils.load_manual_labeled_assets(manual_label_config)
                target_assets.extend(manual_falling_assets)
            if original_label_config:
                original_assets = infinigen_utils.load_original_labeled_assets(original_label_config)
                target_assets.extend(original_assets)
            
            bind_materials_to_assets(
                target_assets,classic_materials,
                is_maintain_material_structure=False,usd_materials_num=10)


            # Load the new environment
            print(f"[SDG-Infinigen] Loading environment: {env_url}")
            infinigen_utils.load_env(env_url, prim_path="/Environment",simulation_app=simulation_app)

            # Setup the environment (add collision, fix lights, etc.) and update the app once to apply the changes
            print(f"[SDG-Infinigen] Setting up the environment")
            infinigen_utils.setup_env(root_path="/Environment", hide_top_walls=debug_mode)
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

            bind_materials_to_assets(plane_prims,materials,is_maintain_material_structure=True)
            plane_prim = random.choice(plane_prims)


            for asset_to_adapt in target_assets:
                infinigen_utils.set_transform_attributes(asset_to_adapt, location=Gf.Vec3d([0,0,0]), rotation=Gf.Vec3f([0,0,0]), scale=Gf.Vec3f([1,1,1]))
                infinigen_utils.asset_size_adaptive(asset_to_adapt)
            
            # translate the env location to make the plane under target prim
            infinigen_utils.translate_env_under_target_asset(plane_prim,target_assets[0],(0,0,0))  # (0,-0.12,0) for disk


            # ⭐⭐我们的主体asset的位置⭐⭐
            # Get the spawn areas as offseted location ranges from the working area (min_x, min_y, min_z, max_x, max_y, max_z)
            print(f"\tRandomizing {len(target_assets)} target assets around the working area")

            # ⭐视窗相机位置和角度设置⭐
            working_area_loc_abs = (0,0,0)
            if debug_mode:
                camera_loc = (working_area_loc_abs[0], working_area_loc_abs[1]+5, working_area_loc_abs[2]+3)
                print(f"相机位置:{camera_loc}")
                set_camera_view(eye=np.array(camera_loc), target=np.array(working_area_loc_abs))




            target_asset_center = infinigen_utils.calculate_asset_world_center(target_assets[0])
            print('[[middle]]',tuple(target_asset_center))
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
            lights_loc_range = infinigen_utils.offset_range(capture_config.get('lights_offset_range',(-1.5, -0.1, -1.5, 1.5, 0.8, 1.5)), working_area_loc_abs)
            infinigen_utils.randomize_lights(
                scene_lights,
                location_range=lights_loc_range,
                intensity_range=capture_config.get('lights_intensity_range',(4000, 6000)),
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
            infinigen_utils.run_simulation(num_frames=20, render=True)        
            
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
                

                infinigen_utils.randomize_camera_poses(
                    cameras, target_assets, camera_distance_to_target_range, polar_angle_range=capture_config['polar_angle_range'],look_at=tuple(target_asset_center),
                    look_at_offset = capture_config['camera_look_at_target_offset']
                )
                
                simulation_app.update()
                
                print(
                    f"\tCapturing floating assets {i+1}/{num_floating_captures_per_env}; total captures: {capture_counter+1}/{total_captures};"
                )
                
                
                infinigen_utils.run_simulation(num_frames=200, render=True)
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
            infinigen_utils.run_simulation(num_frames=200, render=False)

            # Check if the render products need to be enabled for the capture
            if disable_render_products:
                for rp in render_products:
                    rp.hydra_texture.set_updates_enabled(True)

            # Check if the render mode needs to be switched to path tracing for the capture
            if use_path_tracing:
                carb.settings.get_settings().set("/rtx/rendermode", "PathTracing")

            for i in range(num_dropped_captures_per_env):
                if task.cancel_event.is_set():
                    print(f"[TASK {task.task_id}] 收到取消信号，中断任务")
                    task.status = TaskStatus.CANCELLED
                    # simulation_app.close()
                    return



                # Check if the total captures have been reached
                if capture_counter >= total_captures:
                    break
                # Spawn the cameras with a smaller polar angle to have mostly a top-down view of the objects
                print(f"\tRandomizing camera poses")

                distractors = stage.GetPrimAtPath('/Distractors')

                # if random.uniform(0,1) < materials_control_config['pbr']['pbr_prob']:
                bind_materials_to_prims_recursively(plane_prim,omni_pbr_materials,is_mesh_bind_material=True)
                bind_materials_to_prims_recursively(distractors,materials,is_mesh_bind_material=True)
                
                if i%20 == 0:
                    infinigen_utils.random_visibility("/Distractors")
                    
                infinigen_utils.randomize_camera_poses(
                    cameras, target_assets, distance_range=camera_distance_to_target_range, polar_angle_range=task.camera_polar,camera_loc_yaw_range=task.camera_yaw,look_at=tuple(target_asset_center),
                    look_at_offset = capture_config['camera_look_at_target_offset']
                )
                print(
                    f"\tCapturing dropped assets {i+1}/{num_dropped_captures_per_env}; total captures: {capture_counter+1}/{total_captures};"
                )



                # rep.orchestrator.step(rt_subframes=rt_subframes, delta_time=0)
                
                simulation_app.update()
                capture_one_frame(rt_subframes,step_delta_time,pause_timeline=True,wait_after=wait_after_each_capture)
                capture_counter += 1    

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
        
        for cur_asset in target_assets:
            from isaacsim.core.utils.semantics import get_labels
            label = get_labels(cur_asset)
            print(label)


        # Detach the writers
        print(f"[SDG-Infinigen] Detaching writers")
        for writer in writers:
            writer.detach()

        # Destroy render products
        print(f"[SDG-Infinigen] Destroying render products")
        for rp in render_products:
            rp.destroy()

        print(f"[SDG-Infinigen] SDG Finished, captured {capture_counter * num_cameras} frames..")




    # SDG pipeline
    print(f"[SDG-Infinigen] Starting the SDG pipeline.")
    try:
        run_sdg(config,task)
        task.status = TaskStatus.FINISHED
        print(f"[TASK {task.task_id}] 执行完成")
    except Exception as e:
        print(f"[TASK {task.task_id}] 发生错误: {e}")
        task.status = TaskStatus.FAILED
    finally:
        # 从 running_tasks 删除
        running_tasks.pop(task.task_id, None)
    


    print(f"[SDG-Infinigen] SDG pipeline finished.")


    simulation_app.close()


def task_scheduler():
    """后台线程: 负责从队列取任务，保证最多并行两条"""
    while True:
        if len(running_tasks) < MAX_RUNNING:
            try:
                task = task_queue.get(timeout=1)
            except queue.Empty:
                continue

            # 放入运行中集合
            running_tasks[task.task_id] = task

            # 启动任务线程
            t = threading.Thread(target=synthesize_data, args=(task,))
            t.start()

        else:
            time.sleep(0.5)


# 启动调度线程
scheduler_thread = threading.Thread(target=task_scheduler, daemon=True)
scheduler_thread.start()
# -------------------------------
#        FastAPI 端点
# -------------------------------

@app.post("/submit")
def submit_task(req: TaskRequest):
    # task_id = str(uuid.uuid4())
    task = TaskInfo(req.task_id, req.remote_save_root, req.local_glb_path,
                    camera_yaw=req.camera_yaw,
                    camera_polar=req.camera_polar,
                    data_num=req.data_num)

    task_queue.put(task)
    return {
        "task_id": req.task_id,
        "status": task.status
    }






@app.post("/cancel/{task_id}")
def cancel_task(task_id: str):
    # 如果任务在运行，直接发中断信号
    if task_id in running_tasks:
        running_tasks[task_id].cancel_event.set()
        return {"task_id": task_id, "message": "正在运行任务，已发送中断信号"}

    # 如果任务还在队列里，需要从队列中删除
    removed = False
    temp_list = []
    while not task_queue.empty():
        t = task_queue.get()
        if t.task_id == task_id:
            removed = True
            t.status = TaskStatus.CANCELLED
        else:
            temp_list.append(t)
    for t in temp_list:
        task_queue.put(t)

    if removed:
        return {"task_id": task_id, "message": "等待中任务已取消"}

    return {"task_id": task_id, "message": "任务不存在"}


@app.get("/status/{task_id}")
def get_status(task_id: str):
    # 优先查运行中的
    if task_id in running_tasks:
        return {"task_id": task_id, "status": running_tasks[task_id].status}

    # 查队列
    tasks = list(task_queue.queue)
    for t in tasks:
        if t.task_id == task_id:
            return {"task_id": task_id, "status": t.status}

    return {"task_id": task_id, "status": "unknown"}


