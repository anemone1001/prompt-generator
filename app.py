import os
import google.generativeai as genai
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from PIL import Image
import io
from datetime import datetime

# .env 파일에서 환경 변수(API 키) 로드
load_dotenv()

app = Flask(__name__)

# --- 서버 설정 ---
try:
    # 서버에 저장된 비밀 API 키로 Google AI 설정
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
except KeyError:
    # 서버 시작 시 API 키가 없으면 에러 메시지 출력 후 종료
    print("오류: GOOGLE_API_KEY가 .env 파일에 설정되지 않았습니다.")
    exit()

# --- 하루 사용 횟수 제한 (서버 사이드) ---
DAILY_LIMIT = 5  # 하루 총 5회 제한
usage_data = {
    'date': datetime.now().strftime('%Y-%m-%d'),
    'requests': {}  # 사용자 IP별 사용 횟수 저장
}

def check_usage_limit(user_ip):
    """사용자 IP를 기준으로 사용 횟수를 체크하고 관리합니다."""
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # 날짜가 바뀌면 사용량 데이터 초기화
    if usage_data['date'] != today_str:
        usage_data['date'] = today_str
        usage_data['requests'] = {}

    # 현재 사용자의 사용 횟수를 가져오거나 초기화
    user_count = usage_data['requests'].get(user_ip, 0)

    if user_count >= DAILY_LIMIT:
        return False  # 사용량 초과
    
    # 사용량 1 증가
    usage_data['requests'][user_ip] = user_count + 1
    return True # 사용 가능

# --- Flask 라우팅 ---

@app.route('/')
def index():
    """메인 페이지를 보여줍니다."""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    """프롬프트 생성 API 엔드포인트"""
    user_ip = request.remote_addr # 사용자 IP 주소

    # 1. 사용량 체크
    if not check_usage_limit(user_ip):
        # 429: Too Many Requests (너무 많은 요청)
        return jsonify({'error': '하루 사용 횟수를 모두 사용하셨습니다. 내일 다시 시도해 주세요.'}), 429

    if 'image' not in request.files:
        return jsonify({'error': '이미지 파일이 없습니다.'}), 400

    file = request.files['image']
    
    try:
        # 2. 이미지 처리
        image = Image.open(file.stream).convert("RGB") # 이미지를 RGB로 변환
        
        # 3. AI에게 보낼 지시문 생성 (이전과 동일)
        model_prompt = get_model_prompt()
        
        # 4. Google AI API 호출
        response = model.generate_content([model_prompt, image])
        
        # 5. 결과 파싱 및 클라이언트에게 전송
        raw_text = response.text
        json_text = raw_text.replace('```json', '').replace('```', '').strip()
        prompts = eval(json_text) # JSON 텍스트를 Python 딕셔너리로 변환
            
        return jsonify(prompts)

    except Exception as e:
        print(f"오류 발생: {e}")
        # 서버 내부 오류
        return jsonify({'error': f'프롬프트를 생성하는 중 서버에서 오류가 발생했습니다: {str(e)}'}), 500

def get_model_prompt():
    """AI에게 전달할 상세 지시문을 생성하는 함수"""
    # 이전 버전과 동일한 고품질 프롬프트 지시문
    main_instruction = "당신은 세계 최고 수준의 NovelAI 프롬프트 엔지니어링 전문가입니다..." # (지시문이 길어서 생략)
    analysis_process = "..." # (지시문이 길어서 생략)
    # 실제 코드에서는 이 부분에 v12의 getModelPrompt 내용을 그대로 붙여넣으면 됩니다.
    # 여기서는 설명을 위해 축약했습니다.
    return """
        당신은 세계 최고 수준의 NovelAI 프롬프트 엔지니어링 전문가입니다.
        당신의 임무는 주어진 이미지를 아래의 '4단계 분석 프로세스'에 따라 체계적으로 분석하고, 그 결과를 종합하여 전문가 수준의 '포지티브 프롬프트'와 '네거티브 프롬프트'를 생성하는 것입니다.
        최종 결과는 다른 설명 없이 오직 JSON 형식으로만 응답해주세요. (예: {"positive_prompt": "...", "negative_prompt": "..."})

        ---
        ### 4단계 분석 프로세스 (이 순서대로 생각하고 분석하세요)

        **[1단계: 하이퍼-디테일 묘사]**
        - **주제:** 인물(1girl, 2boys) 등
        - **인물 묘사:** 헤어(long flowing wavy blonde hair), 얼굴(small cute face), 의상(oversized shiny white bomber jacket) 등
        - **배경:** 장소(quiet classroom), 분위기(afternoon sun) 등
        - **구도:** 앵글(from below), 구성(full body) 등

        **[2단계: 카테고리 강조 태그 생성 (핵심)]**
        - 예시: (detailed clothing:1.2), (expressive facial features:1.3) 등

        **[3단계: 아트 스타일 & 미학 분석]**
        - **품질:** masterpiece, best quality, incredibly absurdres, highres, 8k
        - **아트 스타일:** anime style, concept art, key visual 등
        - **매체:** digital painting, illustration, 2d art 등
        - **미학적 특징:** (cinematic lighting:1.1), soft shading, vibrant colors 등

        **[4단계: 프롬프트 최종 조합]**
        1. **'포지티브 프롬프트':** NovelAI 스타일에 맞춰 쉼표(,)로 구분된 키워드 형식으로 작성.
        2. **'네거티브 프롬프트':** 저품질 태그와 반대 개념 태그를 조합하여 작성.
    """


if __name__ == '__main__':
    # 서버 실행 (개발용)
    app.run(host='0.0.0.0', port=5000, debug=True)
