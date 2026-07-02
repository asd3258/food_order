# 訂餐統計 App — 開發者說明

對應 `SPEC.md` / `SPEC-english.md`(v0.5)與 `wireframe.html` 線框稿的正式實作。

```
food_order/
├── SPEC.md / SPEC-english.md   規格書
├── wireframe.html              純前端線框稿(無需安裝任何東西,雙擊即可在瀏覽器打開)
├── backend/                    FastAPI + SQLAlchemy
├── frontend/                   Vue3 + Vite + TypeScript
└── docker-compose.yml          正式部署用(API + Postgres + 前端靜態網站)
```

## ⚠️ 這次開發環境的限制(請先讀)

我(Claude)這次是在一個**沒有對外網路存取權限**的沙箱裡寫程式,`pip install` / `npm install`
都連不到 PyPI / npm registry(連線會被 proxy 擋掉、回 403)。所以我**沒有辦法在這個環境裡
實際跑起來、按真正的按鈕做端對端測試**——所有檢查都只做到:

- Python 檔案:用 `ast.parse` 逐檔做語法檢查(全部通過)
- Vue 檔案:檢查 `<template>`/`<script>` 標籤是否成對(全部通過)
- 手動覆閱程式邏輯是否對應 `SPEC.md` 第 3~6 節的規則

也就是說程式碼**沒有經過真正安裝依賴、啟動伺服器的驗證**,第一次在你自己的電腦或 x86 VM
上跑起來時,有機會遇到一些小 bug(型別、拼字、少 import 之類)。這是正常的,把錯誤訊息貼給我
我可以馬上修。

## 本機開發(在你自己的電腦上,需要網路)

### 後端

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # 預設用 SQLite,不需要另外裝 Postgres
python -m app.seed        # 灌入跟 wireframe.html 一樣的測試資料(6 家餐廳、1 筆開單中訂單、1 筆歷史訂單)
uvicorn app.main:app --reload --port 58000
```

> 埠號用 `58000` 而不是 `8000`,是因為你的 x86 VM 上 `sit-web` 這個容器已經佔用了 8000
> (`docker ps` 可以看到)。本機開發跟 VM 部署統一用 58000,之後比較不會搞混。如果你是在
> 自己的筆電上跑(不是這台 VM),8000 沒被佔用的話當然也可以用,但記得下面前端的
> `VITE_API_BASE` 要對得起來。

打開 http://localhost:58000/docs 可以看到自動產生的 Swagger API 文件,直接在網頁上測試每個 API。

### 前端

```bash
cd frontend
npm install
cp .env.example .env       # VITE_API_BASE 預設指向 http://localhost:58000
npm run dev
```

打開 http://localhost:5173,手機請用同一個 Wi-Fi 網段,把網址換成你電腦的區網 IP(例如
`http://192.168.1.50:5173`)即可用手機瀏覽器開啟測試。

## 部署到 x86 VM(mike1-virtual-machine)— 完整步驟

沿用你現有 `sit_web_system` 的 Docker Compose 模式,用獨立的容器名稱/連接埠,不會跟既有的
`sit-web`(8000)/`sit-db`(5433)/`st_app`(8501)/`gitea`(3000,222)/`jenkins-myjk`(8080,50000)
衝突。這個 stack 用的埠是:API `58000`、前端 `55173`、Postgres `55432`。

### 1. 把程式碼傳到 VM 上

在你自己電腦(或 VM 上有 git 的話直接在 VM 執行 clone/pull)。以 `scp` 為例:

```bash
# 在你的電腦上執行,把整個 food_order 資料夾傳到 VM 的家目錄
scp -r food_order root@mike1-virtual-machine:~/food_order
```

如果 `food_order` 已經放進 Gitea 或其他 git repo,改成在 VM 上 `git clone`/`git pull` 也可以,效果一樣。

### 2. 登入 VM,確認埠沒被佔用

```bash
ssh root@mike1-virtual-machine
cd ~/food_order
docker ps --format "table {{.Names}}\t{{.Ports}}"   # 確認 58000 / 55173 / 55432 沒有出現在既有容器上
```

### 3. 修改 Postgres 密碼(部署前必做)

`docker-compose.yml` 裡的密碼目前是佔位的 `food_order`/`food_order`,有兩處都要改成一樣的新密碼
(`food_order_db` 服務的 `POSTGRES_PASSWORD`,以及 `food_order_api` 服務的 `DATABASE_URL` 裡的密碼段):

```bash
nano docker-compose.yml
```

也可以用 `sed` 一次改兩處(把 `CHANGE_ME_STRONG_PW` 換成你真正要用的密碼):

```bash
sed -i 's/food_order:food_order@/food_order:CHANGE_ME_STRONG_PW@/; s/POSTGRES_PASSWORD: food_order/POSTGRES_PASSWORD: CHANGE_ME_STRONG_PW/' docker-compose.yml
```

### 4. Build 並啟動所有容器

