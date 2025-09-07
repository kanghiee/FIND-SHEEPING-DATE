"""
베리시 교환 출고일 조회 서비스 (Flask + Google Sheets API)
---------------------------------------------------------
- 고객 이름과 연락처를 입력하면 Google Sheets에서 교환 신청 현황을 조회
- 예상 출고일, 실제 출고일, 철회사유, 송장번호 등을 반환
- Flask API + HTML 프론트엔드 연동
"""

from flask import Flask, request, jsonify, render_template
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import logging
import os
from dotenv import load_dotenv

app = Flask(__name__)

# ======================== Google Sheets 인증 ========================
load_dotenv()
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

GOOGLE_KEY_PATH = os.getenv("GOOGLE_KEY_PATH")  # .env 파일에서 관리
SPREADSHEET_URL_RAW = os.getenv("SPREADSHEET_URL_RAW")
SPREADSHEET_URL_EXCHANGE = os.getenv("SPREADSHEET_URL_EXCHANGE")

creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_KEY_PATH, scope)
gc = gspread.authorize(creds)

sheet = gc.open_by_url(SPREADSHEET_URL_RAW).worksheet("교환 신청 현황 확인(RAW)")
sheet2 = gc.open_by_url(SPREADSHEET_URL_EXCHANGE).worksheet("[수기] 자사몰 교환")

# ======================== 로깅 ========================
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def format_contact_number(contact_number: str) -> str:
    """전화번호를 010-1234-5678 형식으로 변환"""
    contact_number = contact_number.replace("-", "")
    return f"{contact_number[:3]}-{contact_number[3:7]}-{contact_number[7:]}"

# ======================== API ========================
@app.route('/get_product_info', methods=['POST'])
def get_product_info():
    """이름+연락처로 교환 출고 정보 조회"""
    data = request.get_json()
    customer_name = data.get('name')
    contact_number = data.get('contact')

    # 입력 검증
    if len(contact_number.replace("-", "")) != 11 or not contact_number.replace("-", "").isdigit():
        return jsonify({'error': '잘못된 전화번호 형식입니다.'}), 400

    formatted_contact = format_contact_number(contact_number)
    current_date = datetime.today()
    results = []
    recent_exchange_found = False

    # 시트 전체 조회
    for record in sheet.get_all_records():
        if record['수령자 성함'] == customer_name and record['연락처'].strip() == formatted_contact:
            logging.info("조회 성공: %s, %s", customer_name, formatted_contact)
            recent_exchange_found = True

            # 간단화: 교환 정보 일부만 반환
            exchange_data = {
                '교환 상품명': record['상품명'],
                '교환 옵션명': record['교환 출고 옵션'],
                '수량': record.get('수량', '미제공'),
                '예상 출고일': record.get('예상 출고일', ''),
                '실제 출고일': record.get('실제 출고일(입고일)', ''),
                '송장번호': record.get('출고 송장 번호', ''),
                '지불방법': record.get('지불방법', ''),
                '철회사유': ''  # 필요 시 sheet2에서 조회 가능
            }
            results.append(exchange_data)

    if results:
        return jsonify({'data': results}), 200
    elif not recent_exchange_found:
        return jsonify({'message': '최근 교환 신청 내역이 없습니다.'}), 200
    else:
        return jsonify({'error': '해당 고객 정보를 찾을 수 없습니다.'}), 404

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
