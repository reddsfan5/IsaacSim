import time
from abc import ABC, abstractmethod
from collections.abc import Container
from math import sqrt
from typing import List, Union, Tuple

import cv2
import numpy as np
from shapely import Polygon

if __name__ == '__main__':
    __package__ = 'src.lv_tools.cores'
from .typing_custom import Points, FlattenedPoints, Coordinate

'''
多边形相关的操作，标准化相关操作。
多边形的各种表示方式：
* points
* rect
* rectangle
* topleft_wh

'''


def convert2list(arr: Union[np.ndarray, List], dtype=np.int32) -> List:
    if isinstance(arr, np.ndarray):
        return arr.astype(dtype).tolist()
    elif isinstance(arr, list):
        return arr
    else:
        raise TypeError("The input must be a list or a NumPy ndarray")


def rectangle2points(rec: List[List[float]]) -> Points:
    # labelme 的两点式标注转polygon标注
    (x0, y0), (x1, y1) = rec
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]

def rect2points(rect: FlattenedPoints) -> Points:
    '''
    alva 的扁平化表示转Points
    '''
    # print(len(rect))
    points = [rect[i:i + 2] for i in range(0, len(rect), 2)]
    return points

def topleft_wh2points(corner_wh: Tuple) -> Points:
    x0, y0, w, h = corner_wh
    x1, y1 = x0 + w, y0 + h
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]

def points2rect(points: Union['Polygon4',Points]) -> FlattenedPoints:
    return [cor for point in points for cor in point]


def points2corner_wh(points: Points) -> Tuple:
    return cv2.boundingRect(np.array(points, dtype=np.int32))


def order_rectify_ref_ori_points(ori_points: List[List], rotate_points: List[List]):
    '''
    旋转框的四个点 与 原透视畸变图的 四个点的顺序，依据距离关系进行对应。
    points1:原透视畸变图的0，1，2，3点。
    '''
    distance = []
    for i2 in range(len(rotate_points)):
        dis = point_distance(ori_points[0], rotate_points[i2])
        distance.append(dis)

    p0_index = np.argmin(distance)
    points2_ext = rotate_points.tolist() * 2
    # print('最近点索引:',p0_index)
    return np.array(points2_ext[p0_index:p0_index + 4])


def order_rectify(bbox: Points,y_first=True) -> Points:
    '''
    只能处理顺时针方向的4点polygon顺序矫正
    '''
    if isinstance(bbox, np.ndarray):
        bbox = bbox.astype(np.int32).tolist()
    if y_first:
        y_order = sorted(bbox, key=lambda p: p[1])
        x_order = sorted(y_order[:2], key=lambda p: p[0])
        index = bbox.index(x_order[0])
    else:
        x_order = sorted(bbox, key=lambda p: p[0])
        y_order = sorted(x_order[:2], key=lambda p: p[1])
        index = bbox.index(y_order[0])
    return [bbox[i % 4] for i in range(index, index + 4)]



def convert2rotate_bbox(polygon: Points) -> Points:
    box = cv2.minAreaRect(np.array(polygon, dtype=np.float32))
    # 统一为四点box
    points = cv2.boxPoints(box)

    points = convert2list(points)

    return points


def sort_points_clockwise(points):
    """对任意凸四边形的四点按顺时针排序
 1.计算中心点
    计算四点坐标的平均值作为中心点，消除方向影响：
 2.按相对中心点的角度排序
    将每个点视为从中心点出发的向量，计算向量与正X轴的夹角，按角度从小到大排序（逆时针），再反转顺序即得顺时针：


    """
    points = np.array(points)
    center = np.mean(points, axis=0)
    angles = np.arctan2(points[:,1] - center[1], points[:,0] - center[0])
    sorted_idx = np.argsort(angles)
    return points[sorted_idx]


