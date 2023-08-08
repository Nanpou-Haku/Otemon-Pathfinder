import picamera
import picamera.array
import cv2
import numpy as np
import math
from buildhat import Motor
import time

th = Motor('A')
st = Motor('B')
st.run_to_position(0)
#th.start(20)

isWallAvoided = False
avoidNum = 0

clockwise_detect = True
clockwise = True

leftmost_blue = [0, 0]
leftmost_orange = [0, 0]

def map_value(value):
    if value >= 17000:
        return 70
    elif value <= 10000:
        return 30
    else:
        slope = (70 - 30) / (17000 - 10000)
        intercept = 70 - slope * 17000
    return int(slope * value + intercept)

with picamera.PiCamera() as camera:
    with picamera.array.PiRGBArray(camera) as stream:
        camera.resolution = (320, 240)
        camera.rotation = 180
        camera.framerate = 10 
        
        while True:
            #setup camera
            camera.capture(stream, 'bgr', use_video_port=True)
            frame =  stream.array
            
            #color
            wall_lower = np.array([0, 20, 0])
            wall_upper = np.array([90, 255, 85])
            blue_lower = np.array([80, 25, 60])
            blue_upper = np.array([180, 255, 180])
            orange_lower = np.array([0, 95, 130])
            orange_upper = np.array([180, 255, 215])
            
            #roi
            base_roi = frame[80:240, 0:320]
            
            #gomihsv
            hsv = cv2.cvtColor(base_roi, cv2.COLOR_BGR2HSV)
            
            l_roi = hsv[0:240, 0:160]
            r_roi = hsv[0:240, 160:320]
            
            #kernel
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
            
            #mask
            wall_l_mask = cv2.inRange(l_roi, wall_lower, wall_upper)
            wall_r_mask = cv2.inRange(r_roi, wall_lower, wall_upper)
            blue_mask = cv2.inRange(hsv, blue_lower, blue_upper)
            orange_mask = cv2.inRange(hsv, orange_lower, orange_upper)

            
            #opening
            wall_l_dst = cv2.erode(wall_l_mask, kernel, iterations=1)
            wall_r_dst = cv2.erode(wall_r_mask, kernel, iterations=1)
            blue_dst = cv2.erode(blue_mask, kernel, iterations=1)
            orange_dst = cv2.erode(orange_mask, kernel, iterations=1)
            wall_l_dstt = cv2.dilate(wall_l_dst, kernel, iterations=1)
            wall_r_dstt = cv2.dilate(wall_r_dst, kernel, iterations=1)
            blue_dstt = cv2.dilate(blue_dst, kernel, iterations=1)
            orange_dstt = cv2.dilate(orange_dst, kernel,iterations=1)
            
            #synthesis
            wall_l_res = cv2.bitwise_and(base_roi[0:240, 0:160], base_roi[0:240, 0:160], mask=wall_l_dstt)
            wall_r_res = cv2.bitwise_and(base_roi[0:240, 160:320], base_roi[0:240, 160:320], mask=wall_r_dstt)
            blue_res = cv2.bitwise_and(base_roi, base_roi, mask=blue_dstt)
            orange_res = cv2.bitwise_and(base_roi, base_roi, mask=orange_dstt)
            
            #contour hierarchy
            wall_l_contour, wall_l_hierarchy = cv2.findContours(wall_l_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            wall_r_contour, wall_r_hierarchy = cv2.findContours(wall_r_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            blue_contour, blue_hierarchy = cv2.findContours(blue_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            orange_contour, orange_hierarchy = cv2.findContours(orange_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)            
            
            if len(wall_l_contour) > 0:
                wall_l_maxContour = max(wall_l_contour, key=lambda x: cv2.contourArea(x))
                wall_l_area = cv2.contourArea(wall_l_maxContour)
                cv2.drawContours(wall_l_res, [wall_l_maxContour], -1, (255, 0, 0), 2)
            
            else:
                wall_l_area = 0
                wall_l_maxContour = 0
            
            if len(wall_r_contour) > 0:
                wall_r_maxContour = max(wall_r_contour, key=lambda x: cv2.contourArea(x))
                wall_r_area = cv2.contourArea(wall_r_maxContour)
                cv2.drawContours(wall_r_res, [wall_r_maxContour], -1, (255, 0, 0), 2)
            
            else:
                wall_r_area = 0
                wall_r_maxContour = 0
            
            if len(blue_contour) > 0:
                blue_maxContour = max(blue_contour, key=lambda x: cv2.contourArea(x))
                blue_area = cv2.contourArea(blue_maxContour)
                blue_m = cv2.moments(blue_maxContour)
                if blue_m["m00"] != 0:
                    x_blue, y_blue = int(blue_m["m10"] / blue_m["m00"]), int(blue_m["m01"] / blue_m["m00"])
                    leftmost_blue = tuple(blue_maxContour[blue_maxContour[:,:,0].argmin()][0])
                    cv2.circle(blue_res, (leftmost_blue[0],leftmost_blue[1]), 4, (255, 255, 120), -1)
            
            else:
                blue_maxContour = 0
                blue_area = 0
                leftmost_blue = [0, 0]
            
            if len(orange_contour) > 0:
                orange_maxContour = max(orange_contour, key=lambda x: cv2.contourArea(x))
                orange_area = cv2.contourArea(orange_maxContour)
                orange_m = cv2.moments(orange_maxContour)
                if orange_m["m00"] != 0:
                    x_orange, y_orange = int(orange_m["m10"] / orange_m["m00"]), int(orange_m["m01"] / orange_m["m00"])
                    leftmost_orange = tuple(orange_maxContour[orange_maxContour[:,:,0].argmin()][0])
                    cv2.circle(orange_res, (leftmost_orange[0], leftmost_orange[1]), 4, (255, 255, 120), -1)
            
            else:
                orange_area = 0
                orange_maxContour = 0
                leftmost_orange = [0, 0]
            
            if clockwise_detect == True:
                if leftmost_blue[1] > leftmost_orange[1]:
                    clockwise = True
                
                elif leftmost_orange[1] > leftmost_blue[1]:
                    clockwise = False
                        
                clockwise_detect = False
            
            #wall_l_area ==0 and wall_r_area==0
            if 10000 <= wall_l_area and 10000 <= wall_r_area:
                if isWallAvoided == False:
                    avoidNum += 1
                    print(avoidNum)
                    isWallAvoided = True
                st.run_to_position(70)
                print("ahead")
                
            elif wall_l_area < wall_r_area:
                isWallAvoided = False
                if wall_l_area * 2 > wall_r_area:
                    st.run_to_position(0)
                    print("middle")
                    
                elif wall_l_area * 2 < wall_r_area:
                    angle = -map_value(wall_r_area)
                    st.run_to_position(angle)
                    print("go left")
                    print(angle)
            
            elif wall_l_area > wall_r_area:
                isWallAvoided = False
                if wall_l_area < wall_r_area * 2:
                    st.run_to_position(0)
                    print("middle")
                
                elif wall_l_area > wall_r_area * 2:
                    angle = map_value(wall_l_area)
                    st.run_to_position(angle)
                    print("go right")
                    print(angle)
            
            elif wall_l_area ==0 and wall_r_area==0:
                isWallAvoided = False
                st.run_to_position(0)
                print("middle")
                
               
            
            text_p = (100, 220)
            textp = (100, 440)
            font_scale = 3.0
            fontFace = cv2.FONT_HERSHEY_SIMPLEX
            color = (255, 255, 255)
            thickness = 2
            lineType = cv2.LINE_4
            
            #output
            img = np.zeros((640, 640, 3),dtype=np.uint8)
            cv2.putText(img,  "L:" + str(wall_l_area), text_p, fontFace, font_scale, color, thickness, lineType)
            cv2.putText(img,  "R:" + str(wall_r_area), textp, fontFace, font_scale, color, thickness, lineType)
            cv2.imshow("res1", wall_l_res)
            cv2.imshow("res2", wall_r_res)
            cv2.imshow("blue", blue_res)
            cv2.imshow("orange", orange_res)
            cv2.imshow("frame", base_roi)
            cv2.imshow("text", img)
            print(clockwise)
            stream.seek(0)
            stream.truncate()
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            stream.seek(0)
            stream.truncate()

st.run_to_position(0)
th.stop()
cv2.destroyAllWindows()