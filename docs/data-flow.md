# 資料流程

## 啟動流程

```mermaid
sequenceDiagram
    autonumber
    participant U as uvicorn
    participant L as lifespan (main.py)
    participant CAT as CatalogService
    participant GS as GroupService
    participant WFM as 官方 API

    U->>L: 啟動
    L->>CAT: warm_up()
    CAT->>WFM: GET /versions
    CAT->>WFM: GET /items（language: zh-hant）
    CAT->>WFM: GET /items（language: zh-hans）
    CAT-->>L: 載入約 3,900 筆（失敗只記錄錯誤）
    L->>GS: find_unknown_slugs()
    GS-->>L: 不存在的 slug 記錄警告
    L->>CAT: start_periodic_refresh()
    Note over CAT: 背景工作：每 3600 秒檢查一次版本
    L-->>U: yield，開始接受請求
    U->>L: 關閉
    L->>CAT: stop_periodic_refresh()
```

- 預熱需要 3 個請求（含限速）約 3～4 秒。預熱完成**之後**才開始接受請求，所以第一個請求就查得到物品
- 官方很慢時，最久要等到逾時（每個請求 15 秒）
- 預熱失敗（官方掛掉、網路不通）不會讓後端啟動失敗：物品目錄是空的，等下一次定期檢查或第一次「查不到物品」時再重試

## 物品目錄更新

`CatalogService.refresh(force=False)`，以 `asyncio.Lock` 確保同一時間只有一個更新在執行。

```mermaid
flowchart TD
    A["refresh()"] --> L["取得 asyncio.Lock<br/>（同時只有一個更新）"]
    L --> V["GET /versions<br/>取 collections.items"]
    V --> C{"已載入 且 版本相同<br/>且 非 force？"}
    C -->|是| S["略過下載<br/>回傳 False"]
    C -->|否| H["GET /items<br/>language: zh-hant"]
    H --> HS["GET /items<br/>language: zh-hans"]
    HS --> MG["依 id 合併 i18n<br/>→ en + zh-hant + zh-hans"]
    MG --> MAP["to_market_item()<br/>格式錯誤的那筆略過並記錄"]
    MAP --> SW["一次替換兩個索引<br/>_items_by_id、_items_by_slug"]
    SW --> T["回傳 True"]

    V -.失敗.-> E["丟 KeyError / RuntimeError<br/>舊資料不受影響"]
    H -.失敗.-> E
    HS -.失敗.-> E
```

**為什麼要下載兩次：** 官方 `/items` 的 `i18n` 只會回傳 `en` 加上 `language` header 指定的那一種語言，所以繁中、簡中要各抓一次再合併。

**觸發時機：**

| 觸發 | 方式 | 失敗時 |
|---|---|---|
| 啟動 | `warm_up()` → `refresh(force=True)` | 記錄錯誤，後端照常啟動 |
| 定期 | 背景工作每 `CATALOG_REFRESH_INTERVAL` 秒呼叫 `refresh()` | 記錄錯誤，下一輪繼續 |
| 查不到物品 | `resolve(item_id)`，見下一節 | 記錄警告，回傳 `None` |

## 用 itemId 查物品（resolve）

官方的使用者掛單只有 `itemId`，新物品上架時本地目錄可能還沒有，所以查不到時會嘗試更新一次。

```mermaid
flowchart TD
    A["resolve(item_id)"] --> B{"目錄中有？"}
    B -->|有| R1["直接回傳<br/>（不打官方）"]
    B -->|沒有| C{"距上次因查不到而更新<br/>超過冷卻時間 300 秒？"}
    C -->|否| R2["回傳 None"]
    C -->|是| D["先記錄這次的時間"]
    D --> E["refresh()<br/>版本有變才下載"]
    E --> F{"再查一次"}
    F -->|有| R3["回傳物品"]
    F -->|沒有| R2
    E -.失敗.-> W["記錄警告"] --> R2
```

**先記錄時間再更新**，是為了讓同時進來的多個「查不到」請求只觸發一次更新：第一個請求記下時間後，其餘請求在冷卻檢查時就會直接回傳 `None`。

## 查詢使用者掛單

