from dataclasses import dataclass
import math
import random
from abc import ABC, abstractmethod
from typing import Iterator, List, Tuple

CameraPose = Tuple[float, float, float]  # (polar, azimuth, distance)

@dataclass(frozen=True)
class SpherePatch:


    polar_range: Tuple[float, float]  # in degrees
    azimuth_range: Tuple[float, float] # in degrees
    distance_range: Tuple[float, float] = (1.5, 1.5)


    def azimuth_span_deg(self) -> float:
        a, b = self.azimuth_range
        span = (b - a) % 360.0
        raw = abs(b - a)
        if raw >= 360.0 - 1e-9 or (raw > 1e-9 and abs(raw % 360.0) < 1e-9):
            return 360.0
        return span

    def area_weight(self) -> float:
        p0, p1 = self.polar_range
        p0, p1 = sorted((max(0.0, p0), min(180.0, p1)))
        dphi = math.radians(self.azimuth_span_deg())
        if dphi <= 0:
            return 0.0
        return dphi * (math.cos(math.radians(p0)) - math.cos(math.radians(p1)))


    def sample_uniform(self) -> CameraPose:
        # polar (cos-uniform)
        p0, p1 = self.polar_range
        cmax = math.cos(math.radians(min(p0, p1)))
        cmin = math.cos(math.radians(max(p0, p1)))
        cos_p = cmin + (cmax - cmin) * random.random()
        polar = math.degrees(math.acos(max(-1, min(1, cos_p))))                                    

        # azimuth
        a = self.azimuth_range[0]
        span = self.azimuth_span_deg()
        azimuth = a if span == 0 else (a + span * random.random()) % 360.0

        # distance
        d0, d1 = self.distance_range
        distance = random.uniform(d0, d1)

        return polar, azimuth, distance

    # def deg_to_arc(angle_deg):
    #     return math.radians(angle_deg)


class PatchSampler(ABC):
    '''
    采样数据，在各个sampler体现。
    '''

    @abstractmethod
    def __iter__(self) -> Iterator[CameraPose]:
        ...

class IterPatchSampler(PatchSampler):
    """
    在 SpherePatch 上做确定性遍历：
    - polar 按固定步进
    - azimuth 步长可随 polar 调整（模拟等弧长）
    """

    def __init__(
        self,
        patches: list[SpherePatch],
        polar_step_deg: float = 1.0,
        azimuth_step_min: float = 1.0,
        azimuth_step_max: float = 20.0,
        epochs: int = 1,
    ):
        self.patches = patches
        self.polar_step = polar_step_deg
        self.step_min = azimuth_step_min
        self.step_max = azimuth_step_max
        self.epochs = epochs

    def _azimuth_step(self, polar_deg: float) -> float:

        return self.step_max - (self.step_max - self.step_min) * math.sin(
            math.radians(polar_deg)
        )

    def __iter__(self) -> Iterator[CameraPose]:
        for _ in range(self.epochs):
            for patch in self.patches:
                p0, p1 = patch.polar_range
                p = p0
                while p <= p1:
                    step = self._azimuth_step(p)
                    a0 = patch.azimuth_range[0]
                    span = patch.azimuth_span_deg()
                    a = a0
                    traveled = 0.0

                    while traveled <= span:
                        # distance：iter 模式仍然允许随机
                        d0, d1 = patch.distance_range
                        distance = random.uniform(d0, d1)

                        yield round(p, 2), round(a % 360.0, 2), round(distance, 2)

                        a += step
                        traveled += step

                    p += self.polar_step

class RandomUniformSphereCoord(PatchSampler):
    """
    面积均匀随机采样：
    - 区域之间：按球面面积权重
    - 区域之内：严格等面积
    """

    def __init__(self, patches: list[SpherePatch], total_samples: int):
        self.patches = patches
        self.total_samples = total_samples

        weights = [p.area_weight() for p in patches]
        total = sum(weights)
        if total <= 0:
            raise ValueError("All SpherePatch have zero area.")

        self._weights = [w / total for w in weights]

    def __iter__(self):
        for _ in range(self.total_samples):
            patch = random.choices(self.patches, weights=self._weights, k=1)[0]
            yield patch.sample_uniform()




class RandomQuotaSphereCoord(PatchSampler):
    """
    配额随机采样（全局随机交错）：
    - 每个 patch 产出 exactly quota
    - 输出顺序不是分块，而是全局随机混洗（流式）
    - patch 内仍然使用等面积采样
    """

    def __init__(self, patch_quota: List[Tuple["SpherePatch", int]]):
        if not patch_quota:
            raise ValueError("patch_quota is empty")

        self._patches = []
        self._remaining = []
        for p, q in patch_quota:
            q = int(q)
            if q < 0:
                raise ValueError("quota must be >= 0")
            if q == 0:
                continue
            self._patches.append(p)
            self._remaining.append(q)

        if not self._patches:
            raise ValueError("all quotas are zero")

    def __iter__(self) -> Iterator[tuple[float, float, float]]:
        # 流式：每次从剩余 quota > 0 的 patch 中按 remaining 加权抽一个
        remaining = self._remaining[:]  # 拷贝，避免迭代中污染对象
        patches = self._patches

        total_left = sum(remaining)
        while total_left > 0:
            idx = random.choices(range(len(patches)), weights=remaining, k=1)[0]

            yield patches[idx].sample_uniform()

            remaining[idx] -= 1
            total_left -= 1



if __name__ == "__main__":
    # Example usage
    # patches = [
    #     (SpherePatch((10, 15), (0, 90)), 30),
    #     (SpherePatch((80, 90), (90, 180)), 10),
    # ]

    patches = [
    SpherePatch((10, 15), (0, 90)),
    SpherePatch((80, 90), (90, 180)),
    ]
    sampler = IterPatchSampler(patches)
    sampler = iter(sampler)
    while True:
        try:
            print(next(sampler))

        except StopIteration:
            break
        