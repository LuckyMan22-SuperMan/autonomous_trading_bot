// ---------------------------------------------------------------- utilities
const $ = (id) => document.getElementById(id);
const fmtMoney = (v) => "₹" + Number(v).toLocaleString("en-IN", { maximumFractionDigits: 2 });
const cls = (v) => (v > 0 ? "pos" : v < 0 ? "neg" : "");

let STRATEGIES = {};

async function api(path, opts) {
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}

// ---------------------------------------------------------------- tabs
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    document.querySelectorAll(".tabpane").forEach((p) => p.classList.add("hidden"));
    $("tab-" + tab.dataset.tab).classList.remove("hidden");
  });
});

// ---------------------------------------------------------------- strategy load
async function loadStrategies() {
  const btSel = $("bt-strategy");
  const ppSel = $("pp-strategy");

  if (!btSel || !ppSel) return;

  try {
    STRATEGIES = await api("/api/strategies");
  } catch (e) {
    console.warn("Failed to fetch strategies from API, using fallback:", e);
    STRATEGIES = {
      sma_crossover: {
        label: "SMA Crossover",
        params: { fast: 20, slow: 50 }
      }
    };
  }

  const optionsHTML = Object.entries(STRATEGIES)
    .map(([k, v]) => `<option value="${k}">${v.label}</option>`)
    .join("");

  btSel.innerHTML = optionsHTML;
  ppSel.innerHTML = optionsHTML;

  renderParams();
}

function renderParams() {
  const btSel = $("bt-strategy");
  if (!btSel) return;
  
  const key = btSel.value;
  const params = STRATEGIES[key]?.params || {};
  const box = $("bt-params");
  if (!box) return;

  box.innerHTML = Object.entries(params)
    .map(([p, v]) =>
      `<label class="field"><span>${p}</span><input data-param="${p}" type="number" step="any" value="${v}" /></label>`
    ).join("");
}

function collectParams(scope) {
  const out = {};
  document.querySelectorAll(`${scope} [data-param]`).forEach((inp) => {
    if (inp.value !== "") out[inp.dataset.param] = parseFloat(inp.value);
  });
  return Object.keys(out).length ? out : null;
}

// ---------------------------------------------------------------- charts
let equityChart, paperChart;

function lineChart(canvasId, existing, labels, datasets) {
  if (existing) existing.destroy();
  const el = $(canvasId);
  if (!el) return null;

  return new Chart(el, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          labels: { color: "#8b949e", boxWidth: 12, font: { family: "Inter" } }
        }
      },
      scales: {
        x: {
          ticks: { color: "#8b949e", maxTicksLimit: 8 },
          grid: { color: "rgba(48, 54, 61, 0.5)" }
        },
        y: {
          ticks: { color: "#8b949e" },
          grid: { color: "rgba(48, 54, 61, 0.5)" }
        },
      },
      elements: { point: { radius: 0 } },
    },
  });
}

// ---------------------------------------------------------------- backtest
if ($("bt-strategy")) {
  $("bt-strategy").addEventListener("change", renderParams);
}

if ($("bt-run")) {
  $("bt-run").addEventListener("click", async () => {
    const btn = $("bt-run");
    $("bt-error").textContent = "";
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Running...`;
    try {
      const body = {
        ticker: $("bt-ticker").value.trim(),
        strategy: $("bt-strategy").value,
        period: $("bt-period").value,
        interval: $("bt-interval").value,
        initial_cash: parseFloat($("bt-cash").value),
        commission: parseFloat($("bt-commission").value),
        source: $("bt-source").value,
        market: $("bt-market").value,
        params: collectParams("#bt-params"),
      };
      const r = await api("/api/backtest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      renderBacktest(r);
    } catch (e) {
      $("bt-error").textContent = e.message;
    } finally {
      btn.disabled = false;
      btn.textContent = "Execute Backtest";
    }
  });
}

function metricCard(k, v, cssClass = "") {
  return `<div class="metric"><div class="k">${k}</div><div class="v ${cssClass}">${v}</div></div>`;
}
