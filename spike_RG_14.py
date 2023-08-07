import time
import atexit
import picamera
import picamera.array
import RPi.GPIO as GPIO
from dataclasses import dataclass
import cv2
import numpy as np
from buildhat import Motor, ForceSensor
import copy
import math

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
blue = ColorDatas()
black = ColorDatas()

#camera
camera = picamera.PiCamera()
wide, high = (320, 240)
frame = 10

sig_off = 0
dig_on = 0
start = 0
end = 0
total = 0
clock = 0
direction = 0
counter = 0
surf = 0
blue.area = 0
degree = 0

first = True

poleFlag = False
blueFlag = False
startFlag = False

#Hiroshi
def init():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)              
    GPIO.setup(trig_front, GPIO.OUT)          
    GPIO.setup(echo_front, GPIO.IN)
    GPIO.setup(trig_side, GPIO.OUT)          
    GPIO.setup(echo_side, GPIO.IN)
    
    blue.lower = np.array([104, 85, 0])
    blue.upper = np.array([170, 255, 163])
    blue.color = "blue"
    
    green.lower = np.array([40, 60, 40])
    green.upper = np.array([80, 255, 255])
    green.color = "green"
    
    red.lower = np.array([160, 60, 50])
    red.upper = np.array([179, 255, 255])
    red.color = "red"

    red2.lower = np.array([0, 255, 50])
    red2.upper = np.array([30, 255, 255])   
    red2.color = "red"
    
    black.lower = np.array([0, 0, 0])
    black.upper = np.array([50, 225, 110])
    black.color = "black"
    
    camera.rotation = 180
    camera.resolution = (wide, high)
    camera.framerate = frame
    
