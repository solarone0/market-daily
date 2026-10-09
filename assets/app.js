(() => {
  const $ = (id) => document.getElementById(id);
  marked.use({ tokenizer: { del: () => undefined } });
  let market = null;
  let range = 66;
  try { range = Number(localStorage.getItem("range") ?? 66); } catch (e) {}

  const fmt = (v, unit) => {
    const digits = v >= 1000 ? 0 : v >= 100 ? 1 : 2;
    const n = v.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
    if (unit === "$") return "$" + n;
    if (unit === "%") return n + "%";
    return n;
  };
  const pct = (c) => `<span class="${c > 0 ? "up" : c < 0 ? "down" : ""}">${c > 0 ? "▲" : c < 0 ? "▼" : ""}${Math.abs(c).toFixed(2)}%</span>`;

  $("dateline").textContent = new Date().toLocaleDateString("ko-KR", {
    year: "numeric", month: "long", day: "numeric", weekday: "long", timeZone: "Asia/Seoul",
  });

  function spark(points) {
    const w = 300, h = 56, pad = 3;
    const vals = points.map((p) => p[1]);
    const min = Math.min(...vals), max = Math.max(...vals);
    const x = (i) => (i / (vals.length - 1)) * w;
    const y = (v) => pad + (1 - (v - min) / (max - min || 1)) * (h - pad * 2);
    const d = vals.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
    const color = vals.at(-1) >= vals[0] ? "var(--up)" : "var(--down)";
    return `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" role="img" aria-label="${points[0][0]}~${points.at(-1)[0]}">
      <path class="area" d="${d}L${w},${h}L0,${h}Z" fill="${color}"/>
      <path d="${d}" fill="none" stroke="${color}" stroke-width="1.6" vector-effect="non-scaling-stroke"/>
      <title>${points[0][0]} ${fmt(vals[0], "")} → ${points.at(-1)[0]} ${fmt(vals.at(-1), "")}</title>
    </svg>`;
  }

  function renderCharts() {
    let html = "", group = "";
    for (const s of market.series) {
      if (s.group !== group) { group = s.group; html += `<p class="group-title">${group}</p>`; }
      const pts = range ? s.points.slice(-range) : s.points;
      const periodChange = (pts.at(-1)[1] / pts[0][1] - 1) * 100;
      html += `<div class="chart">
        <div class="chart-head"><b>${s.name}</b><span class="v">${fmt(s.last, s.unit)} ${pct(s.change)}</span></div>
        ${spark(pts)}
        <div class="chart-head small muted"><span>${pts[0][0]}</span><span>기간 ${pct(periodChange)}</span></div>
      </div>`;
    }
    $("charts").innerHTML = html;
    document.querySelectorAll(".range button").forEach((b) => b.classList.toggle("on", Number(b.dataset.range) === range));
  }

  function renderTicker() {
    $("ticker").innerHTML = market.series
      .map((s) => `<div class="tick"><b>${s.name}</b><span class="v">${fmt(s.last, s.unit)}</span> ${pct(s.change)}</div>`)
      .join("");
    const t = new Date(market.updated);
    $("updated").textContent = "지표 갱신 " + t.toLocaleString("ko-KR", { timeZone: "Asia/Seoul", dateStyle: "medium", timeStyle: "short" }) + " (KST)";
  }

  document.querySelectorAll(".range button").forEach((b) =>
    b.addEventListener("click", () => {
      range = Number(b.dataset.range);
      try { localStorage.setItem("range", range); } catch (e) {}
      if (market) renderCharts();
    })
  );

  async function loadColumn(index) {
    const want = new URLSearchParams(location.search).get("d");
    const item = index.find((c) => c.date === want) || index[0];
    if (!item) { $("column").innerHTML = `<p class="muted">아직 칼럼이 없습니다.</p>`; return; }
    const md = await fetch(`data/columns/${item.date}.md`, { cache: "no-cache" }).then((r) => r.text());
    // 한글 앞 **굵게**는 CommonMark 규칙상 풀리지 않아 직접 바꾸고, 범위 표기(3~4%)가 취소선이 되지 않게 막는다
    const prepared = md.replace(/\*\*([^*\n]+?)\*\*/g, "<strong>$1</strong>");
    const html = DOMPurify.sanitize(marked.parse(prepared));
    $("column").innerHTML = `<p class="kicker">${item.date} · 오늘의 경제</p>` + html;
    $("column").querySelectorAll("a[href^='http']").forEach((a) => { a.target = "_blank"; a.rel = "noopener"; });
    document.title = `${item.title} | Market Daily`;
    $("archive").innerHTML = index
      .slice(0, 30)
      .map((c) => `<li class="${c.date === item.date ? "on" : ""}"><span>${c.date}</span><a href="?d=${c.date}">${c.title}</a></li>`)
      .join("");
  }

  fetch("data/market.json", { cache: "no-cache" })
    .then((r) => r.json())
    .then((d) => { market = d; renderTicker(); renderCharts(); })
    .catch(() => { $("charts").innerHTML = `<p class="muted small">지표를 불러오지 못했습니다.</p>`; });

  fetch("data/columns/index.json", { cache: "no-cache" })
    .then((r) => r.json())
    .then(loadColumn)
    .catch(() => { $("column").innerHTML = `<p class="muted">칼럼을 불러오지 못했습니다.</p>`; });
})();