def polygon_normalization(points: Points) -> Points:
    '''
    确保任意polygon都统一为四点表示的polygon，以确保四点映射到一个矩形平面不出现异常变形。
    1.四点判断，存在非四点的，使用旋转矩形统一到四点。
    2.点的顺序归一化，左上角点开始，顺时针旋转。

    关于四点的标准化
    :return: 归一化后的polygon
    '''
    # 有出界风险
    if len(points) > 4:
        points = convert2rotate_bbox(points)
    elif len(points) == 4:
        points = sort_points_clockwise(points)
    else:
        raise ValueError('not illegal polygon')


    # 凸包无法确保输出是几个点。所以，会导致各种点数存在。
    # if is_clockwise(points) == 0:
    #     return points
        # raise ValueError(f'角点异常，疑似三点共线')
        # points = convert_2_rotate_bbox(points)
    if is_clockwise(points) == -1:
        points = points[::-1]

    points = order_rectify(points)

    return points


def poly_area(points: Points) -> float:
    polygon = Polygon(points)
    return polygon.area


def point_distance(p1: Coordinate, p2: Coordinate) -> float:
    return sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def poly_distance(poly1, poly2):
    '''
    求两个poly之间的距离
    '''
    polygon1 = Polygon(poly1)
    polygon2 = Polygon(poly2)

    # 计算两个多边形之间的最短距离
    distance = polygon1.distance(polygon2)

    return distance


def calculate_intersection_area(points1: Union[Points, Polygon], points2: Union[Points, Polygon]) -> float:
    """Calculate the area of intersection between two polygons."""
    polygon1 = Polygon(points1)
    polygon2 = Polygon(points2)
    try:
        if polygon1.intersects(polygon2):
            return polygon1.intersection(polygon2).area
        else:
            return 0
    except:
        return 0


def intersection_percentage_wrt_smaller_one(points1: Points, points2: Points) -> float:
    polygon1 = Polygon(points1)
    polygon2 = Polygon(points2)
    inter_area = calculate_intersection_area(polygon1, polygon2)

    return inter_area / min(polygon1.area, polygon2.area)


def calculate_bounding_box_size(bounding_box: Points) -> Tuple[int, int]:
    p0, p1, p2, _ = bounding_box
    piece_w, piece_h = int(point_distance(p0, p1)), int(
        point_distance(p1, p2))
    return piece_w, piece_h


# 新版本rect 转换为老版本 rect的代码，实测可用
def minAreaRect_to_OldVersion(points):
    # opencv的cv2.minAreaRect函数输出角度问题:https://blog.csdn.net/weixin_34910922/article/details/120239687
    '''恢复老版本的rect格式'''
    rect = cv2.minAreaRect(points)  # 这条语句，新旧版本的返回格式不太一样
    # 手工恢复老版本的数据格式
    if np.abs(rect[2]) == 0:
        rect_old_v = rect
    else:
        rect_old_v = ((rect[0][0], rect[0][1]), (rect[1][1], rect[1][0]), rect[2] - 90.)

    return rect_old_v


def is_clockwise(polygons):
    '''
    用于左上角为（0，0）点的像素坐标系
    https://www.cnblogs.com/Roni-i/p/9058424.html
    由于像素坐标与常规直角坐标系的y轴方向不一致，所以结果刚好相反。
    '''
    p0, p1, p2 = polygons[:3]
    cross_product = (p1[0] - p0[0]) * (p2[1] - p1[1]) - (p1[1] - p0[1]) * (p2[0] - p1[0])
    if cross_product < 0:
        return -1
    elif cross_product > 0:
        return 1
    else:
        return 0
        # raise ValueError(f'多点处于一条直线上了吧：{polygons}')


def box_center(points: Points) -> Tuple[float]:
    center, _, _ = cv2.minAreaRect(np.array(points, np.int32))
    return center


def is_intersection(polygon1: Polygon, polygon2: Polygon):
    return polygon1.intersects(polygon2)



