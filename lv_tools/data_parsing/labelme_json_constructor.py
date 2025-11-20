from typing import List, Union

from lv_tools.cores.typing_custom import BoundingBox


def construct_one_shape(label: Union[str, int], points: BoundingBox, group_id: int = None, shape_type: str = None,
                        **kwargs) -> dict:
    if not shape_type:
        if len(points) == 2:
            shape_type = 'rectangle'
        else:
            shape_type = 'polygon'

    return {
        "label": label,
        "points": points,
        "group_id": group_id,
        "shape_type": shape_type,
        "flags": {
        },
        **kwargs
    }


def construct_labelme_jd(shapes: List[dict], imagePath: str, imageHeight: int, imageWidth: int, **kwargs) -> dict:
    return {
        "version": "5.0.1",
        "flags": {
        },
        "shapes": shapes,
        "imagePath": imagePath,
        "imageData": None,
        "imageHeight": imageHeight,
        "imageWidth": imageWidth,
        **kwargs
    }


class LabelmeConstructor:
    def __init__(self):
        self._shapes = []
    def construct_one_shape(self,label: Union[str, int], points: BoundingBox, group_id: int = None, shape_type: str = None,
                            **kwargs) -> dict:
        if not shape_type:
            if len(points) == 2:
                shape_type = 'rectangle'
            else:
                shape_type = 'polygon'

        self._shapes.append({
            "label": label,
            "points": points,
            "group_id": group_id,
            "shape_type": shape_type,
            "flags": {
            },
            **kwargs
        })

    def construct_final_jd(self,imagePath: str, imageHeight: int, imageWidth: int, **kwargs) -> dict:
        return {
            "version": "5.0.1",
            "flags": {
            },
            "shapes": self._shapes,
            "imagePath": imagePath,
            "imageData": None,
            "imageHeight": imageHeight,
            "imageWidth": imageWidth,
            **kwargs
        }






if __name__ == '__main__':
    import time
    from datetime import datetime
    print(datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H'))