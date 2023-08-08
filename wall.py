import sys
import time
import math

import picamera
import picamera.array
import RPi.GPIO as GPIO

import cv2
import numpy as np
from buildhat import Motor

def map_value(value):
    if value >= 17000:
        return 70
    elif value <= 10000:
        return 30
    else:
        slope = (70 - 30) / (17000 - 10000)
        intercept = 70 - slope * 17000
    return int(slope * value + intercept)

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
    def __init__(self, colorName, lower, upper, lowerOther, upperOther, outlineMethod, divisionDifferenceX = None, windowWidth = None, windowHeight = None):
        self.__colorName = colorName
        self.__lower = np.array(lower)
        self.__upper = np.array(upper)
        if lowerOther is not None and upperOther is not None:
            self.__lowerOther = np.array(lowerOther)
            self.__upperOther = np.array(upperOther)
        self.__outlineMethod = outlineMethod
        self.divisionLeftX = divisionDifferenceX
        if divisionDifferenceX is not None and windowWidth is not None and windowHeight is not None:
            self.divisionRightX = windowWidth - divisionDifferenceX
            self.windowWidth = windowWidth
            self.windowHeight = windowHeight

    def Update(self, camera):
        # Masking
        if self.__colorName == "wall":
            camera.hsv = camera.hsv[80:240, 0:320]
            
        elif self.__colorName == "black":
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
        
        print("GetPositionFromColor retutn None")
        print("divisionLeftX", self.divisionLeftX)
        print("divisionRightX", self.divisionRightX)
        print("windowWidth", self.windowWidth)
        print("originX", self.originX)

    def CanSeeColor(self):
        if self.area is not None and 500 <= self.area:
            return True

    def GetSlope(self):
        cv2.drawContours(self.res, self.maxContour, -1, (255, 0, 0), 2)

        lx, ly = (float("inf"), float("inf"))
        rx, ry = (float("-inf"), float("-inf"))
        
        if self.maxContour is not None:
            for contour in self.maxContour:
                for point in contour:
                    x = point.item(0)
                    y = point.item(1)

                    if x < lx or (x == lx and y > ly):
                        lx, ly = (x, y)

                    if x > rx or (x == rx and y > ry):
                        rx, ry = (x, y)

        if lx != float("inf") and ly != float("inf"):
            cv2.circle(self.res, (lx, ly), 5, (0, 0, 255), -1)

        if rx != float("-inf") and ry != float("-inf"):
            cv2.circle(self.res, (rx, ry), 5, (0, 255, 0), -1)

        tanh = abs(ly - ry)
        degree = math.degrees(math.atan2(tanh, 280))
        slope = abs((30 / 11 * degree) - 1)

        return slope

