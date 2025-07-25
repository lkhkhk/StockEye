from typing import List, Dict, Optional
from src.common.http_client import session

# 전역 세션 객체 생성 (모든 DART API 호출에 재사용)
session = session

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
    try:
        # session 객체를 사용하여 요청
        resp = session.get(url, timeout=60)
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"DART CORPCODE.xml 요청 실패: {e}", exc_info=True)
        raise DartApiError(f"DART API 요청 실패: {e}") from e
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
        "bgn_de": bgn_de,
        "end_de": end_de,
        "page_count": max_count
    }
    if corp_code:
        params["corp_code"] = corp_code

    try:
        # session 객체를 사용하여 요청
        resp = session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"DART 공시 조회 API 요청 실패 (corp_code: {corp_code}): {e}", exc_info=True)
        raise DartApiError(f"DART API 요청 실패: {e}") from e

    status = data.get("status")
    message = data.get("message")

    if status != "000":
        logger.error(f"DART 공시 API가 오류를 반환했습니다. status: {status}, message: {message}, corp_code: {corp_code}")
        raise DartApiError(message, status_code=status)

    return data.get("list", [])
