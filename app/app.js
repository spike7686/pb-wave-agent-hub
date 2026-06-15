const REFRESH_MS = 30_000;

async function readJson(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} ${res.status}`);
  return res.json();
}

function fmtNum(v, digits = 2) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "-";
  return n.toFixed(digits);
}

function fmtPct(v, digits = 2) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "-";
  return `${n.toFixed(digits)}%`;
}

function fmtUsd(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "-";
  return `$${n.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function fmtPrice(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "-";
  if (Math.abs(n) >= 1000) return n.toFixed(2);
  if (Math.abs(n) >= 1) return n.toFixed(4);
  return n.toFixed(6);
}

function fmtTs(v) {
  if (!v) return "-";
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return String(v);
  return d.toLocaleString("zh-CN", { hour12: false });
}

function fmtMaybePct(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "-";
  return fmtPct(n);
}

function pnlToneClass(v) {
  const n = Number(v);
  if (!Number.isFinite(n) || n === 0) return "pnl-flat";
  return n > 0 ? "pnl-pos" : "pnl-neg";
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

function normalizeBooks(books) {
  return Object.values(books || {}).sort((a, b) => {
    const aa = Number(a?.summary?.equity_usd ?? 0);
    const bb = Number(b?.summary?.equity_usd ?? 0);
    return bb - aa;
  });
}

function renderMarket(rows) {
  const tbody = document.getElementById("market-table");
  tbody.innerHTML = "";
  rows.forEach((row) => {
    const signalSymbol = row.signal_symbol || row.binance_perp_symbol || row.binance_pair || "-";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.top15_position ?? "-"}</td>
      <td>
        <div class="symbol-cell">
          <strong>${row.symbol ?? "-"}</strong>
          <span>${signalSymbol}</span>
        </div>
      </td>
      <td>${fmtPct(row.change_24h_pct)}</td>
      <td>${fmtUsd(row.signal_quote_volume_usd ?? row.perp_quote_volume_24h)}</td>
      <td>${fmtUsd(row.perp_quote_volume_24h)}</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderBooks(books) {
  const wrap = document.getElementById("books");
  wrap.innerHTML = "";
  books.forEach((book) => {
    const s = book.summary || {};
    const openOrders = book.open_orders || [];
    const recentClosed = book.recent_closed_orders || [];
    const lastClosed = recentClosed[0];
    const card = document.createElement("article");
    card.className = "book";
    card.innerHTML = `
      <div class="book-head">
        <div>
          <p class="book-code">${book.strategy_code || "-"}</p>
          <h3>${book.strategy_label || book.strategy_id || "-"}</h3>
        </div>
        <span class="pill">${book.strategy_id || "-"}</span>
      </div>
      <div class="book-grid">
        <div class="kv"><span>权益</span><strong>${fmtUsd(s.equity_usd)}</strong></div>
        <div class="kv"><span>已实现</span><strong>${fmtUsd(s.realized_pnl_usd)}</strong></div>
        <div class="kv"><span>总成本</span><strong>${fmtUsd(s.cost_total_usd)}</strong></div>
        <div class="kv"><span>未实现</span><strong>${fmtUsd(s.unrealized_pnl_usd)}</strong></div>
        <div class="kv"><span>开仓</span><strong>${s.open_count ?? 0}</strong></div>
        <div class="kv"><span>平仓</span><strong>${s.closed_count ?? 0}</strong></div>
        <div class="kv"><span>胜率</span><strong>${fmtPct(Number(s.win_rate) * 100)}</strong></div>
        <div class="kv"><span>最大回撤</span><strong>${fmtPct(s.max_drawdown_pct)}</strong></div>
      </div>
      <div class="subpanel">
        <div class="subpanel-head">当前持仓</div>
        ${
          openOrders.length
            ? openOrders
                .slice(0, 5)
                .map(
                  (order) => `
          <div class="order-card live">
            <div class="order-card-head">
              <strong>${order.symbol || "-"}</strong>
              <span class="status-pill">持仓中</span>
            </div>
            <div class="order-meta">
              <span>入场价 ${fmtPrice(order.entry_price)}</span>
              <span>止损价 ${fmtPrice(order.stop_price_live ?? order.stop_price)}</span>
              <span>仓位 ${fmtUsd(order.size_usd)}</span>
              <span>未实现 <strong class="${pnlToneClass(order.unrealized_pnl_pct)}">${fmtPct(order.unrealized_pnl_pct)}</strong></span>
            </div>
            <div class="order-reason">${order.open_reason || order.signal_summary || "-"}</div>
          </div>`
                )
                .join("")
            : `<div class="empty">当前无持仓</div>`
        }
      </div>
      <div class="subpanel">
        <div class="subpanel-head">最近平仓</div>
        ${
          lastClosed
            ? `
          <div class="close-row">
            <strong>${lastClosed.symbol || "-"}</strong>
            <span>${fmtTs(lastClosed.close_time)}</span>
            <span class="${pnlToneClass(lastClosed.realized_pnl_pct)}">${fmtPct(lastClosed.realized_pnl_pct)}</span>
            <span>${lastClosed.close_reason || "-"}</span>
          </div>`
            : `<div class="empty">暂无平仓</div>`
        }
      </div>
    `;
    wrap.appendChild(card);
  });
}

function historyRowsForBook(book) {
  const openOrders = (book.open_orders || []).map((order) => ({
    ...order,
    _status: "持仓中",
    _sortTime: order.entry_time || order.entry_signal_time || "",
  }));
  const closedOrders = (book.recent_closed_orders || []).map((order) => ({
    ...order,
    _status: "已平仓",
    _sortTime: order.close_time || order.entry_time || "",
  }));
  return [...openOrders, ...closedOrders]
    .sort((a, b) => String(b._sortTime).localeCompare(String(a._sortTime)))
    .slice(0, 12);
}

function renderOrderHistory(books) {
  const wrap = document.getElementById("order-history");
  if (!wrap) return;
  wrap.innerHTML = "";
  books.forEach((book) => {
    const rows = historyRowsForBook(book);
    const card = document.createElement("article");
    card.className = "history-book";
    card.innerHTML = `
      <div class="history-book-head">
        <div>
          <p class="book-code">${book.strategy_code || "-"}</p>
          <h3>${book.strategy_label || book.strategy_id || "-"}</h3>
        </div>
      </div>
      <div class="table-wrap">
        ${
          rows.length
            ? `
          <table class="history-table">
            <thead>
              <tr>
                <th>状态</th>
                <th>币种</th>
                <th>入场时间</th>
                <th>入场价</th>
                <th>止损价</th>
                <th>仓位</th>
                <th>入场理由</th>
                <th>平仓时间</th>
                <th>平仓原因</th>
                <th>已实现盈亏</th>
              </tr>
            </thead>
            <tbody>
              ${rows
                .map(
                  (order) => `
              <tr class="${order._status === "持仓中" ? "row-live" : ""}">
                <td><span class="status-pill">${order._status}</span></td>
                <td>${order.symbol || "-"}</td>
                <td>${fmtTs(order.entry_time)}</td>
                <td>${fmtPrice(order.entry_price)}</td>
                <td>${fmtPrice(order.stop_price_live ?? order.stop_price)}</td>
                <td>${fmtUsd(order.size_usd)}</td>
                <td class="reason-cell">${order.open_reason || order.signal_summary || "-"}</td>
                <td>${order._status === "持仓中" ? "-" : fmtTs(order.close_time)}</td>
                <td>${order._status === "持仓中" ? "持仓中" : order.close_reason || "-"}</td>
                <td>${
                  order._status === "持仓中"
                    ? "-"
                    : `<span class="${pnlToneClass(order.realized_pnl_usd)}">${fmtUsd(order.realized_pnl_usd)} / ${fmtMaybePct(order.realized_pnl_pct)}</span>`
                }</td>
              </tr>`
                )
                .join("")}
            </tbody>
          </table>`
            : `<div class="empty">暂无仓位历史</div>`
        }
      </div>
    `;
    wrap.appendChild(card);
  });
}

function flattenEvents(books) {
  return books
    .flatMap((book) =>
      (book.recent_events || []).map((event) => ({
        ...event,
        strategy_code: book.strategy_code,
        strategy_label: book.strategy_label,
      }))
    )
    .sort((a, b) => String(b.created_at || b.captured_at_utc || "").localeCompare(String(a.created_at || a.captured_at_utc || "")))
    .slice(0, 18);
}

function renderEvents(books) {
  const wrap = document.getElementById("events");
  const events = flattenEvents(books);
  wrap.innerHTML = "";
  if (!events.length) {
    wrap.innerHTML = `<div class="empty">最近还没有事件</div>`;
    return;
  }
  events.forEach((event) => {
    const row = document.createElement("article");
    row.className = "event";
    row.innerHTML = `
      <div class="event-head">
        <strong>${event.strategy_code || "-"} · ${event.symbol || "-"}</strong>
        <span>${fmtTs(event.created_at || event.captured_at_utc)}</span>
      </div>
      <div class="event-body">${event.detail || event.reason || event.type || "-"}</div>
    `;
    wrap.appendChild(row);
  });
}

function renderSummary(summary) {
  setText("sum-equity", fmtUsd(summary.equity_usd));
  setText("sum-realized", fmtUsd(summary.realized_pnl_usd));
  setText("sum-cost", fmtUsd(summary.cost_total_usd));
  setText("sum-open", String(summary.open_count ?? "-"));
  setText("sum-closed", String(summary.closed_count ?? "-"));
  setText("sum-dd", fmtPct(summary.max_drawdown_pct));
  document.getElementById("summary-json").textContent = JSON.stringify(summary || {}, null, 2);
}

function renderRuntime(runtime) {
  const warnings = runtime?.warnings || [];
  const text =
    warnings.length > 0
      ? `有 ${warnings.length} 条 warning`
      : "运行正常";
  setText("health-text", text);
  document.getElementById("runtime-json").textContent = JSON.stringify(runtime || {}, null, 2);
}

function markRefreshTime() {
  setText("refresh-at", fmtTs(new Date().toISOString()));
}

async function boot() {
  try {
    const [market, trader] = await Promise.all([readJson("/api/market"), readJson("/api/trader")]);
    const books = normalizeBooks(trader.strategy_books || {});
    setText("market-snapshot", market.manifest?.snapshot_id || "-");
    setText("trader-snapshot", trader.last_processed_snapshot_id || "-");
    setText("market-count", `${(market.rows || []).length} 个币`);
    setText("books-count", `${books.length} 个策略`);
    renderMarket(market.rows || []);
    renderBooks(books);
    renderOrderHistory(books);
    renderEvents(books);
    renderSummary(trader.summary || {});
    renderRuntime(trader.runtime || {});
    markRefreshTime();
  } catch (err) {
    document.body.innerHTML = `<main class="page"><section class="panel"><h2>加载失败</h2><pre class="json-block">${String(err)}</pre></section></main>`;
  }
}

boot();
setInterval(boot, REFRESH_MS);