```bash
docker compose build
docker compose up -d
```

第一次 `up` 時,`food_order_api` 容器會自動跑 `python -m app.seed` 灌測試資料(6 家餐廳、
1 筆開單中訂單、1 筆歷史訂單),之後每次重啟因為資料庫已經有資料,seed 腳本會自動跳過,不會
重複灌資料。

### 5. 確認都跑起來了

```bash
docker compose ps
docker compose logs -f food_order_api      # Ctrl+C 離開;確認看到 "Application startup complete"
docker compose logs -f food_order_web
```

```bash
curl http://localhost:58000/api/health          # 應該回 {"status":"ok"}
curl -I http://localhost:55173                  # 應該回 200 OK
```

### 6. 如果有防火牆,開放連接埠

```bash
sudo ufw status                        # 先看有沒有啟用
sudo ufw allow 58000/tcp
sudo ufw allow 55173/tcp
```

### 7. 從手機/PC 實際連線測試

```bash
hostname -I     # 在 VM 上查區網 IP,例如 192.168.1.23
```

用手機瀏覽器開 `http://192.168.1.23:55173`(或 `http://mike1-virtual-machine:55173`,如果你的
區網有做好內部 DNS/hosts 解析),應該會看到跟 wireframe.html 一樣的畫面,但資料是真的從
FastAPI + Postgres 讀出來的。

### 8. 把連結分享到 Teams

確認手機能連上之後,把 `http://mike1-virtual-machine:55173`(內網;之後接 Tailscale 的話換成
Tailscale 網址)貼到 Teams 的「蘆竹訂餐團」聊天室,就是最終使用方式——不需要 Teams App 上架。

### 之後要改程式碼、重新部署時

```bash
cd ~/food_order
git pull                              # 或重新 scp 覆蓋
docker compose up -d --build          # 只會重 build 有變動的服務
```

### 常用維運指令

```bash
docker compose logs -f food_order_api     # 看 API 即時 log
docker compose restart food_order_api     # 只重啟 API,不動資料庫
docker compose down                       # 全部停掉(資料庫資料還在 volume 裡,不會消失)
docker compose down -v                    # 連資料庫資料一起清空,重新開始用
```

### AI 菜單解析設定(建立新餐廳 →「上傳菜單照片,AI 自動解析品項」,v0.9)

這個功能會把你上傳的菜單照片送給 Gemini(優先)或 ChatGPT(備援)幫忙辨識品項/價格/口味選項,
自動填進「品項清單」讓你檢查修正,不用手動一個一個打。兩個服務只要設定一個 API 金鑰就能用,
設定兩個的話 Gemini 失敗時會自動切到 ChatGPT。

**取得 Gemini API 金鑰(免費,推薦先設這個):**

1. 用你的 Google 帳號打開 https://aistudio.google.com/apikey
2. 點「Create API key」,選一個 Google Cloud 專案(沒有的話它會幫你建一個)
3. 複製產生的金鑰(長得像 `AIza...`)
4. 免費額度:Flash 系列模型每天 1500 次請求、每分鐘 15 次——17 人團隊偶爾上傳菜單照片綽綽有餘,
   不需要綁信用卡

**取得 OpenAI API 金鑰(備援用,選填):**

1. 打開 https://platform.openai.com/api-keys,登入後點「Create new secret key」
2. 複製金鑰(長得像 `sk-...`)——OpenAI 需要先在帳戶裡設定付款方式才能呼叫 API

**設定到專案裡:**
<<<<<<< HEAD
Windows11上傳
```bash
# 1. 切換回主分支，並確保同步雲端最新的程式碼
git checkout main
git pull origin main

# 2. 建立並同時切換到新的改版分支
git checkout -b feature/ai-api

# 改版過程中，可以多次重複以下提交步驟：
git add .
git commit -m "feat: 完成重大改版的第一階段核心功能"

# 3. 第一次將這個新分支推送到 GitHub（加上 -u 建立遠端追蹤）
git push -u origin feature/ai-api
```


