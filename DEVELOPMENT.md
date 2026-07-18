# 系統開發紀錄與架構說明 (DEVELOPMENT.md)

本檔案用於記錄專案的開發進度、系統架構改動，以及開發除錯相關指引，以便直接於 Git 中追蹤。

---

## 🌟 最新功能與變更

### 1. 歷史訂單「已收款」機制升級為依品項獨立計算 (不連動)
- **資料庫變更**：在明細表 `order_history_lines` 新增 `is_paid` 欄位。自動資料遷移腳本已實作，系統啟動時會自動將舊資料的付款狀態對齊。
- **UI 調整**：
  - 前端「歷史訂單」的 Checkbox 不再連動，可針對特定使用者的特定品項單獨勾選。
  - 表頭資訊顯示由「已收款 X/Y 人」改為「已收款 X/Y 品項」。
  - 歷史明細表格與複製出的純文字均套用了排序要求：「人員 -> 品項 -> 數量 -> 價格」。
  - 複製出的收款狀態改為條列各品項的狀態（例如 `✅ Kris - 雞排 x1 ($100)`）。

### 2. 「訂餐」目前所有人統計排序與品項統計表格
- **UI 調整**：
  - 在點餐畫面中，「目前所有人統計(彙總)」表格內的所有人點餐明細已依照「人員 -> 品項/選項 -> 數量 -> 金額」進行排序。
  - 在該表格下方新增了一個「品項統計(總共 XX 個)」的統計表格，類似歷史訂單的統計模式，自動加總不含已刪除項目的相同品項數量。

### 3. 「管理使用者」次數計算方式修正
- **計算調整**：管理使用者列表中的點餐次數，由原先「明細列數加總」改為「一個歷史訂單只算一次」（計算 distinct 的 `order_history_id`），精確反映該使用者的訂單參與率。

### 4. 權限維護與參數維護返回按鈕
- **UI 調整**：在「權限維護」與「參數維護」頁面標頭的左側，加入了返回選單頁面 `/more` 的箭頭 `←` 連結。

---

## 📂 系統架構簡介

### 資料庫 (PostgreSQL)

目前系統已在 Docker 容器內整合 Postgres。資料表結構主要分為：
1. **使用者管理 (`users`)**
2. **餐廳與菜單 (`restaurants`, `menu_items`, `menu_item_options`)**
3. **即時訂單與投票 (`orders`, `order_items`, `vote_batches`, `vote_selections`)**
4. **歷史紀錄群 (`order_history`, `order_history_lines`, `order_history_payments`)**
   - 結單時，`orders` 與 `order_items` 會轉換並保存至 `order_history` 和 `order_history_lines` 做文字快照存檔。
   - `order_history_lines` 記錄了該次點餐的所有明細與其收款狀態 (`is_paid`)。

---

## 🔧 開發除錯與資料庫維護指引

### 1. 本地啟動命令
```bash
# 拉取最新代碼
git pull origin main

# 重建並啟動所有 Docker 容器
docker compose up -d --build
```

### 2. 如何直接連接並修改資料庫 (SQL)
由於系統目前使用 PostgreSQL 容器，您可以直接在主機上透過 `docker exec` 連入資料庫，對歷史訂單的資料進行更正：

```bash
# 進入 Postgres 容器中的 psql 工具
docker exec -it food_order_db psql -U food_order -d food_order
```

**常用的 SQL 修改操作：**

- **查詢最近的歷史訂單**
  ```sql
  SELECT id, restaurant_name, closed_date, total_amount FROM order_history ORDER BY id DESC LIMIT 5;
  ```

- **查詢某張歷史訂單下的所有品項明細 (假設 order_history_id 為 10)**
  ```sql
  SELECT id, "user", item_label, quantity, amount, is_paid FROM order_history_lines WHERE order_history_id = 10;
  ```

- **修改特定品項的點餐人、品項名或金額 (假設明細 id 為 42)**
  ```sql
  UPDATE order_history_lines
  SET "user" = '新名字',
      item_label = '新調整品項',
      amount = 150
  WHERE id = 42;
  ```

- **同步更新主表的總金額 (如果明細金額有變，假設總額需要增加 50 元)**
  ```sql
  UPDATE order_history
  SET total_amount = total_amount + 50
  WHERE id = 10;
  ```
