import math
import os
import shutil
import traceback
from functools import partial
from pathlib import Path
from typing import Union

import PIL
import cv2
import numpy as np
from PIL import ImageDraw
from tqdm import tqdm
import sys

sys.path.append('/home/ubuntu/lxd/lxd_code/isaacsim')
from lv_tools.cores.img_io import cv2imwrite,cv2imread
from lv_tools.cores.json_io import load_json_to_dict, save_json

RGB_ANNOT_NAME = "rgb"
BB3D_ANNOT_NAME = "bounding_box_3d_fast"
CAM_PARAMS_ANNOT_NAME = "camera_params"
SUPPORTED_FORMATS = set(["dope", "centerpose"])
CUBOID_KEYPOINTS_ORDER_DEFAULT = ["Center", "LDB", "LDF", "LUB", "LUF", "RDB", "RDF", "RUB", "RUF"]
CUBOID_KEYPOINT_ORDER_DOPE = ["LUF", "RUF", "RDF", "LDF", "LUB", "RUB", "RDB", "LDB", "Center"]
CUBOID_KEYPOINT_COLORS = ["white", "red", "green", "blue", "yellow", "cyan", "magenta", "orange", "purple"]
CUBOID_EDGE_COLORS = {"front": "red", "back": "blue", "connecting": "green"}


# Transform a 3D point from world coordinates to camera coordinates
def world_point_to_camera_point(world_point: Union[list[float], np.ndarray], view_matrix: np.ndarray) -> np.ndarray:
    # Convert the 3D point to homogeneous coordinates (if not already in that form)
    point_homogeneous = np.array(world_point) if len(world_point) == 4 else np.array([*world_point, 1.0])

    # Transform to camera frame (row-major representation where the translation vector is on the left side of the multiplication)
    point_camera = point_homogeneous @ view_matrix

    return point_camera


# Project a 3D point from camera coordinates to 2D screen coordinates
def project_camera_point_to_screen(camera_point: np.ndarray, projection_matrix: np.ndarray,
                                   screen_size: Union[tuple, list]) -> list:
    # Apply the projection matrix to project to screen coordinates
    point_screen = camera_point @ projection_matrix

    # Normalize to NDC (Normalized Device Coordinates) by dividing x, y, z, by w: (x, y, z, w) -> (x/w, y/w, z/w, 1)
    point_screen_normalized = point_screen / point_screen[3]

    # Map NDC to screen coordinates. Adjust x and y for screen dimensions, flipping y to match screen's coordinate system.
    x = (point_screen_normalized[0] + 1) * screen_size[0] / 2
    y = (1 - point_screen_normalized[1]) * screen_size[1] / 2

    return [round(x), round(y)]


# Project a 3D point from world coordinates to 2D screen coordinates
def project_world_point_to_screen(world_point: Union[list[float], np.ndarray], view_matrix: np.ndarray,
                                  projection_matrix: np.ndarray, screen_size: Union[tuple, list]) -> list:
    point_camera = world_point_to_camera_point(world_point, view_matrix)
    return project_camera_point_to_screen(point_camera, projection_matrix, screen_size)


