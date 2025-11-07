import omni.replicator.core as rep
import omni.usd

# 自定义 Annotator 类
class MaterialAnnotator(rep.AnnotatorBase):
    def __init__(self):
        super().__init__("material_name")

    def setup(self):
        pass

    def post_render(self):
        stage = omni.usd.get_context().get_stage()
        results = []
        for prim in stage.Traverse():
            if prim.GetTypeName() == "Mesh":
                binding = prim.GetRelationship("material:binding")
                if binding and binding.GetTargets():
                    mat_path = binding.GetTargets()[0].pathString
                    results.append({
                        "prim_path": prim.GetPath().pathString,
                        "material": mat_path
                    })
        self._data = results

    def get_data(self):
        return self._data

# ✅ 注册 Annotator
rep.annotator.register(MaterialAnnotator())

# ✅ 初始化 Writer 并启用我们注册的 annotator
writer = rep.WriterRegistry.get("BasicWriter")
writer.initialize(
    output_dir="/tmp/rep_output",
    rgb=True,
    bounding_box_2d_tight=True,
    semantic_segmentation=True,
    material_name=True,  # 启用自定义输出
)

rep.orchestrator.run_once()
