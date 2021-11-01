
import os
import sys
import time
import argparse

import numpy as np
import cv2

from PySide6 import QtGui


class YoloImageRecognition:

    def __init__(self, image, painter, args):
        '''
        image: an image from cv2.imread(image_name)
        args:
        '''
        self.image = image
        self.painter = painter

        self.args = args
            
        # derive the paths to the YOLO weights and model configuration
        weightsFile = "yolo/yolov4-cards-%02d_%03dx%03d.weights" % (int(args["nb_classes"]), int(args["yolotrainingsize"]), int(args["yolotrainingsize"]))
        configFile = "yolo/yolov4-cards-%02d_%03dx%03d.cfg" % (int(args["nb_classes"]), int(args["yolotrainingsize"]), int(args["yolotrainingsize"]))
        
        labelsFile = "yolo/cards-%02d.names" % int(self.args["nb_classes"])
        self.LABELS = open(labelsFile).read().strip().split("\n")

        np.random.seed(42)
        self.COLORS = np.random.randint(0, 255, size=(len(self.LABELS), 3), dtype="uint8")
        
        self.img_training_size = int(args["yolotrainingsize"])
        if self.img_training_size == 0:
            print("set training size for images - mandatory - with which size did you made the training?")
            sys.exit(1)

        print("LABELS", self.LABELS)
        
        # check
        if not os.path.exists(weightsFile):
            print("%s not found in current directory - exit", weightsFile)
            sys.exit(1)
        if not os.path.exists(configFile):
            print("%s not found in current directory - exit", configFile)
            sys.exit(1)
        if not os.path.exists(labelsFile):
            print("%s not found in current directory - exit", labelsFile)
            sys.exit(1)

        # load our YOLO object detector trained on *** dataset (<nb_classes> classes)
        self.net = cv2.dnn.readNetFromDarknet(configFile, weightsFile)

    def process(self):
        print("[INFO] loading YOLO from disk...")
    
        # determine only the *output* layer names that we need from YOLO
        ln = self.net.getLayerNames()
        #ln = [ln[i[0] - 1] for i in self.net.getUnconnectedOutLayers()]
        ln = [ln[i - 1] for i in self.net.getUnconnectedOutLayers()]
        
        start = time.time()
        
        # construct a blob from the input image and then perform a forward
        # pass of the YOLO object detector, giving us our bounding boxes and
        # associated probabilities
        blob = cv2.dnn.blobFromImage(self.image, 1 / 255.0, (self.img_training_size, self.img_training_size), swapRB=True, crop=False)
        self.net.setInput(blob)
        layerOutputs = self.net.forward(ln)    
        self.process_image("video_frame", self.image, layerOutputs)

        end = time.time()
        
        # show timing information on YOLO
        print("[INFO] YOLO took: %.6f seconds  -- %s" % ((end - start), "video_frame") )
       
    def getProcessingData(self, image, layerOutputs):
        
        # load our input image and grab its spatial dimensions
        (H, W) = image.shape[:2]
        
        # initialize our lists of detected bounding boxes, confidences, and
        # class IDs, respectively
        boxes = []
        confidences = []
        classIDs = []
        
        # loop over each of the layer outputs
        for output in layerOutputs:
            # loop over each of the detections
            for detection in output:
                # extract the class ID and confidence (i.e., probability) of
                # the current object detection
                scores = detection[5:]
                classID = np.argmax(scores)
                confidence = scores[classID]
        
                # filter out weak predictions by ensuring the detected
                # probability is greater than the minimum probability
                if confidence:
                    # scale the bounding box coordinates back relative to the
                    # size of the image, keeping in mind that YOLO actually
                    # returns the center (x, y)-coordinates of the bounding
                    # box followed by the boxes' width and height
                    box = detection[0:4] * np.array([W, H, W, H])
                    (centerX, centerY, width, height) = box.astype("int")
        
                    # use the center (x, y)-coordinates to derive the top and
                    # and left corner of the bounding box
                    x = int(centerX - (width / 2))
                    y = int(centerY - (height / 2))
        
                    # update our list of bself.imageounding box coordinates, confidences,
                    # and class IDs
                    boxes.append([x, y, int(width), int(height)])
                    confidences.append(float(confidence))
                    classIDs.append(classID)  
                    
        return (boxes, confidences, classIDs)
        
    def process_image(self, image_name, image, layerOutputs):
        ''' '''
        boxes, confidences, classIDs = self.getProcessingData(image, layerOutputs)
        
        # apply non-maxima suppression to suppress weak, overlapping bounding boxes
        idxs = cv2.dnn.NMSBoxes(boxes, confidences, self.args["confidence"], self.args["threshold"])

        # ensure at least one detection exists
        if len(idxs) > 0:
            # loop over the indexes we are keeping
            for i in idxs.flatten():
                # extract the bounding box coordinates
                (x, y) = (boxes[i][0], boxes[i][1])
                (w, h) = (boxes[i][2], boxes[i][3])
        
                # draw a bounding box rectangle and label on the image
                color = [int(c) for c in self.COLORS[classIDs[i]]]
                pen = QtGui.QPen()
                pen.setColor(QtGui.QColor(*color))
                pen.setWidth(5)
                self.painter.setPen(pen)
                self.painter.setFont(QtGui.QFont("Arial", 15))
                self.painter.drawRect(x, y, w, h)
                text = "{}: {:.3f}".format(self.LABELS[classIDs[i]], confidences[i])
                self.painter.drawText(x, y-5, text)
    

#[INFO] loading YOLO from disk...
#[INFO] YOLO took 0.347815 seconds

if __name__ == '__main__':
    
    ap = argparse.ArgumentParser()
    ap.add_argument("-x", "--nb_classes", required=True, help="nb classes (cards ids) config")
    ap.add_argument("-c", "--confidence", type=float, default=0.5, help="minimum probability to filter weak detections")
    ap.add_argument("-t", "--threshold", type=float, default=0.5, help="threshold when applying non-maxima suppression")
    ap.add_argument("-z", "--yolotrainingsize", type=int, default=0, help="size when trained (cfg file)")
    args = vars(ap.parse_args())
    
    im = YoloImageRecognition(args)
    im.process()
