class DartApiError(Exception):
    """DART Open API와 통신 중 발생하는 오류"""
    def __init__(self, message: str, status_code: str = None):
        self.status_code = status_code
        super().__init__(f"[{status_code}] {message}" if status_code else message)

class UserAlreadyExistsException(Exception):
    """사용자가 이미 존재할 때 발생하는 오류"""
    pass

class InvalidCredentialsException(Exception):
    """인증 정보가 유효하지 않을 때 발생하는 오류"""
    pass