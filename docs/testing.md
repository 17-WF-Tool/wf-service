# 測試

## 執行

```powershell
pytest                                                    # 全部（不連網，約 1 秒）
pytest tests/unit/test_price_service.py                   # 單一檔案
pytest tests/unit/test_wfm_mapper.py::TestToOrder::test_maps_fields  # 單一測試
ruff check .                                              # lint
ruff format --check .                                     # 格式檢查；ruff format . 自動修正
```

設定在 `pyproject.toml`：
- `pythonpath = ["."]`：測試可以直接 `import main`、`import app`
- `asyncio_mode = "auto"`：`async def test_…` 不需要加 `@pytest.mark.asyncio`

## 測試結構

```
tests/
├── fixtures/            錄製的官方 API 回應（JSON）
├── support.py           共用工具：讀取 fixtures、假的 client、分組工具
├── conftest.py          pytest fixtures
├── unit/                單元測試：單一類別或函式
│   ├── test_domain.py
│   ├── test_wfm_mapper.py
│   ├── test_wf_market_client.py
│   ├── test_rate_limiter.py
│   ├── test_catalog_service.py
│   ├── test_order_service.py
│   ├── test_price_service.py
│   └── test_groups.py
└── api/                 API 測試：透過 TestClient 打 HTTP
    ├── test_orders_api.py
    ├── test_price_api.py
    ├── test_groups_api.py
    ├── test_lifespan.py
    └── test_routes.py
```

**所有測試都不連網**：client 測試替換掉 `curl_cffi` 的 `AsyncSession`，其他測試都使用 `FakeMarketClient`。

## Fixtures（錄製的官方回應）

| 檔案 | 內容 |
|---|---|
| `versions.json` | `/versions` |
| `user_orders.json` | `/orders/user/rrrrrrrrrrrrrrrrr_17`：17 筆，全部是收購單 |
| `error_user_not_found.json` | 不存在使用者的 404 回應 |
| `top_orders_primed_continuity.json` | `/orders/item/primed_continuity/top`，每邊只保留 3 筆，使用者資料只保留必要欄位 |
| `items_zh-hant.json`、`items_zh-hans.json` | `/items`，只保留使用者掛單用到的物品加上 `primed_continuity`、`vadarya_prime_blueprint`，共 18 筆 |

檔案保留完整的官方外殼 `{apiVersion, data, error}`。

### 重新錄製 fixtures

官方回應格式改變時：

```powershell
python scripts/record_fixtures.py                 # 預設使用者 rrrrrrrrrrrrrrrrr_17
python scripts/record_fixtures.py 其他使用者名稱
```

重新錄製後部分測試可能需要調整，例如寫死的物品名稱、價格與筆數。

## 測試工具（`tests/support.py`）

| 工具 | 用途 |
|---|---|
| `load_fixture(name)` | 讀取完整的官方回應外殼，每次回傳獨立的副本 |
| `load_data(name)` | 只讀取 `data` |
| `merged_raw_items()` | 合併繁中、簡中目錄的 `i18n`，模擬三語齊全的原始資料 |
| `FakeMarketClient` | 假的官方 client，見下方 |
| `make_group(id, *slugs)` | 快速建立 `ItemGroup` |
| `StaticGroupRepository(groups)` | 回傳固定分組的 repository |

### FakeMarketClient

```python
client = FakeMarketClient(
    user_orders=[...],                     # 覆寫 fetch_user_orders 的回傳
    top_orders={"sell": [...], "buy": [...]},
    items={"zh-hant": [...]},              # 依語言覆寫，沒指定的語言讀 fixtures
    errors={"fetch_top_orders": KeyError("…")},  # 呼叫時丟出這個例外
)

client.calls                         # [("fetch_top_orders", ("primed_continuity", 10)), …]
client.call_count("fetch_items")     # 呼叫次數，用來驗證快取
client.set_items_version("new")      # 模擬官方物品目錄更新
```

沒有覆寫的方法回傳 fixtures 的內容。

## pytest fixtures（`tests/conftest.py`）