def UpdateCamera(stream, kernel):
    #camera
    camera.capture(stream, 'bgr', use_video_port=True)
    hsv = cv2.cvtColor(stream.array, cv2.COLOR_BGR2HSV)
    
    hsvline = cv2.cvtColor(stream.array, cv2.COLOR_BGR2HSV)
    blind = cv2.rectangle(hsvline, (0, 0), (320, 130), (100, 100, 100), -1)
    
    hsvblack = cv2.cvtColor(stream.array, cv2.COLOR_BGR2HSV)
    black_blind1 = cv2.rectangle(hsvblack, (0, 0), (320, 100), (240, 240, 240), -1)
    black_blind2 = cv2.rectangle(black_blind1, (0, 0), (20, 240), (240, 240, 240), -1)
    black_blind3 = cv2.rectangle(black_blind2, (300, 0), (320, 240), (240, 240, 240), -1)
    
    #マスク処理
    green.mask = cv2.inRange(hsv, green.lower, green.upper)
    red.mask = cv2.inRange(hsv, red.lower, red.upper)
    red2.mask = cv2.inRange(hsv, red2.lower, red2.upper)
    red.mask = red.mask + red2.mask
    
    blue.mask = cv2.inRange(hsvline, blue.lower, blue.upper)
    black.mask = cv2.inRange(hsvblack, black.lower, black.upper)
    
    #オープニング
    green.dst = cv2.erode(green.mask, kernel, iterations=1)
    green.dstt = cv2.dilate(green.dst, kernel, iterations=1)
    red.dst = cv2.erode(red.mask, kernel, iterations=1)
    red.dstt = cv2.dilate(red.dst, kernel, iterations=1)
    
    blue.dst = cv2.erode(blue.mask, kernel, iterations=1)
    blue.dstt = cv2.dilate(blue.dst, kernel, iterations=1)
    black.dst = cv2.erode(black.mask, kernel, iterations=1)
    black.dstt = cv2.dilate(black.dst, kernel, iterations=1)
    
    #合成
    green.res = cv2.bitwise_and(stream.array, stream.array, mask=green.dstt)
    red.res = cv2.bitwise_and(stream.array, stream.array, mask=red.dstt)
    
    blue.res = cv2.bitwise_and(stream.array, stream.array, mask=blue.dstt)
    black.res = cv2.bitwise_and(stream.array, stream.array, mask=black.dstt)
    
    #輪郭検出
    green.contour, green.hierarchy = cv2.findContours(green.mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    red.contour, red.hierarchy = cv2.findContours(red.mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    blue.contour, blue.hierarchy = cv2.findContours(blue.mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    black.contour, black.hierarchy = cv2.findContours(black.mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    
    #分割線描画
    cv2.line(green.res, (41, 0), (41,240), (255, 215, 0), 1)
    cv2.line(green.res, (280, 0), (280,240), (255, 215, 0), 1)
    cv2.line(red.res, (41, 0), (41,240), (255, 215, 0), 1)
    cv2.line(red.res, (280, 0), (280,240), (255, 215, 0), 1)

#Fujimura
def situation():
    stream = picamera.array.PiRGBArray(camera)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
    UpdateCamera(stream, kernel)
    
    if (len(green.contour) != 0):
        green.maxContour = max(green.contour, key = lambda x: cv2.contourArea(x))
        green.area = cv2.contourArea(green.maxContour)
        green.moments = cv2.moments(green.maxContour)
    
    if (len(red.contour) != 0):
        red.maxContour = max(red.contour, key = lambda x: cv2.contourArea(x))
        red.area = cv2.contourArea(red.maxContour)
        red.moments = cv2.moments(red.maxContour)
    
    if (len(black.contour) != 0):
        black.maxContour = max(black.contour, key = lambda x: cv2.contourArea(x))
        black.area = cv2.contourArea(black.maxContour)
        black.moments = cv2.moments(black.maxContour)
    
    else:
        green.area = 0
        red.area = 0
        black.area = 0
    
def situationBlue():
    stream = picamera.array.PiRGBArray(camera)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
    UpdateCamera(stream, kernel)
    
    if (len(blue.contour) != 0):
        blue.maxContour = max(blue.contour, key = lambda x: cv2.contourArea(x))
        blue.area = cv2.contourArea(blue.maxContour)
        blue.moments = cv2.moments(blue.maxContour)
    
    else:
        blue.area = 0
        
    return blue.area
    
def CameraShow(stream, kernel):
    #表示
    cv2.imshow("frame", stream.array)
    cv2.imshow("Green", green.res)
    cv2.imshow("Red", red.res)
    cv2.imshow("Blue", blue.res)
    cv2.imshow("black", black.res)
    cv2.waitKey(1)
    stream.seek(0)
    stream.truncate()

#Hiroshi
def fini():
    motor.stop()
    cv2.destroyAllWindows()

#Hiroshi
def motorMove(motor, nowPosition, goPosition):
    global startFlag
    if(nowPosition != goPosition):
        motor.run_to_position(goPosition)
        nowPosition = goPosition
        
        global start, end, total

        if nowPosition != 0:
            start = time.perf_counter()

        elif (startFlag):
            end = time.perf_counter()
            total = end - start
            
            print("total =", total)
            
    startFlag = True
            
    return nowPosition

#Hiroshi
def motorPosition(color, left, center, right):
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

#Yasui
def read_distance_front():
    GPIO.output(trig_front, GPIO.HIGH)
    time.sleep(0.00001)
    GPIO.output(trig_front, GPIO.LOW)
    
    sig_on_front = 0
    sig_off_front = 0
    
    while GPIO.input(echo_front) == GPIO.LOW:
        sig_off_front = time.time()
    while GPIO.input(echo_front) == GPIO.HIGH:
        sig_on_front = time.time()
     
    duration_front = sig_on_front - sig_off_front
    distance_front = duration_front * 34000 / 2
    return distance_front

#Yasui
def read_distance_side():
    GPIO.output(trig_side, GPIO.HIGH)
    time.sleep(0.00001)
    GPIO.output(trig_side, GPIO.LOW)
    
    sig_on_side = 0
    sig_off_side = 0
    
    while GPIO.input(echo_side) == GPIO.LOW:
        sig_off_side = time.time()
    while GPIO.input(echo_side) == GPIO.HIGH:
        sig_on_side = time.time()
     
    duration_side = sig_on_side - sig_off_side
    distance_side = duration_side * 34000 / 2
    return distance_side

#Yasui
def distanceMove(steering, nowPosition, left):
    cm_front = read_distance_front()
    cm_side = read_distance_side()
    global pole, counter, blueFlag, poleFlag, first
    
    stream = picamera.array.PiRGBArray(camera)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
    
    if first == True:
        if cm_front < 40:
            motor.stop()
            situation()
            UpdateCamera(stream, kernel)
            nowPosition = pointDetect(nowPosition, cm_side)
            CameraShow(stream, kernel)
        
        else:
            print("first")
            motor.start(30)
    
    elif poleFlag and blueFlag:
        if cm_front < 40:
            motor.stop()
            situation()
            UpdateCamera(stream, kernel)
            nowPosition = pointDetect(nowPosition, cm_side)
            CameraShow(stream, kernel)
        
        else:
            motor.start(30)
            
    else:
        motor.start(30)
    
    return nowPosition

#Fujimura
def avoid(nowPosition):
    if poleFlag and blueFlag:
        print("ignore")
        nowPosition = distanceMove(steering, nowPosition, left)
        
    else:
        situationBlue()
        #緑あり
        if (len(green.contour) != 0):
            green.maxContour = max(green.contour, key = lambda x: cv2.contourArea(x))
            green.area = cv2.contourArea(green.maxContour)
            green.moments = cv2.moments(green.maxContour)
            #赤あり
            if (len(red.contour) != 0):
                red.maxContour = max(red.contour, key = lambda x: cv2.contourArea(x))
                red.area = cv2.contourArea(red.maxContour)
                red.moments = cv2.moments(red.maxContour)
                #緑が近いなら緑を優先
                if red.area < green.area and 1200 < green.area < 9000:
                    if green.moments["m00"] != 0:
                       goPosition = motorPosition(green, left, left, 0)
                       nowPosition = motorMove(steering, nowPosition, goPosition)
                       lineDetect()
            
                #赤が近いなら赤を優先
                elif green.area < red.area and 1200 < red.area < 9000:
                    if red.moments["m00"] != 0:
                        goPosition = motorPosition(red, 0, right, right)
                        nowPosition = motorMove(steering, nowPosition, goPosition)
                        lineDetect()
 
                else:
                    nowPosition = distanceMove(steering, nowPosition, left)
                    lineDetect()
        
            #緑あり赤なし
            elif 1200 < green.area < 9000:
                if green.moments["m00"] != 0:
                    goPosition = motorPosition(green, left, left, 0)
                    nowPosition = motorMove(steering, nowPosition, goPosition)
                    lineDetect()
            
            else:
                nowPosition = distanceMove(steering, nowPosition, left)
                lineDetect()
    
        #緑なし赤あり
        elif (len(red.contour) != 0):
            red.maxContour = max(red.contour, key = lambda x: cv2.contourArea(x))
            red.area = cv2.contourArea(red.maxContour)
            red.moments = cv2.moments(red.maxContour)
            if 1200 < red.area < 9000:
                if red.moments["m00"] != 0:
                    goPosition = motorPosition(red, 0, right, right)
                    nowPosition = motorMove(steering, nowPosition, goPosition)
                    lineDetect()

            else:
                nowPosition =  distanceMove(steering, nowPosition, left)
                lineDetect()

        else:
            nowPosition = distanceMove(steering, nowPosition, left)
            lineDetect()

    return nowPosition

#Fujimura
def back(nowPosition, color):
    global total, clock, counter, surf, blueFlag, poleFlag
    
    poleFlag = True
    steering.run_to_position(0)
    time.sleep(1.6)
    
    if color == "red":
        steering.run_to_position(-70)

    elif color == "green":
        steering.run_to_position(70)
    
    situationBlue()
    lineDetect()
    
    print("------")
    print("poleFlag =", poleFlag)
    print("blueFlag =", blueFlag)
    
    time.sleep(total*0.75)
    steering.run_to_position(0)

    time.sleep(1.8)
    
    total = 0
    clock = 0
    
def lineDetect():
    global blueFlag, poleFlag
    
    if poleFlag:
        if 500 <= blue.area:
            blueFlag = True
            print("------")
            print("Detect line")
            print("blueArea =", blue.area)
            print("poleFlag =", poleFlag)
            print("blueFlag =", blueFlag)
        
    else:
        print("------")
        print("mada")
        print("blueArea =", blue.area)
        print("poleFlag =", poleFlag)
        print("blueFlag =", blueFlag)
        
def pointDetect(nowPosition, cm_side):
    global degree
    cv2.drawContours(black.res, black.maxContour, -1, (255, 0, 0), 2)
    
    lx, ly = (float("inf"), float("inf"))
    rx, ry = (float("-inf"), float("-inf"))
    
    for contour in black.maxContour:
        for point in contour:
            x = point.item(0)
            y = point.item(1)
            
            if x < lx or (x == lx and y > ly):
                lx, ly = (x, y)
            
            if x > rx or (x == rx and y > ry):
                rx, ry = (x, y)
                
    if lx != float("inf") and ly != float("inf"):
        cv2.circle(black.res, (lx, ly), 5, (0, 0, 255), -1)
    
    if rx != float("-inf") and ry != float("-inf"):
        cv2.circle(black.res, (rx, ry), 5, (0, 255, 0), -1)
    
    tanh = abs(ly - ry)
    
    black_degree = (math.degrees(math.atan2(tanh, 280)))
    
    degree = (30/11 * black_degree) - 1
    
    print("------")
    
    if ry <= ly:
        degree = -1*degree

    return judgeDegree(nowPosition, cm_side)

def judgeDegree(nowPosition, cm_side):
    global poleFlag, blueFlag, first
    
    print("degree =", degree)
    if 4 <= degree:
        steering.run_to_position(40)
        motor.start(20)
        
    elif degree <= 0:
        steering.run_to_position(-40)
        motor.start(20)
        
    elif 0 < degree < 4:
        steering.run_to_position(0)
        motor.stop()
        print("ok")
        
        if cm_side >= 100:
            print("cm_side =", cm_side)
            direction = 0 #0=cw 1=ccw/acw
            motor.run_for_seconds(1.3, 70)
            time.sleep(0.1)
            motor.run_for_seconds(0.5, -70)
            steering.run_to_position(-75)
            motor.run_for_seconds(2, -70)
            steering.run_to_position(0)
            motor.run_for_seconds(1.2, -100)
            time.sleep(0.1)
            situation()
            
            poleFlag = False
            blueFlag = False
            first = False
            
            nowPosition = motorMove(steering, nowPosition, 0)
            
        else:
            print("cm_side =", cm_side)
            direction = 1
            motor.run_for_seconds(1.3, 70)
            time.sleep(0.1)
            motor.run_for_seconds(0.5, -70)
            steering.run_to_position(75)
            motor.run_for_seconds(2, -70)
            steering.run_to_position(0)
            motor.run_for_seconds(1.2, -100)
            time.sleep(0.1)
            situation()
            
            poleFlag = False
            blueFlag = False
            first = False
            
            nowPosition = motorMove(steering, nowPosition, 0)
    
    return nowPosition

#Fujimura
def main():
    nowPosition = motorMove(steering, -1, 0)
    stream = picamera.array.PiRGBArray(camera)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
    motor.start(30)
    
    while True:
        UpdateCamera(stream, kernel)
        
        if total == 0:
            situationBlue()
            lineDetect()
            nowPosition = avoid(nowPosition)
            
        elif total >= 0.5:
            global clock
            
            if red.area == None:
                red.area = 0.0
                
            if green.area == None:
                green.area = 0.0
            
            if red.area < green.area:
                color = "green"
                print("------")
                print("green")
                print("midori = ", green.area)
                print("aka = ", red.area)

            elif green.area < red.area:
                color = "red"
                print("------")
                print("red")
                print("midori = ", green.area)
                print("aka = ", red.area)

            back(nowPosition, color)
        CameraShow(stream, kernel)
            
if __name__ == '__main__':
    init()

    try:
        main()

    finally:
        fini()