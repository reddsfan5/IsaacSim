import omni.usd
from pxr import UsdGeom,Usd
import random
# too big:[GD960_JJ_50HP,]
# too small: crane # 侧翻(模型转化，up axis怎么设置)


def random_visibility(parent="/Distractors"):
    stage = omni.usd.get_context().get_stage()
    root = stage.GetPrimAtPath(parent)
    children = root.GetChildren()
    
    
    # Step 1: 全部显示
    for p in children:
        UsdGeom.Imageable(p).MakeVisible()

    # Step 2: 随机隐藏
    hide_count = random.randint(0,len(children))
    print(hide_count)
    to_hide = random.sample(children, hide_count)
    for p in to_hide:
        UsdGeom.Imageable(p).MakeInvisible()

    print(f"保持 {len(children)-hide_count} 个，隐藏 {hide_count} 个")

prim_path = '/Distractors'

random_visibility(prim_path)