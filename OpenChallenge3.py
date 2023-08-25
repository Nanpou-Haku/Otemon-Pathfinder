import sys
import time
import math
import threading
import queue

import picamera
import picamera.array
import RPi.GPIO as GPIO

import cv2
import numpy as np
import multiprocessing as mp
from buildhat import Motor

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
        

    def Update(self, camera):
        # Masking
        if self.__colorName == "black":
            height = (camera.height, camera.height, camera.height)
            cv2.rectangle(camera.hsv, (0, 0),   (camera.width, 100),           height, -1)
            cv2.rectangle(camera.hsv, (0, 0),   (20, camera.height),           height, -1)
            cv2.rectangle(camera.hsv, (300, 0), (camera.width, camera.height), height, -1)

        self.mask = cv2.inRange(camera.hsv, self.__lower, self.__upper)
        
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

    def Render(self):# Render
        if self.res is not None:
            cv2.imshow(self.__colorName, self.res)

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
        slope = (30/11 * degree) - 1
        
        if ry <= ly:
            slope = -1 * slope

        return slope

class DistanceSensor:
    # Private
    __SPEED_OF_SOUND = 33145
    __trig = None
    __echo = None
    __wait = None
    __signalOff = None
    __signalOn = None

    # Function
    def __init__(self, trig, echo, wait = 0.00001):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(trig, GPIO.OUT)
        GPIO.setup(echo, GPIO.IN)
        self.__trig = trig
        self.__echo = echo
        self.__wait = wait

    def GetDistance(self):
        GPIO.output(self.__trig, GPIO.LOW)
        time.sleep(self.__wait)
        GPIO.output(self.__trig, True)
        time.sleep(self.__wait)
        GPIO.output(self.__trig, False)

        while GPIO.input(self.__echo) == 0:
            self.__signalOff = time.time()
        while GPIO.input(self.__echo) == 1:
            self.__signalOn = time.time()

        timePassed = self.__signalOn - self.__signalOff
        distance = self.__SPEED_OF_SOUND * timePassed / 2
        return distance
    