`GET /api/v1/market/users/{username}/orders?type=buy`（`/me/orders` 走同一段處理）

```mermaid
sequenceDiagram
    autonumber
    participant FE as 前端
    participant R as router
    participant OS as OrderService
    participant CL as WarframeMarketClient
    participant CAT as CatalogService
    participant WFM as 官方 API

    FE->>R: GET /users/{username}/orders?type=buy
    R->>OS: get_user_orders(username, BUY)
    alt 沒有 username 且 config 沒有預設值
        OS-->>R: ValueError → 400
    end
    OS->>CL: fetch_user_orders(username)
    CL->>WFM: GET /orders/user/{username}
    alt 使用者不存在
        WFM-->>CL: 404
        CL-->>R: KeyError → 404
    end
    WFM-->>CL: 掛單（只有 itemId）
    CL-->>OS: 原始資料（不過濾買賣）
    OS->>OS: to_orders()：格式錯誤的略過
    OS->>OS: 依 type 篩選
    loop 每一筆掛單
        OS->>CAT: resolve(itemId)
        CAT-->>OS: MarketItem 或 None
    end
    OS-->>R: list[OrderListing]
    R-->>FE: UserOrderDTO（item 只有 id 表示目錄查不到）
```

## 查詢市價

`GET /api/v1/market/items/{slug}/price?rank=10`

```mermaid
flowchart TD
    A["get_item_price(slug, rank)"] --> K["key = (slug 轉小寫, rank)"]
    K --> C1{"快取中且未過期？"}
    C1 -->|是| R1["回傳快取"]
    C1 -->|否| L["取得這個 key 的 Lock"]
    L --> C2{"再查一次快取<br/>（等鎖期間可能已有結果）"}
    C2 -->|有| R1
    C2 -->|沒有| F["fetch_top_orders(slug, rank)<br/>經過限速器"]
    F --> T["to_orders()<br/>sell 取最低價、buy 取最高價"]
    T --> S["寫入快取<br/>順便清除過期項目"]
    S --> R2["回傳 ItemPrice"]
    F -.KeyError / RuntimeError.-> X["不快取，往上丟<br/>→ 404 / 502"]
    R1 --> U["釋放後若沒人在等<br/>移除這把 Lock"]
    R2 --> U
```

- 快取以 `(slug, rank)` 為單位：`rank=None`、`rank=0`、`rank=10` 是三筆不同的快取
- **同一個 key 同時有多個請求**時，只有第一個會打官方，其餘等鎖後直接拿到快取結果
- 不同物品之間不互相等待，但都會經過同一個限速器排隊
- 錯誤不快取，下一次查詢會重新打官方

## 請求限速

所有連到官方的請求都經過 `WarframeMarketClient._get()`，第一步就是 `await RateLimiter.wait()`。

```mermaid
sequenceDiagram
    participant A as 請求 A
    participant B as 請求 B
    participant C as 請求 C
    participant RL as RateLimiter（間隔 0.35 秒）
    participant WFM as 官方 API

    A->>RL: wait()
    RL-->>A: 立即通過（t=0）
    A->>WFM: GET
    B->>RL: wait()
    Note over RL: 排隊，等到 t=0.35
    RL-->>B: 通過
    B->>WFM: GET
    C->>RL: wait()
    Note over RL: 排隊，等到 t=0.70
    RL-->>C: 通過
    C->>WFM: GET
```

限速器只限制「發出請求的時間間隔」，不會等前一個請求回應完成，所以官方回應慢時不會拖累後面的請求排隊。

## 查詢分組物品

`GET /api/v1/market/groups/{group_id}/items`

```mermaid
flowchart LR
    A["get_group_items(group_id)"] --> B{"分組存在？"}
    B -->|否| E["KeyError → 404"]
    B -->|是| C["依 groups.json 中的 slug 順序"]
    C --> D["catalog.get_by_slug(slug)<br/>只查記憶體，不打官方"]
    D --> F["略過目錄中沒有的 slug"]
    F --> G["回傳 list[MarketItem]"]
```

分組查詢**完全不會打官方**，所以很快；但若啟動時預熱失敗、目錄是空的，分組會回傳空陣列，直到目錄載入成功。
