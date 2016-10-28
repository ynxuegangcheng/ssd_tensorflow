from pycocotools.coco import COCO
import numpy as np
import os
import skimage.io as io
import matplotlib.pyplot as plt
import cv2
import random
import skimage.transform
import vgg.utils as utils
from constants import image_size, classes

annFile = "/media/sean/HDCL-UT1/mscoco/annotations/instances_train2014.json"
trainDir = "/media/sean/HDCL-UT1/mscoco/train2014"
coco = COCO(annFile)

cats = coco.loadCats(coco.getCatIds())

nms=[cat['name'] for cat in cats]
id2name = dict((cat["id"], cat["name"]) for cat in cats)
id2i = dict((cats[i]['id'], i) for i in range(len(cats)))
i2name = {v: id2name[k] for k, v in id2i.iteritems()}
i2name[classes-1]="void"
print("NUMBER OF CLASSES: %i" % len(id2name))

catIds = coco.getCatIds()
imgIds = coco.getImgIds()
print("%i total training images" % len(imgIds))

def prepare_batch(batch):
    imgs = []
    all_anns = []

    for b in batch:
        anns = []
        img = b[0]
        w = img.shape[1]
        h = img.shape[0]

        option = 0#np.random.randint(2)

        if option == 0:
            sample = img
        elif option == 1:
            ratio = random.uniform(0.5, 2.0) #  0.5=portrait, 2.0=landscape
            scale = random.uniform(0.1, 1.0)
            if w > h:
                p_w = w * scale
                p_h = p_w / ratio

                if p_w > w or p_h > h:
                    p_h = h * scale
                    p_w = p_h * ratio
            else:
                p_h = h * scale
                p_w = p_h * ratio

                if p_w > w or p_h > h:
                    p_w = w * scale
                    p_h = p_w / ratio

            if p_w > w or p_h > h:
                print("patch is too big.")
                exit()

            p_x = random.uniform(0, w - p_w)
            p_y = random.uniform(0, h - p_h)

            sample = img[int(p_y):int(p_y + p_h), int(p_x):int(p_x + p_w)]

            #print("patch: %i to %i, %i to %i" % (int(p_y), int(p_y + p_h), int(p_x), int(p_x + p_w)))

            for box, id in b[1]: # b[0] is image
                box[0] -= p_x
                box[1] -= p_y

        resized_img = skimage.transform.resize(sample, (image_size, image_size))

        for box, id in b[1]:  # b[0] is image
            scaleX = 1.0 / float(sample.shape[1])
            scaleY = 1.0 / float(sample.shape[0])

            box[0] *= scaleX
            box[1] *= scaleY
            box[2] *= scaleX
            box[3] *= scaleY

        for box, id in b[1]: # keep boxes with center in image
            cX = box[0] + box[2] / 2.0
            cY = box[1] + box[3] / 2.0

            if cX >= 0 and cX <= 1 and cY >= 0 and cY <= 1:
                anns.append((box, id))

        if random.uniform(0.0, 1.0) < 2.0:#0.5:
            resized_img = np.fliplr(resized_img)
            for box, id in anns:
                box[0] = 1.0 - box[0] - box[2]

        imgs.append(resized_img)
        all_anns.append(anns)

    return np.asarray(imgs), all_anns

def create_batches(batch_size, shuffle=True):
    # 1 batch = [(image, [([x, y, w, h], id), ([x, y, w, h], id), ...]), ...]
    batches = []

    while True:
        indices = range(len(imgIds))

        if shuffle:
            indices = np.random.permutation(indices)

        for index in indices:
            img = coco.loadImgs(imgIds[2])[0]
            I = io.imread(os.path.join(trainDir, "COCO_train2014_%012d.jpg" % img['id']))

            if len(I.shape) != 3:
                continue

            annIds = coco.getAnnIds(imgIds=img['id'], catIds=catIds, iscrowd=None)
            anns = coco.loadAnns(annIds)
            ann_list = []

            for obj in anns:
                bb = [f for f in obj["bbox"]]
                ann_list.append((bb, id2i[obj["category_id"]]))

            batches.append((I, ann_list))

            if len(batches) >= batch_size:
                yield batches
                batches = []

if __name__ == "__main__":
    batch = create_batches(1, shuffle=False)

    for b in batch:
        # [(image, [([x, y, w, h], id), ([x, y, w, h], id), ...]), ...]

        imgs, anns = prepare_batch(b)

        I = imgs[0] * 255.0

        for bb, id in anns[0]:
            cv2.rectangle(I, (int(bb[0]), int(bb[1])), (int(bb[0] + bb[2]), int(bb[1] + bb[3])), (0, 255, 0), 2)
            cv2.putText(I, id2name[id], (int(bb[0]), int(bb[1] + bb[3])), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0))

        I = cv2.cvtColor(I.astype(np.uint8), cv2.COLOR_RGB2BGR)
        cv2.imshow("image", I)
        cv2.imshow("original image", b[0][0])
        cv2.waitKey(0)