Ubuntu下載
```bash
# 1. 進入 Ubuntu 的專案目錄
cd ~/food_order

# 2. 更新env
cp .env.example .env
nano .env   # 填入 GEMINI_API_KEY=... (Gemini 2.0 Flash 已停用,改用 2.5)

# 3. 強制同步 GitHub 上的最新分支資訊
git fetch origin

# 4. 切換到改版分支
git checkout feature/ai-api

# 5. 讓 Docker Compose 針對新分支重新 build Image 並部署
docker compose up -d --build
=======

```bash
cd ~/food_order
cp .env.example .env
nano .env        # 把 GEMINI_API_KEY=... 和/或 OPENAI_API_KEY=... 填進去,存檔離開
>>>>>>> 47bb1a2edf343bce08cf09234a4b4a967a489034
```

`.env` 已經加進 `.gitignore`,不會被 commit 上去,金鑰只留在這台 VM 上。

**套用設定(不需要 `down -v`,這次沒有動到資料庫結構):**

```bash
docker compose up -d --build food_order_api
```

**測試:** 到「其他功能 → 建立餐廳」畫面,點「上傳菜單照片,AI 自動解析品項」旁的「上傳照片」,
選一張菜單照片,等幾秒(vision AI 辨識比一般文字慢),應該會看到品項清單被自動填入。如果兩個
金鑰都沒設或都失敗,會跳出錯誤訊息,不影響手動輸入品項。

<<<<<<< HEAD
### Google Places API 設定(建立/編輯餐廳 →「從 Google Map 讀取電話/地址/營業時間」,v0.10)

這個功能是貼上 Google Map 連結後,自動把電話、地址、營業時間讀出來填進表單。**這是跟上面
Gemini/ChatGPT 完全不同的 Google 服務**,需要另外設定,而且**一定要先在帳戶裡綁信用卡才能用**
(即使正常用量大概率落在每月 $200 免費額度內、不會真的被扣款)。

**設定步驟:**

1. 打開 https://console.cloud.google.com/,建立一個新專案(或沿用申請 Gemini 時建立的專案)
2. 左上「☰ → 帳單」,確認這個專案已經綁定信用卡(第一次用 Cloud Console 通常會要求設定)
3. 左上「☰ → API 和服務 → 已啟用的 API 和服務 → + 啟用 API 和服務」,搜尋「Places API (New)」,
   點進去按「啟用」
4. 左邊「憑證」→「+ 建立憑證」→「API 金鑰」,複製產生的金鑰
5. **強烈建議**點剛建立好的金鑰進去設定「API 限制」,只勾選「Places API (New)」——避免這支金鑰
   被盜用後拿去打其他 Google API 燒錢
6. 填進 `.env` 的 `GOOGLE_MAPS_API_KEY=`,存檔後:
   ```bash
   docker compose up -d --build food_order_api
   ```

**費用:** 讀「電話+地址」約 $5/1000 次,一旦加上「營業時間」會跳到 Pro 等級約 $17/1000 次
(這個功能一次會把三項一起讀,所以都算 Pro 等級)。17 人團隊偶爾新增/編輯餐廳,一個月用不到
幾十次,幾乎不可能超過 Google Maps Platform 每月 $200 的免費額度。

**已知限制:** 沒有上傳菜單照片時,不會自動去 Google Map 抓菜單照片來跑 AI 解析——Google 官方
Places API 不提供「菜單分類 + 依日期排序」的照片篩選,只能抓到一般照片(無法確定是不是菜單、
也無法篩選最新),真要做到那樣只能靠非官方第三方爬蟲服務,考量費用/穩定性/服務條款風險後決定
不做,想生成菜單品項還是要手動上傳一張菜單照片。

Stashed changes
=======
>>>>>>> 47bb1a2edf343bce08cf09234a4b4a967a489034
### 之後接 Tailscale

`docker-compose.yml` 裡前端的 `VITE_API_BASE` 是在 build time 就烤進靜態檔案裡的(Vite 的
環境變數規則),目前指到 `http://mike1-virtual-machine:58000`。接了 Tailscale 之後,把這行
改成 Tailscale 幫這台機器配的 MagicDNS 名稱(例如 `http://mike1-vm.tailxxxx.ts.net:58000`),
存檔後跑:

```bash
docker compose build food_order_web
docker compose up -d food_order_web
```

讓手機在公司外面也連得到。

## 已知簡化 / 尚未做的事(對應 SPEC.md 第 8 節)

- 沒有真正的登入,`username` 是前端自己記在 `localStorage` 的文字欄位,所有「僅發起者可操作」
  的檢查都是後端用字串比對 `initiator == acting_user`,不是真正的權限系統——換裝置會變成新身分。
- 截止時間到了不會自動開票/結單,純顯示用。
<<<<<<< HEAD
Updated upstream
- 建立餐廳的 AI 解析菜單(Phase 2)、Google Maps 生成菜單(Phase 3)都還沒做,維持 wireframe 的
  disabled 提示卡片。

- 建立餐廳的 AI 解析菜單(v0.9)、Google Map 讀取電話/地址/營業時間(v0.10)都已完成,見上方
  對應章節。「串接 Uber Eats/foodpanda 生成菜單」已直接移除,沒有計畫做。
Stashed changes
=======
- 建立餐廳的 AI 解析菜單(v0.9 已完成,見上方「AI 菜單解析設定」)。Google Maps 生成菜單
  (Phase 3)、串接 Uber Eats/foodpanda 還沒做,維持 wireframe 的 disabled 提示卡片。
>>>>>>> 47bb1a2edf343bce08cf09234a4b4a967a489034
- 餐廳照片上傳目前直接把 `data:` URL 存進資料庫的 `TEXT` 欄位(跟線框稿行為一致,方便先跑起來),
  正式量產建議改成物件儲存(S3-compatible)+ 存網址,否則圖片一多資料庫會變得很肥。
