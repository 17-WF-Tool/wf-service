from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: T | None = None


class ItemResponseDTO(BaseModel):
    id: str
    name_en: str
    name_tc: str
    category: str
    current_price: int
    user_price: int
    is_visible: bool


class MyOrderResponseDTO(BaseModel):
    order_id: str
    name_en: str
    platinum: int
    quantity: int
    order_type: str
    is_visible: bool
    mod_rank: int | None = None


class UpdatePriceRequest(BaseModel):
    price: int = Field(..., ge=0, description="設定價格不能小於 0")


class ToggleVisibilityRequest(BaseModel):
    is_visible: bool