def is_point_outside_img(point: Coordinate, img_hw: Union[list, tuple]) -> bool:
    x, y = point
    return not (0 <= x <= img_hw[1] and 0 <= y <= img_hw[0])


def is_polygon_with_outside_point(polygons: list, img_hw: Union[list, tuple]) -> bool:
    return any(is_point_outside_img(point, img_hw) for point in polygons)


class PolygonNormal:
    def __init__(self, polygon: Points):
        self.polygon = self.polygon_normalization(polygon)

    def __getitem__(self, index: int) -> Coordinate:
        return self.polygon[index]

    def __iter__(self):
        return iter(self.polygon)

    def __repr__(self):
        return repr(self.polygon)

    def __array__(self, dtype=np.int32):
        """
        通过定义类的 __array__ 方法来实现自定义的 NumPy 转换行为。
        __array__ ，用来告诉 NumPy 如何将自定义对象转换为 NumPy 数组
        """
        return np.array(self.polygon, dtype=dtype)

    def centroid(self):
        p = Polygon(self.polygon)
        return p.centroid.x, p.centroid.y

    @staticmethod
    def _guarantee_legal_poly(points: Points) -> Points:
        rectangle_points_num = 2
        if len(points) == rectangle_points_num:
            points = rectangle2points(points)
            return points
        elif len(points) > rectangle_points_num:
            return points
        else:
            raise ValueError('not illegal polygon')

    @staticmethod
    def _is_clockwise(points: Points):
        '''
        用于左上角为（0，0）点的像素坐标系
        https://www.cnblogs.com/Roni-i/p/9058424.html
        由于像素坐标与常规直角坐标系的y轴方向不一致，所以结果与博主教程刚好相反。
        '''
        p0, p1, p2 = points[:3]
        cross_product = (p1[0] - p0[0]) * (p2[1] - p1[1]) - (p1[1] - p0[1]) * (p2[0] - p1[0])
        if cross_product < 0:
            return -1
        elif cross_product > 0:
            return 1
        else:
            return 0

    def polygon_normalization(self, points: Points) -> Points:

        points = self._guarantee_legal_poly(points)
        if self._is_clockwise(points) == 0:

            # 常规多边形通常没有顺逆时针的需求。

            print((f'角点异常，疑似三点共线{points}'))

            return points


        elif self._is_clockwise(points) == -1:
            points = points[::-1]

        return points

    @staticmethod
    def _residual_value(point_cord: float, center_cord: float, scale_factor: float) -> float:

        return (point_cord - center_cord) * (scale_factor - 1)

    @staticmethod
    def _restrict_residual_value(res_value: float, max_abs_value: float) -> float:

        sig_value = 1 if res_value >= 0 else -1

        return sig_value * (min(abs(res_value), abs(max_abs_value)))

    def shrink_polygon(self, scale_factors: Union[float, tuple[float]], max_values: Union[float, tuple[float]]):

        """缩放多边形顶点
        scale_factor:正数，为1时，不缩放。
        如果，缩放参数在方法中进行传递，其使用上会依赖


        """
        if not isinstance(scale_factors, Container):
            scale_factors = (scale_factors, scale_factors)
        if not isinstance(max_values, Container):
            max_values = (max_values, max_values)
        scaled_pts = []
        # center = self.box_center()
        center = self.centroid()
        # print(center)
        for point in self.polygon:
            dst_point = []
            for i in range(2):
                res = self._residual_value(point[i], center[i], scale_factors[i])
                res = self._restrict_residual_value(res, max_values[i])
                dst_point.append(point[i] + res)
            scaled_pts.append(dst_point)
        self.polygon = scaled_pts
        return self

    def box_center(self) -> tuple[float]:
        center = np.mean(self.polygon, axis=0)
        return center.tolist()

    def convert_2_rotate_bbox(self, polygon: Points) -> Points:
        box = cv2.minAreaRect(np.array(polygon, dtype=np.float32))
        # 统一为四点box
        points = cv2.boxPoints(box)

        points = convert2list(points)

        return points


