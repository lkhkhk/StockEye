class DartApiError(Exception):
    """DART Open API와 통신 중 발생하는 오류"""
    def __init__(self, message: str, status_code: str = None):
        self.status_code = status_code
        super().__init__(f"[{status_code}] {message}" if status_code else message) 