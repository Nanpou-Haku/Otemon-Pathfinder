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
    blueFlag = None
    poleFlag = None
    avoidedColor = None
    isTurnLeft = None

    # Function
    def __init__(self, port):
        self.steering = Motor(port)
        self.__nowPosition = self.steering.get_aposition()

    def DistanceChangePosition(self, goPosition):
        if self.__nowPosition != goPosition:
            self.steering.run_to_position(goPosition)
            self.__nowPosition = goPosition
            
    def DistanceTrace(self):
        distanceSide = distanceSensorSide.GetDistance()
        
        print("distanceSide =", distanceSide)
        if distanceSide < 29:
            self.DistanceChangePosition(-70)
        
        elif 29 <= distanceSide <= 43:
            self.DistanceChangePosition(0)
            
        elif 43 < distanceSide <= 70:
            self.DistanceChangePosition(70)
            
        elif 70 < distanceSide:
            self.DistanceChangePosition(0)
            
        time.sleep(0.2)

# Sensor
distanceSensorFront = DistanceSensor(27, 18)
distanceSensorSide  = DistanceSensor(23, 24)

# motor
motor = Motor('C')
steering = steering('D')

def Initialize():
    print("Initialize")
    steering.steering.run_to_position(0)
    motor.start(30)
    
def Finalize():
     print("Finalize")
     motor.stop()
     GPIO.cleanup()
     cv2.destroyAllWindows()
     
def Main():
    while True:
        steering.DistanceTrace()

if __name__ == '__main__':
    Initialize()
    try:
        Main()
    finally:
        Finalize()