const state = {
  analysis: null,
  loading: false,
  requestId: 0,
};

const symbolSelect = document.getElementById("symbolSelect");
const refreshButton = document.getElementById("refreshButton");
const initialSymbol = new URLSearchParams(window.location.search).get("symbol");

if (initialSymbol && [...symbolSelect.options].some((option) => option.value === initialSymbol)) {
  symbolSelect.value = initialSymbol;
}

refreshButton.addEventListener("click", () => loadAnalysis({ force: true }));
symbolSelect.addEventListener("change", () => loadAnalysis());

loadAnalysis();

async function loadAnalysis(options = {}) {
  const requestId = state.requestId + 1;
  state.requestId = requestId;
  state.loading = true;
  const symbol = symbolSelect.value;
  const force = Boolean(options.force);
  renderLoading(symbol);
  try {
    const forceQuery = force ? "&force=1" : "";
    const response = await fetch(`/api/fibonacci-master?symbols=${encodeURIComponent(symbol)}${forceQuery}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    if (requestId !== state.requestId) return;
    state.analysis = payload.analyses?.[0] || null;
    if (!state.analysis) throw new Error(payload.errors?.[symbol] || "没有生成分析结果");
    renderAnalysis(state.analysis);
  } catch (error) {
    if (requestId !== state.requestId) return;
    renderError(error);
  } finally {
    if (requestId === state.requestId) state.loading = false;
  }
}

function renderLoading(symbol) {
  document.getElementById("statusPanel").innerHTML = `<div>状态</div><strong>正在同步 ${escapeHtml(symbol)} 的真实行情、历史K线、斐波那契工具与双AI复核</strong>`;
}

function renderError(error) {
  document.getElementById("statusPanel").innerHTML = `<div>状态</div><strong>同步失败</strong><div>${escapeHtml(error.message || error)}</div>`;
}

function renderAnalysis(item) {
  const std = item.standardized_output;
  renderStatus(item, std);
  renderChartHeader(item, std);
  renderKlineChart(item, std);
  renderSidePanel(item, std);
  renderTables(item, std);
}

function renderStatus(item, std) {
  const values = [
    ["股票", `${std["股票名称"]} ${std["股票代码"]}`],
    ["当前价格", formatPrice(std["当前价格"])],
    ["更新时间", std["更新时间"]],
    ["数据源", std["数据来源"]],
    ["数据状态", std["数据状态"]],
    ["当前动作", std["最终结论"]["当前动作"]],
  ];
  document.getElementById("statusPanel").innerHTML = values.map(([label, value]) => `<section><div>${label}</div><strong>${value ?? "--"}</strong></section>`).join("");
}

function renderChartHeader(item, std) {
  const confluence = std["共振"];
  const conclusion = std["最终结论"];
  document.getElementById("chartHeader").innerHTML = [
    metric("主波段", `${std["主波段"]["A点价格"]} → ${std["主波段"]["B点价格"]}`),
    metric("最佳买入区间", `${formatPrice(std["买点"]["最佳买入区间"][0])} - ${formatPrice(std["买点"]["最佳买入区间"][1])}`),
    metric("共振评分", `${confluence["共振评分"]} / ${confluence["共振等级"]}`),
    metric("是否允许交易", conclusion["是否允许交易"] ? "允许" : "不允许"),
  ].join("");
}

function renderKlineChart(item, std) {
  const bars = item.chart_bars || [];
  const width = 1120;
  const height = 620;
  const plotWidth = 930;
  const labelX = plotWidth + 18;
  const overlays = collectOverlayPrices(item, std);
  const barPrices = bars.flatMap((bar) => [bar.high, bar.low]).filter(Number.isFinite);
  const barMin = Math.min(...barPrices);
  const barMax = Math.max(...barPrices);
  const barRange = Math.max(0.001, barMax - barMin);
  const visibleOverlays = overlays.filter((line) => {
    if (!Number.isFinite(Number(line.price))) return false;
    if (line.className !== "line-extension") return true;
    return Number(line.price) <= barMax + barRange * 1.25;
  });
  const prices = [...barPrices, ...visibleOverlays.map((line) => line.price)].filter(Number.isFinite);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const padding = 48;
  const scaleY = (price) => height - padding - ((price - minPrice) / Math.max(0.001, maxPrice - minPrice)) * (height - padding * 2);
  const step = plotWidth / Math.max(1, bars.length);
  const zone = std["买点"]["最佳买入区间"];
  const zoneY1 = scaleY(zone[1]);
  const zoneY2 = scaleY(zone[0]);
  const candles = bars.map((bar, index) => {
    const x = index * step + step / 2;
    const openY = scaleY(bar.open);
    const closeY = scaleY(bar.close);
    const highY = scaleY(bar.high);
    const lowY = scaleY(bar.low);
    const up = bar.close >= bar.open;
    const bodyY = Math.min(openY, closeY);
    const bodyH = Math.max(2, Math.abs(closeY - openY));
    return `<line x1="${x.toFixed(1)}" y1="${highY.toFixed(1)}" x2="${x.toFixed(1)}" y2="${lowY.toFixed(1)}" class="wick ${up ? "up" : "down"}"></line><rect x="${(x - Math.max(2, step * 0.28)).toFixed(1)}" y="${bodyY.toFixed(1)}" width="${Math.max(3, step * 0.56).toFixed(1)}" height="${bodyH.toFixed(1)}" class="body ${up ? "up" : "down"}"></rect>`;
  }).join("");
  const lines = visibleOverlays.map((line, index) => {
    const y = scaleY(line.price);
    const labelY = Math.max(18, Math.min(height - 12, y - 6 - (index % 3) * 12));
    return `<line x1="0" y1="${y.toFixed(1)}" x2="${plotWidth}" y2="${y.toFixed(1)}" class="${line.className}"></line><text x="${labelX}" y="${labelY.toFixed(1)}" class="axis-label">${line.label} ${formatPrice(line.price)}</text>`;
  }).join("");
  document.getElementById("klineChart").innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="K线图与斐波那契价格轴">
      <rect x="0" y="${Math.min(zoneY1, zoneY2).toFixed(1)}" width="${plotWidth}" height="${Math.abs(zoneY2 - zoneY1).toFixed(1)}" class="line-zone"></rect>
      <line x1="${plotWidth}" y1="0" x2="${plotWidth}" y2="${height}" class="label-divider"></line>
      ${candles}
      ${lines}
    </svg>
  `;
}

function collectOverlayPrices(item, std) {
  const retracement = std["回撤斐波那契"];
  const extension = std["上升映射与扩展"];
  return [
    { label: "当前价", price: item.current_price, className: "line-current" },
    { label: "回撤0.618", price: retracement["0.618"], className: "line-retracement" },
    { label: "回撤0.786/买点1", price: retracement["0.786"], className: "line-retracement" },
    { label: "上升0.236/买点2", price: extension["0.236"], className: "line-retracement" },
    { label: "止损", price: std["卖点"]["止损"], className: "line-stop" },
    { label: "止盈1 1.272", price: extension["1.272"], className: "line-extension" },
    { label: "止盈2 1.618", price: extension["1.618"], className: "line-extension" },
    { label: "强趋势 2.618", price: extension["2.618"], className: "line-extension" },
  ];
}

function renderSidePanel(item, std) {
  const confluence = std["共振"];
  const conclusion = std["最终结论"];
  document.getElementById("analysisPanel").innerHTML = `
    ${card("锚点确认", [
      `A点：${std["主波段"]["A点日期"]} / ${formatPrice(std["主波段"]["A点价格"])}`,
      `B点：${std["主波段"]["B点日期"]} / ${formatPrice(std["主波段"]["B点价格"])}`,
      `波段方向：${std["主波段"]["波段方向"]}`,
      `波段有效性：${std["主波段"]["波段有效性"]}`,
    ])}
    ${card("买点生成逻辑", [
      `买点1：${formatPrice(std["买点"]["买点1"])}，来源：${std["买点"]["买点1来源"]}`,
      `买点2：${formatPrice(std["买点"]["买点2"])}，来源：${std["买点"]["买点2来源"]}`,
      `最佳买入区间：${std["买点"]["最佳买入区间"].map(formatPrice).join(" - ")}`,
      `扩展线只用于止盈，不直接开仓。`,
    ])}
    ${card("多工具共振", [
      `评分：${confluence["共振评分"]}`,
      `等级：${confluence["共振等级"]}`,
      `三重共振：${confluence["是否满足三重共振"] ? "满足" : "未满足"}`,
      `参与工具：${(confluence["参与共振工具"] || []).join(" / ") || "暂无"}`,
    ])}
    ${card("当前交易结论", [
      `动作：${conclusion["当前动作"]}`,
      `是否允许交易：${conclusion["是否允许交易"] ? "允许" : "不允许"}`,
      `原因：${conclusion["原因"]}`,
      `风险提示：${conclusion["风险提示"]}`,
    ])}
  `;
}

function renderTables(item, std) {
  document.getElementById("waveTable").innerHTML = table("多波段明细表", ["波段", "A点", "B点", "0.618", "0.786", "1.618", "纳入"], item.multi_wave_table.map((row) => [
    row.wave_name,
    `${row.low_date} / ${formatPrice(row.anchor_low)}`,
    `${row.high_date} / ${formatPrice(row.anchor_high)}`,
    formatPrice(row.retracement_0_618),
    formatPrice(row.retracement_0_786),
    formatPrice(row.extension_1_618),
    row.included_in_final ? "是" : "否",
  ]));
  document.getElementById("toolTable").innerHTML = table("工具计算明细表", ["工具", "波段", "系数", "价格", "触达", "成功", "失败", "胜率"], item.win_rate_table.slice(0, 18).map((row) => [
    row.tool_name,
    row.wave_name,
    row.ratio,
    formatPrice(row.price),
    row.historical_touch_count,
    row.success_count,
    row.failure_count,
    `${row.success_rate}%`,
  ]));
  document.getElementById("riskTable").innerHTML = table("止损止盈表", ["项目", "价格", "来源"], [
    ["第一止盈", formatPrice(std["卖点"]["第一止盈"]), "上升映射/扩展1.272"],
    ["核心止盈", formatPrice(std["卖点"]["核心止盈"]), "上升映射/扩展1.618"],
    ["强趋势止盈", formatPrice(std["卖点"]["强趋势止盈"]), "上升映射/扩展2.618"],
    ["止损", formatPrice(std["卖点"]["止损"]), item.stop_loss.source],
  ]);
  document.getElementById("aiPanel").innerHTML = `
    <section class="analysis-card">
      <h2>AI解释区</h2>
      <p><strong>DeepSeek：</strong>${item.deepseek_review?.deepseek_structure_view || "等待结构复核"}</p>
      <p><strong>豆包：</strong>${item.doubao_review?.doubao_sentiment_view || "等待情绪复核"}</p>
      <p><strong>规则：</strong>AI不能改价格，只能解释结构和风险；最终动作由真实价格、斐波那契结构和硬性过滤规则决定。</p>
    </section>
  `;
}

function metric(label, value) {
  return `<div class="metric"><span>${label}</span><strong>${value ?? "--"}</strong></div>`;
}

function card(title, lines) {
  return `<section class="analysis-card"><h2>${title}</h2><ul>${lines.map((line) => `<li>${line}</li>`).join("")}</ul></section>`;
}

function table(title, headers, rows) {
  return `<h2>${title}</h2><table><thead><tr>${headers.map((item) => `<th>${item}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${cell ?? "--"}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
}

function formatPrice(value) {
  if (!Number.isFinite(Number(value))) return "--";
  return Number(value).toFixed(2);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[char]));
}
