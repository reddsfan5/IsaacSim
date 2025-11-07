import omni.usd
import omni.kit.commands
import omni.scene.optimizer.core
import time
import json
import carb
 
# Get the UsdContext, which manages the application's scenes.
usd_context = omni.usd.get_context()
# Get the stage that is currently open in the application.
stage = usd_context.get_stage()
 
if not stage:
    carb.log_error("No stage is open. Please open your USD file first and run this script again.")
else:
    optimizer_interface = None
    # Get the optimizer interface.
    optimizer_interface = omni.scene.optimizer.core.acquire_interface()
     
    # Create the execution context.
    execution_context = omni.scene.optimizer.core.ExecutionContext()

    # Get the unique ID of the currently open stage.
    stage_id = usd_context.get_stage_id()
    execution_context.usdStageId = stage_id
    # -----------------------------------------

    # Define parameters.
    merge_params = {
        "merge_materials": True, 
        "merge_visuals_only": True
    }
    
    hidden_mesh_params = {
        "operation": "findHiddenMeshes",
        "paths": [],
        "gridResolution": 100.0,
        "action": 0, #This flag '0' sets the mesh to deactivate
        "useGpu": False
    }

    # Max mean error prevents the new mesh surface from deviating more than this amount from the original.
    decimation_params = {
        "decimation_filter_prim_type": "Mesh",
        "max_mean_error": 0.1
    }

    carb.log_info("Context prepared. Executing operations...")

    # --- Execute Step 1: Merge Meshes ---
    carb.log_info("Running Step 1: Merge Meshes...")
    result = optimizer_interface.execute_operation("merge", execution_context, json.dumps(merge_params))
     
    if not result[0]:
        carb.log_error(f"Merge operation failed: {result[1]}")
    else:
        carb.log_info(f"Merge operation successful. Log: {result[1]}")

        # --- Execute Step 2: Find Hidden Meshes ---
        carb.log_info("Running Step 2: Find Hidden Meshes...")
        result = optimizer_interface.execute_operation("findHiddenMeshes", execution_context, json.dumps(hidden_mesh_params))
         
        if not result[0]:
            print("Find hidden meshes operation failed: ", result[1])
        else:
            print("Find hidden meshes successful. Log: ", result[1])
            # --- Execute Step 3: Decimate Meshes by Error ---
            carb.log_info("Running Step 3: Decimate Meshes...")
            result = optimizer_interface.execute_operation("decimateMeshes", execution_context, json.dumps(decimation_params))
             
            if not result[0]:
                carb.log_error(f"Decimate meshes operation failed: {result[1]}")
            else:
                carb.log_info(f"Decimate meshes successful. Log: {result[1]}")

print("--- Script finished. ---")
