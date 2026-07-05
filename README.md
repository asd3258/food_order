# 訂餐統計 App

這是一套為團隊設計的午餐訂餐統計系統。後端使用 FastAPI + SQLAlchemy + PostgreSQL，前端採用 Vue3 + Vite + TypeScript 打造。

```text
food_order/
├── SPEC.md                     規格書
├── backend/                    FastAPI + SQLAlchemy + bcrypt
├── frontend/                   Vue3 + Vite + TypeScript
├── docker-compose.yml          正式部署用 (API + Postgres + MinIO + 前端靜態網站)
└── .env.example                環境變數範例檔
```

## 功能亮點與架構

1. **AI 菜單解析 (v0.9)**：上傳菜單照片，自動呼叫 Gemini / OpenAI 解析品項與價格。
2. **Google Places API 整合 (v0.10)**：貼上 Google Map 連結，自動帶入餐廳電話、地址與營業時間。
3. **MinIO 物件儲存 (v0.11)**：餐廳菜單照片與圖片統一集中管理，減少資料庫負擔。
4. **帳號與權限系統 (v0.16)**：完整的密碼驗證機制 (`bcrypt`)，支援綁定 Email 與「忘記密碼」SMTP 驗證碼發送。

---

## 本機開發 (Local Development)

### 後端 (Backend)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # 預設用 SQLite，不需要另外裝 Postgres
python -m app.seed        # 灌入預設測試資料 (餐廳與訂單)
uvicorn app.main:app --reload --port 58000
```
> 打開 http://localhost:58000/docs 可以看到自動產生的 Swagger API 文件。

### 前端 (Frontend)

```bash
cd frontend
npm install
cp .env.example .env       # VITE_API_BASE 預設指向 http://localhost:58000
npm run dev
```
> 打開 http://localhost:5173 即可瀏覽網頁。

---

## 部署到 x86 VM (正式環境部署)

專案使用 `docker-compose.yml` 統一管理服務，使用的連接埠分別為：API `58000`、前端 `55173`、Postgres `55432`、MinIO `59001`。

### 1. 準備環境與密碼設定

將專案 clone 或複製到伺服器後，務必先修改 `docker-compose.yml` 中的預設密碼：
- `POSTGRES_PASSWORD` 及 `DATABASE_URL` 裡的密碼。
- `MINIO_ROOT_PASSWORD` 及 API 環境變數裡的 `MINIO_SECRET_KEY`。

```bash
cd ~/food_order
cp .env.example .env
nano .env   # 填寫 API 金鑰與 SMTP 資訊 (詳見下方說明)
nano docker-compose.yml # 更改預設密碼
```

### 2. 啟動所有容器

```bash
docker compose build
docker compose up -d
```
> 第一次啟動時，`food_order_api` 容器會自動執行 `app.seed` 寫入初始資料（包含預設的 `admin` 帳號）。之後重啟不會重複灌入。

### 3. 確認服務狀態

```bash
docker compose ps
docker compose logs -f food_order_api
```
確認手機能連上之後，只需把 `http://<VM_IP>:55173` 貼到團隊群組即可開始使用！

---

## 進階功能設定 (.env)

專案有幾個強大的外部整合功能，您可以透過修改 `.env` (或 `docker-compose.yml`) 來啟用它們。

### A. 忘記密碼與 SMTP 寄信 (v0.16)
若要讓系統自動寄送「忘記密碼」的臨時 4 位數驗證碼，請設定您的 SMTP 伺服器 (以 Gmail 為例，請先申請「應用程式密碼」)：
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=您的信箱@gmail.com
SMTP_PASSWORD=您的應用程式密碼
```

### B. AI 菜單解析 (v0.9)
在建立餐廳時，上傳照片自動辨識品項。支援 Gemini 與 OpenAI，兩者擇一設定即可：
```env
# 優先使用 Gemini
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.5-flash

# 備援使用 OpenAI
OPENAI_API_KEY=sk-...
```

### C. Google Places API (v0.10)
輸入 Google Map 網址自動讀取電話與營業時間。需至 Google Cloud Console 啟用 `Places API (New)` 並綁定帳單：
```env
GOOGLE_MAPS_API_KEY=AIzaSy...
```

---

## 常用維運指令

```bash
# 看 API 即時日誌
docker compose logs -f food_order_api     

# 重新部署 (當拉取了新程式碼時)
git pull origin main
docker compose up -d --build

# 完全清空資料庫重來 (注意：資料會全部遺失！)
docker compose down -v
```

## 已知限制 / 尚未實作 (對應 SPEC)

- **自動結單**：截止時間到了目前不會自動結單，僅為顯示用途，需人工按下完成訂單。
- **權限與 Token**：目前的登入驗證會在首次輸入密碼後，由前端 `localStorage` 記住 `username` 作為後續操作的身分證明，後端尚未實作嚴格的 JWT Token 驗證機制。 (但在重要操作時已會檢查使用者身分與密碼)。
