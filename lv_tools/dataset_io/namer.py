from typing import Literal, Union
from dataclasses import dataclass

from lv_tools.cores.str_utils import rand_str
from lv_tools.cores.timestemp import get_datetime


@dataclass
class NameIt:
    '''
    专用于给要存储的数据起名字
    '''

    '''
    :param task_name: 体现数据使用场景
    :param data_source: 生成数据 or 标注数据
    :param feature: 突出数据特殊属性
    :param time_stemp: 时间戳
    :param data_num: 
    example:
        code128_rec_syn_startcodeC_single_first_0416-1923-32_200W
    '''
    task_name: str
    data_source: Literal['manu', 'syn']
    feature: str
    data_num: Union[str,int]
    rand_str:str = None
    time_stemp: str = None

    def __str__(self):
        name = '_'.join([self.task_name,self.data_source,self.feature,self.time_stemp,self.rand_str,self._num_str()])

        return name.lower()

    def _num_str(self):
        if isinstance(self.data_num,int) and self.data_num // 10**4>0:
            return str(self.data_num//10**4) + 'w'
        else:
            return str(self.data_num)

    def __post_init__(self):
        self.time_stemp = get_datetime()
        self.rand_str = rand_str(3)

if __name__ == '__main__':
    namer = NameIt('code128_rec','syn','startcodeC',2897890)