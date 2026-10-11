# Warframe.Market v2 官方 API 實測紀錄

實測時間：2026 年 10 月，官方 `apiVersion` 為 `0.25.0`。官方 API 仍在演進，行為改變時請更新這份文件並重新錄製 fixtures（見 [testing.md](testing.md#重新錄製-fixtures)）。

- Base URL：`https://api.warframe.market/v2`
- 圖片前綴：`https://warframe.market/static/assets/`

## 共通

### 回應外殼

所有回應都包在同一個外殼：

```json
{ "apiVersion": "0.25.0", "data": { }, "error": null }
```

錯誤時 `data` 為 `null`，`error` 為物件，例如：

```json
{ "apiVersion": "0.25.0", "data": null, "error": { "request": ["app.user.notFound"] } }
```

| 情境 | HTTP | `error` |
|---|---|---|
| 使用者不存在 | 404 | `{"request": ["app.user.notFound"]}` |
| 物品不存在 | 404 | `{"request": ["app.item.notFound"]}` |
| 參數值不合法（例如 `rank=abc`） | 400 | `{"inputs": {"rank": "app.field.unsupportedValue"}}` |
| 需要登入（例如 `/me`） | 401 | |

本專案的 `WarframeMarketClient._get()` 會拆掉外殼只回傳 `data`，並把 404 轉成 `KeyError`、其他非 200 或 `error` 有值轉成 `RuntimeError`。

### Request headers

| header | 作用 |
|---|---|
| `language` | `i18n` 中**除了 `en` 以外**要回傳的語言，例如 `zh-hant`、`zh-hans` |
| `platform` | 平台，例如 `pc`；影響掛單範圍 |
| `crossplay` | `true` 時包含跨平台玩家的掛單 |

### Cloudflare

官方前面有 Cloudflare。一般的 Python HTTP 套件（requests、httpx）容易被擋，本專案使用 `curl_cffi` 的 `impersonate="chrome124"` 模擬 Chrome 的 TLS 指紋。

### 請求頻率限制

約每秒 3 個請求。本專案以 `RateLimiter` 讓連續請求至少間隔 `WF_MARKET_MIN_REQUEST_INTERVAL`（0.35 秒）。

## 端點

### `GET /versions`

各資料集的版本號，本專案用 `collections.items` 判斷物品目錄是否更新。

```json
{
  "collections": {
    "items": "MjAyNi0xMC0wOFQwMDo1MDo0OA==",
    "rivens": "…",
    "liches": "…"
  },
  "updatedAt": "2026-10-08T00:50:48Z"
}
```

版本號是 base64 編碼的時間（`MjAyNi0xMC0wOFQwMDo1MDo0OA==` 解碼為 `2026-10-08T00:50:48`），只需比對是否相同，不需解碼。

### `GET /items`

完整物品目錄，約 **3,900 筆**，一次回傳全部（沒有分頁）。

```json
{
  "id": "54c6855ee779891362942572",
  "slug": "primed_continuity",
  "gameRef": "/Lotus/Upgrades/Mods/Warframe/Expert/AvatarAbilityDurationModExpert",
  "tags": ["mod", "legendary", "warframe"],
  "maxRank": 10,
  "i18n": {
    "en": {
      "name": "Primed Continuity",
      "icon": "items/images/en/primed_continuity.01e1….webp",
      "thumb": "items/images/en/thumbs/primed_continuity.01e1….128x128.webp"
    },
    "zh-hant": { "name": "持久力 Prime", "icon": "…", "thumb": "…" }
  }
}
```

注意事項：
- **`i18n` 只有 `en` + `language` header 指定的一種語言**，要三語就要抓兩次再合併
- 圖片是**相對路徑**，要接上圖片前綴
- 新上架的物品 `thumb` 可能是**空字串**；本專案會轉成 `None` 並改用 `icon`
- 部分欄位只出現在特定物品：`maxRank`、`ducats`、`vaulted`、`bulkTradable`、`subtypes`
- `tags` 沒有商人或集團資訊；集團武器只有 `syndicate`，看不出是哪個集團（所以分組由本專案維護，見 [groups.md](groups.md)）

### `GET /item/{slug}`

單一物品詳情，比目錄多了 `rarity`、`tradingTax`、`description` 等欄位。本專案目前沒有使用。

### `GET /orders/user/{username}`

使用者的公開掛單（買單與賣單都有），不需登入。

```json
{
  "id": "6aafcdf39703a8846c9f576a",
  "type": "buy",
  "platinum": 5,
  "quantity": 1,
  "perTrade": 1,
  "visible": true,
  "createdAt": "2026-09-20T12:13:39Z",
  "updatedAt": "2026-09-24T19:03:35Z",
  "itemId": "69d67675b3984cc97e241750"
}
```

注意事項：
- **只有 `itemId`，沒有物品名稱與圖片**，必須對照 `/items` 目錄
- 買單與賣單混在一起，用 `type` 區分（舊版程式只保留賣單，造成只有收購單的帳號回傳空陣列）
- `rank`、`subtype` 只在相關物品出現

### `GET /orders/item/{slug}/top`

物品的最佳掛單，**只包含線上（`online` / `ingame`）使用者**。

```json
{ "sell": [ { "platinum": 40, "rank": 0, "user": { "status": "online" } } ], "buy": [ ] }
```

注意事項：
- 每邊最多 5 筆，賣單由低到高、收購單由高到低（本專案仍自行取 min / max，不依賴排序）
- 每筆附帶 `user` 物件（名稱、狀態等）
- **`rank` 查詢參數**可篩選 Mod 等級，例如 `?rank=10`；不分等級的物品會忽略這個參數
- **不帶 `rank` 時兩邊可能是不同等級**。實測 Primed Continuity：賣單最低 40（rank 0）、收購最高 100（rank 10）
- `rank` 不是整數時回 400

### `GET /me`

需要登入（401）。寫入類操作（改價、上下架）都需要登入，本專案尚未實作。

## 沒有提供的資料

| 想要的資料 | 狀況 | 本專案的做法 |
|---|---|---|
| 商人 / 集團分組 | 官方沒有 | `data/groups.json` + WFCD 資料，見 [groups.md](groups.md) |
| 掛單附物品名稱 | 只有 itemId | `CatalogService.resolve()` 對照目錄 |
| 三語名稱一次取得 | 一次只有一種中文 | 抓兩次合併 |
