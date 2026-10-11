from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.adapters.inbound.rest.dto import (
    APIResponse,
    ItemGroupDTO,
    ItemPriceDTO,
    MarketItemDTO,
    UserOrderDTO,
)
from app.domain.order import OrderType
from app.ports.group_service_port import GroupServicePort
from app.ports.order_service_port import OrderServicePort
from app.ports.price_service_port import PriceServicePort

router = APIRouter(prefix="/api/v1/market", tags=["Market"])


# 依賴注入提供者函數（main.py 會透過 dependency_overrides 覆蓋）
def get_order_service() -> OrderServicePort:
    raise NotImplementedError("Dependency not injected")


def get_price_service() -> PriceServicePort:
    raise NotImplementedError("Dependency not injected")


def get_group_service() -> GroupServicePort:
    raise NotImplementedError("Dependency not injected")


# 使用 Annotated 定義型別別名，徹底消除 B008 警告
OrderServiceDep = Annotated[OrderServicePort, Depends(get_order_service)]
PriceServiceDep = Annotated[PriceServicePort, Depends(get_price_service)]
GroupServiceDep = Annotated[GroupServicePort, Depends(get_group_service)]
OrderTypeQuery = Annotated[
    OrderType | None,
    Query(alias="type", description="掛單類型 buy / sell，不給則回傳全部"),
]


@router.get(
    "/users/{username}/orders",
    response_model=APIResponse[list[UserOrderDTO]],
    summary="查詢指定使用者的公開掛單列表",
)
async def get_user_orders(
    username: str,
    service: OrderServiceDep,
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
    service: OrderServiceDep,
    username: str | None = None,
    order_type: OrderTypeQuery = None,
):
    return await _list_user_orders(service, username, order_type)


async def _list_user_orders(
    service: OrderServicePort,
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


@router.get(
    "/items/{slug}/price",
    response_model=APIResponse[ItemPriceDTO],
    summary="查詢物品市價（最低賣價與最高收購價）",
    description="取自線上使用者的掛單，結果快取 5 分鐘。"
    "Mod 等可升級物品請帶 rank，否則賣價與收購價可能是不同等級。",
)
async def get_item_price(
    slug: str,
    service: PriceServiceDep,
    rank: Annotated[int | None, Query(ge=0, description="Mod 等級")] = None,
):
    try:
        price = await service.get_item_price(slug, rank)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e).strip("'\""),
        ) from e
    except (RuntimeError, OSError) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"第三方服務通訊異常: {e!s}",
        ) from e
    return APIResponse(
        code=200, message="success", data=ItemPriceDTO.from_domain(price)
    )


@router.get(
    "/groups",
    response_model=APIResponse[list[ItemGroupDTO]],
    summary="取得物品分組清單（商人、集團等）",
)
async def list_groups(service: GroupServiceDep):
    data = [ItemGroupDTO.from_domain(group) for group in service.list_groups()]
    return APIResponse(code=200, message="success", data=data)


@router.get(
    "/groups/{group_id}/items",
    response_model=APIResponse[list[MarketItemDTO]],
    summary="取得分組內的物品",
    description="只回傳存在於官方物品目錄中的物品。",
)
async def get_group_items(group_id: str, service: GroupServiceDep):
    try:
        items = service.get_group_items(group_id)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e).strip("'\""),
        ) from e
    data = [MarketItemDTO.from_domain(item) for item in items]
    return APIResponse(code=200, message="success", data=data)
