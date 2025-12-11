
# '''
# ignore_materials = False  # Don't import/export materials
# ignore_animations = False  # Don't import/export animations
# ignore_camera = False  # Don't import/export cameras
# ignore_light = False  # Don't import/export lights
# single_mesh = False  # By default, instanced props will be export as single USD for reference. If
# # this flag is true, it will export all props into the same USD without instancing.
# smooth_normals = True  # Smoothing normals, which is only for assimp backend.
# export_preview_surface = False  # Imports material as UsdPreviewSurface instead of MDL for USD export
# support_point_instancer = False  # Deprecated
# embed_mdl_in_usd = True  # Deprecated.
# use_meter_as_world_unit = False  # Sets world units to meters, this will also scale asset if it's centimeters model.
# create_world_as_default_root_prim = True  # Creates /World as the root prim for Kit needs.
# embed_textures = True  # Embedding textures into output. This is only enabled for FBX and glTF export.
# convert_fbx_to_y_up = False  # Always use Y-up for fbx import.
# convert_fbx_to_z_up = False  # Always use Z-up for fbx import.
# keep_all_materials = False  # If it's to remove non-referenced materials.
# merge_all_meshes = False  # Merges all meshes to single one if it can.
# use_double_precision_to_usd_transform_op = False  # Uses double precision for all transform ops.
# ignore_pivots = False  # Don't export pivots if assets support that.
# disabling_instancing = False  # Don't export instancing assets with instanceable flag.
# export_hidden_props = False  # By default, only visible props will be exported from USD exporter.
# baking_scales = False  # Only for FBX. It's to bake scales into meshes.
# ignore_flip_rotations = False  # Don't ignore animation's flip rotation value.
# ignore_unbound_bones = False  # Only for FBX. Don't ignore unbound bones.
# bake_mdl_material = False  # Bake mdl material when export
# export_separate_gltf = False  # Export gltf with separate bin file if true, else export one standalone gltf.
# export_mdl_gltf_extension = False  # Only for glTF. Export materials as NV_materials_mdl extension materials.
# convert_stage_up_y = False  # Set stage up-axis to y-up.
# convert_stage_up_z = False  # Set stage up-axis to z-up.


from pathlib import Path
from isaacsim import SimulationApp

# 1. 以 headless 模式启动 Omniverse Kit
simulation_app = SimulationApp({"headless": True})

import asyncio
import omni.kit.asset_converter as converter
from omni.kit.asset_converter import AssetConverterContext


def progress_callback(current_step: int, total: int):
    # Show progress
    print(f"{current_step} of {total}")

async def convert_glb_to_usd(src, dst):

    asset_converter_obj = AssetConverterContext()
    asset_converter_obj.single_mesh = True
    # asset_converter_obj.use_meter_as_world_unit = True
    asset_converter_obj.merge_all_meshes = True
    asset_converter_obj.convert_stage_up_z = False
    asset_converter_obj.bake_mdl_material = True
    asset_converter_obj.embed_mdl_in_usd = True  # Deprecated.



    mgr = converter.get_instance()
    task = mgr.create_converter_task(
        import_path=src,
        output_path=dst,
        progress_callback=progress_callback,
        asset_converter_context=asset_converter_obj,
    )

    print("开始转换:", src)
    success = await task.wait_until_finished()

    if success:
        print("转换成功:", dst)
    else:
        print("转换失败！错误信息：")
        print("status:", task.get_status())
        print("error:", task.get_error_message())

if __name__ == "__main__":
    src_root = "/data2/isaacsim/assets/glb"
    for src_file in Path(src_root).glob("*.glb"):

    
    
        dst_file = src_file.with_suffix(".usd").with_stem(src_file.stem + "_converted")
        asyncio.get_event_loop().run_until_complete(convert_glb_to_usd(str(src_file), str(dst_file)))
    simulation_app.close()