class Polygon4(PolygonNormal):

    def polygon_normalization(self, points: Points) -> Points:
        '''
        确保任意polygon都统一为四点表示的polygon，以确保四点映射到一个矩形平面不出现异常变形。
        1.四点判断，存在非四点的，使用旋转矩形统一到四点。
        2.点的顺序归一化，左上角点开始，顺时针旋转。
        :return: 归一化后的polygon
        '''
        if len(points) > 4:
            points = self.convert_2_rotate_bbox(points)
        # 凸包无法确保输出是几个点。所以，会导致各种点数存在。
        elif self._is_clockwise(points) == 0:
            raise ValueError(f'角点异常，疑似三点共线')
        elif self._is_clockwise(points) == -1:
            points = points[::-1]

        points = self.order_rectify(points)

        return points

    def order_rectify(self, bbox: Points) -> Points:
        '''
        只能处理顺时针方向的4点polygon顺序矫正
        '''
        if isinstance(bbox, np.ndarray):
            bbox = bbox.astype(np.int32).tolist()
        y_order = sorted(bbox, key=lambda y: y[1])
        x_order = sorted(y_order[:2], key=lambda x: x[0])
        index = bbox.index(x_order[0])

        return [bbox[i % 4] for i in range(index, index + 4)]


class PolygonMasker(ABC):
    '''
    如果传进来的不是四点多边形呢？在哪个环节进行转换
    本着自己对自己负责的原则，多边形转换逻辑应该由本类负责


    '''

    def __init__(self, polygons: Polygon4, img_hw: Union[tuple, list]):
        '''
        如果传参列表形式的多边形。为了确保四点多边形，需要加入校验和转换逻辑。
        如果该验证逻辑依赖于客户端，则本类在职责上，就不是自己对自己负责。
        如果把校验转换逻辑加入到本类中，其它需要四点验证逻辑的对象，就需要实例化本类。违背了单一职责原则。
        所以使用类与类之间的组成关系，使用方式是依赖注入。
        '''

        self.polygons = polygons
        self.img_h, self.img_w = img_hw

    @abstractmethod
    def get_mask_polygon(self):
        pass

    @abstractmethod
    def shrink_mask_polygon(self):
        pass


class PolygonMaskerLeft(PolygonMasker):
    def get_mask_polygon(self):
        '''
        依赖于四点多边形的相关方法。（需要封装这两个类）
        # 顺时针，四点
        '''
        return [[0, 0], self.polygons[0], self.polygons[-1], [0, self.img_h]]

    def shrink_mask_polygon(self):
        pass


class PolygonMaskerRight(PolygonMasker):
    def get_mask_polygon(self):
        '''
        依赖于四点多边形的相关方法。（需要封装这两个类）
        # 顺时针，四点
        '''
        return [self.polygons[1], [self.img_w, 0], [self.img_w, self.img_h], self.polygons[2]]

    def shrink_mask_polygon(self):
        pass


def points_resize(points: Points, wh_ratio: tuple) -> Points:
    return [[int(point[0] * wh_ratio[0]), int(point[1] * wh_ratio[1])] for point in points]


def cut_rect(rect: FlattenedPoints, topleft: Coordinate):
    x0, y0 = topleft
    new_rect = []
    for index, value in enumerate(rect):
        if index % 2 == 0:
            new_rect.append(value - x0)
        else:
            new_rect.append(value - y0)

    return new_rect


if __name__ == '__main__':
    point = [250, 50]
    points = [[0, 0], [100, 12], [100, 222], [5, 226]]

    s = time.time()
    for i in range(100000):
        c = box_center(points)
    print(time.time()-s)

    # poly4.shrink_polygon(.6, max_values=5)
    # arr = np.array(poly4)
    s= time.time()
    p = Polygon(points)
    for i in range(100000):

        c= p.centroid
    # print(p.centroid)
    print(time.time()-s)



