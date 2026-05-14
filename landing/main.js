/* ccm landing — interactivity & animations */

(function () {
  "use strict";

  const $  = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
  const prefersReducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ── Year in footer ─────────────────────────────────────── */
  const yearEl = $("#year");
  if (yearEl) yearEl.textContent = new Date().getFullYear();

  /* ── Scroll progress bar + sticky-nav blur ──────────────── */
  const progressEl = $("#scrollProgress");
  const topnavEl = $("#topnav");
  const onScroll = () => {
    const h = document.documentElement;
    const scrolled = h.scrollTop / Math.max(1, h.scrollHeight - h.clientHeight);
    if (progressEl) progressEl.style.width = (scrolled * 100).toFixed(2) + "%";
    if (topnavEl) topnavEl.classList.toggle("scrolled", h.scrollTop > 12);
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  /* ── Reveal on scroll ───────────────────────────────────── */
  const revealTargets = $$(".reveal");
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        const delay = parseInt(el.dataset.revealDelay || "0", 10);
        setTimeout(() => el.classList.add("in-view"), delay);
        io.unobserve(el);
      });
    }, { rootMargin: "0px 0px -10% 0px", threshold: 0.08 });
    revealTargets.forEach((el) => io.observe(el));
  } else {
    revealTargets.forEach((el) => el.classList.add("in-view"));
  }

  /* ── Claude-style 8-frame asterisk spinner ──────────────── */
  // From src/ccm/palette.py — the canonical SPINNER_FRAMES.
  const SPINNER_FRAMES = "✶✷✸✹✺✻✼✽".split("");
  const SPINNER_INTERVAL = 110;
  const spinnerTargets = ["#heroSpinner", "#tuiSpinner", "#bigSpinner", "#bigTuiSpinner"]
    .map((sel) => $(sel))
    .filter(Boolean);
  if (spinnerTargets.length && !prefersReducedMotion) {
    let i = 0;
    setInterval(() => {
      i = (i + 1) % SPINNER_FRAMES.length;
      const frame = SPINNER_FRAMES[i];
      spinnerTargets.forEach((el) => (el.textContent = frame));
    }, SPINNER_INTERVAL);
  }

  /* ── Animated stat counters ─────────────────────────────── */
  const counters = $$(".counter");
  if (counters.length && "IntersectionObserver" in window) {
    const animateCounter = (el) => {
      const target = parseInt(el.dataset.target || "0", 10);
      if (prefersReducedMotion || target === 0) { el.textContent = String(target); return; }
      const duration = 1400;
      const start = performance.now();
      const step = (now) => {
        const t = Math.min(1, (now - start) / duration);
        // ease-out cubic
        const eased = 1 - Math.pow(1 - t, 3);
        el.textContent = String(Math.round(target * eased));
        if (t < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    };
    const ioc = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (!e.isIntersecting) return;
        animateCounter(e.target);
        ioc.unobserve(e.target);
      });
    }, { threshold: 0.4 });
    counters.forEach((c) => ioc.observe(c));
  }

  /* ── Magnetic buttons ───────────────────────────────────── */
  const magnetics = $$(".magnetic");
  if (!prefersReducedMotion) {
    magnetics.forEach((el) => {
      el.addEventListener("mousemove", (e) => {
        const r = el.getBoundingClientRect();
        const dx = (e.clientX - (r.left + r.width / 2)) * 0.18;
        const dy = (e.clientY - (r.top + r.height / 2)) * 0.18;
        el.style.transform = `translate(${dx}px, ${dy}px)`;
      });
      el.addEventListener("mouseleave", () => { el.style.transform = ""; });
    });
  }

  /* ── Copy-to-clipboard ──────────────────────────────────── */
  const showToast = (msg = "Copied to clipboard") => {
    const t = $("#toast");
    if (!t) return;
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(showToast._timer);
    showToast._timer = setTimeout(() => t.classList.remove("show"), 1600);
  };
  const copyTo = async (text, sourceEl) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (_) {
      // Fallback for non-https / older browsers
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); } catch (e) { /* swallow */ }
      ta.remove();
    }
    showToast();
    if (sourceEl) {
      sourceEl.classList.add("copied");
      setTimeout(() => sourceEl.classList.remove("copied"), 1200);
    }
  };
  $$("[data-copy]").forEach((el) => {
    el.addEventListener("click", (e) => {
      e.preventDefault();
      copyTo(el.dataset.copy, el);
    });
  });

  /* ── Hero TUI live demo ─────────────────────────────────── */
  const projects = [
    {
      name: "my_projects/ccm",
      sessions: [
        ["build landing page",          "2m ago · 218 msgs"],
        ["fix textual _size shadow",    "3h ago · 64 msgs"],
        ["ci: actions for tests + pypi","yesterday · 110 msgs"],
        ["memory inspector v2",         "2d ago · 42 msgs"],
        ["stats: disk usage graph",     "3d ago · 88 msgs"],
        ["export to markdown",          "5d ago · 31 msgs"],
      ],
    },
    {
      name: "work/anthropic-sdk",
      sessions: [
        ["bump sdk to 4.7",             "5m ago · 88 msgs"],
        ["prompt-cache hit rate",       "1h ago · 142 msgs"],
        ["batch endpoint sample",       "yesterday · 56 msgs"],
        ["streaming chunks bugfix",     "2d ago · 71 msgs"],
        ["replace deprecated headers",  "3d ago · 39 msgs"],
        ["typing fix for tool_use",     "4d ago · 28 msgs"],
      ],
    },
    {
      name: "my_projects/agent-eval",
      sessions: [
        ["v3 eval rubric",              "12m ago · 312 msgs"],
        ["scorer regression",           "2h ago · 188 msgs"],
        ["dataset import script",       "yesterday · 64 msgs"],
        ["pass-rate dashboard",         "3d ago · 96 msgs"],
        ["normalize transcripts",       "4d ago · 47 msgs"],
        ["replay harness",              "1w ago · 81 msgs"],
      ],
    },
    {
      name: "notes/research-2026",
      sessions: [
        ["mech-interp reading list",    "1h ago · 22 msgs"],
        ["weekly summary",              "yesterday · 18 msgs"],
        ["citation export to bib",      "3d ago · 36 msgs"],
        ["chart of param counts",       "5d ago · 14 msgs"],
      ],
    },
  ];

  function setSessions(listEl, sessions, activeIdx = 0) {
    if (!listEl) return;
    listEl.innerHTML = sessions
      .map(([name, meta], idx) => `
        <li${idx === activeIdx ? ' class="active"' : ""}>
          <span class="t-name">${name}</span>
          <span class="t-meta">${meta}</span>
        </li>
      `)
      .join("");
  }

  // Cycle the hero TUI through projects
  const heroSessionsList = $("#sessionsList");
  const heroProjectLabel = $("#tuiProject");
  const heroProjectsList = $("#projectsList");
  if (heroSessionsList && heroProjectsList && !prefersReducedMotion) {
    let pIdx = 0;
    setInterval(() => {
      pIdx = (pIdx + 1) % projects.length;
      // mark active project in left pane (only for the first 4 entries — extra rows stay)
      $$("#projectsList > li").forEach((li, i) => li.classList.toggle("active", i === pIdx));
      if (heroProjectLabel) heroProjectLabel.textContent = projects[pIdx].name;
      // fade-swap the sessions list
      heroSessionsList.style.transition = "opacity 0.25s ease";
      heroSessionsList.style.opacity = "0";
      setTimeout(() => {
        setSessions(heroSessionsList, projects[pIdx].sessions, 0);
        heroSessionsList.style.opacity = "1";
      }, 250);
    }, 3600);
  }

  // Big TUI demo — cycle a bit slower, change selected session row too
  const bigProjects = $("#bigProjects");
  const bigSessions = $("#bigSessions");
  const bigProject  = $("#bigProject");
  const bigPaneTitle = $("#bigPaneTitle");
  if (bigProjects && bigSessions && !prefersReducedMotion) {
    let pIdx = 0;
    let sIdx = 0;
    let toggle = 0;
    setInterval(() => {
      // alternate: bump session selection, then advance project
      if (toggle % 3 !== 2) {
        sIdx = (sIdx + 1) % projects[pIdx].sessions.length;
        setSessions(bigSessions, projects[pIdx].sessions, sIdx);
      } else {
        pIdx = (pIdx + 1) % projects.length;
        sIdx = 0;
        $$("#bigProjects > li").forEach((li, i) => li.classList.toggle("active", i === pIdx));
        if (bigProject) bigProject.textContent = projects[pIdx].name;
        if (bigPaneTitle) bigPaneTitle.textContent = `Sessions of ${projects[pIdx].name}`;
        bigSessions.style.transition = "opacity 0.25s ease";
        bigSessions.style.opacity = "0";
        setTimeout(() => {
          setSessions(bigSessions, projects[pIdx].sessions, 0);
          bigSessions.style.opacity = "1";
        }, 250);
      }
      toggle++;
    }, 2200);
  }

  /* ── Command tabs ───────────────────────────────────────── */
  const cmdTitle = $("#cmdTitle");
  const cmdBody  = $("#cmdBody");
  const cmdTabs  = $$(".cmd-tab");

  // Each tab maps to {title, html} — HTML uses the .c-* span classes from style.css
  const commands = {
    ls: {
      title: "ccm ls --sort size -n 10",
      html: `<span class="prompt">$</span> <span class="cmd">ccm ls --sort size -n 10</span>

<span class="c-h">PROJECT                          SESSIONS   SIZE   LAST ACTIVE</span>
<span class="c-r">my_projects/agent-eval                <span class="c-acc">31</span>  12.0M   2 hours ago</span>
<span class="c-r">work/anthropic-sdk                    <span class="c-acc">22</span>   6.1M   3 hours ago</span>
<span class="c-r">work/claude-rag                       <span class="c-acc">17</span>   4.8M   yesterday</span>
<span class="c-r">my_projects/ccm                       <span class="c-acc">14</span>   3.2M   2 min ago</span>
<span class="c-r">notes/research-2026                    <span class="c-acc">8</span>   1.4M   3 days ago</span>
<span class="c-r">scratch/quick-tests                    <span class="c-acc">3</span>   0.4M   1 week ago</span>

<span class="c-ok">✓ 6 projects · 95 sessions · 28.0 MB total</span>`,
    },
    show: {
      title: "ccm show my_projects/ccm",
      html: `<span class="prompt">$</span> <span class="cmd">ccm show my_projects/ccm</span>

<span class="c-h">Project</span>
  Path        <span class="c-r">/home/q/my_projects/ccm</span>
  Encoded     <span class="c-dim">-home-q-my-projects-ccm</span>
  Sessions    <span class="c-acc">14</span>
  Memory      <span class="c-acc">3</span> file<span class="c-dim">(s)</span>
  Disk usage  <span class="c-acc">3.2 MB</span>
  Last active <span class="c-r">2 min ago</span>

<span class="c-h">Top sessions by size</span>
  <span class="c-r">218 msgs   142 KB   build landing page          2m ago</span>
  <span class="c-r">110 msgs    71 KB   ci: actions for tests       1d ago</span>
  <span class="c-r"> 88 msgs    51 KB   stats: disk usage graph     3d ago</span>

<span class="c-ok">tip: ccm sessions my_projects/ccm  →  full list</span>`,
    },
    sessions: {
      title: "ccm sessions my_projects/ccm",
      html: `<span class="prompt">$</span> <span class="cmd">ccm sessions my_projects/ccm</span>

<span class="c-h">SESSION    TITLE                          MSGS    SIZE   AGE</span>
<span class="c-r"><span class="c-acc">f9c2a1d3</span>   build landing page              218   142K   2m</span>
<span class="c-r"><span class="c-acc">a31b6e08</span>   fix textual _size shadow         64    38K   3h</span>
<span class="c-r"><span class="c-acc">7df4218e</span>   ci: actions for tests + pypi    110    71K   1d</span>
<span class="c-r"><span class="c-acc">c0e51a7b</span>   memory inspector v2              42    24K   2d</span>
<span class="c-r"><span class="c-acc">b89dc4f2</span>   stats: disk usage graph          88    51K   3d</span>
<span class="c-r"><span class="c-acc">12fa6b9e</span>   export to markdown               31    18K   5d</span>

<span class="c-dim"># short prefix is enough:  ccm view ccm f9c2 </span>`,
    },
    export: {
      title: "ccm export my_projects/ccm f9c2 -f md",
      html: `<span class="prompt">$</span> <span class="cmd">ccm export my_projects/ccm f9c2 -f md</span>

<span class="c-ok">✓</span> resolved project    <span class="c-r">my_projects/ccm</span>
<span class="c-ok">✓</span> resolved session    <span class="c-r">f9c2a1d3-…</span>  <span class="c-dim">(unique prefix)</span>
<span class="c-ok">✓</span> rendered <span class="c-acc">218</span> messages  (user · assistant · tool-result)
<span class="c-ok">✓</span> wrote               <span class="c-r">build-landing-page.md</span>  <span class="c-dim">(142 KB)</span>

<span class="c-amber">Formats:</span> -f <span class="c-acc">md</span>  |  -f <span class="c-acc">json</span>  |  -f <span class="c-acc">raw</span>
<span class="c-amber">Pipe:</span>    ccm export ccm f9c2 -f md | gh issue comment 42 -F -</span>`,
    },
    memory: {
      title: "ccm memory my_projects/ccm",
      html: `<span class="prompt">$</span> <span class="cmd">ccm memory my_projects/ccm</span>

<span class="c-h">memory/ — 3 files</span>
  <span class="c-r">MEMORY.md                        <span class="c-dim">(index, 412 B)</span></span>
  <span class="c-r">user_language.md                 <span class="c-dim">(user · 286 B)</span></span>
  <span class="c-r">user_python_tooling.md           <span class="c-dim">(user · 318 B)</span></span>

<span class="c-amber">show:</span> ccm memory ccm --show user_python_tooling
<span class="c-amber">rm:  </span> ccm memory ccm --rm   user_python_tooling

<span class="c-dim"># memories are plain markdown — read them like any other file</span>`,
    },
    stats: {
      title: "ccm stats",
      html: `<span class="prompt">$</span> <span class="cmd">ccm stats</span>

<span class="c-h">~/.claude/projects/</span>
  Projects        <span class="c-acc">9</span>
  Sessions        <span class="c-acc">108</span>
  Memory files    <span class="c-acc">21</span>
  Disk usage      <span class="c-acc">32.1 MB</span>

<span class="c-h">Top by size</span>
  <span class="c-r">my_projects/agent-eval   ████████████████  12.0 MB</span>
  <span class="c-r">work/anthropic-sdk       ████████          6.1 MB</span>
  <span class="c-r">work/claude-rag          ██████            4.8 MB</span>
  <span class="c-r">my_projects/ccm          ████              3.2 MB</span>
  <span class="c-r">notes/research-2026      ██                1.4 MB</span>

<span class="c-ok">✓ no daemon · read directly from disk</span>`,
    },
  };

  function renderCmd(key) {
    const entry = commands[key];
    if (!entry || !cmdBody) return;
    if (cmdTitle) cmdTitle.textContent = entry.title;
    cmdBody.style.opacity = "0";
    cmdBody.style.transition = "opacity 0.18s ease";
    setTimeout(() => {
      cmdBody.innerHTML = entry.html;
      cmdBody.style.opacity = "1";
    }, 180);
  }

  cmdTabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const key = tab.dataset.tab;
      cmdTabs.forEach((t) => {
        const on = t === tab;
        t.classList.toggle("active", on);
        t.setAttribute("aria-selected", on ? "true" : "false");
      });
      renderCmd(key);
    });
  });

  /* ── Subtle parallax on hero mockup (mouse only) ────────── */
  const heroMockup = $(".hero-mockup");
  if (heroMockup && !prefersReducedMotion && matchMedia("(pointer: fine)").matches) {
    const inner = $(".window", heroMockup);
    heroMockup.addEventListener("mousemove", (e) => {
      const r = heroMockup.getBoundingClientRect();
      const x = (e.clientX - (r.left + r.width / 2)) / r.width;
      const y = (e.clientY - (r.top + r.height / 2)) / r.height;
      inner.style.transform = `rotateX(${(-y * 4).toFixed(2)}deg) rotateY(${(x * 6).toFixed(2)}deg)`;
    });
    heroMockup.addEventListener("mouseleave", () => {
      inner.style.transform = "rotateX(2deg) rotateY(-4deg)";
    });
  }

})();
