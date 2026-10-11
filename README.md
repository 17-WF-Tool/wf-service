# Warframe.Service 核心服務 (Backend)

基於 Python + FastAPI 開發的《Warframe》多功能後端核心平台。採用六角架構（Hexagonal Architecture）設計，主要用於對接《Warframe.Market》v2 官方介面，提供其他專案的前端需求。

> 📖 架構、流程圖、API 說明與設計決策請見 [docs/](docs/README.md)。

## 核心特性

* **六角架構解耦**：嚴格劃分領域層（Domain）、連接埠（Ports）、應用層（Application）與適配器（Adapters），業務邏輯完全獨立於 Web 框架。
* **Cloudflare 防禦穿透**：整合 `curl_cffi` 模擬真實 Chrome 瀏覽器 TLS 指紋，避免直接請求官方 API 時遭遇阻擋或驗證碼攔截。
* **零依賴配置設計**：不強制綁定外部 `.env` 設定檔，支援純 Python 常數配置與動態 Query 參數傳入。
* **非同步高效能**：全面採用 `async/await` 非同步處理，支援內建快取與預熱機制，降低對外請求頻率並加速接口回應。
* **自動化 CI 流程**：整合 GitHub Actions，推送程式碼自動執行 Ruff 語法檢查、排版風格校驗與 Pytest 單元測試。

## 技術棧

* **核心框架**：FastAPI
  > 高效能、自動生成 OpenAPI (Swagger) 文件的非同步 Web 框架。
* **ASGI 伺服器**：Uvicorn
* **資料驗證**：Pydantic v2
* **網路通訊**：curl-cffi（模擬瀏覽器 TLS 指紋）
* **測試與代碼品質**：Pytest、pytest-asyncio、httpx2（TestClient）& Ruff
* **開發語言**：Python 3.11+

## 快速開始

### 1. 建立並啟用虛擬環境

```powershell
# 建立虛擬環境
python -m venv .venv

# 啟用虛擬環境
.\.venv\Scripts\Activate.ps1
```

### 2. 安裝套件

> 確認終端機提示字元最前方已出現`.venv`

```powershell
pip install -r requirements-dev.txt
```

### 3. 啟動後端服務

```powershell
python main.py
```

### 4. 服務資料

- Swagger UI 介面：http://127.0.0.1:8000/docs
- ReDoc 說明文件：http://127.0.0.1:8000/redoc

### 5. 執行測試

測試使用 `tests/fixtures/` 中錄製的官方回應，不需連網。

```powershell
# 執行全部測試
pytest

# 執行單一檔案或單一測試
pytest tests/unit/test_wfm_mapper.py
pytest tests/unit/test_wfm_mapper.py::TestToOrder::test_maps_fields

# 官方回應格式變動時，重新錄製 fixtures
python scripts/record_fixtures.py
```

`api.http` 收錄官方 API 與本專案 API 的請求範例，可搭配 VS Code 的 REST Client 擴充套件使用。

### 6. 物品分組資料

官方沒有商人或集團的分組，分組資料由本專案維護於 `data/groups.json`：

- `source: manual`：手動維護，例如會輪替商品的 Baro Ki'Teer，直接編輯 slug 清單
- `source: wfcd`：六大集團與鋼鐵之路追隨者，由腳本依 WFCD 物品資料產生

```powershell
# 重新產生自動分組，手動分組會原樣保留
python scripts/build_groups.py
```

後端啟動時會檢查分組中的 slug 是否都存在於官方物品目錄，不存在的會記錄警告。
