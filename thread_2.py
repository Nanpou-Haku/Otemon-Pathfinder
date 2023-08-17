import sys
import time
import math
import concurrent.futures

import picamera
import picamera.array

import cv2
import numpy as np

class Camera:
    # Private
    __COLOR = "bgr"
    __USE_VIDEO_PORT = True
    __name = None
    __camera = None
    __stream = None
    
    # Public
    width = None
    height = None
    streamDatas = None
    kernel = None
    hsv = None

    # Function
    def __init__(self, name, width, height, frame, rotation = 180):
        self.__name = name
        self.width = width
        self.height = height
        self.__camera = picamera.PiCamera()
        self.__camera.resolution = (width, height)
        self.__camera.framerate = frame
        self.__camera.rotation = rotation

    def Update(self):
        self.__stream = picamera.array.PiRGBArray(self.__camera)
        self.kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
        self.__camera.capture(self.__stream, self.__COLOR, self.__USE_VIDEO_PORT)
        self.streamDatas = self.__stream.array
        self.hsv = cv2.cvtColor(self.__stream.array, cv2.COLOR_BGR2HSV)
    
    def Render(self):
        cv2.imshow(self.__name, self.__stream.array)
        cv2.waitKey(1)
        self.__stream.seek(0)
        self.__stream.truncate()

class Color:
    # Private
    __DIVISION_LINE_COLOR = (255, 215, 0)
    __DIVISION_LINE_THICKNESS = 1
    __OPENING_ITERATIONS = 1
    __colorName  = None
    __lower      = None
    __upper      = None
    __lowerOther = None
    __upperOther = None
    __outlineMethod = None

    # Public
    mask       = None
    dst        = None
    dstt       = None
    res        = None
    contour    = None
    hierarchy  = None
    maxContour = None
    area       = None
    moments    = None
    originX = None
    originY = None
    divisionDifferenceX = None
    divisionLeftX       = None
    divisionRightX      = None
    windowWidth  = None
    windowHeight = None

    # Function
    def __init__(self, colorName, lower, upper, lowerOther, upperOther, __outlineMethod, divisionDifferenceX = None, windowWidth = None, windowHeight = None):
        self.__colorName = colorName
        self.__lower = np.array(lower)
        self.__upper = np.array(upper)
        if lowerOther is not None and upperOther is not None:
            self.__lowerOther = np.array(lowerOther)
            self.__upperOther = np.array(upperOther)
        self.__outlineMethod = __outlineMethod
        self.divisionLeftX = divisionDifferenceX
        if divisionDifferenceX is not None and windowWidth is not None and windowHeight is not None:
            self.divisionRightX = windowWidth - divisionDifferenceX
            self.windowWidth = windowWidth
            self.windowHeight = windowHeight

    def Update(self, camera):
        # Masking
        if self.__colorName == "black":
            height = (camera.height, camera.height, camera.height)
            cv2.rectangle(camera.hsv, (0, 0),   (camera.width, 100),           height, -1)
            cv2.rectangle(camera.hsv, (0, 0),   (20, camera.height),           height, -1)
            cv2.rectangle(camera.hsv, (300, 0), (camera.width, camera.height), height, -1)
        elif self.__colorName == "blue":
            cv2.rectangle(camera.hsv, (0, 0), (camera.width, 120), (100, 100, 100), -1)

        self.mask = cv2.inRange(camera.hsv, self.__lower, self.__upper)
        if self.__lowerOther is not None and self.__upperOther is not None:
            maskOther = cv2.inRange(camera.hsv, self.__lowerOther, self.__upperOther)
            self.mask += maskOther
        
        # Opening
        self.dst = cv2.erode(self.mask, camera.kernel, self.__OPENING_ITERATIONS)
        self.dstt = cv2.dilate(self.dst, camera.kernel, self.__OPENING_ITERATIONS)

        # Synthesis
        self.res = cv2.bitwise_and(camera.streamDatas, camera.streamDatas, mask=self.dstt)

        # Outline
        self.contour, self.hierarchy = cv2.findContours(self.mask, cv2.RETR_EXTERNAL, self.__outlineMethod)

        # Moments and area
        if (len(self.contour) != 0):
            self.maxContour = max(self.contour, key = lambda x: cv2.contourArea(x))
            self.area = cv2.contourArea(self.maxContour)
            self.moments = cv2.moments(self.maxContour)
            if self.moments["m00"] != 0 and self.moments["m01"] != 0 and self.moments["m10"] != 0:
                self.originX = int(self.moments["m10"] / self.moments["m00"])
                self.originY = int(self.moments["m01"] / self.moments["m00"])
        else:
            self.area = None
            self.originX = None
            self.originY = None

    def Render(self):
        # DivisionLine
        if self.divisionLeftX is not None or self.divisionRightX is not None:
            windowTop = 0
            cv2.line(self.res, (self.divisionLeftX,  windowTop), (self.divisionLeftX,  self.windowHeight), self.__DIVISION_LINE_COLOR, self.__DIVISION_LINE_THICKNESS)
            cv2.line(self.res, (self.divisionRightX, windowTop), (self.divisionRightX, self.windowHeight), self.__DIVISION_LINE_COLOR, self.__DIVISION_LINE_THICKNESS)

        # Origin
        if self.originX is not None or self.originY is not None:
            cv2.circle(self.dstt, (self.originX,self.originY), 2, 100, 2, 4)
            cv2.circle(self.res, (self.originX, self.originY), 2, 100, 2, 4)
        
        # Render
        if self.res is not None:
            cv2.imshow(self.__colorName, self.res)

    def GetPositionFromColor(self, left, midle, right):
        windowLeft = 0
        # Left
        if windowLeft <= self.originX <= self.divisionLeftX:
            return left
        # Middle
        elif self.divisionLeftX <= self.originX <= self.divisionRightX:
            return midle
        # Right              
        elif self.divisionRightX <= self.originX <= self.windowWidth:
            return right

    def CanSeeColor(self):
        if self.area is not None and 500 <= self.area:
            return True
    
# Parameter
MODE_DEBUG = True

# Camera
camera = Camera("PiCamera", 320, 240, 10)

# Color
divisionDifferenceX = 60
red   = Color("red",   [ 160, 60, 50 ], [ 179, 255, 255 ], [ 0, 255, 50 ], [ 30, 255, 255 ], cv2.CHAIN_APPROX_SIMPLE, divisionDifferenceX, camera.width, camera.height)
green = Color("green", [ 40, 60, 40 ],  [ 80, 255, 255 ],  None,           None,             cv2.CHAIN_APPROX_SIMPLE, divisionDifferenceX, camera.width, camera.height)
blue  = Color("blue",  [ 104, 85, 0 ],  [ 170, 255, 163 ], None,           None,             cv2.CHAIN_APPROX_SIMPLE, divisionDifferenceX, camera.width, camera.height)
black = Color("black", [ 0, 0, 0 ],     [ 50, 255, 110 ],  None,           None,             cv2.CHAIN_APPROX_NONE)

def ThreadUpdateCamera(camera):
    camera.Update()
    
def ThreadUpdateColor(camera, color):
    color.Update(camera)

def Initialize():
    print("Initialize")

def Finalize():
     print("Finalize")
     cv2.destroyAllWindows()

def Main():
    while True:
        # Update
        camera.Update()
        red.Update(camera)
        green.Update(camera)
        blue.Update(camera)
        
        # Render
        if MODE_DEBUG:
            camera.Render()
            red.Render()
            green.Render()
            black.Render()
            blue.Render()

if __name__ == '__main__':
    Initialize()
    try:
        Main()
    finally:
        Finalize()