# Projects the local frame axes of the object to the screen
def draw_local_frame_axes(

        draw,
        local_to_world_transform,
        camera_view_matrix,
        camera_projection_matrix,
        screen_size,
        size_local=[1, 1, 1],
        origin_local=[0, 0, 0],
        axes_length_perc=0.25,
):
    # The length of the local axes is a percentage of the mean size of the object in local frame (before any scaling)
    local_axes_length = np.mean(size_local) * axes_length_perc

    # Define the end points of the local coordinate system axes include the local center of the object bounds
    origin_local = np.array([origin_local[0], origin_local[1], origin_local[2], 1])
    x_axis_end_point_local = np.array([local_axes_length + origin_local[0], origin_local[1], origin_local[2], 1])
    y_axis_end_point_local = np.array([origin_local[0], local_axes_length + origin_local[1], origin_local[2], 1])
    z_axis_end_point_local = np.array([origin_local[0], origin_local[1], local_axes_length + origin_local[2], 1])

    # Transform local end points to world frame using row-major matrix multiplication (translation on the left side)
    origin_world = origin_local @ local_to_world_transform
    x_axis_end_point_world = x_axis_end_point_local @ local_to_world_transform
    y_axis_end_point_world = y_axis_end_point_local @ local_to_world_transform
    z_axis_end_point_world = z_axis_end_point_local @ local_to_world_transform

    # Define a partial helper function to project 3D world points to 2D screen points
    project_to_screen = partial(
        project_world_point_to_screen,
        view_matrix=camera_view_matrix,
        projection_matrix=camera_projection_matrix,
        screen_size=screen_size,
    )

    # Project the origin and axes end points from 3D world coordinates to 2D screen coordinates
    origin_2d = project_to_screen(origin_world)
    x_axis_end_2d = project_to_screen(x_axis_end_point_world)
    y_axis_end_2d = project_to_screen(y_axis_end_point_world)
    z_axis_end_2d = project_to_screen(z_axis_end_point_world)

    # Draw the 3D axes on the 2D screen using lines with appropriate colors for each axis
    draw.line([origin_2d, x_axis_end_2d], fill="red", width=2)  # X-axis in red
    draw.line([origin_2d, y_axis_end_2d], fill="green", width=2)  # Y-axis in green
    draw.line([origin_2d, z_axis_end_2d], fill="blue", width=2)  # Z-axis in blue


# Draws the world frame axes at the bottom left corner of the image.
def draw_world_frame_axes_bottom_left(
        draw, camera_view_matrix, camera_projection_matrix, screen_size, axes_scale=0.03, margin_percentage=0.03
):
    # Set a world location for the axes origin (1 unit in front of the camera) where -Z is the camera's forward direction
    camera_to_world_matrix = np.linalg.inv(camera_view_matrix)
    point_in_camera_space = np.array([0, 0, -1, 1])

    # Create the axes in world (1 unit in front of the camera) with the given axes size
    origin_world = point_in_camera_space @ camera_to_world_matrix
    x_axis_end_point_world = np.array([axes_scale + origin_world[0], origin_world[1], origin_world[2], 1])
    y_axis_end_point_world = np.array([origin_world[0], axes_scale + origin_world[1], origin_world[2], 1])
    z_axis_end_point_world = np.array([origin_world[0], origin_world[1], axes_scale + origin_world[2], 1])

    # Create a partial function with fixed camera parameters
    project_to_screen = partial(
        project_world_point_to_screen,
        view_matrix=camera_view_matrix,
        projection_matrix=camera_projection_matrix,
        screen_size=screen_size,
    )

    # Project the origin and axes end points into 2D screen coordinates
    origin_2d = project_to_screen(origin_world)
    x_axis_end_2d = project_to_screen(x_axis_end_point_world)
    y_axis_end_2d = project_to_screen(y_axis_end_point_world)
    z_axis_end_2d = project_to_screen(z_axis_end_point_world)

    # Calculate offset margin (a percentage of the screen size) to ensure axes are not on the edge of the screen
    margin = int(margin_percentage * min(screen_size))
    offset_x = margin - min(origin_2d[0], x_axis_end_2d[0], y_axis_end_2d[0], z_axis_end_2d[0])
    offset_y = screen_size[1] - margin - max(origin_2d[1], x_axis_end_2d[1], y_axis_end_2d[1], z_axis_end_2d[1])

    # Apply the offset to the projected points
    origin_2d = (origin_2d[0] + offset_x, origin_2d[1] + offset_y)
    x_axis_end_2d = (x_axis_end_2d[0] + offset_x, x_axis_end_2d[1] + offset_y)
    y_axis_end_2d = (y_axis_end_2d[0] + offset_x, y_axis_end_2d[1] + offset_y)
    z_axis_end_2d = (z_axis_end_2d[0] + offset_x, z_axis_end_2d[1] + offset_y)

    # Draw the axes with the specified colors
    draw.line([origin_2d, x_axis_end_2d], fill="red", width=2)  # X-axis in red
    draw.line([origin_2d, y_axis_end_2d], fill="green", width=2)  # Y-axis in green
    draw.line([origin_2d, z_axis_end_2d], fill="blue", width=2)  # Z-axis in blue


