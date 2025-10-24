import pickle
import sys


sys.path.append('/home/ubuntu/lxd/lxd_code/isaacsim')
from lv_tools.cores.img_io import img_byte_to_arr
from lv_tools.dataset_io.data_loader import LmdbLoader


lmdbloader = LmdbLoader('/data2/data/_out_infinigen_posewriter_lv_1024_test/_out_infinigen_posewriter_lv_1024_test_lmdb')
print(len(lmdbloader))

for i in lmdbloader:
    from matplotlib import pyplot as plt
    print(i[0])
    if i[0].decode()=='num-samples':
        print(i[1].decode())
    else:
        s = pickle.loads(i[1])
        
        print(s['label']['objects'][0]['visibility'])

    # img_arr = s['img']
    # plt.imshow(img_arr)
    # plt.show()