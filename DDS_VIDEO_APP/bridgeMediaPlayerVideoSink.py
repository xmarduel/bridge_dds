
from PySide6 import QtCore
from PySide6 import QtGui

from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsView
   
from PySide6.QtMultimedia import QVideoFrame, QVideoFrameFormat, QVideoSink
from PySide6.QtMultimediaWidgets import QGraphicsVideoItem

from bridgeYoloImageRecognition import YoloImageRecognition

import numpy as np
import cv2

class BridgeMediaPlayerVideoSink(QVideoSink):
    '''
    '''
    def __init__(self, video_item: QGraphicsVideoItem, graphics_view: QGraphicsView):
        super().__init__()

        self.video_item = video_item
        self.graphics_view = graphics_view

        self.vs = None

        self.pixmap_item = None
        self.rect_item = None

        self.videoFrameChanged.connect(self.grabbedFrame)

    def grabbedFrame(self, video_frame: QVideoFrame):
        print("DDSVideoSink::grabbedFrame", video_frame)

        WITH_SCENE = True
        WITH_SCENE = False

        if WITH_SCENE:
        
            image = video_frame.toImage()

            video_frame_size = video_frame.size()
            w = video_frame_size.width()
            h = video_frame_size.height()
    
            view_w = self.graphics_view.width()
            view_h = self.graphics_view.height()

            factor = max(w/view_w, h/view_h)

            ww = int(w/factor) - 2
            hh = int(h/factor) - 2 

            # write directly to the scene
            if self.pixmap_item == None:
                self.pixmap_item = QGraphicsPixmapItem(QPixmap(image).scaled(ww,hh))
                self.graphics_view.scene().addItem(self.pixmap_item)
            else:
                self.pixmap_item.setPixmap(QPixmap(image).scaled(ww,hh))

            if self.rect_item == None:
                self.rect_item = QGraphicsRectItem(100,100,50,50)
                self.graphics_view.scene().addItem(self.rect_item)

        else:

            ### https://stackoverflow.com/questions/69432427/how-to-use-qvideosink-in-qml-in-qt6
            np_image = self.QImageToCvMat(image = video_frame.toImage())

            if ( (not video_frame.isValid()) or (not video_frame.map(QVideoFrame.WriteOnly))):
                QtCore.qWarning("QVideoFrame is not valid or not writable")
                return
    
            image_format = QVideoFrameFormat.imageFormatFromPixelFormat(video_frame.pixelFormat())
            if (image_format == QtGui.QImage.Format_Invalid) :
                QtCore.qWarning("It is not possible to obtain image format from the pixel format of the videoframe")
                return
    
            plane = 0
            image = QtGui.QImage(video_frame.bits(plane), video_frame.width(),video_frame.height(), image_format)
            painter = QPainter(image)

            # YOLO PROCESSING / augment the image during the processing
            yolo = YoloImageRecognition(np_image, painter, {
                "nb_classes" : 52,
                "confidence" : 0.9,
                "threshold"  : 0.9,
                "yolotrainingsize" : 512
            })
            yolo.process()

            painter.end()
            video_frame.unmap()

            self.video_item.videoSink().setVideoFrame(video_frame)
            

    def QImageToCvMat(self, image):
        '''  Converts a QImage into an opencv MAT format  '''
        # take care the conversion format !
        # Format_RGB888 seems to swap R and B !!!
        image = image.convertToFormat(QtGui.QImage.Format.Format_BGR888)

        width = image.width()
        height = image.height()

        ptr = image.constBits()
        arr = np.array(ptr).reshape(height, width, 3)  #  Copies the data

        return arr