# Draw the projected cuboid and its edges
def draw_projected_keypoints(draw, keypoints, point_size=4, edge_size=2):
    # Draw the projected cuboid keypoint vertices in the specified colors
    for i, point in enumerate(keypoints):
        draw.ellipse(
            (point[0] - point_size, point[1] - point_size, point[0] + point_size, point[1] + point_size),
            fill=CUBOID_KEYPOINT_COLORS[i],
        )

    # Draw the edges of the projected cuboid with specified colors for each set
    edges = {
        "front": [(1, 2), (2, 4), (4, 3), (3, 1)],  # Front face
        "back": [(5, 6), (6, 8), (8, 7), (7, 5)],  # Back face
        "connecting": [(1, 5), (2, 6), (3, 7), (4, 8)],  # Connecting edges
    }
    for edge_type, edge_list in edges.items():
        for start, end in edge_list:
            draw.line(keypoints[start] + keypoints[end], fill=CUBOID_EDGE_COLORS[edge_type], width=edge_size)


def mid_point(p1: Union[np.ndarray, list], p2: Union[np.ndarray, list]) -> np.ndarray:
    p1 = np.array(p1) if isinstance(p1, list) else p1
    p2 = np.array(p2) if isinstance(p2, list) else p2
    return (p1 + p2) / 2


def point4_to_point9(points: list) -> list:
    '''
    points: dl,dr,ul,ur

    '''
    dl, dr, ul, ur = points

    um = mid_point(ul, ur)
    dm = mid_point(dl, dr)
    ml = mid_point(ul, dl)
    mm = mid_point(um, dm)
    mr = mid_point(dr, ur)
    return [p.tolist() if isinstance(p, np.ndarray) else p for p in [dl, dm, dr, ml, mm, mr, ul, um, ur]]






def cuboid9_to_cuboid27(world_points: list) -> list:
    '''
    outer loop: left -> right
    middle loop: down -> up
    inner loop: back -> front

    :param points: 9 center style points
    :return:
    '''
    wc, wldb, wldf, wlub, wluf, wrdb, wrdf, wrub, wruf = world_points
    wmdb = mid_point(wldb, wrdb)
    wmdf = mid_point(wldf, wrdf)
    wmub = mid_point(wlub, wrub)
    wmuf = mid_point(wluf, wruf)
    cuboid_27 = []
    # 左，中，右平面
    for plain4 in [[wldb, wldf, wlub, wluf], [wmdb, wmdf, wmub, wmuf], [wrdb, wrdf, wrub, wruf]]:
        plain9 = point4_to_point9(plain4)
        cuboid_27.extend(plain9)

    return cuboid_27


def cuboid27_to_alva27(cuboid_27: list) -> list:
    '''
    outer loop: left -> right
    middle loop: down -> up
    inner loop: back-> front


    to

    outer loop: back -> front
    middle loop: left -> right
    inner loop: down -> up


    :param cuboid_27:
    :return:
    '''


    cuboid_array = np.array(cuboid_27).reshape(3,3,3,-1)
    cuboid_array_ret = cuboid_array.transpose(2,0,1,3).reshape(-1,3)
    return cuboid_array_ret.tolist()



def cuboid_world_to_screen(cuboid: list, view_matrix: np.ndarray, proj_matrix: np.ndarray,
                           screen_size: Union[list, tuple]) -> list:
    cuboid_screen = []
    for p in cuboid:
        cuboid_screen.append(project_world_point_to_screen(p, view_matrix, proj_matrix, screen_size))

    return cuboid_screen


def add_cuboid_27(jd: dict):
    for obj in jd['objects']:

        world_points = obj.get("cuboid_keypoints_world_frame", None)
        if world_points is None:
            continue
        view_matrix = np.array(jd["camera_data"]["camera_view_matrix"], dtype=float)
        proj_matrix = np.array(jd["camera_data"]["camera_projection_matrix"], dtype=float)
        screen_size = jd["camera_data"]["resolution"]

        cuboid_27_world = cuboid9_to_cuboid27(world_points)

        # alva_style
        cuboid_27_world = cuboid27_to_alva27(cuboid_27_world)




        cuboid_27_screen = cuboid_world_to_screen(cuboid_27_world, view_matrix, proj_matrix, screen_size)
        obj["cuboid_27_world"] = cuboid_27_world
        obj["cuboid_27_screen"] = cuboid_27_screen
        # obj["cuboid_27_world_alva"] = cuboid_27_world_alva


