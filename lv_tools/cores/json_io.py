import itertools
import json
from pathlib import Path
from typing import Union


def load_json_to_dict(json_path: Union[str,Path]) -> dict:
    '''
    json_path: json_file 路径。
    return:json_dict
    '''
    with open(json_path, encoding='utf8', mode='r') as f:
        json_dict = json.load(f)
    return json_dict

def save_json(dst_json_path:Union[str,Path], jd:dict):
    dst_json_path = Path(dst_json_path)
    if not (dst_dir:=dst_json_path.parent).exists():
        dst_dir.mkdir(parents=True,exist_ok=True)
    with open(dst_json_path, mode='w', encoding='utf8') as f:
        json.dump(jd, f, ensure_ascii=False)


if __name__ == '__main__':
    from collections import namedtuple
    AnnotatorParams = namedtuple(
        "AnnotatorParams",
        ["template", "data_type", "num_elems", "is_2d_array", "is_gpu_enabled", "hidden", "documentation"],
    )
    _annotators = {
        "camera_params": AnnotatorParams("CameraParams", None, None, None, True, False, ""),
        "rgb": AnnotatorParams("LdrColorSD", np.uint8, 4, True, True, False, ""),
        "normals": AnnotatorParams("NormalSD", np.float32, 4, True, True, False, ""),
        "motion_vectors": AnnotatorParams("TargetMotionSD", np.float32, 4, True, True, False, ""),
        "cross_correspondence": AnnotatorParams("CrossCorrespondenceSD", np.float32, 4, True, True, False, ""),
        "occlusion": AnnotatorParams(
            "OcclusionSD",
            np.dtype([("instanceId", "<u4"), ("semanticId", "<u4"), ("occlusionRatio", "<f4")]),
            1,
            False,
            True,
            False,
            "",
        ),
        "distance_to_image_plane": AnnotatorParams("DistanceToImagePlaneSD", np.float32, 1, True, True, False, ""),
        "distance_to_camera": AnnotatorParams("DistanceToCameraSD", np.float32, 1, True, True, False, ""),
    }
    print(t.template)

