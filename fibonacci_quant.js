const state = {
  analysis: null,
  loading: false,
  requestId: 0,
  manualAnchors: {},
};

const symbolSelect = document.getElementById("symbolSelect");
const refreshButton = document.getElementById("refreshButton");
const initialSymbol = new URLSearchParams(window.location.search).get("symbol");

if (initialSymbol && [...symbolSelect.options].some((option) => option.value === initialSymbol)) {
  symbolSelect.value = initialSymbol;
}

refreshButton.addEventListener("click", () => loadAnalysis({ force: true }));
symbolSelect.addEventListener("change", () => loadAnalysis());
document.addEventListener("click", (event) => {
  if (event.target.id === "applyManualAnchor") {
    applyManualAnchor();
  }
  if (event.target.id === "clearManualAnchor") {
    clearManualAnchor();
  }
});

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
  const effectiveItem = buildEffectiveAnalysis(item);
  const std = effectiveItem.standardized_output;
  renderStatus(effectiveItem, std);
  renderChartHeader(effectiveItem, std);
  renderKlineChart(effectiveItem, std);
  renderSidePanel(effectiveItem, std);
  renderManualAnchorPanel(effectiveItem);
  renderTables(effectiveItem, std);
}

function buildEffectiveAnalysis(item) {
  const anchor = state.manualAnchors[item.symbol];
  if (!anchor) return item;
  const clone = cloneJson(item);
  const std = clone.standardized_output;
  const low = Number(anchor.low);
  const high = Number(anchor.high);
  const range = high - low;
  const retracement = {};
  [0.236, 0.382, 0.5, 0.618, 0.786, 1].forEach((ratio) => {
    retracement[formatRatioKey(ratio)] = roundPrice(high - ratio * range);
  });
  const extension = {};
  [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1, 1.272, 1.382, 1.618, 2, 2.618].forEach((ratio) => {
    extension[formatRatioKey(ratio)] = roundPrice(low + ratio * range);
  });
  const stopLoss = roundPrice(Math.min(low, retracement["0.786"] * 0.98));

  std["主波段"] = {
    ...(std["主波段"] || {}),
    "A点日期": "手动锚点",
    "A点价格": low,
    "B点日期": "手动锚点",
    "B点价格": high,
    "波段方向": "上升",
    "波段有效性": "手动复盘",
  };
  std["回撤斐波那契"] = retracement;
  std["上升映射与扩展"] = extension;
  std["买点"] = {
    ...(std["买点"] || {}),
    "买点1": retracement["0.786"],
    "买点1来源": "手动主波段回撤0.786",
    "买点2": extension["0.236"],
    "买点2来源": "手动主波段上升映射0.236",
    "最佳买入区间": [retracement["0.786"], retracement["0.618"]],
  };
  std["卖点"] = {
    ...(std["卖点"] || {}),
    "第一止盈": extension["1.272"],
    "核心止盈": extension["1.618"],
    "强趋势止盈": extension["2.618"],
    "止损": stopLoss,
  };
  clone.stop_loss = {
    ...(clone.stop_loss || {}),
    price: stopLoss,
    source: "手动锚点：回撤0.786下方 / 主波段低点",
  };
  clone.multi_wave_table = [
    {
      wave_name: "manual_anchor_wave",
      low_date: "手动",
      high_date: "手动",
      anchor_low: low,
      anchor_high: high,
      retracement_0_618: retracement["0.618"],
      retracement_0_786: retracement["0.786"],
      extension_1_618: extension["1.618"],
      included_in_final: true,
    },
    ...(clone.multi_wave_table || []),
  ];
  clone.manual_anchor_mode = true;
  clone.manual_anchor = { low, high, range };
  return clone;
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
  const width = 1180;
  const height = 620;
  const plotWidth = 900;
  const labelX = plotWidth + 24;
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
  const labelPlacements = buildOverlayLabelPlacements(visibleOverlays, scaleY, height);
  const lines = visibleOverlays.map((line, index) => {
    const y = scaleY(line.price);
    const labelY = labelPlacements.get(index) ?? y;
    const anchorX = plotWidth + 6;
    return `<line x1="0" y1="${y.toFixed(1)}" x2="${plotWidth}" y2="${y.toFixed(1)}" class="${line.className}"></line><line x1="${anchorX}" y1="${y.toFixed(1)}" x2="${(labelX - 8).toFixed(1)}" y2="${labelY.toFixed(1)}" class="label-guide"></line><text x="${labelX}" y="${labelY.toFixed(1)}" class="axis-label">${line.label} ${formatPrice(line.price)}</text>`;
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

function buildOverlayLabelPlacements(overlays, scaleY, height) {
  const top = 20;
  const bottom = height - 16;
  const minGap = 19;
  const placed = overlays
    .map((line, index) => ({
      index,
      y: Math.max(top, Math.min(bottom, scaleY(line.price) - 4)),
    }))
    .sort((a, b) => a.y - b.y);

  for (let i = 1; i < placed.length; i += 1) {
    if (placed[i].y < placed[i - 1].y + minGap) {
      placed[i].y = placed[i - 1].y + minGap;
    }
  }

  const overflow = placed.length ? placed[placed.length - 1].y - bottom : 0;
  if (overflow > 0) {
    placed.forEach((item) => {
      item.y = Math.max(top, item.y - overflow);
    });
  }

  return new Map(placed.map((item) => [item.index, item.y]));
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

function renderManualAnchorPanel(item) {
  const anchor = state.manualAnchors[item.symbol] || {};
  const manual = Boolean(item.manual_anchor_mode);
  const message = manual
    ? `当前使用手动锚点：低点 ${formatPrice(anchor.low)}，高点 ${formatPrice(anchor.high)}。历史胜率仍沿用真实历史验证，不伪造样本。`
    : "可手动输入最高点、最低点进行复盘计算；应用后会刷新K线叠加线、买点、止损止盈和多波段明细。";
  document.getElementById("manualAnchorPanel").innerHTML = `
    <section class="manual-anchor-card">
      <div class="manual-anchor-head">
        <h2>手动锚点计算</h2>
        <span>${manual ? "手动复盘中" : "可选"}</span>
      </div>
      <div class="manual-anchor-form">
        <label>最高点
          <input id="manualAnchorHigh" type="number" min="0" step="0.01" inputmode="decimal" value="${anchor.high ?? ""}" placeholder="输入最高点" />
        </label>
        <label>最低点
          <input id="manualAnchorLow" type="number" min="0" step="0.01" inputmode="decimal" value="${anchor.low ?? ""}" placeholder="输入最低点" />
        </label>
        <button id="applyManualAnchor" type="button">应用并重算</button>
        <button id="clearManualAnchor" type="button">恢复自动锚点</button>
      </div>
      <p id="manualAnchorMessage">${escapeHtml(message)}</p>
    </section>
  `;
}

function applyManualAnchor() {
  if (!state.analysis) return;
  const high = Number(document.getElementById("manualAnchorHigh")?.value);
  const low = Number(document.getElementById("manualAnchorLow")?.value);
  const message = document.getElementById("manualAnchorMessage");
  if (!Number.isFinite(high) || !Number.isFinite(low) || high <= 0 || low <= 0 || high <= low) {
    if (message) message.textContent = "请输入有效锚点：最高点必须大于最低点，且都要大于0。";
    return;
  }
  state.manualAnchors[state.analysis.symbol] = { high: roundPrice(high), low: roundPrice(low) };
  renderAnalysis(state.analysis);
}

function clearManualAnchor() {
  if (!state.analysis) return;
  delete state.manualAnchors[state.analysis.symbol];
  renderAnalysis(state.analysis);
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
  document.getElementById("riskTable").innerHTML = table("止损止盈表", ["项目", "价格", "来源", "胜率", "触达", "成功", "失败"], [
    riskRewardRow(item, "第一止盈", std["卖点"]["第一止盈"], "上升映射/扩展1.272", "upward_projection", "1.272"),
    riskRewardRow(item, "核心止盈", std["卖点"]["核心止盈"], "上升映射/扩展1.618", "upward_projection", "1.618"),
    riskRewardRow(item, "强趋势止盈", std["卖点"]["强趋势止盈"], "上升映射/扩展2.618", "upward_projection", "2.618"),
    riskRewardRow(item, "止损", std["卖点"]["止损"], item.stop_loss.source, "fibonacci_retracement", "0.786"),
  ]);
  document.getElementById("aiPanel").innerHTML = `
    <section class="analysis-card ai-summary-card">
      <h2>AI解释区</h2>
      <p><strong>一句话：</strong>${escapeHtml(buildAiOneLineSummary(item))}</p>
    </section>
  `;
}

function buildAiOneLineSummary(item) {
  const fusionReason = item.ai_fusion?.reason || item.reason;
  if (fusionReason) return toOneLine(fusionReason, 120);
  const deepseek = item.deepseek_review?.deepseek_structure_view || "";
  const doubao = item.doubao_review?.doubao_sentiment_view || "";
  if (deepseek.includes("AIConsensusError") || doubao.includes("AIConsensusError")) {
    return "AI复核暂未完成，保持观察，不生成交易动作。";
  }
  const text = [deepseek, doubao].filter(Boolean).join("；");
  return text ? toOneLine(text, 120) : "等待 DeepSeek 与豆包完成复核。";
}

function toOneLine(value, maxLength) {
  const text = String(value ?? "").replace(/\s+/g, " ").trim();
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength)}...`;
}

function riskRewardRow(item, label, price, source, toolName, ratio) {
  const stat = findWinRateStat(item, toolName, ratio, price);
  return [
    label,
    formatPrice(price),
    source,
    formatWinRate(stat),
    stat ? stat.historical_touch_count : "--",
    stat ? stat.success_count : "--",
    stat ? stat.failure_count : "--",
  ];
}

function findWinRateStat(item, toolName, ratio, price) {
  const rows = item.win_rate_table || [];
  const ratioText = String(ratio);
  const candidates = rows.filter((row) => row.tool_name === toolName && String(row.ratio) === ratioText);
  if (!candidates.length) return null;
  const numericPrice = Number(price);
  if (!Number.isFinite(numericPrice)) return candidates[0];
  return [...candidates].sort((a, b) => Math.abs(Number(a.price) - numericPrice) - Math.abs(Number(b.price) - numericPrice))[0];
}

function formatWinRate(stat) {
  if (!stat) return "样本不足";
  const touches = Number(stat.historical_touch_count || 0);
  if (touches < 3) return `${stat.success_rate}% / 样本不足`;
  return `${stat.success_rate}%`;
}

function metric(label, value) {
  return `<div class="metric"><span>${label}</span><strong>${value ?? "--"}</strong></div>`;
}

function card(title, lines) {
  return `<section class="analysis-card"><h2>${title}</h2><ul>${lines.map((line) => `<li>${line}</li>`).join("")}</ul></section>`;
}

function table(title, headers, rows) {
  return `<h2>${title}</h2><div class="table-scroll"><table><thead><tr>${headers.map((item) => `<th>${item}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${cell ?? "--"}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

function formatPrice(value) {
  if (!Number.isFinite(Number(value))) return "--";
  return Number(value).toFixed(2);
}

function roundPrice(value) {
  return Math.round(Number(value) * 100) / 100;
}

function formatRatioKey(value) {
  return Number(value).toFixed(3).replace(/0+$/, "").replace(/\.$/, "");
}

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[char]));
}
