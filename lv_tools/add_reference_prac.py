from pxr import PhysxSchema, UsdPhysics,UsdGeom
import omni.usd

# get stage, create scene prim, and apply physx schema scene API
stage = omni.usd.get_context().get_stage()
scenePath = "/World/PhysicsScene"
scene = UsdPhysics.Scene.Define(stage, scenePath)
physxSceneAPI = PhysxSchema.PhysxSceneAPI(scene.GetPrim())

# force all actors in the scene to a fixed position and velocity iteration count
posIters = 16
velIters = 1
physxSceneAPI.CreateMaxPositionIterationCountAttr().Set(posIters)
physxSceneAPI.CreateMinPositionIterationCountAttr().Set(posIters)
physxSceneAPI.CreateMaxVelocityIterationCountAttr().Set(velIters)
physxSceneAPI.CreateMinVelocityIterationCountAttr().Set(velIters)