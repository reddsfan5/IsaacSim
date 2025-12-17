import asyncio
import omni.replicator.core as rep

async def run():
    cam = rep.create.camera(position=(10,10,10))

    rp = rep.create.render_product(cam, (1024, 512))

    cam_params = rep.annotators.get("CameraParams")
    cam_params.attach(rp)

    await rep.orchestrator.step_async()

    data = cam_params.get_data()
    T_c2w = data["cameraViewTransform"]      # shape (16,) 或 (4,4) 取决于版本
    print("cameraViewTransform:", T_c2w)

asyncio.ensure_future(run())
