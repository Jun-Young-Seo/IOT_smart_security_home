import base64
import time
import cv2
from flask import Flask, render_template, url_for
from pub import Camera

app = Flask(__name__)  # 플라스크 객체 생성

@app.route('/')
def index():
    return render_template('index.html')
@app.route('/show_cctv/')
def cctv():
    camera = Camera()
    imBytes = camera.take_picture()
    if imBytes is not None:
        # 바이트 배열을 Base64 문자열로 인코딩
        img_base64 = base64.b64encode(imBytes).decode('utf-8')
    else:
        img_base64 = None
        print("img is None")
    return render_template("show_cctv.html", img_data=img_base64)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)  # debug=True 속성을 사용하면 오류 발생


