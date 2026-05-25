import os
import pickle
import shutil
from pathlib import Path

import cv2
import numpy as np
from skimage.feature import local_binary_pattern
from PIL import Image
from torchvision import transforms
import torch.nn.functional as F


import torch
import timm
from safetensors.torch import load_file

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}



device = 'cuda' if torch.cuda.is_available() else 'cpu'


# device = 'cpu'

# 创建模型结构
model = timm.create_model(
    'vit_base_patch14_dinov2',
    pretrained=False,
    num_classes=0,
)

# 加载本地权重
state_dict = load_file(
    '/data2/hf_cache/model.safetensors'
)

model.load_state_dict(state_dict, strict=True)

model.eval().to(device)


transform = transforms.Compose([
    transforms.Resize((518, 518)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=(0.485, 0.456, 0.406),
        std=(0.229, 0.224, 0.225),
    )
])



def center_crop(img, crop_ratio=0.2):
    h, w = img.shape[:2]
    cw = int(w * crop_ratio)
    ch = int(h * crop_ratio)
    left = (w - cw) // 2
    top = (h - ch) // 2
    return img[top:top + ch, left:left + cw]


def l2_normalize(vec):
    return vec / (np.linalg.norm(vec) + 1e-8)


def extract_hsv_hist(img, h_bins=32, s_bins=32, v_bins=16):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    hist = cv2.calcHist(
        [hsv],
        [0, 1, 2],
        None,
        [h_bins, s_bins, v_bins],
        [0, 180, 0, 256, 0, 256],
    ).flatten().astype("float32")

    hist /= hist.sum() + 1e-8
    return hist


def extract_lbp_hist(img, points=24, radius=3):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    lbp = local_binary_pattern(
        gray,
        P=points,
        R=radius,
        method="uniform"
    )

    n_bins = points + 2
    hist, _ = np.histogram(
        lbp.ravel(),
        bins=n_bins,
        range=(0, n_bins)
    )

    hist = hist.astype("float32")
    hist /= hist.sum() + 1e-8
    return hist


def extract_edge_hist(img, bins=32):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = np.sqrt(gx * gx + gy * gy)

    hist, _ = np.histogram(
        mag.ravel(),
        bins=bins,
        range=(0, 255)
    )

    hist = hist.astype("float32")
    hist /= hist.sum() + 1e-8
    return hist


def extract_image_feature(
    image_path,
    image_size=256,
    crop_ratio=0.2,
):
    img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError(f"无法读取图像: {image_path}")

    img = center_crop(img, crop_ratio=crop_ratio)
    img = cv2.resize(img, (image_size, image_size), interpolation=cv2.INTER_AREA)

    hsv_feat = extract_hsv_hist(img)
    lbp_feat = extract_lbp_hist(img)
    edge_feat = extract_edge_hist(img)

    feature = np.concatenate([
        hsv_feat * 0.85,
        lbp_feat * 0.05,
        edge_feat * 0.1,
    ]).astype("float32")


    return l2_normalize(feature)





# @torch.no_grad()
# def extract_image_feature(image_path,image_size=256,crop_ratio=0.75,):
#     img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)

#     if img is None:
#         raise ValueError(f"无法读取图像: {image_path}")

#     img = center_crop(img, crop_ratio=crop_ratio)
#     img = cv2.resize(img, (image_size, image_size), interpolation=cv2.INTER_AREA)

#     # img = Image.open(image_path).convert("RGB")
#     img = Image.fromarray(img)

#     x = transform(img).unsqueeze(0).to(device)

#     feat = model(x)

#     feat = F.normalize(feat, dim=-1)

#     return feat.squeeze().cpu().numpy()




def collect_images(folder):
    folder = Path(folder)
    return sorted([
        p for p in folder.rglob("*")
        if p.suffix.lower() in IMAGE_EXTS
    ])


def build_feature_library(
    image_folder,
    save_path="material_features.pkl",
    crop_ratio=0.75,
):
    image_paths = collect_images(image_folder)

    if not image_paths:
        raise RuntimeError(f"没有找到图像文件: {image_folder}")

    items = []

    for path in image_paths:
        try:
            feature = extract_image_feature(path, crop_ratio=crop_ratio)
            items.append({
                "path": str(path),
                "name": path.name,
                "feature": feature,
            })
            print(f"[OK] {path.name}")
        except Exception as e:
            print(f"[SKIP] {path}: {e}")

    with open(save_path, "wb") as f:
        pickle.dump(items, f)

    print(f"\n特征库构建完成: {save_path}")
    print(f"有效图片数量: {len(items)}")

    return items


def cosine_similarity(a, b):
    """
    因为特征已经 L2 normalize，
    所以 dot product 就是 cosine similarity。
    """
    return float(np.dot(a, b))


def search_topk(
    query_image_path,
    feature_library_path="material_features.pkl",
    topk=10,
    crop_ratio=0.75,
):
    with open(feature_library_path, "rb") as f:
        items = pickle.load(f)

    query_feature = extract_image_feature(
        query_image_path,
        crop_ratio=crop_ratio
    )

    results = []

    for item in items:
        score = cosine_similarity(query_feature, item["feature"])
        results.append({
            "score": score,
            "name": item["name"],
            "path": item["path"],
        })

    results.sort(key=lambda x: x["score"], reverse=True)

    return results[:topk]


if __name__ == "__main__":
    print(os.getcwd())
    sub_dir = 'test10'
    # # 第一次运行：构建材质特征库
    build_feature_library(
        image_folder=r"/data2/isaacsim/materials/material_sphere",
        save_path="material_features.pkl",
        crop_ratio=0.2,
    )


    # 查询：给定目标图，找最像的10张材质图
    results = search_topk(
        query_image_path=fr"/data2/target_photo/{sub_dir}/img.jpg",
        feature_library_path="material_features.pkl",
        topk=20,
        crop_ratio=0.2,
    )

    print("\nTop 10 相似材质：")
    for i, r in enumerate(results, 1):
        print(f"{i:02d}. score={r['score']:.4f} | {r['name']}")
        shutil.copy(os.path.join(r'/data2/isaacsim/materials/material_sphere',r['name']),os.path.join(rf'/data2/target_photo/{sub_dir}',r['name']))



    # count = 0
    # with open(r'F:\dataset\Omniverse\materials\mat.txt',mode='r') as f:
    #     file_stems = [line.strip() for line in f.readlines()]
    
    # mat_set = set(file_stems)
    
    
    # mat_paths= Path(r'F:\dataset\Omniverse\materials\material_sphere').glob('*.jpg')
    # # file_stem_set = {mat_path.stem for mat_path in mat_paths}
    # for mat_path in mat_paths:
    #     if mat_path.stem not in mat_set:
    #         shutil.move(mat_path,os.path.join(r'F:\dataset\Omniverse\materials\delete',mat_path.name))
    #         print(mat_path.stem)







    # @torch.no_grad()
    # def extract_feature(image_path):

    #     img = Image.open(image_path).convert("RGB")

    #     x = transform(img).unsqueeze(0).to(device)

    #     feat = model(x)

    #     feat = F.normalize(feat, dim=-1)

    #     return feat.squeeze().cpu().numpy()


    # print(extract_image_feature(r'/data2/target_photo/test1.jpg'))