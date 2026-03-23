import omni.usd
from pxr import UsdShade, Sdf

stage = omni.usd.get_context().get_stage()

material_path = "/World/Materials/GoldBrushed"
shader_path = material_path + "/Shader"

# 创建Material
material = UsdShade.Material.Define(stage, material_path)

# 创建OmniPBR shader
shader = UsdShade.Shader.Define(stage, shader_path)
shader.CreateIdAttr("OmniPBR")

material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")

# ======================
# 贴图路径
# ======================

base_path = "/data2/isaacsim/materials/pbr_texture/Metal/MetalGoldBrushed002/SPECULAR/6K/"

col_map   = base_path + "MetalGoldBrushed002_COL_6K_SPECULAR.jpg"
rough_map = base_path + "MetalGoldBrushed002_ROUGH_6K_SPECULAR.jpg"
nrm_map   = base_path + "MetalGoldBrushed002_NRM_6K_SPECULAR.jpg"
refl_map  = base_path + "MetalGoldBrushed002_REFL_6K_SPECULAR.jpg"

# ======================
# BaseColor (COL)
# ======================

shader.CreateInput(
    "diffuse_texture", Sdf.ValueTypeNames.Asset
).Set(col_map)

shader.CreateInput(
    "diffuse_texture_enable", Sdf.ValueTypeNames.Bool
).Set(True)

# ======================
# Roughness
# ======================

shader.CreateInput(
    "reflection_roughness_texture", Sdf.ValueTypeNames.Asset
).Set(rough_map)

shader.CreateInput(
    "reflection_roughness_texture_influence", Sdf.ValueTypeNames.Float
).Set(1.0)

# ======================
# Normal
# ======================

shader.CreateInput(
    "normalmap_texture", Sdf.ValueTypeNames.Asset
).Set(nrm_map)

shader.CreateInput(
    "normalmap_texture_enable", Sdf.ValueTypeNames.Bool
).Set(True)

# ======================
# Specular (REFL)
# ======================

shader.CreateInput(
    "specular_texture", Sdf.ValueTypeNames.Asset
).Set(refl_map)

shader.CreateInput(
    "specular_texture_enable", Sdf.ValueTypeNames.Bool
).Set(True)

# ======================
# Metallic = 0 (specular workflow)
# ======================

shader.CreateInput(
    "metallic_constant", Sdf.ValueTypeNames.Float
).Set(0.0)

print("Material created:", material_path)