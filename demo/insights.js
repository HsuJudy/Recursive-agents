// agent: claude-code  2026-10-17
// Insights tab: charts of how the team improved. Plain SVG, no libraries. Reads /api/insights.
// Colours are the first three slots of a validated categorical palette (dark mode, checked against the panel surface).
(() => {
const COL = { train: "#3987e5", val: "#d95926", test: "#199e70" };
const NAME = { train: "Practice tasks", val: "Checking tasks", test: "Unseen tasks" };
const INK = "#eef0f4", DIM = "#93a1b8", GRID = "#243044", SURF = "#141b27";
const RAMP = ["#0d366b", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4"]; // single-hue magnitude ramp

const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const pct = v => (v == null ? "–" : Math.round(v * 100) + "%");
const pts = v => (v == null ? "–" : (v >= 0 ? "+" : "") + Math.round(v * 100));
const short = m => String(m || "").split("/").pop();
const money = v => "$" + (v < 0.01 && v > 0 ? v.toFixed(4) : v.toFixed(2));
const tip = html => `data-tip="${esc(html)}"`;

const css = document.createElement("style");
css.textContent = `
#insightsView { padding:24px 32px; }
.ins-grid { display:grid; grid-template-columns:1fr 1fr; gap:24px; }
@media (max-width:1100px) { .ins-grid { grid-template-columns:1fr; } }
.ins-wide { grid-column:1/-1; }
.ins-panel { background:#141b27; border:1px solid #243044; border-radius:12px; padding:20px 24px; min-width:0; }
.ins-panel h3 { margin:0 0 4px; font-size:24px; font-weight:700; }
.ins-sub { color:#93a1b8; font-size:17px; margin:0 0 14px; }
.ins-legend { display:flex; gap:20px; flex-wrap:wrap; margin:0 0 8px; font-size:16px; }
.ins-legend i { display:inline-block; width:12px; height:12px; border-radius:50%; margin-right:8px; vertical-align:-1px; }
.ins-legend i.dia { border-radius:2px; transform:rotate(45deg) scale(.85); }
.ins-tiles { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:24px; }
@media (max-width:900px) { .ins-tiles { grid-template-columns:1fr 1fr; } }
.ins-tile { background:#141b27; border:1px solid #243044; border-radius:12px; padding:14px 20px; }
.ins-tile span { font-size:15px; color:#93a1b8; }
.ins-tile b { display:block; font-size:40px; line-height:1.15; }
.ins-note { padding:12px 18px; margin-bottom:20px; background:#3a2f12; border:1px solid #ffc247; border-radius:10px; color:#ffc247; font-size:17px; }
.ins-panel svg { width:100%; max-width:900px; height:auto; display:block; margin:0 auto; }
.ins-panel svg text { font-family:inherit; }
.ins-panel details { margin-top:10px; }
.ins-panel summary { cursor:pointer; color:#93a1b8; font-size:15px; }
.ins-table { width:100%; border-collapse:collapse; font-size:16px; margin-top:8px; }
.ins-table th { text-align:left; color:#93a1b8; font-weight:600; border-bottom:1px solid #243044; padding:6px 8px; }
.ins-table td { padding:6px 8px; border-bottom:1px solid #1c2535; vertical-align:top; }
.ins-table td.n, .ins-table th.n { text-align:right; font-variant-numeric:tabular-nums; }
.ins-scroll { max-height:560px; overflow:auto; }
.ins-ramp { display:inline-block; width:160px; height:12px; border-radius:6px; vertical-align:middle; margin:0 8px; background:linear-gradient(90deg,${RAMP.join(",")}); }
#tip { position:fixed; display:none; z-index:50; pointer-events:none; background:#0b0f17; border:1px solid #2c3a52; border-radius:8px; padding:8px 12px; font-size:15px; max-width:380px; line-height:1.4; }
`;
document.head.appendChild(css);
const tipEl = document.createElement("div");
tipEl.id = "tip";
document.body.appendChild(tipEl);
document.addEventListener("mousemove", e => {
  const t = e.target.closest && e.target.closest("[data-tip]");
  if (!t) { tipEl.style.display = "none"; return; }
  tipEl.innerHTML = t.getAttribute("data-tip");
  tipEl.style.display = "block";
  tipEl.style.left = Math.min(e.clientX + 14, innerWidth - tipEl.offsetWidth - 8) + "px";
  tipEl.style.top = Math.min(e.clientY + 14, innerHeight - tipEl.offsetHeight - 8) + "px";
});

const tbl = (heads, rows) => `<div class="ins-scroll"><table class="ins-table"><tr>${heads.map(h => `<th class="${h.n ? "n" : ""}">${esc(h.t)}</th>`).join("")}</tr>` +
  rows.map(r => `<tr>${r.map((c, i) => `<td class="${heads[i].n ? "n" : ""}">${c}</td>`).join("")}</tr>`).join("") + `</table></div>`;
const legend = items => `<div class="ins-legend">${items.map(i => `<span><i class="${i.shape || ""}" style="background:${i.color}"></i>${esc(i.name)}</span>`).join("")}</div>`;
const panel = (title, sub, body, table, wide) => `<section class="ins-panel ${wide ? "ins-wide" : ""}"><h3>${esc(title)}</h3><p class="ins-sub">${sub}</p>${body}` +
  (table ? `<details><summary>View as table</summary>${table}</details>` : "") + `</section>`;

// ---- charts ------------------------------------------------------------------------------
function lineChart(cats, series, extraTip) {
  const W = 760, H = 300, Lm = 56, Rm = 130, Tm = 14, Bm = 40, iw = W - Lm - Rm, ih = H - Tm - Bm;
  const x = i => Lm + (cats.length === 1 ? iw / 2 : (iw * i) / (cats.length - 1));
  const y = v => Tm + ih * (1 - v);
  let g = "";
  for (const v of [0, 0.25, 0.5, 0.75, 1])
    g += `<line x1="${Lm}" x2="${W - Rm}" y1="${y(v)}" y2="${y(v)}" stroke="${GRID}" stroke-width="1"/><text x="${Lm - 10}" y="${y(v) + 5}" text-anchor="end" fill="${DIM}" font-size="16">${Math.round(v * 100)}%</text>`;
  cats.forEach((c, i) => { g += `<text x="${x(i)}" y="${H - 14}" text-anchor="middle" fill="${DIM}" font-size="16">${esc(c)}</text>`; });
  let lines = "", dots = "", ends = [];
  for (const s of series) {
    let d = "", pen = false, last = null;
    s.vals.forEach((v, i) => {
      if (v == null) { pen = false; return; }
      d += `${pen ? "L" : "M"}${x(i)} ${y(v)} `; pen = true; last = { i, v };
      dots += `<circle cx="${x(i)}" cy="${y(v)}" r="5" fill="${s.color}" stroke="${SURF}" stroke-width="2"/>`;
    });
    lines += `<path d="${d}" fill="none" stroke="${s.color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>`;
    if (last) ends.push({ y: y(last.v), x: x(last.i), text: `${s.short || s.name} ${pct(last.v)}` });
  }
  let labels = "";
  const groups = [];
  for (const e of ends.sort((a, b) => a.y - b.y)) { // ends that would collide share one label
    const g = groups[groups.length - 1];
    if (g && e.y - g.y < 20) g.texts.push(e.text); else groups.push({ x: e.x, y: e.y, texts: [e.text] });
  }
  for (const g of groups) labels += `<text x="${g.x + 12}" y="${g.y + 5}" fill="${INK}" font-size="16">${esc(g.texts.join(" · "))}</text>`;
  const bw = cats.length === 1 ? iw : iw / (cats.length - 1);
  const hover = cats.map((c, i) => {
    const rows = series.map(s => `${esc(s.name)}: <b>${pct(s.vals[i])}</b>`).join("<br>");
    return `<rect x="${x(i) - bw / 2}" y="${Tm}" width="${bw}" height="${ih}" fill="transparent" ${tip(`<b>${esc(c)}</b><br>${rows}${extraTip ? "<br>" + extraTip(i) : ""}`)}/>`;
  }).join("");
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Line chart of pass rate by team version">${g}${lines}${dots}${labels}${hover}</svg>`;
}

function columnChart(cats, vals, tipFor) {
  const W = 760, H = 240, Lm = 56, Rm = 24, Tm = 20, Bm = 40, iw = W - Lm - Rm, ih = H - Tm - Bm;
  const top = Math.max(0.04, Math.ceil(Math.max(...vals.filter(v => v != null), 0) * 1.3 * 25) / 25); // multiple of 4% so quarter ticks are whole percents
  const y = v => Tm + ih * (1 - v / top), slot = iw / cats.length, bw = Math.min(24, slot * 0.5);
  let g = "";
  for (let k = 0; k <= 4; k++) { const v = (top * k) / 4;
    g += `<line x1="${Lm}" x2="${W - Rm}" y1="${y(v)}" y2="${y(v)}" stroke="${GRID}"/><text x="${Lm - 10}" y="${y(v) + 5}" text-anchor="end" fill="${DIM}" font-size="16">${Math.round(v * 100)}%</text>`; }
  let bars = "";
  cats.forEach((c, i) => {
    const cx = Lm + slot * (i + 0.5), v = vals[i];
    bars += `<text x="${cx}" y="${H - 14}" text-anchor="middle" fill="${DIM}" font-size="16">${esc(c)}</text>`;
    if (v == null) return;
    const x0 = cx - bw / 2, y0 = y(v), yb = y(0), r = Math.min(4, yb - y0);
    bars += `<path d="M${x0} ${yb} L${x0} ${y0 + r} Q${x0} ${y0} ${x0 + r} ${y0} L${x0 + bw - r} ${y0} Q${x0 + bw} ${y0} ${x0 + bw} ${y0 + r} L${x0 + bw} ${yb} Z" fill="${COL.train}"/>` +
      `<text x="${cx}" y="${y0 - 8}" text-anchor="middle" fill="${INK}" font-size="16">${pct(v)}</text>` +
      `<rect x="${cx - slot / 2}" y="${Tm}" width="${slot}" height="${ih}" fill="transparent" ${tip(tipFor(i))}/>`;
  });
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Column chart">${g}${bars}</svg>`;
}

function barRows(rows, fmt) { // horizontal bars: label left, value at the tip
  const W = 760, rh = 34, Lm = 300, Rm = 90, H = rows.length * rh + 8, max = Math.max(...rows.map(r => r.v), 1e-9);
  let s = "";
  rows.forEach((r, i) => {
    const y = 4 + i * rh, w = Math.max(2, ((W - Lm - Rm) * r.v) / max);
    s += `<text x="${Lm - 12}" y="${y + 19}" text-anchor="end" fill="${INK}" font-size="16">${esc(r.label)}</text>` +
      `<path d="M${Lm} ${y + 5} L${Lm + w - 4} ${y + 5} Q${Lm + w} ${y + 5} ${Lm + w} ${y + 9} L${Lm + w} ${y + 19} Q${Lm + w} ${y + 23} ${Lm + w - 4} ${y + 23} L${Lm} ${y + 23} Z" fill="${COL.train}"/>` +
      `<text x="${Lm + w + 10}" y="${y + 19}" fill="${INK}" font-size="16">${esc(fmt(r.v))}</text>` +
      `<rect x="0" y="${y}" width="${W}" height="${rh}" fill="transparent" ${tip(r.tip)}/>`;
  });
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Bar chart">${s}</svg>`;
}

function scatter(gate) {
  const W = 760, H = 380, Lm = 64, Rm = 24, Tm = 16, Bm = 56, iw = W - Lm - Rm, ih = H - Tm - Bm;
  const xs = gate.map(g => g.train * 100), ys = gate.map(g => g.val * 100);
  const lo = (a, floor) => Math.min(floor, Math.floor((Math.min(...a) - 3) / 5) * 5);
  const hi = (a, ceil) => Math.max(ceil, Math.ceil((Math.max(...a) + 3) / 5) * 5);
  const x0 = lo(xs, -10), x1 = hi(xs, 10), y0 = lo(ys, -10), y1 = hi(ys, 10);
  const X = v => Lm + (iw * (v - x0)) / (x1 - x0), Y = v => Tm + ih * (1 - (v - y0) / (y1 - y0));
  const step = Math.max(x1 - x0, y1 - y0) > 40 ? 10 : 5;
  let g = "";
  for (let v = Math.ceil(x0 / step) * step; v <= x1; v += step)
    g += `<line x1="${X(v)}" x2="${X(v)}" y1="${Tm}" y2="${Tm + ih}" stroke="${GRID}"/><text x="${X(v)}" y="${H - 34}" text-anchor="middle" fill="${DIM}" font-size="16">${v}</text>`;
  for (let v = Math.ceil(y0 / step) * step; v <= y1; v += step)
    g += `<line x1="${Lm}" x2="${W - Rm}" y1="${Y(v)}" y2="${Y(v)}" stroke="${GRID}"/><text x="${Lm - 10}" y="${Y(v) + 5}" text-anchor="end" fill="${DIM}" font-size="16">${v}</text>`;
  // the two keep thresholds: practice must rise by 3+ points, checking must not fall more than 2
  g += `<line x1="${X(3)}" x2="${X(3)}" y1="${Tm}" y2="${Tm + ih}" stroke="${DIM}" stroke-width="1.5"/>` +
       `<line x1="${Lm}" x2="${W - Rm}" y1="${Y(-2)}" y2="${Y(-2)}" stroke="${DIM}" stroke-width="1.5"/>` +
       `<text x="${X(3) + 8}" y="${Tm + ih - 8}" fill="${INK}" font-size="16">practice +3 or more</text>` +
       `<text x="${Lm + 8}" y="${Y(-2) + 20}" fill="${INK}" font-size="16">checking not below −2</text>` +
       `<text x="${W - Rm - 6}" y="${Tm + 16}" text-anchor="end" fill="${INK}" font-size="16" font-weight="700">keep zone</text>`;
  g += `<text x="${Lm + iw / 2}" y="${H - 8}" text-anchor="middle" fill="${DIM}" font-size="16">Change on practice tasks (points)</text>` +
       `<text transform="translate(16 ${Tm + ih / 2}) rotate(-90)" text-anchor="middle" fill="${DIM}" font-size="16">Change on checking tasks (points)</text>`;
  let dots = "";
  gate.forEach(p => {
    const cx = X(p.train * 100), cy = Y(p.val * 100), t = tip(`<b>${p.action === "keep" ? "Kept" : "Rejected"}</b> · round ${p.round}<br>${esc(p.text)}<br>practice ${pts(p.train)}, checking ${pts(p.val)}<br><i>${esc(p.reason)}</i>`);
    dots += p.action === "keep"
      ? `<circle cx="${cx}" cy="${cy}" r="7" fill="${COL.train}" stroke="${SURF}" stroke-width="2" ${t}/>`
      : `<path d="M${cx} ${cy - 9} L${cx + 9} ${cy} L${cx} ${cy + 9} L${cx - 9} ${cy} Z" fill="${COL.val}" stroke="${SURF}" stroke-width="2" ${t}/>`;
  });
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Scatter of each proposal by its effect on practice and checking tasks">${g}${dots}</svg>`;
}

function taskGrid(lineage, tasks) {
  const cols = lineage.filter(v => v.has_data), cw = Math.max(84, Math.min(200, Math.floor(640 / Math.max(cols.length, 1)))), ch = 18, gap = 2, Lm = 64, Tm = 34, gh = 28;
  const groups = ["train", "val", "test"].map(sp => ({ sp, rows: tasks.filter(t => t.split === sp) })).filter(g => g.rows.length);
  const H = Tm + groups.reduce((a, g) => a + gh + g.rows.length * (ch + gap), 0) + 8, W = Lm + cols.length * (cw + gap) + 8;
  const color = s => RAMP[Math.max(0, Math.min(RAMP.length - 1, Math.round(s * (RAMP.length - 1))))];
  let s = cols.map((c, i) => `<text x="${Lm + i * (cw + gap) + cw / 2}" y="22" text-anchor="middle" fill="${DIM}" font-size="16">${esc(c.name)}</text>`).join("");
  let y = Tm;
  for (const g of groups) {
    s += `<text x="0" y="${y + 18}" fill="${INK}" font-size="16" font-weight="700">${NAME[g.sp]}</text>`; y += gh;
    for (const t of g.rows) {
      s += `<text x="${Lm - 8}" y="${y + 14}" text-anchor="end" fill="${DIM}" font-size="14">${esc(t.id)}</text>`;
      cols.forEach((c, i) => {
        const v = c.scores[t.id], x = Lm + i * (cw + gap);
        if (v == null) { s += `<rect x="${x}" y="${y}" width="${cw}" height="${ch}" rx="2" fill="none" stroke="${GRID}"/>`; return; }
        const prev = i > 0 ? cols[i - 1].scores[t.id] : null, d = prev == null ? 0 : v - prev, cx = x + cw / 2, cy = y + ch / 2;
        s += `<rect x="${x}" y="${y}" width="${cw}" height="${ch}" rx="2" fill="${color(v)}" ${tip(`<b>${esc(t.id)}</b> (${esc(t.family)}) · ${esc(c.name)}<br>pass rate ${pct(v)}${prev == null ? "" : `<br>was ${pct(prev)} in ${esc(cols[i - 1].name)}`}`)}/>`;
        if (d >= 0.3) s += `<path d="M${cx} ${cy - 5} L${cx + 5} ${cy + 4} L${cx - 5} ${cy + 4} Z" fill="${INK}" pointer-events="none"/>`;
        if (d <= -0.3) s += `<path d="M${cx} ${cy + 5} L${cx + 5} ${cy - 4} L${cx - 5} ${cy - 4} Z" fill="${INK}" pointer-events="none"/>`;
      });
      y += ch + gap;
    }
  }
  return `<div class="ins-scroll"><svg viewBox="0 0 ${W} ${H}" style="width:${W}px;max-width:none" role="img" aria-label="Pass rate of every task in every team version">${s}</svg></div>`;
}

// ---- page --------------------------------------------------------------------------------
function build(d) {
  if (d.error) return `<div class="ins-note">Insights could not load: ${esc(d.error)}</div>`;
  const L = d.lineage, wd = L.filter(v => v.has_data), parts = [];
  const sum = (a, f) => a.reduce((t, x) => t + f(x), 0);
  const bestTest = wd.length ? Math.max(...wd.map(v => v.test ?? -1)) : null;
  const spendRun = sum(d.spend, s => s.cost);
  const tile = (l, v) => `<div class="ins-tile"><span>${l}</span><b>${v}</b></div>`;
  let html = `<div class="ins-tiles">${tile("Attempts recorded for this run", wd.length ? sum(wd, v => v.n) : "–")}${tile("Team versions scored", `${wd.length} of ${L.length}`)}` +
    `${tile("Best score on unseen tasks", bestTest != null && bestTest >= 0 ? pct(bestTest) : "–")}${tile("Spend on this run", wd.length ? money(spendRun) : "–")}</div>`;
  if (!d.run) html += `<div class="ins-note">Pick a run at the top of the page.</div>`;
  else if (!wd.length) html += `<div class="ins-note">${/^real/.test(d.run)
    ? "This run's attempts are not in the cache yet. Charts fill in as the loop scores each team version."
    : "Offline runs do not write the attempt cache, so scores over versions are not recorded for this run. The proposal chart and receipts below still work."}</div>`;

  if (wd.length) {
    const cats = L.map(v => v.name);
    const series = ["train", "val", "test"].map(k => ({ key: k, name: NAME[k], short: k === "test" ? "unseen" : k === "val" ? "checking" : "practice", color: COL[k], vals: L.map(v => (v.has_data ? v[k] : null)) }));
    parts.push(panel("Score by team version", "Average pass rate per version. Practice tasks teach the proposer, checking tasks decide keep or reject, unseen tasks never decide anything.",
      legend(series.map(s => ({ name: s.name, color: s.color }))) + lineChart(cats, series, i => L[i].has_data ? `${L[i].n} attempts` : "no attempts recorded"),
      tbl([{ t: "Version" }, { t: "Rules" }, { t: "Practice", n: 1 }, { t: "Checking", n: 1 }, { t: "Unseen", n: 1 }, { t: "Attempts", n: 1 }],
        L.map(v => [esc(v.name), v.units, pct(v.train), pct(v.val), pct(v.test), v.has_data ? v.n : "–"])), true));
  }
  if (d.gate.length) parts.push(panel("Why each proposal was kept or rejected", "One mark per proposal. A change is kept only inside the keep zone (and its gain must also beat its own noise).",
    legend([{ name: "Kept", color: COL.train }, { name: "Rejected", color: COL.val, shape: "dia" }]) + scatter(d.gate),
    tbl([{ t: "Round", n: 1 }, { t: "Result" }, { t: "Change" }, { t: "Practice", n: 1 }, { t: "Checking", n: 1 }, { t: "Why" }],
      d.gate.map(g => [g.round, g.action === "keep" ? "Kept" : "Rejected", esc(g.text), pts(g.train), pts(g.val), esc(g.reason)]))));
  if (wd.length) parts.push(panel("Overconfidence by version", "How often the team said “done” and the hidden tests disagreed, across every task scored for that version.",
    columnChart(L.map(v => v.name), L.map(v => (v.has_data ? v.over : null)), i => `<b>${esc(L[i].name)}</b><br>said done but was wrong in ${pct(L[i].over)} of ${L[i].n} attempts`),
    tbl([{ t: "Version" }, { t: "Said done, tests disagreed", n: 1 }], L.map(v => [esc(v.name), v.has_data ? pct(v.over) : "–"]))));
  if (d.receipts.length) parts.push(panel("Receipts", "Every surviving change with its measured effect, in points. “Removal cost” is how much the score falls if it is taken out.",
    tbl([{ t: "Change" }, { t: "Round", n: 1 }, { t: "Practice", n: 1 }, { t: "Checking", n: 1 }, { t: "Removal cost", n: 1 }, { t: "After model swap", n: 1 }],
      d.receipts.map(r => [esc(r.text), r.round ?? "–", pts(r.train), pts(r.val), pts(r.worth), pts(r.swap)]))));
  if (wd.length && d.tasks.length) parts.push(panel("Task by task", "Every task in every team version. Lighter is a higher pass rate. A triangle marks a task that moved by a third or more since the previous version.",
    `<div class="ins-legend"><span>Lower<span class="ins-ramp"></span>Higher</span><span>▲ improved &nbsp; ▼ got worse</span></div>` + taskGrid(L, d.tasks), "", true));
  if (d.all_versions.length) parts.push(panel("Every team version in the recorded attempts", "Compare rows with the same task count only; older experiments may have used a different task set. “File” shows where the version is saved, if it still is.",
    tbl([{ t: "File" }, { t: "Rules", n: 1 }, { t: "Tasks", n: 1 }, { t: "Attempts", n: 1 }, { t: "Practice", n: 1 }, { t: "Checking", n: 1 }, { t: "Unseen", n: 1 }, { t: "Said done, wrong", n: 1 }],
      d.all_versions.map(v => [esc(v.names[0]) + (v.names.length > 1 ? ` <span style="color:${DIM}">+${v.names.length - 1}</span>` : ""), v.units ?? "–", v.tasks, v.n, pct(v.train), pct(v.val), pct(v.test), pct(v.over)])), "", true));
  const sp = d.spend.length ? d.spend : d.spend_all, spLabel = d.spend.length ? "This run" : "All recorded runs";
  if (sp.length) parts.push(panel("Spend by model", `${spLabel}, from recorded token counts and Crusoe’s listed prices.`,
    barRows(sp.map(s => ({ label: short(s.model), v: s.cost, tip: `<b>${esc(short(s.model))}</b><br>${s.prompt.toLocaleString()} tokens in, ${s.completion.toLocaleString()} out` })), money),
    tbl([{ t: "Model" }, { t: "Tokens in", n: 1 }, { t: "Tokens out", n: 1 }, { t: "Cost", n: 1 }], sp.map(s => [esc(short(s.model)), s.prompt.toLocaleString(), s.completion.toLocaleString(), money(s.cost)]))));
  if (d.judge.length > 1) parts.push(panel("Judge scorecard over time", "Share of the hackathon checks the repo passes, scored by code. Each point is one scoring.",
    lineChart(d.judge.map((_, i) => "#" + (i + 1)), [{ name: "Judge score", short: "judge", color: COL.train, vals: d.judge.map(j => j.overall) }], i => esc(d.judge[i].label)),
    tbl([{ t: "#", n: 1 }, { t: "Label" }, { t: "Score", n: 1 }], d.judge.map((j, i) => [i + 1, esc(j.label), pct(j.overall)]))));
  return html + `<div class="ins-grid">${parts.join("")}</div>`;
}

let last = "";
window.renderInsights = async run => {
  try {
    const txt = await (await fetch("/api/insights?id=" + encodeURIComponent(run || ""))).text();
    if (txt === last) return; // nothing changed: leave the page (and any open table) alone
    last = txt;
    document.getElementById("insightsView").innerHTML = build(JSON.parse(txt));
  } catch (e) {
    document.getElementById("insightsView").innerHTML = `<div class="ins-note">Insights could not load: ${esc(e.message)}</div>`;
  }
};
})();
