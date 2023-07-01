import time
import copy
import atexit
import picamera
import picamera.array
import RPi.GPIO as GPIO
from dataclasses import dataclass
import cv2
import numpy as np
from buildhat import Motor, ForceSensor

@dataclass
class ColorDatas:
    color      : int = 0
    lower      : np.ndarray = None
    upper      : np.ndarray = None
    mask       : np.ndarray = None
    dst        : np.ndarray = None
    dstt       : np.ndarray = None
    res        : np.ndarray = None
    contour    : np.ndarray = None
    hierarchy  : np.ndarray = None
    maxContour : int = None
    area       : int = None
    moments    : dict = None
    
#pin
trig_front = 27
echo_front = 18
trig_side = 20
echo_side = 21

#connect
motor = Motor('A')
steering = Motor('B')
left = -70
right = 70

#color
green = ColorDatas()
red = ColorDatas()
red2 = ColorDatas()

#camera
camera = picamera.PiCamera()
wide, high = (320, 240)
frame = 10
mode = 'sunlight'

sig_off = 0
dig_on = 0
start = 0
end = 0
total = 0
clock = 0
direction = 0

startFlag = False;

def Init():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)              
    GPIO.setup(trig_front, GPIO.OUT)          
    GPIO.setup(echo_front, GPIO.IN)
    GPIO.setup(trig_side, GPIO.OUT)          
    GPIO.setup(echo_side, GPIO.IN)

    green.lower = np.array([40, 60, 40])
    green.upper = np.array([80, 255, 255])
    green.color = "green"
    
    red.lower = np.array([160, 60, 50])
    red.upper = np.array([179, 255, 255])
    red.color = "red"

    red2.lower = np.array([0, 255, 50])
    red2.upper = np.array([30, 255, 255])   
    red2.color = "red"
    
    camera.rotation = 180
    camera.resolution = (wide, high)
    camera.framerate = frame
    
def Fin():
    motor.stop()
    cv2.destroyAllWindows()

def MotorMove(motor, nowPosition, goPosition):
    global startFlag
    if(nowPosition != goPosition):
        motor.run_to_position(goPosition)
        nowPosition = goPosition
        
        global start
        global end
        global total

        if nowPosition != 0:
            start = time.perf_counter()

        elif (startFlag):
            end = time.perf_counter()
            total = end - start
            
            print(total)
            
    startFlag = True
            
    return nowPosition

def MotorPosition(color, left, center, right):
    cube_x = int(color.moments["m10"] / color.moments["m00"])
    cube_y = int(color.moments["m01"] / color.moments["m00"])
    cv2.circle(color.dstt, (cube_x, cube_y), 2, 100, 2, 4)
    cv2.circle(color.res, (cube_x, cube_y), 2, 100, 2, 4)
    global end
    
    if 0 <= cube_x <= 40:
        position = left
    elif 41 <= cube_x <= 280:
        position = center                   
    elif 281 <= cube_x <= 320:
        position = right

    return position

def Read_distance_front():
    GPIO.output(trig_front, GPIO.HIGH)
    GPIO.output(trig_front, GPIO.LOW)

    while GPIO.input(echo_front) == GPIO.LOW:
        sig_off_front = time.time()
    while GPIO.input(echo_front) == GPIO.HIGH:
        sig_on_front = time.time()
     
    duration_front = sig_on_front - sig_off_front
    distance_front = duration_front * 34000 / 2
    return distance_front

def Read_distance_side():
    GPIO.output(trig_side, GPIO.HIGH)
    GPIO.output(trig_side, GPIO.LOW)

    while GPIO.input(echo_side) == GPIO.LOW:
        sig_off_side = time.time()
    while GPIO.input(echo_side) == GPIO.HIGH:
        sig_on_side = time.time()
     
    duration_side = sig_on_side - sig_off_side
    distance_side = duration_side * 34000 / 2
    return distance_side

def DistanceMove(steering, nowPosition, left):
    cm_front = Read_distance_front()
    cm_side = Read_distance_side()

    if cm_front < 40:
        motor.stop()
        if cm_side >=100:
            direction = 0 #0=cw 1=ccw/acw
            motor.run_for_seconds(1.3, 70)
            motor.stop()
            steering.run_to_position(-70)
            motor.run_for_seconds(2.5, -70)
            steering.run_to_position(0)
            motor.run_for_seconds(2, -100)
            motor.stop()
            
            nowPosition = MotorMove(steering, nowPosition, 0)
            
        else:
            direction = 1
            motor.run_for_seconds(1.3, 70)
            motor.stop()
            steering.run_to_position(70)
            motor.run_for_seconds(2.5, -70)
            steering.run_to_position(0)
            motor.run_for_seconds(2, -100)
            motor.stop()
            
            nowPosition = MotorMove(steering, nowPosition, 0)
            
    else:
        motor.start(30)
    
    return nowPosition

