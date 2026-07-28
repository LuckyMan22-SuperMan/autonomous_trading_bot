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

