from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.adapters.inbound.rest.dto import (
    APIResponse,
    ToggleVisibilityRequest,
    UpdatePriceRequest,
    UserOrderDTO,
)
from app.domain.order import OrderType
from app.ports.item_service_port import ItemServicePort

router = APIRouter(prefix="/api/v1/market", tags=["Market"])


# 依賴注入提供者函數（main.py 會透過 dependency_overrides 覆蓋）
def get_item_service() -> ItemServicePort:
    raise NotImplementedError("Dependency not injected")


# 使用 Annotated 定義型別別名，徹底消除 B008 警告
ItemServiceDep = Annotated[ItemServicePort, Depends(get_item_service)]
OrderTypeQuery = Annotated[
    OrderType | None,
    Query(alias="type", description="掛單類型 buy / sell，不給則回傳全部"),
]


@router.get(
    "/items",
    response_model=APIResponse[list[dict[str, Any]]],
    summary="取得特定分類的商品列表",
)
async def get_items(
    service: ItemServiceDep,
    category: str = "baro",
):
    items = await service.list_items_by_category(category)
    data = [
        {
            "id": item.id,
            "name_en": item.name_en,
            "name_tc": item.name_tc,
            "category": item.category,
            "current_price": item.current_price,
            "user_price": item.user_price,
            "is_visible": item.is_visible,
        }
        for item in items
    ]
    return APIResponse(code=200, message="success", data=data)


@router.get(
    "/users/{username}/orders",
    response_model=APIResponse[list[UserOrderDTO]],
    summary="查詢指定使用者的公開掛單列表",
)
async def get_user_orders(
    username: str,
    service: ItemServiceDep,
    order_type: OrderTypeQuery = None,
):
    return await _list_user_orders(service, username, order_type)


@router.get(
    "/me/orders",
    response_model=APIResponse[list[UserOrderDTO]],
    summary="查詢個人拍賣場公開掛單列表",
    description="未帶 username 時使用 config 的 DEFAULT_WF_USERNAME；"
    "登入功能完成後將改為查詢登入者本人。",
)
async def get_my_orders(
    service: ItemServiceDep,
    username: str | None = None,
    order_type: OrderTypeQuery = None,
):
    return await _list_user_orders(service, username, order_type)


async def _list_user_orders(
    service: ItemServicePort,
    username: str | None,
    order_type: OrderType | None,
) -> APIResponse[list[UserOrderDTO]]:
    try:
        listings = await service.get_user_orders(username, order_type)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e).strip("'\""),
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except (RuntimeError, OSError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"第三方服務通訊異常: {e!s}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="系統內部未知錯誤",
        ) from e
    data = [UserOrderDTO.from_domain(listing) for listing in listings]
    return APIResponse(code=200, message="success", data=data)


@router.patch(
    "/items/{item_id}/price",
    response_model=APIResponse[dict[str, Any]],
    summary="更新特定商品自訂價格",
)
async def update_item_price(
    item_id: str,
    payload: UpdatePriceRequest,
    service: ItemServiceDep,
):
    try:
        updated = await service.update_item_price(item_id, payload.price)
        data = {
            "id": updated.id,
            "name_en": updated.name_en,
            "name_tc": updated.name_tc,
            "category": updated.category,
            "current_price": updated.current_price,
            "user_price": updated.user_price,
            "is_visible": updated.is_visible,
        }
        return APIResponse(code=200, message="價格更新成功", data=data)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        ) from e


@router.patch(
    "/items/{item_id}/visibility",
    response_model=APIResponse[dict[str, Any]],
    summary="切換特定商品上下架顯示狀態",
)
async def toggle_item_visibility(
    item_id: str,
    payload: ToggleVisibilityRequest,
    service: ItemServiceDep,
):
    try:
        updated = await service.toggle_item_visibility(item_id, payload.is_visible)
        data = {
            "id": updated.id,
            "name_en": updated.name_en,
            "name_tc": updated.name_tc,
            "category": updated.category,
            "current_price": updated.current_price,
            "user_price": updated.user_price,
            "is_visible": updated.is_visible,
        }
        return APIResponse(code=200, message="顯示狀態更新成功", data=data)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
