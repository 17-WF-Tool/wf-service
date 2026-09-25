# Warframe.Service 核心服務 (Backend)

基於 Python + FastAPI 開發的《Warframe》多功能後端核心平台。採用六角架構（Hexagonal Architecture）設計，主要用於對接《Warframe.Market》v2 官方介面，提供其他專案的前端需求。

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
* **網路通訊**：curl-cffi & HTTPX
* **測試與代碼品質**：Pytest & Ruff
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