import requests
import zipfile
import io
from lxml import etree
import os
from typing import List, Dict, Optional

def dart_get_all_stocks(api_key: Optional[str] = None) -> List[Dict[str, str]]:
    """
    DART OpenAPI에서 CORPCODE.xml을 다운로드하여 전체 상장종목(6자리 종목코드 포함) 리스트 반환
    반환 예시: [{"symbol": "005930", "name": "삼성전자", "corp_code": "00126380"}, ...]
    """
    if api_key is None:
        api_key = os.getenv("DART_API_KEY")
    if not api_key:
        raise ValueError("DART_API_KEY가 환경변수에 없거나 인자로 전달되지 않았습니다.")
    url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={api_key}"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    zip_content = resp.content
    with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
        if 'CORPCODE.xml' not in z.namelist():
            raise RuntimeError("ZIP 파일 내에 CORPCODE.xml이 없습니다.")
        with z.open('CORPCODE.xml') as xml_file:
            xml_content = xml_file.read()
    root = etree.fromstring(xml_content)
    corp_data = []
    for corp in root.xpath('//list'):
        corp_code = corp.xpath('./corp_code/text()')
        corp_name = corp.xpath('./corp_name/text()')
        stock_code = corp.xpath('./stock_code/text()')
        if corp_code and corp_name:
            data = {
                'corp_code': corp_code[0].strip(),
                'name': corp_name[0].strip(),
                'symbol': stock_code[0].strip() if stock_code and stock_code[0].strip() else None
            }
            # 6자리 숫자 종목코드만 추가
            if data['symbol'] and data['symbol'].isdigit() and len(data['symbol']) == 6:
                corp_data.append(data)
    return corp_data

def dart_get_disclosures(corp_code: str, api_key: Optional[str] = None, bgn_de: Optional[str] = None, end_de: Optional[str] = None, max_count: int = 10) -> List[Dict[str, str]]:
    """
    DART OpenAPI에서 특정 기업의 공시(list.json)를 조회하여 최근 공시 목록을 반환
    반환 예시: [{"corp_name": ..., "report_nm": ..., "rcept_no": ..., "rcept_dt": ..., ...}, ...]
    """
    import datetime
    if api_key is None:
        api_key = os.getenv("DART_API_KEY")
    if not api_key:
        raise ValueError("DART_API_KEY가 환경변수에 없거나 인자로 전달되지 않았습니다.")
    if bgn_de is None:
        bgn_de = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y%m%d")
    if end_de is None:
        end_de = datetime.datetime.now().strftime("%Y%m%d")
    url = "https://opendart.fss.or.kr/api/list.json"
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bgn_de": bgn_de,
        "end_de": end_de,
        "page_count": max_count
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "000":
        raise RuntimeError(f"DART 공시 API 오류: {data.get('status')} - {data.get('message')}")
    return data.get("list", []) 