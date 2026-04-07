from typing import Optional, Union

from pydantic import BaseModel, Field


class ErrorBase(BaseModel):
    code: Optional[str] = None
    msg: Optional[str] = None


class ResponseBase(BaseModel):
    success: bool = Field(False, title="API 요청 결과 성공여부")
    result: Optional[Union[dict, list, bool, str, None]] = Field(None, title="API 요청 성공 시 데이터")
    error: Optional[ErrorBase] = Field(None, title="API 요청 실패 시 에러정보")
    detail: Optional[dict] = Field(None, title="예비")


def api_res(
    success: bool,
    data: object = None,
    error_code: str = None,
    error_msg: str = None,
) -> dict:
    """표준 응답 생성 유틸 (기존 서버 api_res 패턴 준수)"""
    res = {
        "success": success,
        "result": data,
    }
    if not success and (error_code or error_msg):
        res["error"] = {
            "code": error_code or "",
            "msg": error_msg or "",
        }
    return res