| fixture | 說明 |
|---|---|
| `fake_client` | 一個新的 `FakeMarketClient` |
| `loaded_catalog` | 已載入 fixtures（18 筆）的 `CatalogService`。使用**獨立的** `FakeMarketClient`，所以不會出現在測試 client 的 `calls` 裡 |
| `make_service` | 建立 `OrderService` 的工廠：`make_service(client, default_username="", catalog=None)`，預設注入 `loaded_catalog` |
| `app_catalog` | 把 `main.catalog_service` 與 `main.group_service` 換成使用假 client 的版本，讓 app 啟動時的預熱**不會連網** |
| `api_client` | 進入 `TestClient(app)` 並回傳 `use_service()`，用來注入要測試的服務 |

### API 測試寫法

```python
def test_example(api_client, make_service):
    client = api_client(make_service())                    # 注入 OrderService
    client = api_client(price_service=PriceService(...))   # 注入 PriceService
    client = api_client(group_service=GroupService(...))   # 注入 GroupService
    client = api_client()                                  # 使用 main 組裝好的服務

    response = client.get("/api/v1/market/...")
```

測試結束後 `api_client` 會還原 `dependency_overrides`。

> ⚠️ **任何進入 `TestClient(app)` 的測試都必須使用 `app_catalog`**（`api_client` 已經依賴它）。否則 lifespan 會用真正的 client 預熱，測試會連到官方。

## 寫測試時的注意事項

### 時間相關的測試用假時鐘

`CatalogService`、`PriceService`、`RateLimiter` 都可以注入時鐘：

```python
class FakeClock:
    def __init__(self): self.now = 1000.0
    def __call__(self): return self.now
    def advance(self, seconds): self.now += seconds

PriceService(client, clock=clock, now=lambda: FIXED_NOW)
RateLimiter(0.5, clock=fake.clock, sleep=fake.sleep)
```

**不要用實際經過的時間來斷言**。Windows 的計時精度約 15 毫秒，`time.monotonic()` 量出來的時間可能比 `asyncio.sleep()` 的秒數還短，測試會時好時壞。

### `CatalogService` 是 falsy

`CatalogService` 實作了 `__len__`，**空的目錄會被當成 `False`**：

```python
catalog or default          # ❌ 空目錄會被換成 default
catalog if catalog is not None else default   # ✅
```

### 浮點數比較用 `pytest.approx`

```python
assert fake.sleeps == [pytest.approx(0.3)]   # 0.5 - 0.2 = 0.29999999999999716
```

### 路由清單測試

`tests/api/test_routes.py` 從 OpenAPI schema 列出所有路由並與預期清單比對。**新增或移除 API 時要同步更新**。

FastAPI 0.141 會把 `include_router` 進來的路由包在 `_IncludedRouter` 中，`app.routes` 看不到，所以改用 `app.openapi()["paths"]`。

## 連官方的手動驗證

自動測試不連網。要確認與真實官方 API 的整合時，可以：

```powershell
python main.py
```

然後用 `api.http` 或 Swagger 實際呼叫。

> ⚠️ 若以 UTF-8 模式執行 Python（設定了 `PYTHONUTF8=1`，或使用 `python -X utf8`），連官方會出現 **curl 錯誤 77**（讀不到 CA 憑證）：專案路徑含中文時，curl 無法讀取 certifi 的憑證檔。改用一般模式執行即可；要在終端機印出中文，可以用 `sys.stdout.reconfigure(encoding="utf-8")`。

## CI

`.github/workflows/ci.yml` 在 push 到 `main` 與 PR 時執行：

| job | 內容 |
|---|---|
| Secret Scanning | gitleaks 掃描密鑰 |
| Dependency Audit | `pip-audit -r requirements.txt` |
| Code Style | `ruff check .`、`ruff format --check .` |
| Tests | `pytest` |
| CodeQL | 靜態安全分析 |
| Build & Smoke | `python -c "import main"`（等前三項通過後執行） |

只改動 `README.md`、`docs/**`、`.vscode/**` 時**不會觸發 CI**（`paths-ignore`）。