def is_ann_valid(jd: dict, truncation_ratio: float = .4, visibility_ratio: float = .75,
                 rotate_threshold: int = 90) -> bool:
    if not jd.get('objects') or any(obj['visibility'] < visibility_ratio or obj[
        'truncation_ratio'] > truncation_ratio or compute_asset_direction(
        np.array(obj['rotation_matrix_world_frame']))[1] > rotate_threshold for obj in jd['objects']):
        return False
    return True


def move_out_invalid_data(json_path: Path, dst_folder: Path):
    if not dst_folder.exists():
        dst_folder.mkdir(exist_ok=True, parents=True)
    shutil.move(str(json_path), str(dst_folder / json_path.name))
    if (img_path := json_path.with_suffix('.png')).exists():
        shutil.move(img_path, str(dst_folder / img_path.name))
    if (img_path_show := img_path.with_stem(img_path.stem + '_overlay')).exists():
        shutil.move(img_path_show, str(dst_folder / img_path_show.name))


def calculate_vfov(sensor_height: float, focal_length: float) -> float:
    """
    计算相机垂直视场角（VFOV）,单位：degrees（角度，非弧度）

    参数:
    - sensor_height: 传感器高度（单位同焦距）
    - focal_length: 镜头焦距（单位同传感器高度）
    返回:
    - VFOV（单位：度）
    """
    vfov_rad = 2 * math.atan(sensor_height / (2 * focal_length))
    return math.degrees(vfov_rad)


def add_vfov(jd: dict):
    sensor_height = jd["camera_data"]["aperture"][1]
    focal_length = jd["camera_data"]["focal_length"]
    vfov = calculate_vfov(sensor_height, focal_length)
    jd['camera_data']['vfov'] = round(vfov, 2)

def move_out_none_interesting_obj(jd:dict,interesting_labels:list=None):
    if not interesting_labels:
        return
    if not jd.get('objects'):
        return
    new_shapes = []
    for shape in jd['objects']:
        if shape['label'] in interesting_labels:
            new_shapes.append(shape)
    jd['objects'] = new_shapes


def data_filter_and_adapt(root: Union[str, Path], dst_folder: Union[Path, str] = None,interesting_labels: list = None):
    root = Path(root)
    dst_folder = Path(dst_folder) if dst_folder else root.with_stem(root.stem + '_invalid')
    json_paths = root.rglob('*.json')

    for json_path in tqdm(json_paths):
        # print(json_path)
        jd = load_json_to_dict(json_path)

        move_out_none_interesting_obj(jd,interesting_labels)


        if not is_ann_valid(jd, truncation_ratio=.5, visibility_ratio=.65,rotate_threshold=360):
            move_out_invalid_data(json_path, dst_folder)
            continue
        add_cuboid_27(jd)
        add_vfov(jd)
        save_json(json_path, jd)






def compute_asset_direction(rot_world: np.ndarray) -> list:
    """
    计算 asset 在世界坐标系下的前向（Z轴）在X、Y、Z轴上的分量和夹角。

    参数：
        rot_world: np.array, shape (3,3)
            asset在世界坐标系下的旋转矩阵

    返回：
        dict 包含每个世界轴的分量和与轴的夹角（度）
    """
    # 假设本地Z轴是前方向
    forward_world = rot_world[:, 1]
    # 单位化
    forward_norm = forward_world / np.linalg.norm(forward_world)

    axes = ['X', 'Y', 'Z']
    angle_degs = []
    for i, axis in enumerate(axes):
        component = forward_norm[i]
        # 与世界轴夹角
        angle_deg = np.degrees(np.arccos(np.clip(component, -1.0, 1.0)))
        angle_degs.append(angle_deg)

    return angle_degs


def bbox_2d_convert(bbox_2d_void:np.void)->list[list[float]]:

    x0,y0,x1,y1 = bbox_2d_void[0][['x_min','y_min','x_max','y_max']]
    return [[x0,y0],[x1,y1]]




if __name__ == '__main__':

    for i in range(1,2):
        root = rf'/data2/data/_out_infinigen_posewriter_lv_1023_junjian_larger_polar'

        data_filter_and_adapt(root,interesting_labels=['airship','jj','disk','tanke','tuopan'])



