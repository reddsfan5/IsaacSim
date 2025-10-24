from typing import List,Union,Tuple
Coordinate = List[Union[int, float]]  # 二元列表

BoundingBox = List[Coordinate]  # 2点标注，左上角，右下角。
Points = List[Coordinate]  # 多点表示,包括四点标注
FlattenedPoints = List[Union[int, float]]  # 八元列表
Index = int
Size = Tuple[Union[int, float], Union[int, float]]
GLYF_ID = str