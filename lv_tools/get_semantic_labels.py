import omni.usd
from pxr import UsdSemantics


def get_direct_labels_from_prim(prim):
    """
    获取某个 Prim 上“直接挂载”的 semantic labels。
    返回格式示例：
    {
        "class": ["729_disk"]
    }
    """
    labels_info = {}

    for schema_name in prim.GetAppliedSchemas():
        # Isaac Sim 5.0+ 的语义标签 schema 形如：
        # SemanticsLabelsAPI:class
        if not schema_name.startswith("SemanticsLabelsAPI:"):
            continue

        instance_name = schema_name.split(":", 1)[1]

        labels_api = UsdSemantics.LabelsAPI(prim, instance_name)
        labels_attr = labels_api.GetLabelsAttr()

        if labels_attr:
            labels = labels_attr.Get()
            if labels:
                labels_info[instance_name] = list(labels)

    return labels_info


def collect_all_labeled_prims():
    """
    遍历当前 Stage：
    1. 找到所有带 semantic label 的 Prim
    2. 汇总本次任务中出现过的所有 class label
    """
    stage = omni.usd.get_context().get_stage()

    labeled_prims = []
    all_class_labels = set()

    for prim in stage.Traverse():
        if not prim.IsValid():
            continue

        labels_info = get_direct_labels_from_prim(prim)

        if not labels_info:
            continue

        prim_path = prim.GetPath().pathString

        labeled_prims.append({
            "prim_path": prim_path,
            "labels": labels_info,
        })

        # 只统计 class 标签
        if "class" in labels_info:
            all_class_labels.update(labels_info["class"])

    return labeled_prims, sorted(all_class_labels)


# 使用
labeled_prims, task_class_labels = collect_all_labeled_prims()

print("===== 当前任务中所有带标注的 Prim =====")
for item in labeled_prims:
    print(item)

print("\n===== 当前任务中涉及的全部 class label =====")
print(task_class_labels)















