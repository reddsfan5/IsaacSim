'''
support multi material category

'''
from enum import StrEnum
import os
from typing import List
from pathlib import Path
MATERIAL_BASE_PATH = Path('/data2/isaacsim/materials/material_aggregation_usd')
class MaterialEnum(StrEnum):

    _base_path ='/data2/isaacsim/materials/material_aggregation_usd'
    # 金属
    metal = 'moto_poliigon_metal_v9'
    # 锈迹金属
    rust = 'poliigon_rust' 

    # 木材
    wood = 'poliigon_wood'
    # 塑料
    plastics = 'poliigon_plastics'

    # 石头
    stone = 'poliigon_stone'
    # 砖块
    brick = 'poliigon_brick'
    # 瓷砖
    tile = 'poliigon_tiles'
    # 大理石
    marble = 'poliigon_marble'    
    # 混凝土
    concrete = 'poliigon_concrete'
    # 石膏
    plaster= 'poliigon_plaster'

    # 城市道路，井盖
    city = 'poliigon_city'

    # 平面设计
    design = 'poliigon_design'

    # 布料
    fabric = 'poliigon_fabric'

    # 大地材料
    ground = 'poliigon_ground' 

    # 斑驳材质
    grunge = 'poliigon_grunge'

    # 冰块材质
    ice = 'poliigon_ice'

    # 人造材料
    manmade = 'poliigon_manmade'

    # 素背景
    pure = 'poliigon_pure_bg'

    # 壁纸贴图

    color_bg = 'poliigon_color_bg'

    

    @property
    def file_path(self) -> str:
        return str(MATERIAL_BASE_PATH / f'{self.value}.usd')




if __name__ == '__main__':
    print(MaterialEnum[MaterialEnum.metal.name].value)





