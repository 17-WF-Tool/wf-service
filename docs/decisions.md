# 設計決策紀錄

記錄「為什麼這樣做」。想修改這些設計之前，先看當初的理由與取捨；推翻某個決策時，請更新該筆紀錄而不是直接刪除。

括號內為相關的 issue 編號。

## 目錄

- [D1. 以官方 v2 API 為核心，前端跟隨後端](#d1-以官方-v2-api-為核心前端跟隨後端)
- [D2. Client 只取資料，不做業務過濾](#d2-client-只取資料不做業務過濾)
- [D3. 錯誤以例外類型區分](#d3-錯誤以例外類型區分)
- [D4. 路徑參數完整編碼](#d4-路徑參數完整編碼)
- [D5. 用 curl_cffi 模擬瀏覽器](#d5-用-curl_cffi-模擬瀏覽器)
- [D6. 物品目錄放記憶體，以版本號判斷是否更新](#d6-物品目錄放記憶體以版本號判斷是否更新)
- [D7. 啟動時同步預熱](#d7-啟動時同步預熱)
- [D8. 查不到物品時不讓請求失敗](#d8-查不到物品時不讓請求失敗)
- [D9. 對外欄位使用 snake_case，語意對應官方](#d9-對外欄位使用-snake_case語意對應官方)
- [D10. /users/{username}/orders 與 /me/orders 並存](#d10-usersusernameorders-與-meorders-並存)
- [D11. 每筆報價附上自己的 rank](#d11-每筆報價附上自己的-rank)
- [D12. 市價快取以 (slug, rank) 為單位，錯誤不快取](#d12-市價快取以-slug-rank-為單位錯誤不快取)
- [D13. 限速放在 client，所有請求共用](#d13-限速放在-client所有請求共用)
- [D14. 分組由後端維護](#d14-分組由後端維護)
- [D15. 分組資料以 WFCD 產生，固定版本](#d15-分組資料以-wfcd-產生固定版本)
- [D16. 依分組列物品使用 /groups/{group_id}/items](#d16-依分組列物品使用-groupsgroup_iditems)
- [D17. 移除記憶體假資料，ItemService 更名為 OrderService](#d17-移除記憶體假資料itemservice-更名為-orderservice)
- [D18. 測試使用錄製的官方回應](#d18-測試使用錄製的官方回應)
- [D19. 文件放在 repo 的 docs/，不使用 Wiki](#d19-文件放在-repo-的-docs不使用-wiki)

---

## D1. 以官方 v2 API 為核心，前端跟隨後端

- **背景**：早期後端只有 `/me/orders` 真的串接官方，其餘是寫死的假資料，前後端各自定義資料格式且不一致。
- **決定**：資料結構以 WFM v2 官方 API 為核心；後端預計給多個前端共用，因此 **API 格式由後端決定，前端跟隨**。
- **理由**：多個前端各自定義格式會讓後端被迫配合每一個；以官方為核心，欄位語意清楚、不必自創概念。

## D2. Client 只取資料，不做業務過濾

- **背景**：舊版 client 在取得使用者掛單時只保留賣單，只有收購單的帳號因此回傳空陣列。（#4）
- **決定**：`MarketClientPort` 的實作只回傳官方 `data` 的原始內容；篩選、合併、補資料都在 service 層。
- **理由**：過濾屬於業務規則，放在 client 會被所有呼叫者繼承，而且很難察覺。client 保持單純也比較好測試。

## D3. 錯誤以例外類型區分

- **決定**：client 找不到資源丟 `KeyError`、其他失敗丟 `RuntimeError`；router 統一轉成 404 / 502，`ValueError` 轉 400。
- **理由**：service 與 router 不需要知道 HTTP 狀態碼或官方的錯誤格式；換掉 client 實作也不影響上層。
- **取捨**：`KeyError` 的 `str()` 會帶引號，router 需要 `strip("'\"")`。

## D4. 路徑參數完整編碼

- **背景**：使用者名稱、slug 直接拼進官方網址。
- **決定**：使用 `quote(segment, safe="")`，連 `/` 也編碼。（#6）
- **理由**：`quote()` 預設不編碼 `/`，輸入 `a/../b` 會改變實際請求的路徑。

## D5. 用 curl_cffi 模擬瀏覽器

- **決定**：使用 `curl_cffi` 的 `AsyncSession(impersonate="chrome124")`。
- **理由**：官方前面有 Cloudflare，一般 HTTP 套件的 TLS 指紋容易被擋。

## D6. 物品目錄放記憶體，以版本號判斷是否更新

- **背景**：使用者掛單只有 `itemId`，需要對照約 3,900 筆的物品目錄才知道名稱與圖片。（#7）
- **決定**：
  - 啟動時下載完整目錄放在記憶體，以 itemId、slug 建索引
  - 定期查 `/versions` 的 `collections.items`，**版本變了才重新下載**
  - 繁中、簡中各下載一次再合併成三語
  - 以 `asyncio.Lock` 讓同時間只有一個更新；更新失敗保留舊資料；一次替換整個索引
- **理由**：每個請求都去查官方太慢也會撞到頻率限制；目錄約 3,900 筆，放記憶體沒有負擔。版本號讓定期檢查只花一個小請求。
- **取捨**：多個後端實例各自有一份目錄；重啟後要重新下載。

## D7. 啟動時同步預熱

- **決定**：lifespan 中 `await catalog_service.warm_up()`，預熱完成才開始接受請求；預熱失敗只記錄錯誤，不讓後端啟動失敗。（#7）
- **理由**：第一個請求就查得到物品名稱；官方暫時異常也不該讓後端起不來。
- **取捨**：啟動多約 3～4 秒，官方很慢時最久等到逾時。若之後更在意啟動速度，可以改成背景預熱，代價是剛啟動時查不到物品名稱。

## D8. 查不到物品時不讓請求失敗

- **決定**：
  - `resolve(item_id)` 查不到時，在冷卻時間（300 秒）外觸發一次版本檢查；**先記錄時間再更新**，避免同時多個請求都觸發
  - 仍查不到時，掛單的 `item` 只帶 `id`，其他欄位為 `null`
  - 格式異常的單筆物品或掛單略過並記錄，不影響整份資料
- **理由**：新物品上架時本地目錄可能還沒更新；少一筆物品名稱不該讓整個掛單列表失敗。冷卻時間防止有人一直查不存在的 id 而不斷打官方。（#8）

## D9. 對外欄位使用 snake_case，語意對應官方

- **決定**：欄位名稱沿用官方語意（`platinum`、`quantity`、`rank`、`visible`、`per_trade`），命名轉成 snake_case；回應包在 `APIResponse{code, message, data}`。
- **理由**：與 Python 程式碼風格一致；語意對應官方，不必再對照一套自訂名詞。
- **取捨**：#8 改格式時，舊欄位（`order_id`、`name_en`、`order_type`、`is_visible`、`mod_rank`）屬於破壞性變更；當時前端沒有使用這支 API，所以沒有保留相容性。

## D10. /users/{username}/orders 與 /me/orders 並存

- **決定**：`/users/{username}/orders` 是查詢任何人的正式路由；`/me/orders` 保留，目前用 `username` 參數或 `DEFAULT_WF_USERNAME`。（#8）
- **理由**：`/me` 的語意是「登入者本人」，等登入功能完成後再改成真正的「我」；先不刪除，避免之後又要改前端的呼叫。

## D11. 每筆報價附上自己的 rank

- **背景**：官方 `/orders/item/{slug}/top` 不帶 `rank` 時會混用不同等級的掛單。實測 Primed Continuity：賣單最低 40（rank 0）、收購最高 100（rank 10），看起來像「收購價比賣價還高」。（#9）
- **決定**：`lowest_sell`、`highest_buy` 都附上該筆掛單的 `rank`；API 支援 `rank` 參數。
- **理由**：只回數字會誤導；附上 rank 讓前端能判斷兩邊等級是否一致，並決定是否帶 rank 重查。

## D12. 市價快取以 (slug, rank) 為單位，錯誤不快取

- **決定**：
  - 快取 key 為 `(slug 轉小寫, rank)`，預設 5 分鐘
  - 每個 key 一把 `asyncio.Lock`，同一物品同時多個查詢只打一次官方；用完沒人等待時移除這把鎖
  - 寫入快取時順便清除過期項目
  - 錯誤（找不到物品、官方異常）不快取
- **理由**：價格變動不需要即時到秒；前端批次顯示時常會同時查同一物品。清除過期項目避免任意 slug、rank 組合讓記憶體無限增加。錯誤快取會讓暫時性的官方異常持續 5 分鐘。
- **取捨**：路徑使用 `/api/v1/market/items/{slug}/price`（issue 草稿原本寫 `/api/v1/items/...`），以和其他 API 共用前綴。

## D13. 限速放在 client，所有請求共用

- **決定**：`WarframeMarketClient._get()` 發送前先 `await RateLimiter.wait()`，連續請求至少間隔 0.35 秒；main 只建立一個 client，所以目錄、掛單、市價共用同一個限速器。（#9）
- **理由**：官方限制約每秒 3 次。放在 client 才能涵蓋所有呼叫者，service 不需要各自處理。
- **取捨**：啟動預熱多約 0.7 秒；大量查詢不同物品時會排隊（實測 5 個物品約 1.9 秒）。限速器只控制「發出」間隔，不會等前一個回應，所以官方慢不會讓排隊更久。

## D14. 分組由後端維護

- **背景**：官方沒有商人或集團的分組；前端原本在 mock 資料中自己定義分組。（#10）
- **決定**：分組資料放在後端的 `data/groups.json`，透過 API 提供；前端只負責顯示與個人偏好（排序、收合、勾選）。
- **理由**：
  - 多個前端共用同一份分組，不必各自維護
  - 分組是資料不是畫面，和物品目錄同一類
  - 只有後端拿得到完整目錄，能在啟動時檢查 slug 是否正確
  - 前端拿到的物品已附三語名稱與圖片，可以移除 WFCD 圖示對照表
- **未來**：使用者自訂分組屬於個人資料，短期可放前端 localStorage，有登入後再存後端。

## D15. 分組資料以 WFCD 產生，固定版本

- **決定**：集團與追隨者分組由 `scripts/build_groups.py` 依 WFCD 的 `drops.location` 產生，以英文名稱對應 WFM slug；Baro Ki'Teer 手動維護。WFCD 固定在 `1.1276.3`。（#10）
- **理由**：
  - 官方 `tags` 只有 `syndicate`，看不出哪個集團；不憑記憶填寫，避免錯誤
  - WFCD `1.1276.19` 起部分物品缺少 `drops`，產生結果全部是 0 筆
  - Baro 商品輪替，沒有可靠的資料來源
- **其他**：
  - 集團中文名稱取自 WFCD 翻譯中的集團浮印名稱（官方譯名）
  - 早期 mock 的「鋼鐵之路（Teshin）」分組中的 Primary Merciless 等賦能，WFCD 顯示為鋼鐵之路追隨者（Angst、Malice 等）掉落，不是 Teshin 商店販售，所以分組命名為「鋼鐵之路追隨者」；此譯名未經驗證

## D16. 依分組列物品使用 /groups/{group_id}/items

- **背景**：issue 原本規劃 `/items?group=xxx`，但當時 `/items` 被舊的 mock `GET /items?category=` 佔用。（#10）
- **決定**：使用 `/groups/{group_id}/items`。
- **現況**：#11 移除 mock 後 `/items` 已空出，但 `/groups/{group_id}/items` 已能滿足需求，是否另外提供 `/items?group=` 等前端串接時再評估。

## D17. 移除記憶體假資料，ItemService 更名為 OrderService

- **決定**：刪除 `InMemoryItemRepository`、舊的 `Item` 模型與 `GET /items?category=`、`PATCH /items/{id}/price`、`PATCH /items/{id}/visibility`。（#11）
- **理由**：
  - 假資料只改記憶體、不寫回官方，容易讓人誤以為功能已完成
  - 改價與上下架之後會改為操作官方掛單，需要登入，屬於另一組 issue
  - 刪除後服務只剩查詢掛單，原名稱 `ItemService` 與用途不符

## D18. 測試使用錄製的官方回應

- **決定**：以 `scripts/record_fixtures.py` 錄製官方回應到 `tests/fixtures/`；測試全部不連網，以 `FakeMarketClient` 取代真正的 client。（#6）
- **理由**：測試快速、穩定，CI 不依賴官方是否正常；fixtures 是真實資料，比手寫的假資料更能反映官方格式。
- **取捨**：官方格式改變時測試不會發現，需要手動重新錄製與連官方驗證。

## D19. 文件放在 repo 的 docs/，不使用 Wiki

- **決定**：系統說明放在 `docs/`，流程圖使用 Mermaid。（#20）
- **理由**：GitHub Wiki 是獨立的 repo，改程式時容易忘記更新；放在 `docs/` 可以和程式碼在同一個 PR 更新與 review，checkout 舊版本也能看到當時的文件。GitHub 會直接渲染 Mermaid。