class Steering:
    # Private
    __nowPosition = None
    __turnNum = 0
    __SLOPE_ADMISSIBLE_VALUE = 4
    
    # Public
    steering = None
    startTime = 0
    moveTime = 0
    blueFlag = None
    poleFlag = None
    avoidedColor = None
    isTurnLeft = None

    # Function
    def __init__(self, port):
        self.steering = Motor(port)
        self.__nowPosition = self.steering.get_aposition()

    def ChangePosition(self, goPosition):
        if self.__nowPosition != goPosition:
            self.steering.run_to_position(goPosition)
            self.__nowPosition = goPosition

            # Count of moving time
            if self.__nowPosition != POS_MIDDLE:
                self.startTime = time.perf_counter()
            else:
                endTime = time.perf_counter()
                self.moveTime = endTime - self.startTime

    def MoveFromWallSlope(self, motor, wallSlope):
        if self.__SLOPE_ADMISSIBLE_VALUE <= wallSlope:
            self.ChangePosition(40)
            motor.start(20)
        elif wallSlope <= 0:
            self.ChangePosition(-40)
            motor.start(20)
        elif 0 < wallSlope < self.__SLOPE_ADMISSIBLE_VALUE:
            self.ChangePosition(POS_MIDDLE)
            motor.stop()

            goPosition = POS_MIDDLE
            if self.isTurnLeft == None:
                distanceSide = distanceSensorSide.GetDistance()
                # Back turn left
                if distanceSide >= 100:
                    goPosition = POS_LEFT
                    self.isTurnLeft = True
                # Back turn right
                else:
                    goPosition = POS_RIGHT
                    self.isTurnLeft = False
            else:
                goPosition = POS_LEFT if self.isTurnLeft else POS_RIGHT

            motor.run_for_seconds(1.3, 70)
            time.sleep(0.1)
            motor.run_for_seconds(0.5, -70)
            self.ChangePosition(goPosition)
            motor.run_for_seconds(2.2, -70)
            self.ChangePosition(POS_MIDDLE)
            motor.run_for_seconds(1.2, -100)
            time.sleep(0.1)
            self.poleFlag = False
            self.blueFlag = False
            self.__turnNum += 1
            self.ChangePosition(POS_MIDDLE)
            self.moveTime = 0

    def MoveFromDistance(self, motor, wallSlope):
        distanceFront = distanceSensorFront.GetDistance()
        if black.area == None:
            black.area = 0
                
        # First only
        print("pole", self.poleFlag, "blue", self.blueFlag)
        if self.__turnNum == 0:
            if distanceFront < 40 and black.area > 5000:
                motor.stop()
                self.MoveFromWallSlope(motor, wallSlope)

            else:
                motor.start(30)
                
        elif distanceFront < 10:
            self.MoveFromWallSlope(motor, 1)

        elif self.poleFlag:
            if distanceFront < 40 and black.area > 5000:
                motor.stop()
                self.MoveFromWallSlope(motor, wallSlope)

            else:
                motor.start(30)
                            
        else:
            motor.start(30)

    def Avoid(self):
        if steering.poleFlag and steering.blueFlag:
            return

        # Has green
        if green.area is not None:
            # Has green and has red
            if red.area is not None:
                # Green priority
                if red.area < green.area and 1200 < green.area < 9000:
                    goPosition = green.GetPositionFromColor(POS_LEFT, POS_LEFT, POS_MIDDLE)
                    steering.ChangePosition(goPosition)
                    self.avoidedColor = "green"

                # Avoid red
                elif green.area < red.area and 1200 < red.area < 9000:
                    goPosition = red.GetPositionFromColor(POS_MIDDLE, POS_RIGHT, POS_RIGHT)
                    steering.ChangePosition(goPosition) 
                    self.avoidedColor = "red"
            # Avoid green
            elif 1200 < green.area < 9000:
                goPosition = green.GetPositionFromColor(POS_LEFT, POS_LEFT, POS_MIDDLE)
                steering.ChangePosition(goPosition) 
                self.avoidedColor = "green"

        # Avoid red
        elif red.area is not None:
            if 1200 < red.area < 9000:
                goPosition = red.GetPositionFromColor(POS_MIDDLE, POS_RIGHT, POS_RIGHT)
                steering.ChangePosition(goPosition)
                self.avoidedColor = "red"

    def Back(self, goPosition):
        self.ChangePosition(POS_MIDDLE)
        time.sleep(2)
        self.ChangePosition(goPosition)
        time.sleep(self.moveTime * 0.5)
        self.ChangePosition(POS_MIDDLE)
        time.sleep(1.8)
        self.poleFlag = True
        self.moveTime = 0
        self.avoidedColor = None

MODE_DEBUG = True

# Camera
camera = Camera("PiCamera", 320, 240, 10)

# Color
wall = Color("wall", [0, 20, 0], [90, 255, 85], None, None, cv2.CHAIN_APPROX_SIMPLE, 160, camera.width, camera.height)

# Motor
motor = Motor('A')
steering = Steering('B')
POS_LEFT = -70
POS_MIDDLE = 0
POS_RIGHT = 70

def Initialize():
    motor.start(30)
    steering.ChangePosition(POS_MIDDLE):
    print("Initialize")

def Main():
    camera.Update()
    wall.Update()

    if MODE_DEBUG:
        camera.Render()
        wall.Render()
        print("Main")

def Finalize():
    print("Finalize")
    motor.stop()
    steering.ChangePosition(POS_MIDDLE):
    GPIO.cleanup()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    Initialize()
    try:
        Main()
    finally:
        Finalize()