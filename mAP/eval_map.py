import os
import cv2
import numpy as np
import bisect

def voc_ap(rec, prec):
    m_rec = np.concatenate(([0.], rec, [1.]))
    m_prec = np.concatenate(([0.], prec, [0.]))

    for i in range(m_prec.size - 1, 0, -1):
        m_prec[i - 1] = np.maximum(m_prec[i - 1], m_prec[i]) 

    i = np.where(m_rec[1:] != m_rec[:-1])[0]

    ap = np.sum((m_rec[i + 1] - m_rec[i]) * m_prec[i + 1])

    return ap

def display(im_name, gt, det):
    im_path = '/data01/kalviny/dataset/MOT/2016/train/MOT16-02/img1/'
    print os.path.join(im_path, '{}.jpg'.format('%06d' % int(im_name)))
    im = cv2.imread(os.path.join(im_path, '{}.jpg'.format('%06d' %  int(im_name))))
    cv2.rectangle(im, (int(gt[0]), int(gt[1])), (int(gt[2]), int(gt[3])), (0, 0, 255), 3)
    #cv2.rectangle(im, (int(det[0]), int(det[1])), (int(det[2]), int(det[3])), (0, 255, 0), 3)
    cv2.imshow('im', im)
    cv2.waitKey(20)

def slice_recall_score(recall, scores, step_size = 0.1):
    res = []
    lrecall = list(recall)
    for x in np.arange(recall[0], recall[len(recall) - 1], step_size):
        idx = bisect.bisect(lrecall, x) - 1
        real_x = recall[idx]
        y = scores[idx]
        res.append((x, y))
        #print 'x,y:', idx, x, real_x, y
    res.append((1.0, recall[len(recall) - 1]))
    return res

"""
    anno: per image gt of "class"
    format: {}
            key: 
                image_id
            val:
                "bbox": x1, y1, x2, y2
                "det": det ([False] * len(bbox))

    det: ndarray, all the detection result of "class"
    format: [[image_id, score, x1, y1, x2, y2]] 

"""
def EvalmAP(anno, det, ov_thr=0.5):

    # Get detection result
    image_ids = det[:, 0]
    confidence = det[:, 1].astype('float')
    bbox = det[:, 2:].astype('float')

    # Sorted the result by confidence score
    sorted_inds = np.argsort(-confidence)
    sorted_scores = confidence[sorted_inds]
    bbox = bbox[sorted_inds, :]
    image_ids = [image_ids[x] for x in sorted_inds]

    # Enumerate all the images and mark TP, FP
    nd = len(image_ids)
    tp = np.zeros(nd)
    fp = np.zeros(nd)

    for d in range(nd):
        im_name = str(image_ids[d])
        if not im_name in anno.keys(): continue
        nw_anno = anno[im_name]
        nw_gt = nw_anno['bbox'].astype(float)
        nw_bbox = bbox[d, :].astype(float)
        ov_max = -np.inf

        if nw_gt.size > 0:
            x_min = np.maximum(nw_gt[:, 0], nw_bbox[0])
            y_min = np.maximum(nw_gt[:, 1], nw_bbox[1])
            x_max = np.minimum(nw_gt[:, 2], nw_bbox[2])
            y_max = np.minimum(nw_gt[:, 3], nw_bbox[3])


            w = np.maximum(0, x_max - x_min + 1.)
            h = np.maximum(0, y_max - y_min + 1.)

            inters = w * h

            uni = ((nw_bbox[2] - nw_bbox[0] + 1.) * (nw_bbox[3] - nw_bbox[1] + 1.) + 
                   (nw_gt[:, 2] - nw_gt[:, 0] + 1.) * (nw_gt[:, 3] - nw_gt[:, 1] + 1.) - inters)

            overlaps = inters / uni

            ov_max = np.max(overlaps)
            cls_max = np.argmax(overlaps)

        if ov_max > ov_thr:
            if not nw_anno['det'][cls_max]:
                #display(im_name, nw_gt[cls_max, :], nw_bbox)
                tp[d] = 1.
                nw_anno['det'][cls_max] = True
            else:
                fp[d] = 1.
        else:
            #if ov_max > -np.inf: display(im_name, nw_gt[cls_max, :], nw_bbox)
            fp[d] = 1.

    # Get the total number of ground truth
    n_pos = 0
    for item in anno:
        n_pos += len(anno[item]['bbox'])

    # Compute precision/recall
    fp = np.cumsum(fp)
    tp = np.cumsum(tp)
    #print fp[-1], tp[-1], fp[-1] + tp[-1], nd
    recall = tp / float(n_pos)
    recall_score_slice = slice_recall_score(recall, sorted_scores, 0.1)

    prec = tp / np.maximum(tp + fp, np.finfo(np.float64).eps)
    ap = voc_ap(recall, prec)

    return recall, prec, ap, recall_score_slice


