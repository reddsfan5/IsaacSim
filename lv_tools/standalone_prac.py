import numpy as np
from isaacsim import SimulationApp

app = SimulationApp(launch_config={"headless": False})



from isaacsim.core.api.objects import DynamicCuboid,GroundPlane
import omni.usd
import omni.replicator.core as rep


omni.usd.get_context().new_stage()
stage = omni.usd.get_context().get_stage()

# GroundPlane(prim_path="/World/GroundPlane",z_position=0)
# DynamicCuboid(prim_path="/World/dynamic_cuboid",name="dynamic_cuboid",translation=np.array([0, 0, 0]),scale=np.array([1, 1, 1]),color=np.array([255, 0, 0]))

with rep.new_layer():
    

    # Add Default Light
    distance_light = rep.create.light(rotation=(315,0,0), intensity=3000, light_type="distant")

    # Defining a plane to place the avocado
    plane = rep.create.plane(scale=100, visible=True)

    rep.create.light(rotation=(315, 0, 0), intensity=6000, light_type="dome")

    # Defining the avocado starting from the NVIDIA residential provided assets. Position and semantics of this asset are modified.
    AVOCADO = '/home/ubuntu/lxd/usd_file/glb/airship.usd'
    airship = rep.create.from_usd(AVOCADO)
    with airship:
        rep.modify.semantics([('class', 'airship')])
        rep.modify.pose(
                position=(0, 0, 10),
                rotation=(-23,-45, 0),
                scale=(1,1,1)
                )

while app.is_running():
    app.update()


app.close()









