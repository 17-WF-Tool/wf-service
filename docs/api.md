# API 說明

- Base URL：`http://127.0.0.1:8000`
- 業務 API 前綴：`/api/v1/market`
- 互動式文件：啟動後開啟 `/docs`（Swagger UI）或 `/redoc`
- 請求範例：`api.http`（VS Code REST Client）

## 共通格式

### 成功回應

所有業務 API 都包在 `APIResponse` 中：

```json
{
  "code": 200,
  "message": "success",
  "data": "…各 API 的資料…"
}
```

### 錯誤回應

錯誤由 FastAPI 的 `HTTPException` 產生，格式為：

```json
{ "detail": "找不到 Warframe.market 使用者: ghost" }
```

| 狀態碼 | 意義 |
|---|---|
| 400 | 請求缺少必要資訊（例如沒有使用者名稱） |
| 404 | 官方找不到使用者或物品、找不到分組 |
| 422 | 參數格式錯誤（FastAPI 驗證），`detail` 為驗證錯誤清單 |
| 502 | 官方 API 異常：非 200、連線失敗、回應不是 JSON。`detail` 以「第三方服務通訊異常:」開頭 |
| 500 | 未預期的錯誤 |

### 欄位命名

對外一律 **snake_case**（官方是 camelCase，例如 `perTrade` → `per_trade`）。時間為 ISO 8601（UTC，結尾 `Z`）。

### 共用物件：三語名稱 `names`

```json
{ "en": "Primed Continuity", "zh_hant": "持久力 Prime", "zh_hans": "持久力 Prime" }
```

`zh_hant`、`zh_hans` 可能為 `null`（官方缺少該語言時）。

---

## 健康檢查

### `GET /`

```json
{ "status": "ok", "app": "Warframe Market Controller Backend" }
```

不包 `APIResponse`。

---

## 使用者掛單

### `GET /api/v1/market/users/{username}/orders`

查詢任何使用者的**公開**掛單（不需登入），並附上物品資訊。

| 參數 | 位置 | 必填 | 說明 |
|---|---|---|---|
| `username` | path | ✅ | WFM 使用者名稱（前後空白會去除） |
| `type` | query | | `buy` 或 `sell`，不給則回傳全部；其他值回 422 |

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": "6aafcdf39703a8846c9f576a",
      "type": "buy",
      "platinum": 5,
      "quantity": 1,
      "per_trade": 1,
      "rank": null,
      "subtype": null,
      "visible": true,
      "created_at": "2026-09-20T12:13:39Z",
      "updated_at": "2026-09-24T19:03:35Z",
      "item": {
        "id": "69d67675b3984cc97e241750",
        "slug": "voruna_prime_systems_blueprint",
        "names": {
          "en": "Voruna Prime Systems Blueprint",
          "zh_hant": "Voruna Prime 系統 藍圖",
          "zh_hans": "Voruna Prime 系统 蓝图"
        },
        "image": "https://warframe.market/static/assets/items/images/en/thumbs/voruna_prime_systems_blueprint.6a82ab2971991cfa9ff8b92df7ed8547.128x128.webp",
        "tags": ["component", "warframe", "prime", "blueprint"]
      }
    }
  ]
}
```

| 欄位 | 說明 |
|---|---|
| `rank` | Mod / 賦能的等級，不分等級的物品為 `null` |
| `subtype` | 物品子類型（例如遺物的精煉程度），沒有子類型的物品為 `null` |
| `visible` | 是否公開顯示 |
| `item` | 物品目錄**查不到**時只有 `id`，其他欄位為 `null` 或 `[]`，請求本身不會失敗 |

| 錯誤 | 狀態碼 |
|---|---|
| 使用者不存在 | 404：`找不到 Warframe.market 使用者: {username}` |
| `type` 不是 buy / sell | 422 |
| 官方異常 | 502 |

### `GET /api/v1/market/me/orders`

與上面相同的回應。差別在使用者名稱的來源：

| 參數 | 位置 | 說明 |
|---|---|---|
| `username` | query | 可選；不給時使用 config 的 `DEFAULT_WF_USERNAME` |
| `type` | query | 同上 |

兩者都沒有時回 **400**：`未指定使用者名稱，請於 config 設定或以參數傳入 username`。

> `/me` 預留給登入功能：完成後會改為查詢登入者本人。查詢其他人請用 `/users/{username}/orders`。

---

## 市價

### `GET /api/v1/market/items/{slug}/price`

取自官方 `/orders/item/{slug}/top`（線上使用者的掛單），回傳最低賣價與最高收購價。結果**快取 5 分鐘**。

| 參數 | 位置 | 必填 | 說明 |
|---|---|---|---|
| `slug` | path | ✅ | 物品 slug，例如 `primed_continuity`（不分大小寫） |
| `rank` | query | | Mod 等級，需為 0 以上的整數，否則回 422 |

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "slug": "primed_continuity",
    "rank": 10,
    "lowest_sell": { "platinum": 100, "rank": 10 },
    "highest_buy": { "platinum": 100, "rank": 10 },
    "updated_at": "2026-10-11T15:05:38.825331Z"
  }
}
```

| 欄位 | 說明 |
|---|---|
| `rank` | 查詢條件（沒帶就是 `null`） |
| `lowest_sell` / `highest_buy` | 沒有線上賣單或收購單時為 `null` |
| `lowest_sell.rank` / `highest_buy.rank` | **該筆報價本身**的等級 |
| `updated_at` | 向官方取得資料的時間；快取命中時是當初取得的時間 |

> ⚠️ **Mod 請帶 `rank`。** 不帶時，官方會混用不同等級的掛單，例如 Primed Continuity 可能得到「賣 40（rank 0）／收 100（rank 10）」。前端可以比對兩邊報價的 `rank` 判斷是否一致。

| 錯誤 | 狀態碼 |
|---|---|
| 物品不存在 | 404：`找不到 Warframe.market 物品: {slug}` |
| `rank` 不是 0 以上的整數 | 422 |
| 官方異常 | 502 |

---

## 物品分組

### `GET /api/v1/market/groups`

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": "steel_meridian",
      "names": { "en": "Steel Meridian", "zh_hant": "鋼鐵防線", "zh_hans": "钢铁防线" },
      "item_count": 81
    }
  ]
}
```

- 依 `data/groups.json` 的定義順序排列
- `item_count` 是分組中定義的 slug 數量（不代表全部都存在於物品目錄）

### `GET /api/v1/market/groups/{group_id}/items`

```json
{
  "code": 200,
  "message": "success",
  "data": [
    {
      "id": "…",
      "slug": "vaykor_marelok",
      "names": { "en": "Vaykor Marelok", "zh_hant": "勇氣 瑪瑞火槍", "zh_hans": "…" },
      "image": "https://warframe.market/static/assets/…",
      "tags": ["syndicate", "weapon", "secondary"],
      "max_rank": null
    }
  ]
}
```

- 依分組中 slug 的順序回傳
- 只回傳存在於物品目錄的物品；目錄未載入時為空陣列
- 不會呼叫官方 API

| 錯誤 | 狀態碼 |
|---|---|
| 分組不存在 | 404：`找不到分組: {group_id}` |

目前的分組見 [groups.md](groups.md)。

---

## 目前沒有的功能

- **寫入類 API**（改價、上下架、新增掛單）：需要 WFM 帳號登入，尚未實作
- **物品目錄搜尋**（例如 `/items?group=`、`/items?tag=`）：目前以 `/groups/{group_id}/items` 依分組列出物品