def Avoid(nowPosition):
    #green
    if (len(green.contour) != 0):
        green.maxContour = max(green.contour, key = lambda x: cv2.contourArea(x))
        green.area = cv2.contourArea(green.maxContour)
        green.moments = cv2.moments(green.maxContour)
        #green and red
        if (len(red.contour) != 0):
            red.maxContour = max(red.contour, key = lambda x: cv2.contourArea(x))
            red.area = cv2.contourArea(red.maxContour)
            red.moments = cv2.moments(red.maxContour)
            #near green
            if red.area < green.area and 1300 < green.area < 9000:
                if green.moments["m00"] != 0:
                    goPosition = MotorPosition(green, left, left, 0)
                    nowPosition = MotorMove(steering, nowPosition, goPosition)
            
            #near red
            elif green.area < red.area and 1300 < red.area < 9000:
                if red.moments["m00"] != 0:
                    goPosition = MotorPosition(red, 0, right, right)
                    nowPosition = MotorMove(steering, nowPosition, goPosition)
 
            else:
                nowPosition = DistanceMove(steering, nowPosition, left)
        
        #green only
        elif 1300 < green.area < 9000:
            if green.moments["m00"] != 0:
                goPosition = MotorPosition(green, left, left, 0)
                nowPosition = MotorMove(steering, nowPosition, goPosition)
            
        else:
            nowPosition = DistanceMove(steering, nowPosition, left)
    
    #red only
    elif (len(red.contour) != 0):
        red.maxContour = max(red.contour, key = lambda x: cv2.contourArea(x))
        red.area = cv2.contourArea(red.maxContour)
        red.moments = cv2.moments(red.maxContour)
        if 1300 < red.area < 9000:
            if red.moments["m00"] != 0:
                goPosition = MotorPosition(red, 0, right, right)
                nowPosition = MotorMove(steering, nowPosition, goPosition)
        
        else:
            nowPosition =  DistanceMove(steering, nowPosition, left)
    
    else:
        nowPosition = DistanceMove(steering, nowPosition, left)
        
    return nowPosition

def Back(nowPosition, color):
    global total
    global clock
    
    print(clock)
    steering.run_to_position(0)
    time.sleep(clock)
    
    if color == "red":
        steering.run_to_position(-70)

    elif color == "green":
        steering.run_to_position(70)
    
    time.sleep(total*0.9)
    steering.run_to_position(0)
    
    time.sleep(2)
    
    total = 0
    clock = 0
    
def main():
    nowPosition = motorMove(steering, -1, 0)
    stream = picamera.array.PiRGBArray(camera)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
    motor.start(30)
    
    while True:
        #camera
        camera.capture(stream, 'bgr', use_video_port=True)
        hsv = cv2.cvtColor(stream.array, cv2.COLOR_BGR2HSV)
        
        #masking
        green.mask = cv2.inRange(hsv, green.lower, green.upper)
        red.mask = cv2.inRange(hsv, red.lower, red.upper)
        red2.mask = cv2.inRange(hsv, red2.lower, red2.upper)
        red.mask = red.mask + red2.mask
        
        #opening
        green.dst = cv2.erode(green.mask, kernel, iterations=1)
        green.dstt = cv2.dilate(green.dst, kernel, iterations=1)
        red.dst = cv2.erode(red.mask, kernel, iterations=1)
        red.dstt = cv2.dilate(red.dst, kernel, iterations=1)
        
        #synthesis
        green.res = cv2.bitwise_and(stream.array, stream.array, mask=green.dstt)
        red.res = cv2.bitwise_and(stream.array, stream.array, mask=red.dstt)
        
        #contour detection
        green.contour, green.hierarchy = cv2.findContours(green.mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        red.contour, red.hierarchy = cv2.findContours(red.mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        #split
        cv2.line(green.res, (41, 0), (41,240), (255, 215, 0), 1)
        cv2.line(green.res, (280, 0), (280,240), (255, 215, 0), 1)
        cv2.line(red.res, (41, 0), (41,240), (255, 215, 0), 1)
        cv2.line(red.res, (280, 0), (280,240), (255, 215, 0), 1)
        
        if total == 0:
            nowPosition = Avoid(nowPosition)
            
        elif total >= 0.5:
            global clock
            if red.area < green.area:
                color = "green"
                print("green")
                clock = 2.5

            elif green.area < red.area:
                color = "red"
                print("red")
                clock = 2.5

            Back(nowPosition, color)
        
        #view
        cv2.imshow("frame", stream.array)
        cv2.imshow("Green", green.res)
        cv2.imshow("Red", red.res)
        cv2.waitKey(1)
        stream.seek(0)
        stream.truncate()
            
if __name__ == '__main__':
    Init()

    try:
        main()

    finally:
        Fin()