class steering:
    # Private
    __nowPosition = None
    __turnNum = 0
    __SLOPE_ADMISSIBLE_VALUE = 4
    
    # Public
    steering = None
    startTime = 0
    moveTime = 0
    LINEstart = 0
    LINEtime = 0
    blueFlag = False
    poleFlag = None
    avoidedColor = None
    isTurnLeft = None
    count = 0

    # Function
    def __init__(self, port):
        self.steering = Motor(port)
        self.__nowPosition = self.steering.get_aposition()
    
    def MoveFromWallSlope(self, motor, wallSlope):
        if self.__SLOPE_ADMISSIBLE_VALUE <= wallSlope:
            self.steering.run_to_position(45)
            motor.start(20)
            
        elif wallSlope <= 0:
            self.steering.run_to_position(-45)
            motor.start(20)
            
        elif 0 < wallSlope < self.__SLOPE_ADMISSIBLE_VALUE:
            self.steering.run_to_position(POS_MIDDLE)
            motor.stop()

            goPosition = POS_MIDDLE
            if self.isTurnLeft == None:
                distanceSide = distanceSensorRight.GetDistance()
                # Back turn left
                if distanceSide >= 100:
                    goPosition = POS_RIGHT
                    self.isTurnLeft = True
                # Back turn right
                else:
                    goPosition = POS_LEFT
                    self.isTurnLeft = False
            else:
                goPosition = POS_RIGHT if self.isTurnLeft else POS_LEFT
            
            motor.run_for_seconds(3, -70)
            self.DistanceChangePosition(goPosition)
            
            motor.run_for_seconds(2.8, 70)
            #motor.run_for_rotations(10, 70)
            
            self.DistanceChangePosition(POS_MIDDLE)
            self.count = self.count + 1
            self.LINEstart = time.perf_counter()
            
    def MoveFromDistance(self, motor, wallSlope):   
        distanceFront = distanceSensorFront.GetDistance()
        if black.area == None:
            black.area = 0
        
        if distanceFront < 10:
            self.MoveFromWallSlope(motor, 1)
            
        if distanceFront < 40:
            black.Update(camera)
            if black.area > 4500:
                motor.stop()
                self.MoveFromWallSlope(motor, wallSlope)
                
            else:
                steering.DistanceTrace()
            
        elif distanceFront < 40:
            LINEend = time.perf_counter()
            self.LINEtime = LINEend - self.LINEstart
            print("line time =", self.LINEtime)
            
            if self.LINEtime > 20:
                motor.stop()
                self.MoveFromWallSlope(motor, wallSlope)
            
            else:
                steering.DistanceTrace()
                
        else:
            steering.DistanceTrace()
    
    def DistanceChangePosition(self, goPosition):
        if self.__nowPosition != goPosition:
            self.steering.run_to_position(goPosition)
            self.__nowPosition = goPosition
    
    def DistanceTrace(self):
        motor.start(80)
        distanceSide = distanceSensorRight.GetDistance()
            
        if self.count == 0:
            distanceLeft = distanceSensorLeft.GetDistance()
            distanceRight = distanceSensorRight.GetDistance()
        
            if distanceLeft > 100:
            
                if distanceRight < 29:
                    self.DistanceChangePosition(-20)
        
                elif 29 <= distanceRight <= 44:
                    self.DistanceChangePosition(POS_MIDDLE)
            
                elif 44 < distanceRight <= 70:
                    self.DistanceChangePosition(20)
            
                elif 70 < distanceRight:
                    self.DistanceChangePosition(POS_MIDDLE)
                    
            elif distanceRight > 100:
            
                if distanceLeft < 29:
                    self.DistanceChangePosition(20)
        
                elif 29 <= distanceLeft <= 44:
                    self.DistanceChangePosition(POS_MIDDLE)
            
                elif 44 < distanceSide <= 70:
                    self.DistanceChangePosition(-20)
            
                elif 70 < distanceLeft:
                    self.DistanceChangePosition(POS_MIDDLE)
            
            else:
                if distanceRight < 29:
                    self.DistanceChangePosition(-20)
        
                elif 29 <= distanceRight <= 44:
                    self.DistanceChangePosition(POS_MIDDLE)
            
                elif 44 < distanceRight <= 70:
                    self.DistanceChangePosition(20)
            
                elif 70 < distanceRight:
                    self.DistanceChangePosition(POS_MIDDLE)
        
        elif self.isTurnLeft == True:
            distanceSide = distanceSensorLeft.GetDistance()
            
            if distanceSide < 29:
                self.DistanceChangePosition(20)
        
            elif 29 <= distanceSide <= 44:
                self.DistanceChangePosition(POS_MIDDLE)
            
            elif 44 < distanceSide <= 70:
                self.DistanceChangePosition(-20)
            
            elif 70 < distanceSide:
                self.DistanceChangePosition(POS_MIDDLE)
                
        elif self.isTurnLeft == False:
            distanceSide = distanceSensorRight.GetDistance()
            
            if distanceSide < 29:
                self.DistanceChangePosition(-20)
        
            elif 29 <= distanceSide <= 44:
                self.DistanceChangePosition(POS_MIDDLE)
            
            elif 44 < distanceSide <= 70:
                self.DistanceChangePosition(20)
            
            elif 70 < distanceSide:
                self.DistanceChangePosition(POS_MIDDLE)
                    
        time.sleep(0.2)
            
# Parameter
MODE_DEBUG = True

# Thread pool
camera_queue = queue.Queue()

# Camera
camera = Camera("PiCamera", 320, 240, 10)

# Color
divisionDifferenceX = 40
red   = Color("red",   [ 160, 60, 50 ], [ 179, 255, 255 ], [ 0, 255, 50 ], [ 30, 255, 255 ], cv2.CHAIN_APPROX_SIMPLE, divisionDifferenceX, camera.width, camera.height)
green = Color("green", [ 40, 60, 40 ],  [ 80, 255, 255 ],  None,           None,             cv2.CHAIN_APPROX_SIMPLE, divisionDifferenceX, camera.width, camera.height)
blue  = Color("blue",  [ 104, 85, 0 ],  [ 170, 255, 163 ], None,           None,             cv2.CHAIN_APPROX_SIMPLE, divisionDifferenceX, camera.width, camera.height)
black = Color("black", [ 0, 0, 0 ],     [ 50, 255, 110 ],  None,           None,             cv2.CHAIN_APPROX_NONE)

# Sensor
distanceSensorFront = DistanceSensor(27, 18)
distanceSensorRight  = DistanceSensor(23, 24)
distanceSensorLeft = DistanceSensor(5, 6)

# motor
motor = Motor('C')
steering = steering('D')
POS_LEFT = -80
POS_MIDDLE = 0
POS_RIGHT = 80

def Initialize():
    print("Initialize")
    steering.steering.run_to_position(0)
    motor.start(80)

def Finalize():
     print("Finalize")
     motor.stop()
     GPIO.cleanup()
     cv2.destroyAllWindows()
     
def Main():
    while True:
        # Update
        if steering.count < 12:
            camera.Update()
            wallSlope = black.GetSlope()
            steering.MoveFromDistance(motor, wallSlope)
            
        else:
            print("end")
            break
        
        if MODE_DEBUG:
            camera.Render()
            black.Render()

if __name__ == '__main__':
    Initialize()
    try:
        Main()
    finally:
        Finalize()
