import os
import numpy as np
import json
from itertools import groupby
from prettytable import PrettyTable
from trajectory.eval_assn import EvalAssn
from mAP.eval_map import EvalmAP
import math
import copy

thr = np.arange(0, 1.0 + 0.05, 0.05)
thr[0] += 1e-3
#thr = [0.5]

def process_ap(x, y):
    y = np.concatenate(([0.],y, [0.]))
    x = np.concatenate(([0.], x, [1.]))
    for i in range(y.size - 1, 0, -1):
        y[i - 1] = np.maximum(y[i - 1], y[i]) 
    rec = []
    prec = []
    for i in range(len(x)):
        rec.append(str(x[i]))
    for i in range(len(y)):
        prec.append(str(y[i]))
    return rec, prec


def get_im_name(im_name):
    return str(int(im_name))

def conv_bbox(bbox):    
    b = [float(x) for x in bbox]
    sub = []
    x1 = b[0] - 1.
    y1 = b[1] - 1.
    x2 = x1 + b[2]
    y2 = y1 + b[3]
    return [x1, y1, x2, y2]


if __name__ == '__main__':
    vid_path = '/data01/kalviny/dataset/kitti/gt/'

    #method = 'kitti_nms_0.5'
    #method = 'kitti_nms_0.5_mf'
    #method = 'kitti_nms_0.5_pf'
    #method = 'kitti_nms_0.5_mf_pf'
    #method = 'kitti_weighted_nms'
    #method = 'kitti_weighted_nms_mf'
    #method = 'kitti_weighted_nms_pf'
    method = 'kitti_weighted_nms_mf_pf'



    ped_list = ['0011', '0012', '0013', '0014', '0015', '0017', '0016', '0009']


    det_path = '/home/kalviny/workspace/experiment/mx-faster-rcnn-kitti/result/kitti_proposal_300/' + method
    #det_path = '/home/kalviny/workspace/video_detection/tmp/video-detection/metric/method/proposal-flow/script/result/'

    tab = PrettyTable(['video', 'ap@0.5', 'Fragment', 'Center Error', 'Ratio Error'])
    tab.align['video']
    tab.padding_width = 1

    cls = ['Pedestrian']
    vid_list = ped_list

    ap = np.zeros((len(thr), 1))
    st = np.zeros((len(thr), 1))

    for c in cls:
        seq_res = []
        for i in range(len(vid_list)):
            vid_name = vid_list[i]
            print 'processing {}'.format(vid_name)
            seq_gt = np.loadtxt(os.path.join(vid_path, vid_name, '{}.txt'.format(c)), delimiter=' ')
            print len(seq_gt)
            anno = {}
            filter_seq = []
            for x in seq_gt:

                filter_seq.append(x)

            seq_gt = np.array(filter_seq)
            key = []
            val = []
            for k, v in groupby(seq_gt, key = lambda x: x[0]):
                key.append(k)
                val.append(np.array(list(v)))
            for k in range(len(key)):
                im_name = get_im_name(key[k])
                _bbox = val[k][:, 2:]
                traj_id = val[k][:, 1]
                anno[im_name] = {'bbox': np.array(_bbox, dtype=np.float32), 'det': [False] * len(traj_id), 'traj_id': traj_id}

            det_map = []
            det_traj = {}
            seq_det = np.loadtxt(os.path.join(det_path, vid_name, '{}.txt'.format(c)), delimiter=' ')
            seq_det = np.array(sorted(seq_det, key = lambda x: x[0]))

            for x in seq_det:
                im_name = get_im_name(x[0])
                _sub = []
                _sub.append(im_name)
                _sub.append(x[1])
                _sub.extend(x[2:])
                det_map.append(_sub)
                #det_map.append([im_name, x[6], x[2:6]])
            key = []
            val = []
            for k, v in groupby(seq_det, key = lambda x: x[0]):
                key.append(k)
                val.append(np.array(list(v)))
            for x in range(len(key)):
                im_name = get_im_name(key[x])
                _bbox = val[x][:, 2:]
                det_traj[im_name] = {'bbox': np.array(_bbox)}


            out_dir = 'result/kitti/stability/' + method
            if not os.path.exists(out_dir): os.mkdir(out_dir)

            with open(os.path.join(out_dir, '{}_{}.txt'.format(vid_name, c)), 'w') as f:
                for th in thr:
                    _err, _c, _r = EvalAssn(anno, det_traj, th)

                    if math.isnan(_err): _err = 0
                    if math.isnan(_c): _c = 0
                    if math.isnan(_r): _r = 0
                    if th == 0.5:
                        F_err = _err
                        var_c = _c
                        var_r = _r
                    print th, _err, _c, _r
                    f.write('%.2f, %.4f, %.4f, %.4f\n' % (th, _err, _c, _r))

            out_dir = 'result/kitti/accuracy/' + method
            if not os.path.exists(out_dir): os.mkdir(out_dir)

            #_rec, _prec, _ap = EvalmAP(anno, np.copy(np.array(det_map)), 1e-3)
            #print _ap

            with open(os.path.join(out_dir, '{}_{}.txt'.format(vid_name, c)), 'w') as f:
                for th in thr:
                    _det_map = copy.deepcopy(det_map)
                    _anno = copy.deepcopy(anno)
                    _rec, _prec, _ap = EvalmAP(_anno, np.array(_det_map), th)
                    print th, _ap
                    if th == 0.5:
                        ap = _ap
                    if math.isnan(_ap): _ap = 0
                    f.write('%.2f, %.2f\n' % (th, _ap))

            seq_res.append(np.array([ap, F_err, var_c, var_r]))
            tab.add_row([vid_name, ap, F_err, var_c, var_r])
            
        seq_res = np.array(seq_res)
        tab.add_row(['----------', '-----------', '----------', '-----------', '----------'])
        tab.add_row(['Mean', np.mean(seq_res[:, 0]), np.mean(seq_res[:, 1]), np.mean(seq_res[:, 2]), np.mean(seq_res[:, 3])])
    print tab

