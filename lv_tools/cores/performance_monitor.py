import functools
import tracemalloc
from typing import Callable


def memmory_monitor(func:Callable):
    @functools.wraps(func)
    def wrapper(*args,**kwargs):
        tracemalloc.start()

        ret = func(*args,**kwargs)

        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics("lineno")  # 按代码行统计内存占用

        print("[Top 5 内存占用]")
        for i,stat in enumerate(top_stats[:5]):
            print(f"{'-'*50}【top{i+1:02}】{'-'*50}")
            print(f"文件: {stat.traceback[0].filename}")
            print(f"行号: {stat.traceback[0].lineno}, 总内存: {stat.size / 1024:.2f} KiB")
            print(f"分配次数: {stat.count}, 平均每次: {stat.size / stat.count} B\n")
        return ret
    return wrapper
