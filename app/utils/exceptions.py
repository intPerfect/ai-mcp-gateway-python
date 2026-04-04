"""
Custom exceptions for MCP Gateway
"""


class AppException(Exception):
    """Base application exception"""
    
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class IllegalParameterException(AppException):
    """Invalid parameter exception"""
    
    def __init__(self, message: str = "Illegal parameter"):
        super().__init__("ILLEGAL_PARAMETER", message)


class AuthException(AppException):
    """Authentication exception"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__("AUTH_FAILED", message, status_code=401)


class RateLimitException(AppException):
    """Rate limit exceeded exception"""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__("RATE_LIMIT_EXCEEDED", message, status_code=429)


class MethodNotFoundException(AppException):
    """Method not found exception"""
    
    def __init__(self, message: str = "Method not found"):
        super().__init__("METHOD_NOT_FOUND", message, status_code=404)


class SessionNotFoundException(AppException):
    """Session not found exception"""
    
    def __init__(self, message: str = "Session not found"):
        super().__init__("SESSION_NOT_FOUND", message, status_code=404)


class GatewayNotFoundException(AppException):
    """Gateway not found exception"""
    
    def __init__(self, message: str = "Gateway not found"):
        super().__init__("GATEWAY_NOT_FOUND", message, status_code=404)


class ForbiddenException(AppException):
    """Forbidden exception"""
    
    def __init__(self, message: str = "Forbidden"):
        super().__init__("FORBIDDEN", message, status_code=403)
