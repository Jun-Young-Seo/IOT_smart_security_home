let client = null; // MQTT 클라이언트의 역할을 하는 Client 객체를 가리키는 전역변수
let connectionFlag = false; // 연결 상태이면 true
const CLIENT_ID = "client-"+Math.floor((1+Math.random())*0x10000000000).toString(16) // 사용자 ID 랜덤 생성
let tempFlag=False;

function connect() { // 브로커에 접속하는 함수
	if(connectionFlag == true)
		return; // 현재 연결 상태이므로 다시 연결하지 않음

	// 사용자가 입력한 브로커의 IP 주소와 포트 번호 알아내기
	let broker = document.getElementById("broker").value; // 브로커의 IP 주소
	let port = 9001 // mosquitto를 웹소켓으로 접속할 포트 번호

	// id가 message인 DIV 객체에 브로커의 IP와 포트 번호 출력
	//document.getElementById("messages").innerHTML += '<span>접속 : ' + broker + ' 포트 ' + port + '</span><br/>';
	//document.getElementById("messages").innerHTML += '<span>사용자 ID : ' + 	CLIENT_ID + '</span><br/>';

	// MQTT 메시지 전송 기능을 모두 가징 Paho client 객체 생성
	client = new Paho.MQTT.Client(broker, Number(port), CLIENT_ID);

	// client 객체에 콜백 함수 등록 및 연결
	client.onConnectionLost = onConnectionLost; // 접속 끊김 시 onConnectLost() 실행 
	client.onMessageArrived = onMessageArrived; // 메시지 도착 시 onMessageArrived() 실행

	// client 객체에게 브로커에 접속 지시
	client.connect({
		onSuccess:onConnect, // 브로커로부터 접속 응답 시 onConnect() 실행
	});
}

// 브로커로의 접속이 성공할 때 호출되는 함수
function onConnect() {
	let broker = document.getElementById("broker").value; // 브로커 IP 가져오기
    let messageDiv = document.getElementById("connect-message");
    messageDiv.innerHTML = "연결이 완료됐습니다. IP: " + broker; // 메시지 표시	
	connectionFlag = true; // 연결 상태로 설정
	subscribe('alert');
}

function subscribe(topic) {
	if(connectionFlag != true) { // 연결되지 않은 경우
		alert("연결되지 않았음");
		return false;
	}

	if (topic === 'show_cctv') {
        // 'show_cctv'를 구독하기 전에 'camera_control' 토픽에 메시지 발행
        publish('cameraControl', 'release');  // 카메라 자원 해제 요청
        // 실제 'show_cctv' 토픽 구독
        client.subscribe(topic);
	}
	// 구독 신청하였음을 <div> 영역에 출력
	//document.getElementById("messages").innerHTML += '<span>구독신청: 토픽 ' + topic + '</span><br/>';
	client.subscribe(topic); // 브로커에 구독 신청
	
}
function publish(topic, msg) {
	if(connectionFlag != true) { // 연결되지 않은 경우
		alert("연결되지 않았음");
		return false;
	}
	client.send(topic, msg, 0, false);
}

function switchToindex() {
    publish('cameraControl', 'release');  // 카메라 자원 해제 요청
	publish('cameraControl', 'activate'); //pub가 다시 카메라
    location.href = './index/';  // index 페이지로 이동
}

function switchToCCTV() {
    publish('cameraControl', 'release');  // 카메라 자원 해제 요청
    location.href = './show_cctv/';  // CCTV 페이지로 이동
}

function unsubscribe(topic) {
	if(connectionFlag != true) return; // 연결되지 않은 경우
	if(topic === "temp")
		document.getElementById("temp-messages").innerHTML = '다시 온도를 보려면 <온도 보기>버튼을 눌러 주세요.';

	// 구독 신청 취소를 <div> 영역에 출력
	//document.getElementById("messages").innerHTML += '<span>구독신청취소: 토픽 ' + topic + '</span><br/>';
	client.unsubscribe(topic, null); // 브로커에 구독 신청 취소
}

// 접속이 끊어졌을 때 호출되는 함수
function onConnectionLost(responseObject) { // responseObject는 응답 패킷
	let messageDiv = document.getElementById("connect-message");
    messageDiv.innerHTML = "오류 : 연결이 종료되었습니다."; // 메시지 표시	
	if (responseObject.errorCode !== 0) {
		//document.getElementById("messages").innerHTML += '<span>오류 : ' + responseObject.errorMessage + '</span><br/>';
	}
	connectionFlag = false; // 연결 되지 않은 상태로 설정
}

// 메시지가 도착할 때 호출되는 함수
function onMessageArrived(msg) { // 매개변수 msg는 도착한 MQTT 메시지를 담고 있는 객체
	//console.log("onMessageArrived: " + msg.payloadString);
	if(msg.destinationName ==="temp"){
		document.getElementById("temp-messages").innerHTML = '<span>온도 : ' + msg.payloadString + '</span><br/>';
	}
	let alertDiv = document.getElementById("alertImage");
	alertDiv.style.display = "block"; // alertImage DIV를 표시

    let fireImg = document.getElementById("fireImg");
    let thiefImg = document.getElementById("thiefImg");
    if(msg.destinationName === "alert") {
        if(msg.payloadString.includes("화재")) {
            // 화재 이미지 표시
            fireImg.src = "/static/fire.jpg";
			fireImg.style.display = "block"; // 이미지 표시

        } else if(msg.payloadString.includes("침입자")) {
            // 도둑 이미지 표시
            thiefImg.src = "/static/thief.png";
			thiefImg.style.display = "block"; // 이미지 표시

        }
    }
}

// disconnection 버튼이 선택되었을 때 호출되는 함수
function disconnect() {
	if(connectionFlag == false) 
		return; // 연결 되지 않은 상태이면 그냥 리턴
	client.disconnect(); // 브로커와 접속 해제
	let messageDiv = document.getElementById("connect-message");
    messageDiv.innerHTML = "연결이 종료되었습니다."; // 메시지 표시	
	connectionFlag = false; // 연결 되지 않은 상태로 설정
}

