# Team Group-Order Tally App — Product Spec (v0.5 Draft)

> **Version history**
> - v0.2: Bottom nav changed to Home / Restaurant List / Restaurant Vote / More; Restaurant List became a read-only menu browser; the old "voting restaurants" section and "open order now / start a vote" action were merged into one "Restaurant Vote" page; Order History and Create Restaurant moved under a "More" hub; a "Person" column was added to the aggregate stats table and to order history; a Phase 3 item was added to Create Restaurant (AI menu generation from a Google Maps URL).
> - v0.3: The bottom-nav tab "Restaurant Vote" was renamed to "Order & Vote"; "Currently voting" moved back to the Home screen as cards (same pattern as "Active orders"); starting a vote (multi-select) now requires a deadline; added a new "Vote Detail" page where the initiator can "Tally" (auto-create an order from the winning restaurant) or "Delete" the vote; the Order Detail page gained initiator-only "Close order" / "Delete" buttons and a Google Maps link; the read-only restaurant menu page gained a photo carousel, restaurant info (address/phone), and a Google Maps link; added this English spec file (`SPEC-english.md`) alongside the Chinese original for easier AI/automation consumption.
> - v0.4: The four buttons "Close Order," "Delete" (order), "Tally," and "Delete" (vote) now open a Yes/No confirmation dialog on tap — the action only runs if the user picks Yes; No just closes the dialog. Deadlines are simplified to "time of day only" (no date): the UI is two dropdowns, an hour (0–23, 24-hour format) and a minute restricted to 5-minute steps (00/05/…/55), defaulting to "current time + 10 minutes" whenever a new order or vote is created. Vote Detail now displays its deadline, and the initiator can edit it inline. Orders gained the same deadline feature end-to-end (set at creation using the same picker, shown on the Home card and in Order Detail, editable by the initiator; an order created by tallying a vote inherits that vote's deadline). The order initiator can now soft-delete another participant's order line from Order Detail — it stays visible with strikethrough styling rather than disappearing, and is excluded from the aggregate totals and from Order History once the order is closed.
> - **v0.5 (this update)**:
>   1. Order History gains "payment tracking" — closing an order auto-generates a per-person payment list; the initiator can expand a history card and check off who has paid.
>   2. Deadlines get the full date back — the UI is now a native date picker (calendar) plus the existing hour/minute dropdowns, instead of "time of day only."
>   3. Restaurants gain a "Restaurant Type" field (Meal Box / Drinks / Steak / Pasta, single-select); the `category` field on MenuItem is **removed** — menus are now flat lists, no longer grouped by category.
>   4. Restaurant List and Order & Vote pages gain a search box, filtering by restaurant name or item name.
>   5. Restaurant List and Order & Vote pages gain restaurant-type filter chips (Meal Box / Drinks / Steak / Pasta, toggleable, combinable with search).
>   6. A new "Edit Restaurant" screen (reached from the read-only menu page's "✏️ Edit Restaurant" button) supports editing name/phone/address/type/items and uploading or deleting photos.

## 1. Background & Goals

**Current state**: Someone posts a photo of the restaurant menu in a Teams group chat. Everyone else replies with free-text messages describing what they want. There is no way to tally this automatically — someone has to read every message by eye.

**Goal**: Build a standalone web app (designed mobile-first, later expanded to desktop via responsive breakpoints). The link is shared directly in the Teams chat — no Teams Tab app registration/manifest, no SSO required. Core flow:

1. Decide which restaurant to order from today (either pick one directly, or run a group vote with a deadline; search and restaurant-type filters help find a restaurant quickly)
2. When the vote deadline passes (or the initiator taps "Tally" early), the restaurant with the most votes automatically becomes an order
3. Once an order is open, each person selects menu items plus customizations (flavor/quantity, similar to Uber Eats / foodpanda)
4. The system automatically aggregates item counts and totals per person, for the initiator to use when placing the real order with the restaurant; the initiator can close or delete the order
5. Once closed, the order moves to history, where the initiator can mark each person's payment status
6. Closed orders are kept in history for later lookup and re-ordering

**Scope of this deliverable**: spec + clickable wireframe prototype only. No real front-end/back-end integration yet.

**Confirmed technical direction**:
- Frontend: React or Vue (mobile-first, later expanded to responsive layouts via CSS breakpoints)
- Backend: FastAPI (Python)
- Deployment: standalone web page, link shared in the Teams chat (no Teams Tab / app manifest)
- User identity: for now, a freely-editable text field simulating the Teams display name; Teams SSO can be added later if needed
- AI menu parsing for "Create Restaurant" / integration with Google Maps, Uber Eats, foodpanda: **Phase 2/3 — manual entry only in this stage**
  - Phase 2: upload a menu photo → AI OCR + parsing generates menu items
  - Phase 3: paste a Google Maps URL → AI reads the place's public info to draft a menu
  - Under evaluation (high risk, not a commitment): integrating the Uber Eats / foodpanda API to auto-generate a menu — neither platform currently exposes a public third-party API for reading an arbitrary restaurant's menu. Needs confirmation of an official partnership channel before committing; otherwise this item is likely infeasible.

---

## 2. Information Architecture (Sitemap)

The bottom navigation has 4 fixed tabs: **Home / Restaurant List / Order & Vote / More**.

```
Home
├─ Username field (editable + Save button, lives in the top header, not part of the bottom nav)
├─ Active Orders (card list, tap to open the order's ordering screen)
└─ Currently Voting (card list, same visual pattern as above, tap to open Vote Detail)
     Example card:
       Vote 1   Restaurant A / Restaurant B / Restaurant C
       Initiator: Mike Chen   Deadline: 2026/07/02 11:00   ← full date restored in v0.5

Restaurant List — read-only browsing
├─ Search box (filter by restaurant name or item name, new in v0.5)
├─ Restaurant-type filter chips (Meal Box / Drinks / Steak / Pasta, toggleable, new in v0.5)
├─ Restaurant name cards (reflecting the current search/filter)
└─ Tap → opens that restaurant's read-only menu page:
     ├─ Flat item table: Item name / Flavor / Add-ons / Price (v0.5: no longer grouped by category)
     ├─ "✏️ Edit Restaurant" button (new in v0.5) → opens the Edit Restaurant screen
     ├─ Photo carousel (swipe left/right, or tap the arrow buttons)
     ├─ Restaurant info (address, phone, restaurant type)
     └─ Google Maps link

Edit Restaurant — new in v0.5
├─ Restaurant info form: name, phone, address, restaurant type (dropdown)
├─ Photo management: thumbnail grid of existing photos; "Upload photo" opens a local file picker with instant preview; each photo has a per-item "Delete" (confirmed first)
├─ Item list: edit existing items' name/price inline, or add/remove item rows
└─ "Save changes" writes the draft back and returns to the read-only menu page; the back arrow discards the draft instead

Order & Vote page
├─ Search box (filter by restaurant name or item name, new in v0.5)
├─ Restaurant-type filter chips (Meal Box / Drinks / Steak / Pasta, toggleable, new in v0.5)
├─ Select restaurants (checkboxes, reflecting the current search/filter)
└─ A "Deadline" control (v0.5: full date restored — a native date picker plus the existing hour (24-hour) and minute (5-minute steps) dropdowns, defaulting to "now + 10 minutes")
     ├─ Select exactly 1 → button reads "Open Order Now" → creates an Order (with the full deadline) immediately and opens its ordering screen
     └─ Select 2+ → button reads "Start a Vote" → creates a new vote batch (with the full deadline), then returns to Home where it appears under "Currently Voting"

Vote Detail ← opened from a "Currently Voting" card on Home
├─ Shows the deadline (full date as of v0.5); if the current user is the initiator, it's shown as a date picker plus hour/minute dropdowns instead of plain text
├─ Single-select list of candidate restaurants + Save/Edit (any participant can vote, same Save/Edit semantics as before)
└─ If the current user is the vote's initiator, two extra buttons appear, **both gated by a Yes/No confirmation dialog — the action only runs if the user picks Yes**:
     ├─ "Tally" (on Yes) → finds the candidate with the most locked votes (same rule as picking a single restaurant), creates an Order from it (reuses the "Open Order Now" order-creation logic, carrying over this vote's deadline), removes the vote, and opens the new order's screen
     └─ "Delete" (on Yes) → deletes the vote batch outright, no order is created, returns to Home

Order Detail / Ordering screen ← opened from an "Active Orders" card, or automatically after "Open Order Now" / a vote's "Tally"
├─ Shows the deadline (full date as of v0.5); if the current user is the initiator, it's shown as a date picker plus hour/minute dropdowns instead of plain text
├─ If the current user is the order's initiator, two extra buttons appear at the top, **both gated by a Yes/No confirmation dialog**:
│    ├─ "Close Order" (on Yes) → writes the current aggregate stats (as an itemized summary, excluding any soft-deleted lines) plus a per-person payment list into Order History, then removes the order from the active list
│    └─ "Delete" (on Yes) → removes the order from the active list without writing anything to history
├─ Restaurant's menu items list (v0.5: a flat list — MenuItem no longer has a category field)
├─ Tapping an item opens a bottom-sheet modal (flavor + quantity, Uber-Eats-style) → "Add to my order"
├─ "My Order" section uses an eye-catching accent color/background so a user can quickly find their own items in a long list
├─ "Everyone's current totals" aggregate table: Item / Options, Person, Quantity, Amount — the initiator can soft-delete another person's line here (Yes/No confirmation first); the line stays visible with strikethrough styling and is excluded from totals/history
└─ A Google Maps link at the bottom of the page

More — navigation hub
├─ Order History
│   └─ Past orders (read-only), itemized by Item / Person / Quantity / Amount, plus per-person payment checkboxes (new in v0.5)
└─ Create Restaurant
    ├─ Manual entry: restaurant info (with a "Restaurant Type" field, new in v0.5) + item list (items no longer have a category field, v0.5)
    ├─ [Phase 2] Upload a menu photo → AI parsing
    ├─ [Phase 3] Paste a Google Maps URL → AI-generated menu
    └─ [Under evaluation] Integrate the Uber Eats / foodpanda API to generate a menu
```

---

## 3. Data Model (Draft)

| Entity | Fields | Notes |
|---|---|---|
| **User** | `id`, `display_name`, `teams_name_raw` (seeded value), `updated_at` | No real login yet; `user_id` is kept in localStorage, paired with an editable display-name field |
| **Restaurant** | `id`, `name`, `phone`, `address`, `map_url`, `type` (new in v0.5: Meal Box / Drinks / Steak / Pasta, single-select), `created_by`, `created_at`, `updated_at` (new in v0.5) | Base info shown on the Restaurant List; `type` powers the type-filter chips on both the browse and search/select pages |
| **RestaurantPhoto** | `id`, `restaurant_id`, `image_url` (v0.5: photos uploaded via the Edit Restaurant screen are stored as a data URL / file-storage URL), `caption`, `sort_order` | Powers the photo carousel on the read-only menu page. New in v0.3; editable (add/remove) via Edit Restaurant as of v0.5 |
| **MenuItem** | `id`, `restaurant_id`, `name`, `price`, `is_active` | e.g. "Grilled Beef Rice." **v0.5: the `category` field is removed** — menus render as a flat list, no longer grouped |
| **MenuItemOption** | `id`, `menu_item_id`, `option_group` (e.g. "Flavor"), `option_type` (`radio`/`checkbox`), `option_name` (e.g. "Original / Thai style"), `extra_price` | Customization choices. On the read-only menu page, options collapse into two display columns based on `option_type`: `radio` → Flavor column, `checkbox` → Add-ons column |
| **VoteBatch** | `id`, `initiator_user_id`, `deadline_at` (v0.5: now a full date+time, see note below), `status` (`open`/`decided`/`deleted`), `created_at` | One voting round. New standalone entity in v0.3 (replaces the earlier single "current vote" object); backs the "Currently Voting" cards on Home |
| **VoteBatchCandidate** | `vote_batch_id`, `restaurant_id` | The candidate restaurants selected when the vote was started |
| **Vote** | `id`, `vote_batch_id`, `user_id`, `restaurant_id` (the candidate chosen), `status` (`draft`/`locked`), `created_at`, `locked_at` | One user's choice within one vote batch; `status=locked` corresponds to pressing Save |
| **Order** | `id`, `restaurant_id`, `initiator_user_id`, `source_vote_batch_id` (nullable), `deadline_at` (v0.5: now a full date+time), `status` (`open`/`closed`/`deleted`), `created_at`, `closed_at` | The entity behind "Active Orders"; if created via a vote's Tally action, records which vote batch it came from and inherits that batch's `deadline_at` as its initial value |
| **OrderItem** | `id`, `order_id`, `user_id`, `menu_item_id`, `selected_options` (JSON), `quantity`, `note`, `is_deleted` (new in v0.4, default false), `deleted_by_user_id` (new in v0.4, nullable), `created_at` | One line item a person added to an order. `is_deleted=true` means the initiator soft-deleted it — the frontend still shows the original content with strikethrough styling, but it's excluded from stats/closing |
| **OrderHistory** | `id`, `order_id`, `restaurant_name`, `initiator`, `closed_date`, `people_count`, `total_amount` | The read-only summary record generated when an order closes (backs the history cards) |
| **OrderHistoryLine** | `id`, `order_history_id`, `item_label`, `user`, `quantity`, `amount` | An itemized row shown when a history card is expanded (item/person/quantity/amount) |
| **OrderHistoryPayment** (new in v0.5) | `id`, `order_history_id`, `user`, `total_amount`, `is_paid` (default false), `paid_at` (nullable) | One row per person, auto-generated at close time from that person's total; only the original initiator of that history entry can toggle `is_paid` |

**Deadline rule (v0.5 restores the full date)**:
- Stores a full date+time: `deadline_at` (year-month-day hour:minute)
- The UI splits into three inputs: a native date picker (`<input type="date">`, i.e. a calendar control) + an hour dropdown (0–23, 24-hour) + a minute dropdown (restricted to 00/05/10/…/55, 5-minute steps)
- When creating an order or vote, the date defaults to "today" and the hour/minute default to "current time + 10 minutes" (minute rounded to the nearest 5-minute step)
- For now the deadline is purely informational/a reminder — there is no scheduled job that auto-triggers a tally or auto-close when the deadline passes (see Section 8)
- v0.4 had simplified this to "time of day only, no date"; v0.5 restores the full date per the latest requirements — rationale and trade-offs are noted as resolved in Section 8, item 5

**Restaurant Type rule (new in v0.5)**:
- A fixed set of four values: Meal Box / Drinks / Steak / Pasta, single-select, required when creating or editing a restaurant
- Powers the type-filter chips on both the Restaurant List and the Order & Vote page (toggleable — at most one type active at a time, combined with the search box via AND)
- Currently a fixed list hardcoded on the frontend, not yet a manageable backend taxonomy — see the open question in Section 8

**Search / filter rule (new in v0.5)**:
- The search box matches against "restaurant name" OR "any of that restaurant's item names," case-insensitive substring matching (no tokenization or fuzzy matching needed)
- The search box and type filter chips combine via AND; the two pages (Restaurant List, Order & Vote) each keep their own independent search text and filter state — they don't affect each other

**Aggregation logic**:
- Order stats = `SUM(OrderItem.quantity) WHERE is_deleted=false` grouped by `menu_item_id` + `selected_options` + `user_id`; amount = `(price + extra_price)` accumulated per line; the person is shown alongside each row. Rows where `is_deleted=true` still appear on the live "Everyone's current totals" screen (rendered with strikethrough) but are excluded from the order-closing aggregate and from Order History
- Vote stats = `COUNT(Vote WHERE vote_batch_id=? AND status='locked')` grouped by `restaurant_id`; `draft` (unsaved) selections are excluded so people who are still undecided aren't counted
- Tally rule (v0.3): pick the `restaurant_id` with the highest current `locked` vote count; ties are broken by candidate list order (first one wins) — a deliberate simplification; see the open question in Section 8 about whether a more explicit tie-break rule is needed
- Payment aggregation (new in v0.5): at close time, `OrderHistoryLine.amount` is summed grouped by `user` to produce one `OrderHistoryPayment` row per person (`is_paid=false` initially); the initiator later toggles this manually — the system does no automatic reconciliation or payment-gateway integration

---

## 4. Page Specifications

### 4.1 Home

| Section | Behavior |
|---|---|
| Username field | On load, attempts to seed the Teams display name (standard approach: the shared link carries a `?name=` query string, filled in once by whoever shares the link or by the user themself); freely editable, with a "Save" button on the right that persists to localStorage + the backend `User` record |
| Active Orders | Lists orders with `status='open'`, shown as "Order N, Initiator: XXX" plus a deadline (full date as of v0.5, e.g. `2026/07/02 12:30`); shows "No orders right now" when empty; tapping a card opens that order's ordering screen (4.4) |
| Currently Voting | Lists `VoteBatch` rows with `status='open'`, card format: "Vote N   Restaurant A/Restaurant B/Restaurant C" + "Initiator: XXX   Deadline: YYYY/MM/DD HH:mm"; shows "No votes right now" when empty; tapping a card opens Vote Detail (4.3) |

### 4.2 Order & Vote Page

This is the *only* entry point for creating a new order or a new vote (the selection logic that used to live on "Restaurant List" has moved here; Restaurant List is read-only browsing only — see 4.5).

**Search and type filter (new in v0.5)**
- A search box at the top filters the checkbox list below in real time by restaurant name or item name
- Below it, 4 type-filter chips (Meal Box/Drinks/Steak/Pasta) toggle on/off and combine with the search box via AND
- Restaurants that are already checked **stay checked even if a filter hides them** (filtering only affects what's displayed, not the selected set) — so changing a search term or filter never silently drops an already-selected restaurant

**Select restaurants (checkboxes) + deadline (full date restored in v0.5)**
- The page permanently shows one "Deadline" control: a date picker (native calendar) + an hour dropdown (0–23, 24-hour) + a minute dropdown (00/05/10/…/55, 5-minute steps); on entering the page the date defaults to "today" and the hour/minute default to "current time + 10 minutes"
- Select exactly **1** → button reads "Open Order Now"; tapping it immediately creates `Order(status='open', deadline_at=current picker value)` and opens its ordering screen (4.4)
- Select **2 or more** → button reads "Start a Vote"; tapping it creates a `VoteBatch(status='open', deadline_at=current picker value)` plus its `VoteBatchCandidate` rows, clears the selection, and returns to Home, where the new vote now appears under "Currently Voting"
- A deadline is required in both cases — but since the controls always have a default value, there's no separate "empty field" validation needed

### 4.3 Vote Detail

- Title shows "Vote N"
- **Deadline** (full date as of v0.5):
  - Regular participants: plain text "Deadline YYYY/MM/DD HH:mm"
  - If the current user is the initiator: a date picker plus hour/minute dropdowns (pre-filled with the current `deadline_at`) plus an "Update" button that overwrites `VoteBatch.deadline_at` directly
- A single-select list of candidate restaurants with live vote counts, using the same Save/Edit semantics as before:
  - **Save**: locks in the current choice (the options grey out and become unselectable), writes `Vote(status='locked')`
  - **Edit**: un-greys the options so the user can change their pick, but does **not** immediately overwrite the saved backend record — the user must press Save again for the new choice to take effect
  - Acceptance note: if the user presses Edit and then abandons the page without pressing Save again, the system must keep the *previous* Save result
- **If the current user is this vote's initiator**, two additional buttons appear, **both gated by a Yes/No confirmation dialog — the underlying action only fires if the user picks Yes; picking No just closes the dialog and does nothing**:
  - **Tally** (fires on Yes): applies the tie-break rule from Section 3 to find the candidate with the most votes right now, creates an `Order` from it (reusing the same order-creation logic as "Open Order Now", carrying over this vote's `deadline_at`), sets this `VoteBatch.status` to `decided` (removing it from the Home list), and opens the new order's ordering screen
  - **Delete** (fires on Yes): sets this `VoteBatch.status` to `deleted` (removing it from the Home list); no order is created, returns to Home
- This version does not yet address whether anyone other than the initiator may Tally/Delete a vote — see Section 8

### 4.4 Order Detail / Ordering Screen

- **Deadline** (full date as of v0.5): same pattern as Vote Detail — regular users see plain text "Deadline YYYY/MM/DD HH:mm"; the initiator sees a date picker plus hour/minute dropdowns (pre-filled) plus an "Update" button that overwrites `Order.deadline_at`
- **If the current user is this order's initiator**, two extra buttons appear near the top of the page, **both gated by a Yes/No confirmation dialog**:
  - **Close Order** (fires on Yes): packages the current "everyone's totals" aggregate (item / person / quantity / amount, excluding any soft-deleted lines) into an Order History entry, along with a per-person payment list generated from those totals (all starting unpaid), then removes this order from Active Orders
  - **Delete** (fires on Yes): removes this order from Active Orders directly, **without** writing anything to Order History
- Shows the restaurant's menu items as a **flat list (v0.5: no longer grouped by category** since MenuItem's `category` field was removed)
- Tapping an item opens a bottom-sheet modal (Uber-Eats/foodpanda style):
  - Flavor/add-on options (single- or multi-select, rendered as radio or checkbox depending on `option_group` type)
  - Quantity (+/- stepper)
  - An "Add to my order" button that writes one `OrderItem`
- The "My Order" section title and card use an eye-catching warm accent color so a user can quickly spot their own items and running subtotal in a long shared list; items can be removed or have their quantity adjusted
- The order's initiator can see the "Everyone's current totals" aggregate table, columns: **Item / Options, Person, Quantity, Amount** — one row per `OrderItem`, so each line can be soft-deleted individually
  - **Soft-deleting another person's line**: on any row where "Person" isn't the initiator themself, the initiator sees a "Delete" link. Tapping it opens a Yes/No confirmation; on Yes, that `OrderItem.is_deleted` is set to true — the row stays on screen with strikethrough and is excluded from the closing aggregate / Order History. The initiator's own items are instead managed via the "Remove" action in the "My Order" card above (a hard removal, not a soft delete)
- A **Google Maps** link sits at the bottom of the page

### 4.5 Restaurant List — Read-only Browsing

- **Search and type filter (new in v0.5)**: a search box (filters by restaurant name or item name) plus 4 type-filter chips (Meal Box/Drinks/Steak/Pasta, toggleable) sit at the top, combined via AND, applied live to the name cards below
- Shows restaurant **name cards** only (no checkboxes), with the restaurant type shown as a subtitle on each card
- Tapping a card opens that restaurant's read-only menu page, top to bottom:
  1. **Menu table (v0.5: a flat list, no longer grouped by category)**, columns: **Item name, Flavor, Add-ons, Price**
     - Flavor column: all `radio`-type option groups for that item, joined together; shows "None" if there are none
     - Add-ons column: all `checkbox`-type option groups, formatted as "name + extra price"; shows "None" if there are none
  2. **"✏️ Edit Restaurant" button (new in v0.5)**: opens the 4.6 Edit Restaurant screen
  3. **Photo carousel**: multiple photos rendered as horizontally swipeable slides, navigable by touch swipe or the left/right arrow buttons
  4. **Restaurant info**: address, phone, restaurant type
  5. **Google Maps link**: opens a map search for the restaurant
- This page **has no ordering functionality** — to open an order or start a vote, use the "Order & Vote" page (4.2)

### 4.6 Edit Restaurant — new in v0.5

- Reached from the "✏️ Edit Restaurant" button on the read-only menu page (4.5). On entry, the restaurant's data is deep-cloned into a draft (`editingRestaurant`) so pressing back without saving never mutates the original record
- **Restaurant info form**: name, phone, address, restaurant type (dropdown, the fixed 4-value list)
- **Photo management**:
  - A thumbnail grid shows every photo currently in the draft (both the original placeholder images and any newly uploaded real photos)
  - "+ Upload photo" opens the native file picker; the chosen image is converted to a data URL via `FileReader.readAsDataURL()` for instant preview and appended to the draft (this wireframe stage keeps it in browser memory only — production needs to upload to real file storage and store a URL instead)
  - Each thumbnail has an "×" delete button in the corner; tapping it opens a Yes/No confirmation before removing that photo from the draft
- **Item list**: shows every item in the draft (name + price editable inline); "+ Add item" appends a blank row, and each row has a "Delete" link to remove it (v0.5 keeps this simple — editing an item's customization option groups is deferred to a later version)
- **Save changes**: writes the whole draft back into the live `restaurants` array (replacing the original), shows a success toast, and returns to that restaurant's read-only menu page
- **Discard**: tapping the back arrow at top-left discards the draft entirely and returns to the original read-only menu page, leaving the original data untouched

### 4.7 More — Navigation Hub

Groups the less-frequently-used functions behind the 4th bottom-nav tab:
- **Order History** (4.8)
- **Create Restaurant** (4.9)

### 4.8 Order History

- Lists closed orders, read-only
- Each card shows: restaurant, initiator, date, participant count, total amount, and **payment progress (new in v0.5, e.g. "Paid 2/4")**; expanding a card reveals:
  1. The itemized table, columns: **Item, Person, Quantity, Amount**
  2. **A payment-status section (new in v0.5)**: one row per person — name, amount owed, and a "Paid" checkbox. **Only the original initiator of that history entry** can check/uncheck it (toggling flips `is_paid` immediately, no extra confirmation needed since it's an easily reversible bookkeeping action); anyone else viewing the entry sees the checkbox disabled, read-only
- Detail data comes from the aggregation the initiator generated when they pressed "Close Order" on 4.4; the payment list is auto-derived from those same totals, grouped by person

### 4.9 Create Restaurant

**This stage (Phase 1)**: manual entry form only
- Restaurant basics: name, phone, address, Google Maps link, **restaurant type (new in v0.5, required dropdown)**
- Menu items (dynamically add rows): name, price (**v0.5: the category field is removed**)
- Per-item customization option groups (dynamically add groups, e.g. "Flavor" → Original/Thai style/Extra spicy)

**Phase 2 (UI entry point reserved, not implemented in this stage)**:
- Upload a menu photo → call an AI (e.g. the Claude API) to OCR + structure the content, drafting the items/options above for the user to correct manually

**Phase 3 (UI entry point reserved, not implemented in this stage)**:
- Paste a Google Maps URL → AI reads that place's public info (name, menu photos, reviews, etc.) to draft a menu for the user to correct manually
  - Risk note: Google Maps has usage-policy restrictions on third-party data access. Before implementing, confirm the legality and coverage of pulling this data through an official channel like the Google Places API

**Under evaluation (not a commitment)**:
- Integrating the Uber Eats / foodpanda API to auto-generate a menu → **high-risk item**; neither platform has a public third-party read API

---

## 5. Order / Vote State Machines

```
Vote batch lifecycle (VoteBatch):
  open (voting in progress; any participant may Save/Edit their own choice; initiator may edit deadline_at anytime)
    → initiator presses "Tally" → [Yes/No confirm] → Yes → decided (creates an Order from the highest-voted candidate, carrying over deadline_at; removed from Home)
    → initiator presses "Delete" → [Yes/No confirm] → Yes → deleted (removed from Home; no order created)
    (No → stays open, nothing changes)

Individual vote record lifecycle (Vote, belongs to a VoteBatch):
  draft (user is choosing, not yet locked)
    → Save → locked (counted in tally; option greys out)
    → Edit → draft (un-greys; choice can change; backend record not yet overwritten)
    → Save again → locked (overwrites with the new choice)

Order lifecycle (Order):
  open (ordering/editing continues; may have been created via "Open Order Now" or a vote's "Tally"; initiator may edit deadline_at anytime and soft-delete other people's items)
    → initiator presses "Close Order" → [Yes/No confirm] → Yes → closed (aggregate stats + a per-person payment list written to Order History, excluding soft-deleted lines; removed from Home)
    → initiator presses "Delete" → [Yes/No confirm] → Yes → deleted (removed from Home directly; nothing written to history)
    (No → stays open, nothing changes)

OrderItem soft-delete lifecycle:
  is_deleted=false (counted normally)
    → initiator presses "Delete" on someone else's line → [Yes/No confirm] → Yes → is_deleted=true (stays visible with strikethrough; excluded from totals/closing)
    (No → stays is_deleted=false)

OrderHistoryPayment lifecycle (new in v0.5):
  is_paid=false (auto-created at close time, unpaid by default)
    → original initiator checks the box → is_paid=true (paid_at recorded)
    → unchecked again → is_paid=false (paid_at cleared)
    (Anyone else: checkbox is disabled, read-only)
```

---

## 6. API Draft (FastAPI)

| Method | Path | Description |
|---|---|---|
| GET | `/api/users/me` | Look up the display name for the `user_id` stored in localStorage |
| PUT | `/api/users/me` | Update the display name |
| GET | `/api/restaurants?q=&type=` | Restaurant list (for read-only browsing); v0.5 adds `q` (name/item keyword) and `type` (restaurant type) query params |
| POST | `/api/restaurants` | Manually create a restaurant (with type, items and options) |
| GET | `/api/restaurants/{id}/menu` | Fetch that restaurant's menu items + options + photos + address/phone + type |
| PUT | `/api/restaurants/{id}` | New in v0.5: edit a restaurant's info (name/phone/address/type/items) |
| POST | `/api/restaurants/{id}/photos` | New in v0.5: upload one restaurant photo |
| DELETE | `/api/restaurants/{id}/photos/{photo_id}` | New in v0.5: delete one restaurant photo (frontend confirms Yes/No first) |
| GET | `/api/orders?status=open` | Active orders list (used on Home) |
| POST | `/api/orders` | Created by "Open Order Now" on the Order & Vote page, or internally by a vote's "Tally" action |
| GET | `/api/orders/{id}` | Order detail + everyone's current aggregate stats (including the Person column) + Google Maps link |
| POST | `/api/orders/{id}/items` | Add one OrderItem |
| PATCH/DELETE | `/api/orders/{id}/items/{item_id}` | Modify or hard-remove an item **you** added |
| PATCH | `/api/orders/{id}/items/{item_id}/soft-delete` | Initiator soft-deletes **someone else's** item, setting `is_deleted=true` |
| PATCH | `/api/orders/{id}/deadline` | Initiator updates this order's `deadline_at` (v0.5: now a full date+time) |
| POST | `/api/orders/{id}/close` | Initiator closes the order (frontend confirms Yes/No first); aggregate stats (excluding soft-deleted lines) plus a payment list are written to Order History |
| DELETE | `/api/orders/{id}` | Initiator deletes the order (frontend confirms Yes/No first); nothing written to history |
| GET | `/api/votes?status=open` | List of currently-open vote batches (used on Home) |
| POST | `/api/votes` | Create a new vote batch (triggered by multi-select + deadline on the Order & Vote page) |
| GET | `/api/votes/{batch_id}` | Vote detail + current vote counts per candidate + deadline |
| PATCH | `/api/votes/{batch_id}/deadline` | Initiator updates this vote's `deadline_at` (v0.5: now a full date+time) |
| PUT | `/api/votes/{batch_id}/my-choice` | Submit/overwrite your own vote (corresponds to Save) |
| POST | `/api/votes/{batch_id}/decide` | Initiator tallies the vote (frontend confirms Yes/No first): creates an Order from the highest-voted candidate; batch status becomes `decided` |
| DELETE | `/api/votes/{batch_id}` | Initiator deletes the vote batch (frontend confirms Yes/No first); status becomes `deleted`; no order created |
| GET | `/api/orders/history` | Order history list (including a payment-progress summary per entry) |
| PATCH | `/api/orders/history/{history_id}/payments/{user}` | New in v0.5: toggle a person's `is_paid` status; callable only by that history entry's original initiator |

> For every "initiator closes/deletes/tallies/deletes-a-vote" action in the table above, the frontend always shows a Yes/No confirmation dialog first — the corresponding API call only fires if the user picks Yes. Payment-status toggling (v0.5) is a lightweight, reversible action, so the frontend does not show a confirmation dialog — it fires immediately on click.

---

## 7. Responsive (RWD) Strategy

- Build order: mobile size first (390px width baseline), using flex/grid + rem units — no hardcoded pixel values
- Suggested breakpoints: `≤600px` phone (single column), `601–1024px` tablet (two columns, list + detail side by side), `>1024px` desktop (three columns: nav + list + detail/stats sidebar)
- Mobile ordering uses "tap item → bottom-sheet modal"; desktop could switch to a right-side panel instead of forcing a modal, but this stage keeps the modal component as the single implementation reused as-is on desktop
- Photo carousel (4.5): mobile shows one full-width swipeable slide at a time; desktop could switch to a multi-photo grid — to be decided during implementation
- Search box + type filter chips (new in v0.5): mobile stacks them vertically (search box above, wrapping filter chips below); desktop could place them side by side — to be decided during implementation

---

## 8. Open Questions / Risks

1. **User identity**: there's no Teams SSO yet, so the same person switching devices or clearing localStorage will be treated as a new user — is a temporary "match by display name text" identity acceptable for now?
2. **Vote tie-break rule** (new in v0.3): the wireframe currently simplifies this to "the candidate listed first wins ties" — does the production version need an explicit rule?
3. **Permission scope** (new in v0.3, partially addressed in v0.4): "Tally/Delete vote," "Close/Delete order," and "soft-delete someone else's item" all show a Yes/No confirmation before executing, but remain restricted to the initiator only. **New in v0.5**: "Edit Restaurant" and "toggle payment status" also lack a richer permission model beyond this (anyone can edit a restaurant; only that history entry's initiator can toggle payments) — whether finer-grained permissions are needed (e.g. only the restaurant's creator may edit it) remains open
4. **Automating the vote deadline** (new in v0.3): tallying still only happens when the initiator manually presses "Tally" — is a scheduled "auto-tally when the deadline passes" mechanism needed?
5. ~~**Deadlines have no date**~~ **(raised in v0.4, resolved in v0.5)**: v0.4 had simplified this to "today's HH:mm"; v0.5 restores the full date, supporting scenarios that span days (e.g. starting tomorrow's lunch vote tonight)
6. **Notification for soft-deletes** (new in v0.4): the affected person currently isn't notified when their item is soft-deleted — is a toast/notification needed?
7. Uber Eats / foodpanda API integration: high risk — recommend confirming technical feasibility before formally adding this to the roadmap
8. Google Maps data integration (Phase 3 for Create Restaurant, and the map links): the map link currently just builds a search URL from "name + address" — recommend switching to a Google Place ID for production accuracy
9. Concurrent edits to the same vote/order by multiple people (this stage uses "last write wins," no optimistic locking) — a version-number mechanism may be needed once usage scales up
10. **Payment status accuracy and reminders** (new in v0.5): payment status is purely a manual checkbox with no actual payment/transaction verification, and there's no reminder mechanism for people who haven't paid — is a "remind the initiator after N days unpaid" feature needed?
11. **Restaurant type is a fixed list** (new in v0.5): the four types (Meal Box/Drinks/Steak/Pasta) are currently hardcoded on the frontend with no backend-managed taxonomy; if restaurant categories grow more varied (e.g. a drink shop that also sells light meals), is single-select sufficient, or should this become multi-tag?
12. **Photo upload storage and size limits** (new in v0.5): the wireframe stores uploaded photos as in-memory data URLs via `FileReader.readAsDataURL()`; production needs real file storage (e.g. object storage), file-size/format limits, and a decision on server-side image compression
13. **Information density after removing item categories** (new in v0.5): for restaurants with many items, a flat (ungrouped) list may get long on a single page — is an alternative UI aid needed (collapsible sections, price sorting, etc.) while keeping the simplified data model?
