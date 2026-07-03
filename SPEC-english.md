# Team Group-Order Tally App — Product Spec (v0.11 Sync)

> **Version history**
> - v0.2: Bottom nav changed to Home / Restaurant List / Restaurant Vote / More; Restaurant List became a read-only menu browser; the old "voting restaurants" section and "open order now / start a vote" action were merged into one "Restaurant Vote" page; Order History and Create Restaurant moved under a "More" hub; a "Person" column was added to the aggregate stats table and to order history; a Phase 3 item was added to Create Restaurant (AI menu generation from a Google Maps URL).
> - v0.3: The bottom-nav tab "Restaurant Vote" was renamed to "Order & Vote"; "Currently voting" moved back to the Home screen as cards (same pattern as "Active orders"); starting a vote (multi-select) now requires a deadline; added a new "Vote Detail" page where the initiator can "Tally" (auto-create an order from the winning restaurant) or "Delete" the vote; the Order Detail page gained initiator-only "Close order" / "Delete" buttons and a Google Maps link; the read-only restaurant menu page gained a photo carousel, restaurant info (address/phone), and a Google Maps link; added this English spec file (`SPEC-english.md`) alongside the Chinese original for easier AI/automation consumption.
> - v0.4: The four buttons "Close Order," "Delete" (order), "Tally," and "Delete" (vote) now open a Yes/No confirmation dialog on tap — the action only runs if the user picks Yes; No just closes the dialog. Deadlines are simplified to "time of day only" (no date). Orders gained the same deadline feature end-to-end. The order initiator can now soft-delete another participant's order line from Order Detail.
> - v0.5: Order History gains payment tracking; deadlines get the full date back (native date picker + hour/minute dropdowns); Restaurants gain a "Restaurant Type" field (originally a fixed 4-value list); the `category` field on MenuItem was removed (menus flattened, no grouping); Restaurant List and Order & Vote gained a search box and type-filter chips; a new "Edit Restaurant" screen was added.
> - **v0.6–v0.11 (this sync — see details below)**: this update reconciles the spec with the app as actually shipped and running in production. Several v0.5 assumptions turned out to be temporary or were reversed; this revision corrects them rather than leaving stale claims in the document. Headline changes since v0.5:
>   1. **Identity became a real shared roster.** `User` is now a persistent table (name, `is_admin`, `ui_mode`, timestamps) with a dedicated Login screen — a free-text "login & auto-create" field plus a "Quick Login" list of existing names (sorted by how often they've ordered). There is still no password; permission checks are still a server-side string comparison against a display name (see Section 8, item 1), but identity is no longer just a browser-local text field.
>   2. **Admin role.** `is_admin` gates "Manage Users" (rename/delete roster entries) and deleting a History entry. Username creation/rename is validated: reserved prefixes (`admin`/`root`/`ubuntu`/`sysop`/`sysadmin`) are blocked, and only letters/digits/spaces/`-_.` are allowed (max 30 chars) — an allow-list, not a blacklist.
>   3. **Restaurant Type is no longer a fixed list.** The original 4 values (Meal Box/Drinks/Steak/Pasta) are still offered as quick-pick defaults, but the field is free text; any custom value already in use by an existing restaurant is automatically added to the filter-chip set app-wide.
>   4. **`MenuItem.category` is back.** v0.5 removed it in favor of a flat list; it was reinstated because a flat list didn't scale for restaurants with many items. The read-only menu page and the ordering screen both group items by category (first-seen order, with uncategorized items always last under "Uncategorized").
>   5. **AI menu-photo parsing shipped for real** (this was "Phase 2, reserved UI entry point" in v0.5). Uploading a menu photo on Create Restaurant calls Gemini first, falls back to OpenAI if that fails or isn't configured; returns item name/price/category/customization options as an editable draft. As of this sync, the category suggestion is folded into the *same* AI call (previously a second round-trip) to cut API usage.
>   6. **Google Places lookup shipped for real** (this was "Phase 3, reserved UI entry point" in v0.5). Pasting a Google Maps link auto-fills phone/address/opening-hours (and name, if blank) via the Places API (New). It deliberately does not attempt to pull "menu photos" off Maps — no official API exposes that — so a menu photo still has to be uploaded by hand for AI parsing to run.
>   7. **Uber Eats / foodpanda integration is no longer "under evaluation" — it has been dropped from the roadmap entirely.** Neither platform offers a public third-party read API; this is not being pursued.
>   8. **Restaurant photos moved off base64-in-Postgres.** Photos are now stored in a self-hosted, S3-compatible MinIO bucket; the database only holds a short path (e.g. `/media/5/ab12cd.jpg`). Existing base64 rows are migrated automatically, once, on backend startup. Uploaded photos are auto-captioned `picture-1`, `picture-2`, ... based on current photo count (device filenames like `IMG_2026...` are discarded).
>   9. **Restaurant List sorting**: a manual drag-to-reorder feature (▲▼ buttons, a `sort_order` column) was added after v0.5 and then removed again in this same revision — usability feedback favored two simple, unambiguous fixed presets instead: "Created (newest first)" (default) and "Name". `Restaurant.created_at` is exposed by the API to support this.
>   10. **Sharing.** Vote Detail and Order Detail gained "Copy Link" (and, where the Web Share API is available, native "Share") buttons, making it easy to broadcast a link into Teams/LINE. Order History gained a "Copy as Text" button that formats a closed order's items/totals/payment status into a plain-text block suitable for a payment-reminder message.
>   11. **Accessibility: large-text mode.** A "其他功能 / More" toggle switches the whole app into a large-icon/large-text mode for users who need bigger UI (e.g. presbyopia). The preference is tied to the user's account (persists across devices and re-logins), with a local cache so it applies instantly on next page load before the profile round-trip resolves.
>   12. **Correction to v0.5's Vote Detail spec**: pressing "Edit" on a locked vote does **not** just un-grey the radio buttons while keeping the old pick counted (as v0.5 stated) — it immediately clears the locked vote server-side, so it stops counting toward the tally right away. The user must pick again and press Save to be counted. This is the actual, current, intentional behavior.
>   13. **Correction to v0.5's Edit Restaurant spec**: per-item customization option groups (radio/checkbox groups, choice names, extra prices) are fully editable on the Edit Restaurant screen — this was *not* deferred to a later version, as v0.5 speculated.
>   14. The app is deployed via Docker Compose (FastAPI + Postgres + a static Vue build behind nginx + MinIO) on a self-hosted Ubuntu VM, reachable over LAN and Tailscale; see `SPEC.md`'s development-workflow section / `README.md` for the concrete git → build → deploy loop.

## 1. Background & Goals

**Current state (superseded)**: Before this app existed, someone posted a photo of the restaurant menu in a Teams group chat and everyone else replied with free-text messages describing what they want, with no way to tally it automatically.

**Goal**: A standalone web app (mobile-first, responsive to desktop). The link is shared directly in the Teams chat — no Teams Tab app registration/manifest, no SSO required. Core flow:

1. Decide which restaurant to order from today (either pick one directly, or run a group vote with a deadline; search, restaurant-type filters, and category grouping help find a restaurant/item quickly)
2. When the vote deadline passes (or the initiator taps "Tally" early), the restaurant with the most votes automatically becomes an order
3. Once an order is open, each person selects menu items plus customizations (flavor/quantity, similar to Uber Eats / foodpanda)
4. The system automatically aggregates item counts and totals per person, for the initiator to use when placing the real order with the restaurant; the initiator can close or delete the order
5. Once closed, the order moves to history, where the initiator can mark each person's payment status (and copy a plain-text payment summary to paste into chat)
6. Closed orders are kept in history for later lookup and re-ordering

**Confirmed technical direction (as shipped)**:
- Frontend: Vue 3 + TypeScript + Vite, mobile-first, responsive breakpoints
- Backend: FastAPI (Python) + SQLAlchemy, hand-written idempotent migrations (no Alembic) run at startup
- Deployment: Docker Compose — a Postgres container, a FastAPI container, a static-frontend-behind-nginx container (nginx also reverse-proxies `/api/*` and `/media/*` so the same build works from any network/hostname without rebuilding), and a self-hosted MinIO container for photo storage
- User identity: a shared, persistent roster (`User` table) with a "login as" picker and a free-text "login & auto-create" field — still no password (see Section 8, item 1)
- AI menu parsing for "Create Restaurant" (photo → items) and Google Maps info lookup (map link → phone/address/hours): **both fully implemented** (Gemini-first/OpenAI-fallback; Google Places API (New))
- Uber Eats / foodpanda menu-generation integration: **evaluated and explicitly not pursued** — neither platform exposes a public third-party read API

---

## 2. Information Architecture (Sitemap)

The bottom navigation has 4 fixed tabs: **Home / Restaurant List / Order & Vote / More**.

```
Home
├─ Top header: shows the logged-in username + Logout button, or a "not logged in / Login" prompt
├─ Active Orders (card list, tap to open the order's ordering screen)
└─ Currently Voting (card list, same visual pattern as above, tap to open Vote Detail)

Login (new, dedicated screen; superseded the v0.5 idea of an inline-editable header field)
├─ Free-text "Login & auto-create" field — matches an existing roster entry case-insensitively, or creates a new one (subject to the reserved-prefix / allow-listed-character validation)
└─ "Quick Login" list of existing roster entries (excludes admin accounts), searchable, sorted by how often that name has ordered historically

Restaurant List — read-only browsing
├─ Search box (filter by restaurant name or item name)
├─ Restaurant-type filter chips (toggleable; includes the 4 defaults plus any custom type already in use)
├─ Two sort toggles: "Created (newest first)" (default) / "Name" — replaces an earlier, since-removed manual drag-to-reorder feature
├─ Restaurant name cards (reflecting the current search/filter/sort)
└─ Tap → opens that restaurant's read-only menu page:
     ├─ Menu grouped by category (category field was reinstated after v0.5 removed it) — table columns: Item name / Flavor / Add-ons / Price
     ├─ "✏️ Edit Restaurant" button → opens the Edit Restaurant screen
     ├─ Photo carousel (swipe or arrow buttons), photos served from MinIO object storage
     ├─ Restaurant info (address, phone, type, opening hours)
     └─ Google Maps link (uses the manually-entered map link if set, else an auto-generated search URL)

Edit Restaurant
├─ Restaurant info form: name, Google Maps link, phone, address, opening hours (free text), restaurant type (dropdown of known types + a manual override field)
├─ "📍 Read from Google Map" button — calls the Places lookup to auto-fill phone/address/hours (and name, if blank) from the pasted map link
├─ Photo management: thumbnail grid; "+ Upload photo" opens the file picker with instant local preview (uploaded to MinIO on Save); each photo has a per-item delete (confirmed first, also deletes the underlying object)
├─ Item list: name / category / price editable per row, plus fully editable customization option groups (group name, radio-vs-checkbox, comma-separated choices with optional "+price" suffix) — add/remove item rows and option groups freely
├─ "🏷️ AI auto-classify item category" button — asks the backend for a category suggestion per item name (using every other already-categorized item in the DB as reference), shows a before/after diff, and only applies it to the in-memory draft on confirmation
├─ "Save changes" writes the whole draft back and returns to the read-only menu page; the back arrow discards the draft instead
└─ "🗑️ Delete restaurant" — blocked while an open order or open vote still references this restaurant; otherwise cascades to its menu items/options/photos, and cleans up any stale closed/deleted orders pointing at it

Order & Vote page
├─ Search box + restaurant-type filter chips (same semantics as Restaurant List's, kept independent per page)
├─ Select restaurants (checkboxes, reflecting the current search/filter; already-checked restaurants stay checked even if a filter later hides them)
└─ A "Deadline" control (native date picker + hour (24h) + minute (5-min steps) dropdowns, defaulting to "now + 10 min")
     ├─ Select exactly 1 → button reads "Open Order Now" → creates an Order immediately and opens its ordering screen
     └─ Select 2+ → button reads "Start a Vote" → creates a new vote batch, then returns to Home where it appears under "Currently Voting"

Vote Detail ← opened from a "Currently Voting" card on Home
├─ "🔗 Copy Link" / (where supported) "📤 Share" buttons at the top
├─ Shows the deadline; the initiator sees it as an editable date+time picker with an "Update" button instead of plain text
├─ Single-select list of candidate restaurants with live vote counts + Save/Edit:
│    ├─ Save: locks in the current choice (radios grey out), counted in the tally
│    └─ Edit: **immediately clears the locked vote server-side** (not just a client-side unlock) — it stops counting right away; the user must pick again and Save to be counted again
└─ If the current user is the initiator, "Tally" and "Delete" buttons appear, both gated by a Yes/No confirmation:
     ├─ "Tally" → picks the candidate with the most locked votes (ties go to whichever candidate was listed first), creates an Order carrying over this vote's deadline, marks the batch `decided`, opens the new order
     └─ "Delete" → marks the batch `deleted`; no order is created

Order Detail / Ordering screen ← opened from an "Active Orders" card, or automatically after "Open Order Now" / a vote's "Tally"
├─ "🔗 Copy Link" / (where supported) "📤 Share" buttons at the top
├─ Shows the deadline; the initiator sees an editable date+time picker with an "Update" button
├─ If the current user is the initiator, "Close Order" and "Delete" buttons appear, both gated by a Yes/No confirmation
├─ Restaurant's menu, grouped by category (see above) — tapping an item opens a bottom-sheet modal (flavor/add-on options + quantity stepper) → "Add to my order"
├─ "My Order" section uses an accent color so a user can find their own items quickly; items can be removed
├─ Initiator-only "Everyone's current totals" aggregate table (Item/Options, Person, Quantity, Amount) — the initiator can soft-delete another person's line (Yes/No confirm first); soft-deleted lines stay visible with strikethrough and are excluded from the closing aggregate/history
└─ Google Maps link at the bottom

More — navigation hub
├─ Display-mode toggle (new): "Standard" / "Large text" — switches a whole-app large-icon/large-text mode on or off immediately; the choice is saved to the logged-in user's account (see Section 3)
├─ Order History
├─ Create Restaurant
└─ Manage Users (admin-only; hidden entirely for non-admin accounts)

Order History
├─ Past closed orders (read-only): restaurant, initiator, date, participant count, total amount, payment progress (e.g. "Paid 2/4")
├─ Expand a card → itemized table (Item/Person/Quantity/Amount) + a per-person payment-status section (checkbox toggle, enabled only for that entry's original initiator; read-only for everyone else)
├─ "📋 Copy as Text" button — formats the itemized totals + payment status into a plain-text block for pasting into LINE/Teams as a payment reminder
└─ Admin-only "Delete" on each entry

Create Restaurant
├─ Manual entry: restaurant basics (name, phone, address, Google Maps link, opening hours, restaurant type) + menu items (name, price, category) + per-item customization option groups
├─ "📍 Read from Google Map" button — same Places-lookup auto-fill as Edit Restaurant (does not touch menu items)
└─ "📷 Upload menu photo, AI auto-parses items" button — sends the photo to the AI menu parser (Gemini-first/OpenAI-fallback), which returns draft items (name/price/category/options) for review before saving; the category suggestion is generated in this same AI call

Manage Users (admin-only; new page, did not exist in v0.5)
├─ Lists every roster entry (name, historical order count)
├─ Rename (validated the same way as creating a new name) or Delete (removes the roster entry only — past orders/votes/history keep the name as a plain-text snapshot and are unaffected)
```

---

## 3. Data Model (as shipped)

| Entity | Fields | Notes |
|---|---|---|
| **User** | `id`, `name`, `is_admin` (default false), `ui_mode` (`"normal"`\|`"large"`, default `"normal"`), `created_at`, `updated_at` | Persistent shared roster (replacing v0.5's "text field in localStorage" assumption). No password — permission checks compare `acting_user` (a plain string the client sends) against this table server-side. `ui_mode` follows the account across devices/logins and drives the whole-app large-text/large-icon accessibility mode |
| **Restaurant** | `id`, `name`, `phone`, `address`, `map_url`, `hours` (free text, e.g. from Google Places or typed by hand), `type` (free text; a fixed 4-value list is offered as quick-pick defaults but any value is accepted), `created_by`, `created_at`, `updated_at` | `created_at` powers the default "newest first" sort on Restaurant List. There is deliberately no `sort_order` column — an earlier manual-reorder feature that used one was removed in favor of the two fixed sort presets |
| **RestaurantPhoto** | `id`, `restaurant_id`, `image_url` (a short `/media/<restaurant_id>/<uuid>.<ext>` path into the self-hosted MinIO bucket — **not** a base64 data URL as in v0.5), `caption` (auto-generated as `picture-1`, `picture-2`, ... at upload time), `sort_order` | Powers the photo carousel; deleting a row also deletes the underlying MinIO object |
| **MenuItem** | `id`, `restaurant_id`, `name`, `price`, `is_active`, `category` (free text, optional) | **v0.5 removed this `category` field; it was reinstated** because a flat, ungrouped list didn't scale for restaurants with many items. Menu views group by category (first-seen order; items with no category are grouped under "未分類"/Uncategorized, always last) |
| **MenuItemOption** | `id`, `menu_item_id`, `option_group`, `option_type` (`radio`/`checkbox`), `option_name`, `extra_price` | Unchanged from v0.5; fully editable on Edit Restaurant (contrary to v0.5's speculation that this would be deferred) |
| **VoteBatch** | `id`, `initiator`, `deadline_at`, `status` (`open`/`decided`/`deleted`), `created_at` | Unchanged from v0.5 |
| **VoteBatchCandidate** | `vote_batch_id`, `restaurant_id` | Unchanged |
| **Vote** | `id`, `vote_batch_id`, `user`, `restaurant_id`, `status` (`draft`/`locked`), `created_at`, `locked_at` | `status=locked` corresponds to Save; pressing Edit on a locked vote **deletes the row outright** (clears the choice immediately) rather than merely un-graying the UI — see version history item 12 |
| **Order** | `id`, `restaurant_id`, `initiator`, `source_vote_batch_id` (nullable), `deadline_at`, `status` (`open`/`closed`/`deleted`), `created_at`, `closed_at` | Unchanged from v0.5 |
| **OrderItem** | `id`, `order_id`, `user`, `menu_item_id`, `selected_options` (JSON list), `quantity`, `note`, `is_deleted` (default false), `deleted_by` (nullable), `created_at` | Unchanged from v0.5 |
| **OrderHistory** | `id`, `order_id`, `restaurant_name`, `initiator`, `closed_date`, `people_count`, `total_amount` | Unchanged |
| **OrderHistoryLine** | `id`, `order_history_id`, `item_label`, `user`, `quantity`, `amount` | Unchanged |
| **OrderHistoryPayment** | `id`, `order_history_id`, `user`, `total_amount`, `is_paid` (default false), `paid_at` (nullable) | Unchanged; only the original initiator of that history entry may toggle `is_paid` |

**Deadline rule** (unchanged from v0.5, confirmed still accurate): full date+time (`deadline_at`), UI = native date picker + hour dropdown (0–23) + minute dropdown (00/05/…/55); defaults to "today, now + 10 min". Still purely informational/a reminder — **confirmed there is still no scheduled job** that auto-tallies a vote or auto-closes an order when the deadline passes (Section 8, item 4, remains open).

**Restaurant Type rule (corrected from v0.5)**: the 4 baseline values (Meal Box/Drinks/Steak/Pasta) are quick-pick defaults on the dropdown, not an enforced whitelist — the field accepts any free text (a manual-override input takes precedence over the dropdown when filled). `GET /api/restaurants/types` returns the 4 defaults plus every distinct custom value already in use, so filter chips across the app stay in sync automatically.

**Category rule (corrected from v0.5)**: `MenuItem.category` exists (reinstated in a later revision after v0.5 removed it). It's free text, optional. The read-only menu page and the ordering screen both group items by category; AI-assisted category suggestions (either via the merged menu-photo-parse call, or the standalone "AI auto-classify" button on Edit Restaurant) use every other already-categorized item name/category pair in the database as reference, so category naming stays consistent across restaurants over time.

**Search / filter rule**: unchanged from v0.5 — case-insensitive substring match against restaurant name or any of its item names; combines with the type filter via AND; Restaurant List and Order & Vote keep independent search/filter state.

**Aggregation logic**: unchanged from v0.5 (see that section's wording — order stats exclude soft-deleted lines; vote stats exclude `draft` selections; tie-break picks the first-listed candidate; payment rows are auto-derived per person at close time).

---

## 4. Page Specifications

### 4.1 Home

Unchanged in substance from v0.5, except the username field described in v0.5 (an inline editable text field in the header) has moved to a dedicated **Login** screen (4.1a) — the header now just shows the current username + Logout, or a "not logged in" prompt that routes to Login.

### 4.1a Login (new — did not exist as a separate page in v0.5)

- A free-text field + "登入 & 自動建立" (Login & auto-create) button: matches an existing roster entry case-insensitively, or creates a new one (new-name creation is validated — see Section 3's User entity notes)
- A "Quick Login" section: a searchable list of existing roster entries (admin accounts are hidden from this list, though they can still log in via the free-text field), sorted by how many historical orders mention that name

### 4.2 Order & Vote Page

Unchanged from v0.5 in substance — this remains the only entry point for creating a new order or vote; Restaurant List (4.5) stays read-only browsing.

### 4.3 Vote Detail

Same as v0.5 **except**:
- Gained "🔗 Copy Link" and, where the Web Share API is available, "📤 Share" buttons at the top, for broadcasting the link into Teams/LINE
- **Corrected Edit behavior**: pressing Edit on a locked vote immediately deletes the locked `Vote` row server-side (the choice stops counting toward the tally right away) — it is *not* just a client-side un-grey that defers the backend write until the next Save, as v0.5 stated

### 4.4 Order Detail / Ordering Screen

Same as v0.5 **except**:
- Gained "🔗 Copy Link" / "📤 Share" buttons at the top
- The menu items list is grouped by category again (v0.5 had flattened it; category was reinstated — see Section 3)

### 4.5 Restaurant List — Read-only Browsing

Same as v0.5's search/type-filter/name-cards/menu-page structure, **except**:
- Two sort toggle buttons — "Created (newest first)" (default) and "Name" — sit alongside the search box and type filters. (An earlier manual drag-to-reorder feature, added after v0.5, was tried and then removed in favor of these two fixed presets.)
- The read-only menu table is grouped by category again (category field was reinstated)
- The restaurant-info card also shows opening hours (new `hours` field) when set

### 4.6 Edit Restaurant

Same overall flow as v0.5 (draft-then-save, discard-on-back), **except**:
- **Per-item customization option groups are fully editable** here (group name, radio/checkbox type, choice list with optional per-choice extra price) — v0.5 speculated this would be deferred; it was not
- Gained a "📍 Read from Google Map" button that auto-fills phone/address/hours (and name, if blank) from the pasted Google Maps link via the Places API
- Gained a "🏷️ AI auto-classify item category" button — suggests a category per item (reusing categories already seen elsewhere in the DB where the name matches/is similar), shown as a before/after diff the user must confirm before it's applied to the in-memory draft
- Photo upload now round-trips through MinIO object storage instead of storing base64 in the database; uploaded photos are auto-captioned `picture-N` based on current photo count
- Gained a "🗑️ Delete restaurant" button, blocked while an open order or open vote still references this restaurant

### 4.7 More — Navigation Hub

- **Display-mode toggle** (new): "Standard" / "Large text" — instantly switches the whole app into a larger-icon/larger-text presentation for easier reading; the choice is written to the logged-in user's account so it's remembered across devices and future logins (with a local cache so it applies immediately on next page load, before the account round-trip confirms it)
- Order History (4.8)
- Create Restaurant (4.9)
- **Manage Users (4.10, new)** — only visible to admin accounts

### 4.8 Order History

Same as v0.5's payment-tracking flow, **plus**:
- A "📋 Copy as Text" button on each entry that formats the itemized totals and payment checklist into a plain-text block, meant to be pasted straight into a LINE/Teams message asking people to pay
- Delete on an entry is admin-only (v0.5 didn't specify a permission model for this)

### 4.9 Create Restaurant

**No longer phased** — both AI features that v0.5 described as "reserved UI entry points, not implemented in this stage" are fully working:
- Manual entry: restaurant basics + menu items (with `category`) + customization option groups — unchanged from v0.5
- "📍 Read from Google Map" — Google Places API (New) lookup, auto-fills phone/address/hours (and name, if blank); does not touch menu items (no official API exposes "the menu photos" off a Maps listing)
- "📷 Upload menu photo, AI auto-parses items" — Gemini-first, OpenAI-fallback vision parsing; returns name/price/category/customization-options as an editable draft; the category suggestion is generated in the same AI call (an earlier revision made two separate calls — this was merged to save API usage)

**Dropped from the roadmap (was "under evaluation" in v0.5)**: Uber Eats / foodpanda API integration to auto-generate a menu. Neither platform has a public third-party read API; this is not being pursued and should not be treated as a live open question anymore.

### 4.10 Manage Users (new — did not exist in v0.5)

- Admin-only (both the nav entry and the route itself are gated; a non-admin landing here directly is bounced back to More with a toast)
- Lists every roster entry with its historical order count
- **Rename**: validated the same way as creating a brand-new name (reserved-prefix block, allow-listed characters, 30-char max)
- **Delete**: removes the roster entry only (from the "Quick Login" list going forward) — it does *not* retroactively touch any order/vote/history record that already mentions that name as a plain-text snapshot

---

## 5. Order / Vote State Machines

Same as v0.5's state machines for `VoteBatch`, `Order`, `OrderItem` soft-delete, and `OrderHistoryPayment`, **with one correction**:

```
Individual vote record lifecycle (Vote, belongs to a VoteBatch):
  draft (user is choosing, not yet locked)
    → Save → locked (counted in tally; option greys out)
    → Edit → the locked Vote row is deleted immediately (stops counting toward the tally right away;
              this is a real DB write, not just a UI un-grey deferred until the next Save)
    → Save again → locked (a fresh Vote row, with the new choice)
```

---

## 6. API (as shipped)

| Method | Path | Description |
|---|---|---|
| GET | `/api/users` | List the shared roster, sorted by historical order count desc then name |
| GET | `/api/users/{id}` | Fetch one roster entry |
| POST | `/api/users` | Login-or-create by name (case-insensitive match on existing names) |
| PATCH | `/api/users/{id}` | Rename a roster entry (admin-only, `acting_user` re-checked server-side) |
| PATCH | `/api/users/{id}/ui-mode` | Set this account's `ui_mode` (`"normal"`\|`"large"`) — not admin-gated, anyone can set their own |
| DELETE | `/api/users/{id}` | Remove a roster entry (admin-only); does not touch historical records |
| GET | `/api/restaurants?q=&type=&sort=` | Restaurant list; `q` (name/item keyword), `type` (restaurant type), `sort` (`created_desc` default, or `name`) |
| GET | `/api/restaurants/types` | The 4 default types plus any custom type already in use by an existing restaurant |
| POST | `/api/restaurants` | Create a restaurant (type/hours/items/options) |
| GET | `/api/restaurants/{id}/menu` | Restaurant detail: items + options + photos + address/phone/type/hours |
| PUT | `/api/restaurants/{id}` | Edit a restaurant's info/items (bulk-replaces menu items; explicitly deletes orphaned option rows first, since a bulk delete bypasses ORM cascade) |
| DELETE | `/api/restaurants/{id}` | Delete a restaurant; blocked while it has an open order or is a candidate in an open vote |
| POST | `/api/restaurants/parse-menu` | AI menu-photo parsing (Gemini-first/OpenAI-fallback) — returns draft items including a category suggestion, generated in this same call |
| POST | `/api/restaurants/fetch-place-info` | Google Places (New) lookup from a pasted Maps link — returns name/phone/address/hours |
| POST | `/api/restaurants/classify-categories` | Standalone AI category-suggestion endpoint (used by Edit Restaurant's "AI auto-classify" button for items that don't have an associated photo) |
| POST | `/api/restaurants/{id}/photos` | Upload one photo — backend decodes the data URL and pushes it to MinIO, storing only the resulting short path |
| DELETE | `/api/restaurants/{id}/photos/{photo_id}` | Delete one photo (and its underlying MinIO object) |
| GET | `/api/orders?status=open` | Active orders list |
| POST | `/api/orders` | Create an order ("Open Order Now", or internally by a vote's "Tally") |
| GET | `/api/orders/{id}` | Order detail |
| GET | `/api/orders/{id}/stats` | Everyone's current aggregate totals (includes soft-deleted rows, for strikethrough rendering) |
| POST | `/api/orders/{id}/items` | Add one item |
| PATCH/DELETE | `/api/orders/{id}/items/{item_id}` | Modify or hard-remove an item **you** added |
| PATCH | `/api/orders/{id}/items/{item_id}/soft-delete` | Initiator soft-deletes **someone else's** item |
| PATCH | `/api/orders/{id}/deadline` | Initiator updates the deadline |
| POST | `/api/orders/{id}/close` | Initiator closes the order — writes History + per-person Payment rows |
| DELETE | `/api/orders/{id}` | Initiator deletes the order (nothing written to history) |
| GET | `/api/votes?status=open` | Open vote batches |
| POST | `/api/votes` | Create a vote batch (needs ≥2 candidates) |
| GET | `/api/votes/{batch_id}` | Vote detail + current per-candidate vote counts |
| PATCH | `/api/votes/{batch_id}/deadline` | Initiator updates the deadline |
| PUT | `/api/votes/{batch_id}/my-choice` | Save your choice (locks it in) |
| DELETE | `/api/votes/{batch_id}/my-choice` | Edit: immediately clears your locked choice |
| POST | `/api/votes/{batch_id}/decide` | Initiator tallies the vote → creates an Order |
| DELETE | `/api/votes/{batch_id}` | Initiator deletes the vote batch |
| GET | `/api/orders/history` | History list (with payment-progress summary per entry) |
| PATCH | `/api/orders/history/{history_id}/payments/{user}` | Toggle a person's paid status (only that entry's original initiator) |
| DELETE | `/api/orders/history/{history_id}` | Delete a history entry (admin-only) |

> Every "initiator closes/deletes/tallies/deletes-a-vote" action shows a Yes/No confirmation on the frontend before the API call fires. Payment-status toggling and the large-text UI-mode toggle are lightweight, reversible actions with no confirmation dialog.

---

## 7. Responsive (RWD) Strategy

Unchanged from v0.5's breakpoint strategy (mobile-first, `≤600px`/`601–1024px`/`>1024px`), **plus**: an orthogonal, account-level "large text" mode (Section 4.7) scales up font sizes and icon sizes across the app for readability, independent of viewport width — it's an accessibility toggle, not a responsive breakpoint, and applies identically at every screen size.

---

## 8. Open Questions / Risks (re-audited)

1. **User identity**: still no real password/SSO — `acting_user` is a plain string the client sends, re-checked server-side against the `User` table's `name` column. This is a real improvement over v0.5 (a persistent shared roster with an admin role, rather than a raw localStorage text field), but it is still not real authentication: anyone who knows/types an existing name can act as that person. **Still open.**
2. **Vote tie-break rule**: unchanged — first-listed candidate wins ties. **Still open** (no explicit production rule beyond this).
3. **Permission scope**: initiator-only / admin-only gates remain coarse — no per-restaurant "only the creator may edit" model, for example. **Still open.**
4. **Automating the vote/order deadline**: confirmed, still no scheduled job — deadlines remain purely informational. **Still open.**
5. ~~Deadlines have no date~~ — resolved in v0.5, remains resolved.
6. **Notification for soft-deletes**: unchanged — the affected person still isn't notified. **Still open.**
7. ~~Uber Eats / foodpanda API integration~~ — **resolved: explicitly dropped from the roadmap**, not pursued (see version history item 7). No longer an open question.
8. ~~Google Maps data integration~~ — **resolved: Google Places API (New) is live** for phone/address/hours lookup. The map *link itself* still just prefers a manually-entered `map_url`, falling back to a name+address search URL when unset — switching every restaurant to a stored Place ID remains a nice-to-have, not done.
9. **Concurrent edits**: unchanged — still "last write wins," no optimistic locking. **Still open.**
10. **Payment status accuracy and reminders**: unchanged — still a manual checkbox with no payment-gateway integration, though the new "Copy as Text" button at least makes manually nudging people easier. **Still open** (no automated reminder).
11. ~~Restaurant type is a fixed list~~ — **resolved: it's free text now**, with the original 4 values kept only as quick-pick defaults.
12. **Photo upload storage**: **partially resolved** — photos now go to self-hosted MinIO object storage instead of base64-in-Postgres, which was the main scaling concern v0.5 raised. Still open: no server-side file-size/format limits or compression have been added.
13. ~~Information density after removing item categories~~ — **resolved: category was reinstated** and both menu-facing views group by it again.
14. **New (this sync): large-text mode coverage.** The current implementation applies broad CSS overrides to the most common screens (nav, headers, cards, buttons, forms, tables) rather than exhaustively re-styling every single element on every view — worth a periodic pass to confirm no screen was missed as new UI is added.
