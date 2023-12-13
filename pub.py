###라즈베리파이 Publisher 코드###


import RPi.GPIO as GPIO
import cv2
import time
import io
from PIL import Image, ImageFilter
import paho.mqtt.client as mqtt
import sys
from adafruit_htu21d import HTU21D
import busio
from datetime import datetime

trig = 26  #GPIO 26핀 트리거
echo = 27  #GPIO 27핀 에코
sda=2 #온습도센서 I2C
scl=3 #온습도센서 I2C
button=20 #버튼
controlFlag = True #버튼 플래그로 시스템을 제어함

class Led:
	def __init__(self):
		self.red=5
		self.green=6
		GPIO.setup(self.red,GPIO.OUT)
		GPIO.setup(self.green,GPIO.OUT)

	def led_on(self,pin):
		GPIO.output(pin,GPIO.HIGH)
	def led_off(self,pin):
		GPIO.output(pin,GPIO.LOW)

class Button:
	def __init__(self):
		self.led = Led()
		self.status=0 #버튼상태. 0이면 안눌러짐, 1이면 눌러짐.
		GPIO.setup(button, GPIO.IN, GPIO.PUD_DOWN)
		GPIO.add_event_detect(button, GPIO.RISING, callback=self.pressButton, bouncetime=200)

	def pressButton(self,pin):
		global controlFlag#전역변수로
		if controlFlag:
			self.led.led_on(self.led.green)
			self.led.led_off(self.led.red)
		else:
			self.led.led_off(self.led.green)
			self.led.led_on(self.led.red)

		controlFlag = not controlFlag  # controlFlag 값을 토글
#초음파센서 제어 클래스
class Sonic:
	def __init__(self):#생성자
		GPIO.setup(trig, GPIO.OUT) #트리거는 출력용으로 설정 26
		GPIO.setup(echo, GPIO.IN)  #에코는 입력용으로 설정 27

	def measureDistance(self,trig, echo):
		GPIO.output(trig, GPIO.HIGH) # trig = 26 , echo = 27
		time.sleep(0.1)#0.1초 단위로 거리를 측정. 이 코드가 없으면 발사와 동시에 수신해서 측정이 잘 안됨
		GPIO.output(trig, GPIO.LOW) # trig 핀 신호 High->Low. 초음사 발사

		while(GPIO.input(echo) == 0): # echo 핀 값이 1로 바뀔때까지 루프
			pass

		# echo 핀 값이 1이면 초음파 발사
		pulseStart = time.time() # 초음파 발사 시간 기록
		while(GPIO.input(echo) == 1): # echo 핀 값이 0이 될때까지 루프
			pass

		# echo 핀 값이 0이 되면 초음파 수신
		pulseEnd = time.time() # 초음파 돌아 온 시간 기록
		pulseDuration = pulseEnd - pulseStart # 경과 시간 계산
		distance = pulseDuration*340*100/2#cm 단위로

		return distance # 거리 계산하여 리턴(단위 cm)

	def isWhoInvade(self):
		current = self.measureDistance(trig,echo)
		time.sleep(1)
		distance = self.measureDistance(trig,echo)
		if(current-distance > 10) or (distance-current > 10):
			#isInvade에 사용될 boolean값
			#True면 도둑 침입
			return True
		else:
			return False

class Camera:
	def __init__(self):
		self.camera = cv2.VideoCapture(0, cv2.CAP_V4L)
		self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
		self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
		#640x480 사이즈 사진 촬영
		self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
		 # 버퍼 크기를 1로 설정
	def initCamera(self):
		if not self.camera.isOpened():
			self.camera = cv2.VideoCapture(0, cv2.CAP_V4L)
			self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
			self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
			self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

	def releaseCamera(self):
		self.camera.release()

	def take_picture(self):
		ret, frame= self.camera.read()
		if ret:
			pilim = Image.fromarray(frame)  # 프레임 데이터를 이미지 형태로 변환
			stream = io.BytesIO()  # 이미지를 저장할 스트림 버퍼 생성
			pilim.save(stream, 'jpeg')
			imBytes = stream.getvalue()
			return imBytes #Jpeg 데이터 반환
		else :
			return None

	def writeFile(self):
		imBytes = self.take_picture()
		if imBytes:
			# 현재 시간을 파일 이름으로 사용
			filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S.jpg")
			with open(f'static/{filename}', 'wb') as file:
				file.write(imBytes)
			return filename
		else:
			print("file write err")

class Temp:
    def __init__(self):
        self.i2c = busio.I2C(scl=scl, sda=sda)
        self.sensor = HTU21D(self.i2c)

    def getTemperature(self):
        temperature = float(self.sensor.temperature)
        return temperature

class Mqtt:
	def __init__(self,camera):#생성자
		self.camera=camera;
		broker_ip = "localhost" #publisher가 라즈베리파이므로 localhost
		self.client = mqtt.Client() #mqtt 클라이언트 객체 생성
		self.client.connect(broker_ip, 1883)  # 1883 포트로 mosquitto에 접속
		#카메라 자원 공유 문제 해결을 위한 구독
		self.client.subscribe("cameraControl")
		self.client.on_message = self.on_message
		self.client.loop_start()  # 메시지 루프를 실행하는 스레드 생성

	def __del__(self):#소멸자
		self.client.loop_stop()#클라이언트 객체 루프 종료
		self.client.disconnect()#클라이언트 객체 연결 종료

	def on_message(self,client, userdata, message):
		if message.topic == "cameraControl" and message.payload.decode() == 'release':
			self.camera.releaseCamera()  # 카메라 자원 해제
		elif message.topic == "cameraControl" and message.payload.decode() == 'activate':
			self.camera.initCamera() # 카메라 세팅

	def publishTemp(self,temp):
		self.client.publish("temp",temp,qos=0)

	def publishAlert(self,isInvade,temp):
		if(isInvade):
			alert = "집에 침입자가 있을 수 있습니다."
			self.client.publish("alert",alert,qos=0)
		if(temp > 20 ):
			alert = "집에 화재가 발생했을 수 있습니다."
			self.client.publish("alert",alert,qos =0)

class Pub: #publisher 클래스
	def run(self):
		sonic = Sonic()
		temp=Temp()
		camera=Camera()
		mqtt=Mqtt(camera)
		button = Button()
		while True:
			#사용자가 스위치를 눌러 끄지 않은 상태
			if controlFlag:
				temperature = temp.getTemperature()
				mqtt.publishTemp(temperature)
				isInvade = sonic.isWhoInvade()
				mqtt.publishAlert(isInvade,temperature)
				if isInvade:
					#도둑이 들 경우 사진 저장
					camera.writeFile()
				time.sleep(1)  # 루프당 1초 대기



if __name__== "__main__":
	GPIO.setmode(GPIO.BCM)  # BCM 모드로 작동
	GPIO.setwarnings(False)  # 경고글이 출력되지 않게 설정
	pub = Pub()
	try:
		pub.run()
	except KeyboardInterrupt: #Ctrl C 입력시 예외처리
		print("Ctrl+C로 강제종료")
	finally:
		GPIO.cleanup()  # 어떤 식으로 종료되든 GPIO 정리
