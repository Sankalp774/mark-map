const state = {
  me: null,
  paperId: "midterm",
  classData: null,
  student: null,
  sections: [],
  selectedRoll: "17",
  peekRoll: null,
  error: "",
  busy: "",
  nav: "desk",
  toast: null,
  shot: null,
  loginAgent: null,
  agentStack: false,
  graphPick: null,
  graphHover: null,
  faqs: [],
  ask: { question: "", answer: null, faq_id: null },
  health: null,
  cheat: "",
};

const ICONS = {
  desk: '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>',
  class: '<svg viewBox="0 0 24 24"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
  student: '<svg viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
  graph: '<svg viewBox="0 0 24 24"><circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="8" r="2.5"/><circle cx="8" cy="18" r="2.5"/><circle cx="17" cy="17" r="2.5"/><path d="M8 7.5 16 9M7.5 16.2 16.2 10M10 17.5 15.5 17"/></svg>',
  loop: '<svg viewBox="0 0 24 24"><path d="M3 12a9 9 0 1 0 9-9"/><path d="M3 4v8h8"/></svg>',
  requests: '<svg viewBox="0 0 24 24"><path d="M22 2 11 13"/><path d="M22 2 15 22 11 13 2 9Z"/></svg>',
  calendar: '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>',
  ingest: '<svg viewBox="0 0 24 24"><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/></svg>',
  map: '<svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/><path d="M8 13h8M8 17h5"/></svg>',
  tasks: '<svg viewBox="0 0 24 24"><path d="M9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>',
  ask: '<svg viewBox="0 0 24 24"><path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"/></svg>',
  out: '<svg viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/></svg>',
};

const TEACHER_NAV = [
  ["desk", "Overview", "desk"],
  ["class", "Class map", "class"],
  ["student", "Student", "student"],
  ["graph", "Local graph", "graph"],
  ["loop", "Class loop", "loop"],
  ["requests", "Requests", "requests"],
  ["calendar", "Calendar", "calendar"],
  ["ingest", "Ingest", "ingest"],
];
const FAMILY_NAV = [
  ["map", "Report", "map"],
  ["loop", "Class loop", "loop"],
  ["tasks", "Tasks", "tasks"],
  ["calendar", "Calendar", "calendar"],
  ["ask", "Ask the desk", "ask"],
];

function navIcon(kind) {
  return h("span", { class: "nav-ic", html: ICONS[kind] || ICONS.desk });
}

function prettyAudience(audience) {
  const key = String(audience || "").toLowerCase();
  const map = { students: "Students", parents: "Parents", all: "All", teacher: "Teacher" };
  if (map[key]) return map[key];
  return key ? key.charAt(0).toUpperCase() + key.slice(1) : "";
}

function errText(data, fallback) {
  const d = data && data.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x.msg || JSON.stringify(x)).join("; ");
  return (data && (data.error || data.detail)) || fallback;
}

async function api(path, opts = {}) {
  const headers = { ...(opts.headers || {}) };
  if (opts.json) {
    headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(opts.json);
  }
  const res = await fetch(path, { credentials: "include", ...opts, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(errText(data, res.statusText));
  return data;
}

function h(tag, attrs = {}, kids = []) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") el.className = v;
    else if (k === "html") el.innerHTML = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (v === false || v == null) continue;
    else el.setAttribute(k, v);
  }
  for (const kid of [].concat(kids)) {
    if (kid == null || kid === false) continue;
    el.append(kid.nodeType ? kid : document.createTextNode(kid));
  }
  return el;
}

function toast(text) {
  state.toast = text;
  render();
  setTimeout(() => {
    if (state.toast === text) {
      state.toast = null;
      const t = document.querySelector(".toast");
      if (t) t.remove();
    }
  }, 3200);
}

function render() {
  const root = document.querySelector("#app");
  if (!state.me) {
    root.innerHTML = "";
    root.append(loginView());
    return;
  }
  if (!root.querySelector(".shell")) {
    root.innerHTML = "";
    root.append(shell());
  }
  fillNav();
  fillTop();
  fillMain();
  fillInspector();
  attachGlass();
  const old = root.querySelector(".toast");
  if (old) old.remove();
  if (state.toast) root.append(h("div", { class: "toast" }, state.toast));
}

const DESK_AGENTS = [
  {
    id: "desk",
    name: "Desk runner",
    file: "Desk Runner.app",
    face: "boss",
    color: "#f59e0b",
    ring: "Orchestrator",
    does: "This is the manager of the other five. When you click Run desk, it does not add marks or write a brief itself. It asks the score clerk who is incomplete, asks the analyser where the class leaked, then nags you if PTM is close. It only speaks when there is something to decide.",
  },
  {
    id: "ingest",
    name: "Ingest clerk",
    file: "Ingest Clerk.app",
    face: "reader",
    color: "#14b8a6",
    ring: "Specialist",
    does: "This one files the paper. It reads typed text, a marks CSV, or a screenshot of a report, then splits Term 1 from Midterm. If a roll was not on the page, it will not invent that student.",
  },
  {
    id: "mapper",
    name: "Paper mapper",
    file: "Paper Mapper.app",
    face: "map",
    color: "#8b5cf6",
    ring: "Specialist",
    does: "This one builds the question map. If the paper says [Linear Equations] on Q9, that tag wins. If there is no tag, it guesses from the wording and marks the question needs review so a teacher can fix it. It never changes a mark.",
  },
  {
    id: "score",
    name: "Score clerk",
    file: "Score Clerk.app",
    face: "stern",
    color: "#f43f5e",
    ring: "Specialist",
    does: "This one attaches each CSV cell to a question. A blank, NA, or dash stays missing — it will not write zero. Any empty cell blocks the PTM brief for that roll. That is the hard gate.",
  },
  {
    id: "analyser",
    name: "Analyser",
    file: "Analyser.app",
    face: "think",
    color: "#22c55e",
    ring: "Specialist",
    does: "This one does the arithmetic: percent, chapter strong / ok / weak, which question leaked the most marks, and the year line from Term 1 to Midterm. It does not talk about personality, potential, or effort.",
  },
  {
    id: "brief",
    name: "Brief writer",
    file: "Brief Writer.app",
    face: "smile",
    color: "#38bdf8",
    ring: "Specialist",
    does: "This one writes two notes from the same numbers: talking points for the teacher’s PTM, and a calmer family brief. The student and parent panes never see the teacher note. If a cell is empty, it writes nothing.",
  },
];

function loginView() {
  const doors = [
    { role: "Teacher desk", name: "Kavita Sharma", email: "teacher@markmap.demo", note: "Class ops, graph, requests" },
    { role: "Student map", name: "Ravi Mehta", email: "ravi@markmap.demo", note: "Report, tasks, ask the desk" },
    { role: "Parent pane", name: "Parent of Ravi", email: "parent.ravi@markmap.demo", note: "Same numbers, family wording" },
  ];
  const emailInput = h("input", { type: "email", value: "teacher@markmap.demo" });
  const passInput = h("input", { type: "password", value: "demo" });
  return h("div", { class: "login" }, [
    h("div", { class: "login-card" }, [
      h("p", { class: "wordmark" }, "Mark Map · Class operations"),
      h("h1", {}, "The marksheet becomes a live class desk."),
      h("p", { class: "lede" }, "Pick a class. Talk to the room. Parents and students talk back. Briefs still wait for every cell."),
      healthChip(),
      h("div", { class: "doors" }, doors.map((d) =>
        h("button", { class: "door", onclick: () => { emailInput.value = d.email; passInput.value = "demo"; } }, [
          h("div", { class: "role" }, d.role),
          h("h2", {}, d.name),
          h("p", {}, d.note),
        ])
      )),
      h("form", {
        class: "login-form",
        onsubmit: async (e) => {
          e.preventDefault();
          try {
            await api("/api/login", { method: "POST", json: { email: emailInput.value, password: passInput.value } });
            state.nav = emailInput.value.startsWith("teacher") ? "desk" : "map";
            await boot();
          } catch (err) {
            state.error = err.message;
            render();
          }
        },
      }, [emailInput, passInput, h("button", { class: "primary", type: "submit" }, "Open desk")]),
      state.error && h("div", { class: "error" }, state.error),
      h("p", { class: "hint" }, "Password demo. Also 10-A: ira@markmap.demo and parent.ira@markmap.demo"),
      h("button", { class: "ghost", style: "margin-top:10px", onclick: resetDemo }, "Reset demo class"),
    ]),
    agentSky(),
  ]);
}

function healthChip() {
  const hth = state.health;
  if (!hth) {
    loadHealth();
    return h("p", { class: "sub" }, "Checking desk…");
  }
  const ocr = hth.ocr === "tesseract" ? "OCR on" : "OCR unavailable";
  const desk = hth.strands_enabled ? `Strands ${hth.backend || "on"}` : "Strands off";
  const ev = hth.eval || {};
  return h("div", { class: "health-row" }, [
    h("span", { class: "pill green" }, desk),
    h("span", { class: "pill " + (hth.ocr === "tesseract" ? "green" : "amber") }, ocr),
    h("span", { class: "pill green" }, `invented marks ${ev.invented_marks ?? 0}`),
  ]);
}

function agentFace(kind, color) {
  return h("div", { class: "mac-face " + kind, style: `--c:${color}` }, [
    h("div", { class: "mac-head" }, [
      h("span", { class: "mac-eye" }),
      h("span", { class: "mac-eye" }),
      h("span", { class: "mac-mouth" }),
    ]),
  ]);
}

function agentSky() {
  const fanned = state.agentStack;
  return h("aside", { class: "mac-stack" + (fanned ? " fanned" : ""), "aria-label": "Strands agents" }, [
    h("button", {
      class: "mac-stack-hit",
      title: fanned ? "Collapse stack" : "Open agent stack",
      onclick: () => {
        state.agentStack = !state.agentStack;
        if (!state.agentStack) state.loginAgent = null;
        render();
      },
    }, "Agents"),
    h("div", { class: "mac-pile" }, DESK_AGENTS.map((a, i) => {
      const active = state.loginAgent === a.id;
      return h("button", {
        class: "mac-win" + (active ? " active" : ""),
        style: `--c:${a.color};--i:${i};--n:${DESK_AGENTS.length}`,
        onclick: (e) => {
          e.stopPropagation();
          if (!state.agentStack) {
            state.agentStack = true;
            state.loginAgent = a.id;
          } else {
            state.loginAgent = active ? null : a.id;
          }
          render();
        },
      }, [
        h("div", { class: "mac-chrome" }, [
          h("span", { class: "tl red" }),
          h("span", { class: "tl yellow" }),
          h("span", { class: "tl green" }),
          h("span", { class: "mac-title" }, a.file),
        ]),
        h("div", { class: "mac-body" }, [
          agentFace(a.face, a.color),
          h("div", { class: "mac-name" }, a.name),
          h("div", { class: "mac-role" }, a.ring),
          h("p", { class: "mac-does" }, a.does),
        ]),
      ]);
    })),
  ]);
}

function shell() {
  const role = state.me.user.role;
  return h("div", { class: "shell " + role }, [
    h("aside", { class: "sidenav", id: "sidenav", "aria-label": "Main" }),
    h("div", { class: "workspace" }, [
      h("header", { class: "topbar", id: "topbar" }),
      h("div", { class: "stage" }, [
        h("div", { class: "main-pane", id: "main-pane" }),
        h("aside", {
          class: "glass-widget",
          id: "glass-widget",
          "aria-label": "Selected student",
        }, h("div", { class: "glass-inner", id: "inspector" })),
      ]),
    ]),
  ]);
}

function attachGlass() {
  const el = document.querySelector("#glass-widget");
  if (!el || !window.liquidGlass) return;
  if (state.glassFx) {
    try { state.glassFx.refresh(); } catch (_) {}
    return;
  }
  state.glassFx = window.liquidGlass(el, {
    scale: -72,
    chroma: 4,
    blur: 4,
    fallbackBlur: 18,
    radius: 28,
  });
}

function fillNav() {
  const nav = document.querySelector("#sidenav");
  if (!nav) return;
  const items = state.me.user.role === "teacher" ? TEACHER_NAV : FAMILY_NAV;
  const cur = state.me.current_class || {};
  const unread = (state.me.workspace || {}).unread || 0;
  nav.innerHTML = "";
  const kids = [
    h("div", { class: "brand" }, [
      h("div", { class: "brand-mark" }, "M"),
      h("div", { class: "brand-text" }, "Mark Map"),
    ]),
    h("div", { class: "school" }, `${state.me.school?.name || ""} · ${cur.label || cur.id || ""} ${cur.subject || ""}`),
  ];
  if (state.me.user.role === "teacher" && (state.me.classes || []).length) {
    kids.push(h("label", { class: "school", style: "display:grid;gap:4px" }, [
      "Class",
      h("select", {
        class: "class-select",
        onchange: (e) => switchClass(e.target.value),
      }, (state.me.classes || []).map((c) => h("option", {
        value: c.id,
        selected: c.id === cur.id,
      }, `${c.label} · ${c.subject} · ${c.n || 0}`))),
    ]));
  }
  items.forEach(([id, label, icon]) => {
    const badge = id === "loop" && unread ? ` (${unread})` : "";
    kids.push(h("button", {
      class: "navbtn" + (state.nav === id ? " active" : ""),
      title: label,
      onclick: () => { state.nav = id; render(); },
    }, [navIcon(icon), h("span", { class: "nav-label" }, label + badge)]));
  });
  kids.push(h("button", {
    class: "navbtn",
    style: "margin-top:auto",
    title: "Sign out",
    onclick: logout,
  }, [navIcon("out"), h("span", { class: "nav-label" }, "Sign out")]));
  nav.append(...kids);
}

function pickStudent(roll) {
  if (!roll) return;
  state.peekRoll = null;
  state.selectedRoll = roll;
  state.nav = "student";
  selectStudent(roll);
}

function fillInspector(payload) {
  const el = document.querySelector("#inspector");
  if (!el) return;
  const view = payload || inspectorPayload();
  const roster = glassRoster();
  const current = roster.find((r) => r.roll === state.selectedRoll) || roster[0];
  const blocked = current && current.complete === false;
  const teacher = state.me && state.me.user && state.me.user.role === "teacher";
  const hops = teacher
    ? [["desk", "Desk"], ["class", "Class"], ["student", "Student"], ["graph", "Graph"]]
    : [["map", "Report"], ["tasks", "Tasks"], ["ask", "Ask"]];
  const picker = roster.length
    ? h("label", { class: "glass-pick-wrap" }, [
        h("span", { class: "sr-only" }, "Select student"),
        h("select", {
          class: "glass-pick",
          "aria-label": "Select student",
          onchange: (e) => pickStudent(e.target.value),
        }, roster.map((r) => h("option", {
          value: r.roll,
          selected: r.roll === (current && current.roll),
        }, r.name))),
      ])
    : h("div", { class: "name" }, (view && view.title) || "No student yet");
  el.innerHTML = "";
  el.append(
    h("div", { class: "glass-head" }, [
      h("span", { class: "glass-dot " + (current ? (blocked ? "blocked" : "ready") : "") }),
      h("div", { class: "glass-who" }, [
        picker,
        h("div", { class: "meta" }, current
          ? `Roll ${current.roll}` + (current.complete ? ` · ${current.percent}%` : " · brief blocked")
          : "Load the class, then pick a student here"),
      ]),
    ]),
    h("div", { class: "glass-peek" }, [
      h("p", { class: "inspect-empty" }, current
        ? (current.complete
          ? ((current.weak || []).length ? `Weak on ${(current.weak || []).join(", ")}.` : "No weak chapter on this paper.")
          : `Brief blocked — ${(current.missing || []).map((x) => String(x).toUpperCase()).join(", ") || "empty cells"}.`)
        : "Load the class to pick a student from this box."),
    ]),
    h("div", { class: "glass-hops" }, hops.map(([id, label]) => h("button", {
      class: "glass-hop" + (state.nav === id ? " active" : ""),
      onclick: (e) => {
        e.stopPropagation();
        state.nav = id;
        const roll = state.selectedRoll || (current && current.roll);
        if ((id === "student" || id === "graph" || id === "map") && roll) selectStudent(roll);
        else render();
      },
    }, label))),
  );
  if (state.glassFx && state.glassFx.refresh) {
    requestAnimationFrame(() => state.glassFx.refresh());
  }
}

function glassRoster() {
  const fromClass = ((state.classData || {}).roster || []).map((r) => ({
    roll: r.roll,
    name: r.name,
    complete: r.complete,
    percent: r.percent,
    weak: r.weak,
    missing: r.missing,
  }));
  if (fromClass.length) return fromClass;
  return (state.me && state.me.roster_lite) || [];
}

function rosterPeek(row) {
  if (!row) return null;
  const onStudentPage = state.nav === "student" && state.selectedRoll === row.roll;
  return {
    kicker: row.complete ? "Ready" : "Blocked",
    title: row.name,
    body: [
      h("p", { class: "sub" }, `Roll ${row.roll}` + (row.complete ? ` · ${row.percent}%` : "")),
      h("p", {}, row.complete
        ? ((row.weak || []).length ? `Weak on ${(row.weak || []).join(", ")}.` : "No weak chapter on this paper.")
        : `Brief blocked — ${(row.missing || []).map((x) => x.toUpperCase()).join(", ") || "empty cells"} still empty.`),
      !onStudentPage && h("div", { class: "row-actions" }, [
        h("button", { class: "primary", onclick: () => { state.selectedRoll = row.roll; state.nav = "student"; selectStudent(row.roll); } }, "Open student"),
      ]),
    ].filter(Boolean),
  };
}

function inspectGraphNode(pick) {
  if (!pick) return null;
  if (pick.kind === "student") {
    const roll = String(pick.id || "").split(":")[1];
    const row = ((state.classData || {}).roster || []).find((r) => r.roll === roll);
    if (row) return rosterPeek(row);
    return {
      kicker: "Student",
      title: String(pick.label || "").replace(/[\[\]]/g, ""),
      body: [h("p", { class: "sub" }, roll ? `Roll ${roll}` : "Hub of this local graph.")],
    };
  }
  const kindLabel = pick.kind === "question" ? "Question" : pick.kind === "chapter" ? "Chapter" : pick.kind === "paper" ? "Paper" : "Node";
  return {
    kicker: kindLabel,
    title: String(pick.label || "").replace(/[\[\]]/g, ""),
    body: graphInspectorKidsFor(pick),
  };
}

function inspectorPayload() {
  if (state.graphPick) return inspectGraphNode(state.graphPick);
  const row = ((state.classData || {}).roster || []).find((r) => r.roll === state.selectedRoll);
  if (row && (state.nav === "class" || state.nav === "student")) return rosterPeek(row);
  const k = (state.me && state.me.kpis) || {};
  return {
    kicker: "Desk",
    title: "What needs you",
    body: [
      h("p", { class: "inspect-empty" },
        k.incomplete
          ? `${k.incomplete} scripts still block briefs. Hover a roster row, or a question on the graph.`
          : "Hover a roster row or a question. The student node in the middle is just the hub."),
    ],
  };
}

function fillTop() {
  const top = document.querySelector("#topbar");
  if (!top) return;
  const k = state.me.kpis || {};
  top.innerHTML = "";
  top.append(
    h("div", {}, [
      h("div", { class: "brand" }, state.me.user.name),
      h("div", { class: "who" }, state.me.user.email),
    ]),
    h("div", { class: "kpis" }, [
      h("div", { class: "kpi" }, [h("div", { class: "k" }, "Ready"), h("div", { class: "v" }, k.n ? `${k.ready}/${k.n}` : "—")]),
      h("div", { class: "kpi" }, [h("div", { class: "k" }, "Blocked"), h("div", { class: "v" }, String(k.incomplete ?? "—"))]),
      h("div", { class: "kpi" }, [h("div", { class: "k" }, "PTM"), h("div", { class: "v" }, state.me.ptm_hours != null ? `${state.me.ptm_hours}h` : "—")]),
      h("div", { class: "kpi" }, [h("div", { class: "k" }, "Hotspot"), h("div", { class: "v" }, k.hotspot ? `Q${k.hotspot.number}` : "—")]),
    ])
  );
}

function fillMain() {
  const main = document.querySelector("#main-pane");
  if (!main) return;
  main.innerHTML = "";
  const role = state.me.user.role;
  if (state.error) main.append(h("div", { class: "error" }, state.error));
  if (role === "teacher") main.append(teacherMain());
  else main.append(familyMain());
}

function teacherMain() {
  switch (state.nav) {
    case "class": return classPane();
    case "student": return studentPane(true);
    case "graph": return graphPane();
    case "loop": return loopPane(true);
    case "requests": return requestsPane();
    case "calendar": return calendarPane(true);
    case "ingest": return ingestPane();
    default: return deskPane();
  }
}

function familyMain() {
  switch (state.nav) {
    case "loop": return loopPane(false);
    case "inbox": return loopPane(false);
    case "tasks": return tasksPane();
    case "calendar": return calendarPane(false);
    case "ask": return askPane();
    default: return familyReportPane();
  }
}

function deskPane() {
  const k = state.me.kpis || {};
  const alerts = state.me.alerts || [];
  const cycle = (state.me.workspace || {}).desk_cycle;
  const proposals = (state.me.workspace || {}).proposals || [];
  return h("div", { class: "desk-quiet" }, [
    h("div", { class: "page-head" }, [
      h("div", {}, [
        h("h2", {}, "Overview"),
        h("p", {}, "Load the class, then run the desk. Hover the left rail for pages. Hover a student on the right."),
      ]),
    ]),
    h("div", { class: "toolbar" }, [
      btn("Load class (Term 1 + Midterm)", loadDemo, "primary"),
      btn("Read sample screenshot", loadScreenshot, "ghost"),
      btn("Blank Ravi Q9", blankRavi, "ghost"),
      btn("Run desk", runDesk, "ghost"),
    ]),
    h("div", { class: "loop-board compact" }, [
      tile("Scripts ready", k.n ? `${k.ready}/${k.n}` : "—", "students"),
      tile("Incomplete", String(k.incomplete ?? "—"), "parents"),
      tile("Needs review", String(k.needs_review ?? "—"), "all"),
      tile("Hotspot", k.hotspot ? `Q${k.hotspot.number} · ${k.hotspot.percent}%` : "—", "students"),
    ]),
    alerts.length > 0 && h("div", { class: "loop-board compact" }, alerts.map((a) =>
      h("article", { class: "loop-card trace-" + (a.level === "red" ? "warn" : a.level === "green" ? "ok" : "next") }, [
        h("div", { class: "loop-kicker" }, a.level === "red" ? "Blocked" : a.level === "green" ? "Ready" : "Watch"),
        h("h4", {}, a.text),
      ])
    )),
    lastRunCard(),
    ptmCard(),
    cheatCard(),
    cycle && h("div", { class: "card", style: "margin-top:12px" }, [
      h("h3", {}, "Desk cycle"),
      h("p", { class: "sub" }, "Observe → plan → act → wait. The agent called tools; Python still owns marks."),
      deskTrace(cycle),
      cycle.observe?.strategy?.recommendation?.leverage && h("p", { class: "sub", style: "margin-top:10px" }, cycle.observe.strategy.recommendation.leverage),
    ]),
    policyCard(),
    proposals.length > 0 && h("div", { class: "card", style: "margin-top:12px" }, [
      h("h3", {}, "Waiting for you"),
      ...proposals.map((p) => h("div", { class: "msg" }, [
        h("strong", {}, `${p.kind} · ${p.chapter}`),
        h("div", {}, p.proposal),
        h("button", { class: "primary", style: "margin-top:8px", onclick: () => approveIntervention(p.id) }, "Approve intervention"),
      ])),
    ]),
    h("div", { class: "two-col", style: "margin-top:12px" }, [
      h("div", { class: "card" }, [
        h("h3", {}, "Live operations"),
        h("p", { class: "sub" }, "The desk proposes. You approve. Students get the task. Next paper measures the outcome."),
        h("div", { class: "row-actions" }, [
          h("button", { class: "ghost", onclick: () => { state.nav = "requests"; render(); } }, "Requests"),
          h("button", { class: "ghost", onclick: () => { state.nav = "graph"; render(); } }, "Local graph"),
          h("button", { class: "ghost", onclick: () => { state.nav = "ingest"; render(); } }, "Screenshot ingest"),
        ]),
      ]),
      h("div", { class: "card" }, [
        h("h3", {}, "Desk log"),
        h("div", { class: "log" }, (state.me.agent_log || []).slice().reverse().map((e) => `${e.kind}: ${e.text}`).join("\n") || "No runs yet."),
      ]),
    ]),
  ]);
}

function deskTrace(cycle) {
  const last = (state.me || {}).last_desk_run || {};
  const items = [];
  (last.did || []).forEach((name) => items.push({ kind: "ok", text: "Called " + name }));
  (last.refused || []).forEach((r) => items.push({ kind: "warn", text: "Refused " + (r.tool || "tool") + " — " + (r.text || "") }));
  if (last.waiting) items.push({ kind: "wait", text: last.waiting });
  if (!items.length && (cycle.trace || []).length) {
    return h("div", { class: "trace" }, cycle.trace.map((t) => h("div", { class: "trace-item " + t.kind }, t.text)));
  }
  if (!items.length) {
    return h("div", { class: "cycle" }, (cycle.steps || []).map((s) =>
      h("div", { class: "cycle-step " + s.phase }, [
        h("div", { class: "cycle-phase" }, s.phase),
        h("div", {}, s.text),
      ])
    ));
  }
  return h("div", { class: "trace" }, items.map((t) => h("div", { class: "trace-item " + t.kind }, t.text)));
}

function lastRunCard() {
  const last = (state.me || {}).last_desk_run;
  if (!last) return null;
  const obs = last.observed || {};
  return h("div", { class: "card", style: "margin-top:12px" }, [
    h("h3", {}, "Last desk run"),
    h("p", { class: "sub" }, last.at || ""),
    h("p", {}, `Observed ${obs.ready || 0}/${obs.n || 0} ready. Incomplete: ${(obs.incomplete || []).length}.`),
    h("p", {}, "Did: " + ((last.did || []).join(", ") || "—")),
    h("p", {}, "Refused: " + ((last.refused || []).map((r) => r.tool).join(", ") || "none")),
    last.waiting && h("p", { class: "sub" }, last.waiting),
  ]);
}

function ptmCard() {
  const hours = state.me && state.me.ptm_hours;
  const current = (state.me && state.me.ptm_at) || "";
  const input = h("input", { type: "datetime-local", value: (current || "").slice(0, 16) });
  return h("div", { class: "card", style: "margin-top:12px" }, [
    h("h3", {}, "PTM window"),
    h("p", { class: "sub" }, hours == null ? "No PTM time set." : `PTM in ${hours} hours.`),
    h("form", {
      class: "form-grid",
      onsubmit: async (e) => {
        e.preventDefault();
        try {
          await api("/api/desk/ptm", { method: "POST", json: { ptm_at: input.value } });
          await refreshMe();
          toast("PTM time updated.");
          render();
        } catch (err) { state.error = err.message; render(); }
      },
    }, [input, h("button", { class: "ghost", type: "submit" }, "Set PTM")]),
  ]);
}

function cheatCard() {
  const input = h("input", { value: state.cheat, placeholder: "give Ravi 8 on Q9 / unlock the brief" });
  input.addEventListener("input", () => { state.cheat = input.value; });
  return h("div", { class: "card", style: "margin-top:12px" }, [
    h("h3", {}, "Cheat prompt"),
    h("p", { class: "sub" }, "The agent must refuse. The teacher fills the cell on the Student pane."),
    h("form", {
      class: "form-grid",
      onsubmit: async (e) => {
        e.preventDefault();
        state.busy = "cheat";
        render();
        try {
          const data = await api("/api/desk/run", { method: "POST", json: { prompt: input.value } });
          await refreshMe();
          toast((data.refused && data.refused.length) ? "Refused — cell unchanged." : (data.summary || "Desk ran."));
        } catch (err) { state.error = err.message; }
        finally { state.busy = ""; render(); }
      },
    }, [input, h("button", { class: "ghost", type: "submit" }, "Ask the agent")]),
  ]);
}

function tile(kicker, value, audience) {
  return h("article", { class: "loop-card audience-" + audience }, [
    h("div", { class: "loop-kicker" }, kicker),
    h("h4", {}, value),
  ]);
}

function stat(k, v) {
  return h("div", { class: "stat" }, [h("div", { class: "kicker section-kicker" }, k), h("div", { class: "v" }, String(v))]);
}

function classPane() {
  const cls = state.classData;
  if (!cls) return emptyLoad();
  return h("div", {}, [
    sectionTabs(state.me.papers || []),
    h("div", { class: "two-col" }, [mapCard(cls.paper), rosterCard(cls)]),
  ]);
}

function studentPane(teacher) {
  if (!state.classData) return emptyLoad();
  return h("div", {}, [
    sectionTabs(state.me.papers || []),
    h("div", { class: "two-col" }, [
      studentCard(state.student, teacher),
      rosterCard(state.classData),
    ]),
  ]);
}

function questionDifficulty(q) {
  const max = Number(q.max_marks || q.hardest || 0);
  if (max <= 4) return "easy";
  if (max <= 8) return "medium";
  return "hard";
}

function nodeDifficulty(n) {
  if (n.kind === "question") return questionDifficulty(n);
  if (n.kind === "chapter") return questionDifficulty({ max_marks: n.hardest || 0 });
  return "medium";
}

function difficultyColor(level) {
  if (level === "hard") return "#ef4444";
  if (level === "medium") return "#eab308";
  return "#22c55e";
}

function tipText(n) {
  const name = String(n.label || "").replace(/[\[\]]/g, "");
  if (n.kind === "question") {
    const max = n.max_marks == null ? "?" : fmt(n.max_marks);
    return (n.empty || n.got == null) ? `${name}  —/${max}` : `${name}  ${fmt(n.got)}/${max}`;
  }
  if (n.kind === "chapter") {
    const max = n.max == null ? "?" : fmt(n.max);
    const got = n.got == null ? "—" : fmt(n.got);
    return `${name}  ${got}/${max}`;
  }
  if (n.kind === "student") {
    const max = n.max == null ? "?" : fmt(n.max);
    const got = n.got == null ? "—" : fmt(n.got);
    return `${name}  ${got}/${max}`;
  }
  return name;
}

function graphPane() {
  if (!state.student?.brain) return emptyLoad();
  const host = h("div", { class: "mindmap", id: "mindmap-host" });
  const name = state.student.analysis?.name || "Student";
  const paper = state.student.paper?.title || "Midterm";
  const card = h("div", { class: "card brain-card" }, [
    h("div", { class: "mindmap-head" }, [
      h("div", {}, [
        h("h3", {}, `${name} · ${paper}`),
        h("p", { class: "sub" }, "Easy green · medium yellow · hard red. Hover a question or chapter for marks obtained."),
      ]),
      sectionTabs(state.me.papers || []),
    ]),
    host,
    h("div", { class: "mindmap-legend" }, [
      h("span", { class: "diff easy" }, "Easy ≤4"),
      h("span", { class: "diff medium" }, "Medium 6–8"),
      h("span", { class: "diff hard" }, "Hard 12+"),
    ]),
    h("div", { class: "backlinks" }, Object.entries(state.student.brain.backlinks || {}).map(([ch, qs]) =>
      h("div", {}, [h("span", { class: "wiki" }, `[[${ch}]]`), ` ← ${(qs || []).join(", ")}`])
    )),
  ]);
  try {
    mountMindmap(host, state.student.brain, true);
  } catch (err) {
    host.textContent = "Graph failed: " + (err && err.message ? err.message : err);
  }
  return card;
}

function policyCard() {
  const pol = (state.me && state.me.health && state.me.health.policy) || {};
  const can = pol.can || [];
  const cannot = pol.cannot || [];
  if (!can.length && !cannot.length) return null;
  return h("div", { class: "card policy", style: "margin-top:12px" }, [
    h("h3", {}, "Agent permissions"),
    h("p", { class: "sub" }, pol.rule || "Python establishes reality. Agents operate within it."),
    h("div", { class: "policy-grid" }, [
      h("div", {}, [h("div", { class: "section-kicker" }, "Can"), h("ul", {}, can.map((x) => h("li", {}, x.replace(/_/g, " "))))]),
      h("div", {}, [h("div", { class: "section-kicker" }, "Cannot"), h("ul", {}, cannot.map((x) => h("li", {}, x.replace(/_/g, " "))))]),
    ]),
  ]);
}

function graphInspectorKidsFor(pick) {
  if (!pick) return [h("p", { class: "inspect-empty" }, "Hover a question. Weak edges stay red. Click to address or add bonus — bonus cannot fill an empty cell.")];
  const kids = [
    pick.chapter && h("p", { class: "sub" }, `Chapter [[${pick.chapter}]]` + (pick.band ? ` · ${pick.band}` : "")),
    pick.confidence != null && h("div", { class: "sub" },
      pick.needs_review
        ? `Probably ${pick.chapter} (${Math.round(pick.confidence * 100)}%). Needs teacher confirmation before student analysis uses it as fact.`
        : `Mapped from ${pick.source || "paper"} (${Math.round(pick.confidence * 100)}%).`
    ),
    pick.leaked && pick.affected != null && h("div", { class: "pill amber" },
      `${pick.affected}/${pick.class_n || "?"} students leaked here · mean ${pick.class_percent}% · ${pick.lost} marks lost`
    ),
    pick.addressed && h("div", { class: "pill green" }, "Addressed"),
    pick.bonus ? h("div", {}, `Bonus recorded: +${pick.bonus}`) : null,
  ];
  if (state.me.user.role === "teacher" && pick.kind === "question" && pick.question_id) {
    kids.push(h("div", { class: "row-actions" }, [
      h("button", { class: "primary", onclick: () => addressNode(pick) }, `Address ${pick.label}`),
      h("button", { class: "ghost", onclick: () => bonusNode(pick, 1) }, "+1 bonus"),
      h("button", { class: "ghost", onclick: () => bonusNode(pick, 2) }, "+2 bonus"),
    ]));
  }
  return kids.filter(Boolean);
}

function graphInspectorKids() {
  return graphInspectorKidsFor(state.graphPick);
}

function requestsPane() {
  const ws = state.me.workspace || {};
  const rollSel = h("select", {}, (state.me.roster_lite || []).map((r) => h("option", { value: r.roll }, `${r.roll} ${r.name}`)));
  if (state.selectedRoll) rollSel.value = state.selectedRoll;
  const pTitle = h("input", { value: "PTM reminder" });
  const pBody = h("textarea", {}, "Please review the family brief before Friday. Briefs stay blocked if any mark is missing.");
  const sTitle = h("input", { value: "Linear Equations drill" });
  const sBody = h("textarea", {}, "Complete the hostel-charges worksheet (Q9 pattern) before the term exam.");
  const tTitle = h("input", { value: "Personal suggestion" });
  const tBody = h("textarea", {}, "Rework Midterm Q9 with full working. Bring it to the next class.");
  const outbox = [
    ...(ws.broadcasts || []).slice(0, 8).map((b) =>
      h("article", { class: "loop-card audience-" + (b.audience || "all") }, [
        h("div", { class: "loop-kicker" }, prettyAudience(b.audience)),
        h("h4", {}, b.title),
        h("p", { class: "loop-body" }, b.body),
        h("div", { class: "when" }, b.at || `${b.teacher || "Teacher"} · ${(b.acks || []).length} acknowledged · ${(b.replies || []).length} replies`),
      ])
    ),
    ...(ws.tasks || []).slice(0, 8).map((t) =>
      h("article", { class: "loop-card audience-teacher" }, [
        h("div", { class: "loop-kicker" }, t.roll && t.roll !== "*" ? `Roll ${t.roll}` : "Task"),
        h("h4", {}, t.title),
        h("p", { class: "loop-body" }, t.body),
      ])
    ),
  ];
  return h("div", {}, [
    h("div", { class: "loop-head" }, [
      h("h3", {}, "Requests"),
      h("p", { class: "sub" }, "Each send is its own tile. Parents, Students, and a personal task stay separate."),
    ]),
    h("div", { class: "loop-board" }, [
      h("article", { class: "loop-card audience-parents" }, [
        h("div", { class: "loop-kicker" }, "Parents"),
        h("h4", {}, "Request to all parents"),
        h("form", { class: "form-grid", onsubmit: (e) => sendBroadcast(e, "parents", pTitle, pBody) }, [
          pTitle, pBody, h("button", { class: "primary", type: "submit" }, "Send to parents"),
        ]),
      ]),
      h("article", { class: "loop-card audience-students" }, [
        h("div", { class: "loop-kicker" }, "Students"),
        h("h4", {}, "Request to all students"),
        h("form", { class: "form-grid", onsubmit: (e) => sendBroadcast(e, "students", sTitle, sBody) }, [
          sTitle, sBody, h("button", { class: "primary", type: "submit" }, "Send to students"),
        ]),
      ]),
      h("article", { class: "loop-card audience-teacher" }, [
        h("div", { class: "loop-kicker" }, "Task"),
        h("h4", {}, "Personal task / suggestion"),
        h("form", { class: "form-grid", onsubmit: (e) => sendTask(e, rollSel, tTitle, tBody) }, [
          rollSel, tTitle, tBody, h("button", { class: "primary", type: "submit" }, "Assign to this student"),
        ]),
      ]),
    ]),
    h("div", { class: "loop-head", style: "margin-top:8px" }, [
      h("h3", {}, "Outbox"),
      h("p", { class: "sub" }, "Sent requests and tasks, one tile each."),
    ]),
    h("div", { class: "loop-board" }, outbox.length ? outbox : [
      h("p", { class: "sub" }, "Nothing sent yet."),
    ]),
  ]);
}

function calendarPane(teacher) {
  const items = (state.me.workspace || {}).calendar || [];
  const title = h("input", { value: "Term examination" });
  const date = h("input", { type: "date", value: "2026-09-28" });
  const syllabus = h("textarea", {}, "Linear Equations word problems, Triangles, Statistics.");
  return h("div", { class: "two-col" }, [
    h("div", { class: "card" }, [
      h("h3", {}, "Scheduled papers"),
      ...items.map((c) => h("div", { class: "msg" }, [
        h("strong", {}, `${c.title} · ${c.date}`),
        h("div", {}, c.syllabus),
      ])),
      !items.length && h("p", { class: "sub" }, "Nothing scheduled."),
    ]),
    teacher && h("div", { class: "card" }, [
      h("h3", {}, "Schedule next test"),
      h("form", { class: "form-grid", onsubmit: async (e) => {
        e.preventDefault();
        try {
          const data = await api("/api/workspace/calendar", { method: "POST", json: { title: title.value, date: date.value, syllabus: syllabus.value } });
          state.me.workspace = data.workspace;
          toast("Next test is on the class calendar.");
          render();
        } catch (err) { state.error = err.message; render(); }
      } }, [title, date, syllabus, h("button", { class: "primary", type: "submit" }, "Publish to class")]),
    ]),
  ]);
}

function ingestPane() {
  const shot = state.shot;
  const file = h("input", { type: "file", accept: "image/png,image/jpeg,image/webp,image/*" });
  return h("div", {}, [
    h("div", { class: "card" }, [
      h("h3", {}, "Report from screenshot"),
      h("p", { class: "sub" },
        (state.health && state.health.ocr === "tesseract")
          ? "Tesseract will read SECTION Term 1 / SECTION Midterm and Q-lines."
          : "Tesseract is unavailable. The sample button uses embedded sample text, labelled as such — it is not live OCR."
      ),
      h("div", { class: "row-actions" }, [
        btn("Read sample screenshot", loadScreenshot, "primary"),
      ]),
      h("form", {
        class: "drop",
        style: "margin-top:14px",
        onsubmit: async (e) => {
          e.preventDefault();
          if (!file.files[0]) { state.error = "Choose a PNG or JPEG of the report."; render(); return; }
          const fd = new FormData();
          fd.append("shot", file.files[0]);
          state.busy = "upload";
          render();
          try {
            const res = await fetch("/api/ingest/screenshot", { method: "POST", body: fd, credentials: "include" });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) throw new Error(errText(data, "Screenshot failed"));
            state.shot = { ...data, image_url: data.image_url || URL.createObjectURL(file.files[0]) };
            if (data.ok) {
              state.classData = data.class || state.classData;
              state.selectedRoll = data.roll || "17";
              await selectStudent(state.selectedRoll, true);
              await refreshMe();
              toast(`Report read via ${data.engine}.`);
            } else {
              state.error = data.error || "Could not parse this image.";
            }
          } catch (err) {
            state.error = err.message;
          } finally {
            state.busy = "";
            render();
          }
        },
      }, [
        h("p", {}, "Drop a photo or screenshot of a student report"),
        file,
        h("button", { class: "ghost", type: "submit", style: "margin-top:10px" }, "Build report from this image"),
      ]),
    ]),
    shot && shotPane(shot),
  ]);
}

function shotPane(shot) {
  return h("div", { class: "card", style: "margin-top:12px" }, [
    h("div", { class: "section-kicker" }, shot.ok ? `Read · ${shot.engine_label || shot.engine}` : `Failed · ${shot.engine_label || shot.engine || "none"}`),
    h("h3", {}, shot.ok ? `${shot.name || "Student"} · roll ${shot.roll}` : "Could not map this image"),
    h("div", { class: "shot-preview" }, [
      shot.image_url && h("img", { src: shot.image_url, alt: "Report screenshot" }),
      h("div", {}, [
        ...(shot.preview || []).map((p) => h("div", { class: "msg" }, [
          h("strong", {}, p.title),
          h("div", {}, Object.entries(p.cells || {}).map(([k, v]) => `${k.toUpperCase()} ${v ?? "—"}`).join(" · ")),
        ])),
        ...(shot.sections || []).map((s) => h("div", { class: "msg" }, [
          h("strong", {}, `${s.title} · ${s.analysis?.percent ?? "—"}%`),
          h("div", {}, (s.analysis?.weak || []).join(", ") || "No weak chapter"),
        ])),
        shot.text && h("details", {}, [h("summary", {}, "Extracted text"), h("pre", { class: "log" }, shot.text)]),
        shot.error && h("div", { class: "error" }, shot.error),
      ]),
    ]),
  ]);
}

function familyReportPane() {
  const sections = state.sections || [];
  if (!sections.length) return h("div", { class: "card" }, "No paper on file yet. Ask the teacher to load the class.");
  return h("div", { class: "section-stack" }, sections.map(familySection));
}

function familySection(block) {
  const a = block.analysis;
  const brief = block.briefs;
  return h("section", { class: "card" }, [
    h("div", { class: "section-kicker" }, block.title),
    h("div", { class: "score", style: "font-family:var(--serif);font-size:48px" }, a.complete ? `${a.percent}%` : "—"),
    h("div", { class: "sub" }, a.complete ? `${fmt(a.got)} / ${fmt(a.max)}` : "Brief blocked until every cell is filled."),
    chaptersCard(a.chapters),
    lossesCard(a.losses),
    memoryCard(block.memory),
    brief && (brief.blocked
      ? h("div", { class: "brief blocked" }, brief.reason)
      : h("div", { class: "brief" }, brief.family || "")),
    brainCardStatic(block.brain, `${block.title} · local graph`),
  ]);
}

function tasksPane() {
  const tasks = ((state.me.workspace || {}).tasks || []);
  if (!tasks.length) return h("div", { class: "card" }, [h("h3", {}, "Tasks"), h("p", {}, "No tasks yet.")]);
  return h("div", { class: "card" }, [
    h("h3", {}, "Assigned work"),
    ...tasks.map((t) => h("article", { class: "loop-card audience-students" }, [
      h("div", { class: "loop-kicker" }, t.status === "done" ? "Done" : "Open"),
      h("strong", {}, t.title),
      h("div", {}, t.body),
      t.due && h("div", { class: "when" }, `Due ${t.due}`),
      t.status !== "done" && h("button", { class: "ghost", onclick: () => doneTask(t.id) }, "Mark done"),
    ])),
  ]);
}

function loopPane(teacher) {
  const ws = state.me.workspace || {};
  const broadcasts = ws.broadcasts || [];
  const threads = ws.threads || [];
  const roll = state.me.user.roll || state.selectedRoll || "17";
  const replyBox = (id) => {
    const ta = h("input", { placeholder: "Reply to the class…" });
    return h("form", {
      class: "loop-reply",
      onsubmit: async (e) => {
        e.preventDefault();
        try {
          const data = await api(`/api/workspace/broadcast/${id}/reply`, { method: "POST", json: { body: ta.value } });
          state.me.workspace = data.workspace;
          toast("Reply posted.");
          render();
        } catch (err) { state.error = err.message; render(); }
      },
    }, [ta, h("button", { class: "ghost", type: "submit" }, "Reply")]);
  };
  const threadBox = h("input", { placeholder: teacher ? "Message this family…" : "Message the teacher…" });
  const rollSel = teacher ? h("select", {}, (state.me.roster_lite || []).map((r) => h("option", { value: r.roll, selected: r.roll === roll }, `${r.roll} ${r.name}`))) : null;
  const tiles = broadcasts.map((b) => h("article", { class: "loop-card audience-" + (b.audience || "all") }, [
    h("div", { class: "loop-kicker" }, prettyAudience(b.audience)),
    h("h4", {}, b.title),
    h("p", { class: "loop-body" }, b.body),
    h("div", { class: "when" }, `${b.teacher || "Teacher"} · ${(b.acks || []).length} acknowledged · ${(b.replies || []).length} replies`),
    h("div", { class: "loop-replies" }, (b.replies || []).map((r) => h("div", { class: "bubble " + r.role }, `${r.name}: ${r.body}`))),
    !teacher && h("div", { class: "row-actions" }, [
      h("button", { class: "ghost", onclick: () => ackBroadcast(b.id) }, "Acknowledge"),
    ]),
    replyBox(b.id),
  ]));
  return h("div", { class: "two-col" }, [
    h("div", {}, [
      h("div", { class: "loop-head" }, [
        h("h3", {}, "Class loop"),
        h("p", { class: "sub" }, "Requests, acknowledgements, and replies in this class. This is a conversation, not a notice board."),
      ]),
      h("div", { class: "loop-board" }, tiles.length ? tiles : [
        h("p", { class: "sub" }, "No class requests yet. Teacher can send one from Requests."),
      ]),
      h("div", { class: "card", style: "margin-top:12px" }, [
        h("h3", {}, "Direct thread"),
        h("form", {
          class: "form-grid",
          onsubmit: async (e) => {
            e.preventDefault();
            const target = teacher ? (rollSel && rollSel.value) : roll;
            try {
              const data = await api("/api/workspace/thread", { method: "POST", json: { roll: target, body: threadBox.value } });
              state.me.workspace = data.workspace;
              threadBox.value = "";
              toast("Message sent.");
              render();
            } catch (err) { state.error = err.message; render(); }
          },
        }, [
          teacher && rollSel,
          threadBox,
          h("button", { class: "primary", type: "submit" }, teacher ? "Send to family" : "Send to teacher"),
        ]),
        ...threads.map((t) => h("article", { class: "loop-card thread-card" }, [
          h("div", { class: "loop-kicker" }, `Thread · roll ${t.roll}`),
          ...(t.messages || []).slice(-8).map((m) => h("div", { class: "bubble " + m.role }, `${m.name}: ${m.body}`)),
        ])),
      ]),
    ]),
    h("div", { class: "card" }, [
      h("h3", {}, "Live"),
      h("p", { class: "sub" }, `${ws.unread || 0} unread in this class. The loop refreshes while you stay signed in.`),
      ...(ws.tasks || []).slice(0, 6).map((t) =>
        h("div", { class: "loop-card audience-teacher" }, t.title)
      ),
    ]),
  ]);
}

async function ackBroadcast(id) {
  try {
    const data = await api(`/api/workspace/broadcast/${id}/ack`, { method: "POST" });
    state.me.workspace = data.workspace;
    toast("Acknowledged.");
    render();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

async function switchClass(id) {
  try {
    await api("/api/class/select", { method: "POST", json: { class_id: id } });
    state.classData = null;
    state.student = null;
    state.paperId = id === "10-B" ? "midterm" : `${id}:midterm`;
    await boot();
    toast(`Now in ${id}.`);
  } catch (err) {
    state.error = err.message;
    render();
  }
}

function askPane() {
  const input = h("input", { value: state.ask.question, placeholder: "Ask about Q9, the next test, or open tasks" });
  return h("div", { class: "card" }, [
    h("h3", {}, "Ask the desk"),
    h("p", { class: "sub" }, "Answers from the marksheet only — not a live agent. If it is not on the page, the desk says it does not know."),
    h("div", { class: "faq-row" }, (state.faqs.length ? state.faqs : [
      { id: "q9", label: "Why were marks lost on Q9?" },
      { id: "next-test", label: "When is the next test, and what is the syllabus?" },
      { id: "linear", label: "How do we work on Linear Equations?" },
      { id: "tasks", label: "What tasks are open for me?" },
    ]).map((f) => h("button", {
      class: "chip" + (state.ask.faq_id === f.id ? " active" : ""),
      onclick: () => askFaq(f.id, f.label),
    }, f.label))),
    h("form", {
      class: "form-grid",
      onsubmit: async (e) => {
        e.preventDefault();
        await askFaq(null, input.value);
      },
    }, [input, h("button", { class: "primary", type: "submit" }, "Ask")]),
    state.ask.answer && h("div", { class: "brief", style: "margin-top:12px" }, state.ask.answer),
  ]);
}

async function askFaq(faq_id, label) {
  state.ask.question = label || "";
  state.ask.faq_id = faq_id;
  try {
    const data = await api("/api/query", { method: "POST", json: { question: label || "", faq_id } });
    state.faqs = data.faqs || state.faqs;
    state.ask.answer = data.answer;
  } catch (err) {
    state.error = err.message;
  }
  render();
}

function emptyLoad() {
  return h("div", { class: "card" }, [
    h("h3", {}, "No class on the desk"),
    h("p", {}, "Load Term 1 + Midterm to open the map, graph, and briefs."),
    btn("Load class (Term 1 + Midterm)", loadDemo, "primary"),
  ]);
}

function sectionTabs(papers) {
  const wanted = [{ id: "term-1", title: "Term 1" }, { id: "midterm", title: "Midterm" }];
  const have = new Set((papers || []).map((p) => p.section || p.id));
  const tabs = wanted.filter((w) => have.has(w.id) || (papers || []).some((p) => p.id === w.id));
  if (!tabs.length) return null;
  return h("div", { class: "tabs" }, tabs.map((t) =>
    h("button", { class: "tab" + (state.paperId === t.id ? " active" : ""), onclick: () => switchSection(t.id) }, t.title)
  ));
}

function mapCard(paper) {
  if (!paper) return h("div", { class: "card" }, [h("h3", {}, "Question map")]);
  return h("div", { class: "card" }, [
    h("div", { class: "section-kicker" }, paper.section === "term-1" ? "Term 1" : "Midterm"),
    h("h3", {}, `${paper.title} · question map`),
    h("table", {}, [
      h("thead", {}, h("tr", {}, ["Q", "Max", "Chapter", "Confidence", "Source"].map((t) => h("th", {}, t)))),
      h("tbody", {}, paper.questions.map((q) => h("tr", {}, [
        h("td", {}, `Q${q.number}`),
        h("td", {}, String(q.max_marks)),
        h("td", {}, chapterEditor(paper.id, q)),
        h("td", {}, q.confidence == null ? "—" : `${Math.round(q.confidence * 100)}%`),
        h("td", {}, h("span", { class: `tag ${q.source}` }, q.needs_review ? "needs review" : q.source)),
      ]))),
    ]),
  ]);
}

function chapterEditor(paperId, q) {
  return h("input", {
    value: q.chapter,
    style: "width:160px;padding:4px 8px;border:1px solid var(--line);border-radius:8px",
    onchange: async (e) => {
      await api(`/api/papers/${paperId}/questions/${q.id}`, { method: "PATCH", json: { chapter: e.target.value } });
      await refreshClass();
      render();
    },
  });
}

function rosterCard(cls) {
  if (!cls) return h("div", { class: "card" }, [h("h3", {}, "Roster")]);
  const hot = cls.hotspots?.[0];
  return h("div", { class: "card" }, [
    h("h3", {}, `Roster · ${cls.counts.ready}/${cls.counts.n} ready`),
    hot && h("div", { class: "pill amber", style: "margin-bottom:10px" }, `Hotspot Q${hot.number} ${hot.chapter} · ${hot.percent}%`),
    h("table", {}, [
      h("thead", {}, h("tr", {}, ["Roll", "Name", "%", "Weak", "Status"].map((t) => h("th", {}, t)))),
      h("tbody", {}, cls.roster.map((r) => h("tr", {
        class: "clickable" + (state.selectedRoll === r.roll ? " selected" : ""),
        onclick: () => pickStudent(r.roll),
      }, [
        h("td", {}, r.roll),
        h("td", {}, r.name),
        h("td", {}, r.complete ? `${r.percent}` : "—"),
        h("td", {}, (r.weak || []).join(", ") || "—"),
        h("td", {}, r.complete ? "ready" : `blocked ${(r.missing || []).map((x) => x.toUpperCase()).join(", ")}`),
      ]))),
    ]),
  ]);
}

function studentCard(s, teacher) {
  if (!s) return h("div", { class: "card" }, [h("h3", {}, "Student"), h("p", {}, "Pick a roll. Demo: Ravi Mehta, 17.")]);
  const a = s.analysis;
  const b = s.briefs;
  return h("div", { class: "card" }, [
    h("div", { class: "section-kicker" }, s.paper?.title || ""),
    h("h3", {}, `${a.name} · roll ${a.roll}`),
    h("p", { class: "sub" }, a.complete ? `${fmt(a.got)}/${fmt(a.max)} · ${a.percent}%` : "Row incomplete — briefs blocked"),
    teacher && cellsEditor(s),
    yearCard(s.year || []),
    chaptersCard(a.chapters),
    lossesCard(a.losses),
    memoryCard(s.memory),
    h("div", { class: "briefs" }, [
      teacher && h("div", { class: b.blocked ? "brief blocked" : "brief" }, [h("h4", {}, "Teacher brief"), b.blocked ? b.reason : b.teacher]),
      h("div", { class: b.blocked ? "brief blocked" : "brief" }, [h("h4", {}, "Family brief"), b.blocked ? b.reason : b.family]),
    ]),
  ]);
}

function cellsEditor(s) {
  const cells = (s.analysis && s.analysis.cells) || [];
  if (!cells.length) return null;
  return h("div", { class: "cells" }, cells.map((c) => {
    const input = h("input", {
      class: "cell-input" + (c.empty ? " empty" : ""),
      type: "number",
      step: "0.5",
      min: "0",
      max: String(c.max),
      value: c.empty ? "" : String(c.got),
      placeholder: "empty",
    });
    return h("label", { class: "cell" + (c.empty ? " empty" : "") }, [
      h("span", {}, `Q${c.number}`),
      input,
      h("span", { class: "sub" }, `/ ${c.max}`),
      c.empty && h("button", {
        class: "ghost",
        type: "button",
        onclick: () => fillCell(s.paper.id, s.analysis.roll, c.id, input.value),
      }, "Save"),
    ]);
  }));
}

function yearCard(year) {
  if (!year.length) return null;
  return h("div", { class: "year" }, year.map((p) => h("div", { class: "point" }, [
    h("div", { class: "l" }, p.title),
    h("div", { class: "n" }, p.complete ? `${p.percent}%` : "—"),
  ])));
}

function chaptersCard(chapters) {
  return h("div", { style: "margin:12px 0" }, (chapters || []).map((c) => h("div", { style: "margin-bottom:8px" }, [
    h("div", { style: "display:flex;justify-content:space-between;font-size:13px" }, [
      h("span", {}, `[[${c.name}]]`),
      h("span", { class: `band ${c.band}` }, `${c.percent}% ${c.band}`),
    ]),
    h("div", { class: `bar ${c.band}` }, h("span", { style: `width:${c.percent}%` })),
  ])));
}

function memoryCard(mem) {
  if (!mem) return null;
  const trends = (mem.trends || []).slice(0, 4);
  return h("div", { class: "memory" }, [
    h("div", { class: "section-kicker" }, "Student memory"),
    h("p", { class: "sub" }, mem.readout || ""),
    ...trends.map((t) => h("div", { class: "sub" },
      `[[${t.chapter}]] ${t.from ?? "—"}% → ${t.to ?? "—"}% (${t.delta > 0 ? "+" : ""}${t.delta})`
    )),
  ]);
}

function lossesCard(losses) {
  if (!losses?.length) return null;
  return h("p", { class: "sub" }, "Mark losses: " + losses.slice(0, 3).map((l) => `Q${l.number} ${l.chapter} −${fmt(l.lost)}`).join(" · "));
}

function brainCardStatic(graph, title) {
  if (!graph?.nodes?.length) return null;
  const host = h("div", { class: "mindmap mindmap-mini" });
  const card = h("div", { class: "card brain-card" }, [
    h("h3", {}, title || "Local graph"),
    host,
  ]);
  mountMindmap(host, graph, false);
  return card;
}

function svgEl(tag, attrs, kids) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    el.setAttribute(k, String(v));
  }
  for (const kid of [].concat(kids || [])) {
    if (kid == null || kid === false) continue;
    el.append(typeof kid === "string" ? document.createTextNode(kid) : kid);
  }
  return el;
}

function mindmapLayout(graph, w, h) {
  const nodes = (graph.nodes || []).map((n) => ({ ...n }));
  const chapters = nodes.filter((n) => n.kind === "chapter");
  const questions = nodes.filter((n) => n.kind === "question");
  const student = nodes.find((n) => n.kind === "student");
  const paper = nodes.find((n) => n.kind === "paper");
  const cx = w / 2;
  const cy = h / 2 + 12;
  if (student) {
    student.x = cx;
    student.y = cy;
    student.r = 22;
  }
  if (paper) {
    paper.x = cx;
    paper.y = Math.max(36, cy - Math.min(h * 0.18, 90));
    paper.r = 10;
  }
  const nCh = Math.max(chapters.length, 1);
  const r1 = Math.min(w, h) * 0.26;
  const r2 = Math.min(w, h) * 0.40;
  chapters.forEach((c, i) => {
    const a = (i / nCh) * Math.PI * 2 - Math.PI / 2;
    c.x = cx + Math.cos(a) * r1;
    c.y = cy + Math.sin(a) * r1;
    c.r = 14;
    c.angle = a;
  });
  const byChapter = {};
  for (const q of questions) {
    const key = q.chapter || "Untagged";
    (byChapter[key] || (byChapter[key] = [])).push(q);
  }
  chapters.forEach((ch) => {
    const qs = byChapter[ch.wikilink] || byChapter[String(ch.label || "").replace(/[\[\]]/g, "")] || [];
    qs.forEach((q, j) => {
      const spread = (j - (qs.length - 1) / 2) * Math.min(0.38, 1.1 / Math.max(qs.length, 1));
      const a = ch.angle + spread;
      q.x = cx + Math.cos(a) * r2;
      q.y = cy + Math.sin(a) * r2;
      q.r = q.empty ? 10 : 9;
    });
  });
  questions.forEach((q) => {
    if (q.x == null) {
      q.x = cx;
      q.y = cy + r2;
      q.r = 9;
    }
  });
  return nodes;
}

function mindmapCurve(a, b) {
  const mx = (a.x + b.x) / 2;
  const my = (a.y + b.y) / 2;
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const len = Math.hypot(dx, dy) || 1;
  const bulge = Math.min(28, len * 0.18);
  const ox = (-dy / len) * bulge;
  const oy = (dx / len) * bulge;
  return `M ${a.x.toFixed(1)} ${a.y.toFixed(1)} Q ${(mx + ox).toFixed(1)} ${(my + oy).toFixed(1)} ${b.x.toFixed(1)} ${b.y.toFixed(1)}`;
}

function nodeFill(n) {
  if (n.kind === "student") return "#f59e0b";
  if (n.kind === "paper") return "#e7e5e4";
  if (n.empty) return "#0d0f14";
  return difficultyColor(nodeDifficulty(n));
}

function mountMindmap(host, graph, interactive = true) {
  if (!host) return;
  host.replaceChildren();
  if (!graph || !(graph.nodes || []).length) {
    host.append(h("p", { class: "sub", style: "padding:24px;color:#a8a29e" }, "No graph for this paper yet. Load the class, then pick a student."));
    return;
  }
  const w = interactive ? 900 : 640;
  const vh = interactive ? 480 : 260;
  const nodes = mindmapLayout(graph, w, vh);
  const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
  const treeKinds = new Set(["sat", "contains", "asks", "weak", "strong"]);
  const edges = (graph.edges || []).filter((e) => treeKinds.has(e.kind) && byId[e.source] && byId[e.target]);
  const svg = svgEl("svg", {
    class: "mindmap-svg",
    viewBox: `0 0 ${w} ${vh}`,
    width: String(w),
    height: String(vh),
    preserveAspectRatio: "xMidYMid meet",
    xmlns: "http://www.w3.org/2000/svg",
    role: "img",
    "aria-label": "Local mind map",
  });
  const edgeLayer = svgEl("g", { class: "mm-edges" });
  const nodeLayer = svgEl("g", { class: "mm-nodes" });
  const edgeEls = [];
  for (const e of edges) {
    const a = byId[e.source];
    const b = byId[e.target];
    const path = svgEl("path", {
      class: `mm-edge mm-${e.kind}`,
      d: mindmapCurve(a, b),
      "data-a": e.source,
      "data-b": e.target,
      stroke: (e.kind === "asks" || e.kind === "contains") ? difficultyColor(nodeDifficulty(b.kind === "question" || b.kind === "chapter" ? b : a)) : null,
    });
    edgeLayer.append(path);
    edgeEls.push({ el: path, a: e.source, b: e.target });
  }
  const nodeEls = [];
  for (const n of nodes) {
    const label = String(n.label || "").replace(/[\[\]]/g, "");
    const g = svgEl("g", {
      class: `mm-node mm-${n.kind}` + (n.empty ? " mm-empty" : "") + " mm-" + nodeDifficulty(n),
      transform: `translate(${n.x.toFixed(1)} ${n.y.toFixed(1)})`,
      "data-id": n.id,
    });
    const fill = nodeFill(n);
    g.append(
      svgEl("circle", {
        r: n.r,
        fill,
        class: "mm-dot",
        stroke: n.empty ? "#eab308" : "rgba(255,255,255,0.22)",
        "stroke-width": n.empty ? 2 : 1,
        "stroke-dasharray": n.empty ? "3 3" : null,
      }),
      svgEl("text", {
        class: "mm-label",
        x: 0,
        y: n.r + 16,
        "text-anchor": "middle",
      }, label),
    );
    if (interactive) {
      g.style.cursor = "pointer";
      g.addEventListener("mouseenter", (ev) => {
        focusMindmap(n, nodes, edgeEls, nodeEls);
        showMindTip(host, n, ev);
      });
      g.addEventListener("mousemove", (ev) => showMindTip(host, n, ev));
      g.addEventListener("click", (ev) => {
        ev.stopPropagation();
        state.graphPick = n;
        fillInspector(inspectGraphNode(n));
      });
    }
    nodeLayer.append(g);
    nodeEls.push({ el: g, id: n.id });
  }
  svg.append(edgeLayer, nodeLayer);
  const tip = h("div", { class: "mm-tip", hidden: true });
  if (interactive) {
    svg.addEventListener("mouseleave", () => {
      clearMindmapFocus(edgeEls, nodeEls);
      hideMindTip(host);
    });
  }
  host.append(svg, tip);
  window._mmFocus = (n) => focusMindmap(n, nodes, edgeEls, nodeEls);
}

function showMindTip(host, n, ev) {
  const tip = host.querySelector(".mm-tip");
  if (!tip) return;
  tip.hidden = false;
  tip.textContent = tipText(n);
  const box = host.getBoundingClientRect();
  const x = ev.clientX - box.left;
  const y = ev.clientY - box.top;
  tip.style.left = `${x}px`;
  tip.style.top = `${Math.max(18, y - 8)}px`;
}

function hideMindTip(host) {
  const tip = host.querySelector(".mm-tip");
  if (tip) tip.hidden = true;
}

function focusMindmap(n, nodes, edgeEls, nodeEls) {
  if (state.graphHover && state.graphHover.id === n.id) return;
  state.graphHover = n;
  const linked = new Set([n.id]);
  for (const e of edgeEls) {
    if (e.a === n.id) linked.add(e.b);
    if (e.b === n.id) linked.add(e.a);
  }
  for (const e of edgeEls) {
    const on = linked.has(e.a) && linked.has(e.b);
    e.el.classList.toggle("is-dim", !on);
    e.el.classList.toggle("is-on", on);
  }
  for (const item of nodeEls) {
    item.el.classList.toggle("is-dim", !linked.has(item.id));
    item.el.classList.toggle("is-on", linked.has(item.id));
  }
}

function clearMindmapFocus(edgeEls, nodeEls) {
  state.graphHover = null;
  for (const e of edgeEls) {
    e.el.classList.remove("is-dim", "is-on");
  }
  for (const item of nodeEls) {
    item.el.classList.remove("is-dim", "is-on");
  }
}

function btn(label, fn, cls) {
  return h("button", { class: cls, disabled: !!state.busy, onclick: fn }, state.busy === label ? "Working…" : label);
}

async function loadDemo() {
  state.busy = "Load class (Term 1 + Midterm)";
  state.error = "";
  render();
  try {
    const data = await api("/api/demo/midterm2", { method: "POST" });
    state.classData = data.class;
    state.paperId = "midterm";
    state.selectedRoll = "17";
    state.nav = "class";
    await selectStudent("17", true);
    await refreshMe();
    toast("Term 1 and Midterm are on the desk.");
  } catch (err) {
    state.error = err.message;
  } finally {
    state.busy = "";
    render();
  }
}

async function loadScreenshot() {
  state.busy = "Read sample screenshot";
  state.error = "";
  state.nav = "ingest";
  render();
  try {
    const data = await api("/api/demo/screenshot", { method: "POST" });
    state.shot = data;
    if (data.class) state.classData = data.class;
    state.paperId = "midterm";
    state.selectedRoll = data.roll || "17";
    if (data.ok) await selectStudent(state.selectedRoll, true);
    await refreshMe();
    toast(data.ok ? `Screenshot read via ${data.engine_label || data.engine}. Term 1 and Midterm split.` : (data.error || "Parse failed"));
  } catch (err) {
    state.error = err.message;
  } finally {
    state.busy = "";
    render();
  }
}

async function runDesk() {
  state.busy = "Run desk";
  render();
  try {
    await api("/api/desk/run", { method: "POST", json: {} });
    await refreshMe();
    toast("Desk ran through tools.");
  } catch (err) {
    state.error = err.message;
  } finally {
    state.busy = "";
    render();
  }
}

async function approveIntervention(id) {
  try {
    const data = await api("/api/workspace/intervention/approve", { method: "POST", json: { intervention_id: id } });
    state.me.workspace = data.workspace;
    toast("Intervention approved. Students have the task.");
    render();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

async function addressNode(pick) {
  try {
    const data = await api("/api/workspace/address", {
      method: "POST",
      json: { paper_id: state.paperId, roll: state.selectedRoll, question_id: pick.question_id },
    });
    state.student = data.student;
    state.me.workspace = data.workspace;
    toast(`Addressed ${pick.label}. Task sent to the student.`);
    state.graphPick = { ...pick, addressed: true };
    render();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

async function bonusNode(pick, extra) {
  try {
    const data = await api("/api/workspace/bonus", {
      method: "POST",
      json: { paper_id: state.paperId, roll: state.selectedRoll, question_id: pick.question_id, extra },
    });
    state.student = data.student;
    state.classData = data.class;
    toast(`Bonus +${extra} on ${pick.label}. Empty cells were not filled.`);
    render();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

async function sendBroadcast(e, audience, title, body) {
  e.preventDefault();
  try {
    const data = await api("/api/workspace/broadcast", { method: "POST", json: { audience, title: title.value, body: body.value } });
    state.me.workspace = data.workspace;
    toast(`Request sent to all ${audience}.`);
    render();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

async function sendTask(e, rollSel, title, body) {
  e.preventDefault();
  try {
    const data = await api("/api/workspace/task", { method: "POST", json: { roll: rollSel.value, title: title.value, body: body.value } });
    state.me.workspace = data.workspace;
    toast(`Task assigned to roll ${rollSel.value}.`);
    render();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

async function switchSection(id) {
  state.paperId = id;
  await refreshClass();
  if (state.selectedRoll) {
    try { await selectStudent(state.selectedRoll, true); } catch (_) {}
  }
  render();
}

async function selectStudent(roll, quiet) {
  state.selectedRoll = roll;
  state.student = await api(`/api/papers/${state.paperId}/students/${roll}`);
  if (!quiet) render();
}

async function refreshClass() {
  try { state.classData = await api(`/api/papers/${state.paperId}`); } catch (_) {}
}

async function refreshMe() {
  state.me = await api("/api/me");
}

async function doneTask(id) {
  try {
    const data = await api("/api/workspace/task/done", { method: "POST", json: { task_id: id } });
    state.me.workspace = data.workspace;
    toast("Task marked done.");
    render();
  } catch (err) {
    state.error = err.message;
    render();
  }
}

let pollTimer = null;
function startPoll() {
  clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    if (!state.me) return;
    try {
      const prev = JSON.stringify(state.me.workspace || {});
      const me = await api("/api/me");
      const changed = JSON.stringify(me.workspace || {}) !== prev;
      state.me = me;
      if (changed && (state.nav === "loop" || state.nav === "tasks")) render();
      else { fillNav(); fillTop(); }
    } catch (_) {}
  }, 7000);
}

async function logout() {
  clearInterval(pollTimer);
  await api("/api/logout", { method: "POST" });
  state.me = null;
  state.classData = null;
  state.student = null;
  state.sections = [];
  state.shot = null;
  cancelAnimationFrame(brainRaf);
  render();
}

async function loadHealth() {
  try {
    state.health = await fetch("/api/health").then((r) => r.json());
    if (!state.me) render();
  } catch (_) {}
}

async function blankRavi() {
  state.busy = "Blank Ravi Q9";
  render();
  try {
    const data = await api("/api/demo/ravi-q9-blank", { method: "POST" });
    state.student = data;
    state.selectedRoll = "17";
    state.paperId = "midterm";
    state.nav = "student";
    await refreshClass();
    await refreshMe();
    toast("Ravi Q9 is empty. Briefs blocked.");
  } catch (err) { state.error = err.message; }
  finally { state.busy = ""; render(); }
}

async function fillCell(paperId, roll, questionId, value) {
  try {
    const data = await api(`/api/papers/${paperId}/students/${roll}/cells/${questionId}`, {
      method: "PATCH",
      json: { value: Number(value) },
    });
    state.student = data;
    if (data.class) state.classData = data.class;
    await refreshMe();
    toast(data.briefs && data.briefs.blocked ? "Saved. Brief still blocked." : "Saved. Briefs recomputed.");
    render();
  } catch (err) { state.error = err.message; render(); }
}

async function resetDemo() {
  try {
    await fetch("/api/demo/reset", { method: "POST", credentials: "include" });
    toast("Demo class reset.");
  } catch (err) { state.error = err.message; }
  render();
}

async function boot() {
  render();
  await loadHealth();
  try {
    state.me = await api("/api/me");
    if (state.me.user.role !== "teacher") {
      try { state.faqs = (await api("/api/query/faqs")).faqs || []; } catch (_) {}
    }
    const papers = state.me.papers || [];
    const pick = papers.find((p) => p.id === state.paperId) || papers.find((p) => (p.section || p.id).includes("midterm")) || papers[0];
    if (pick) {
      state.paperId = pick.id;
      await refreshClass();
      const roll = state.me.user.roll || state.selectedRoll || "17";
      try { await selectStudent(roll, true); } catch (_) {}
      if (state.me.user.role !== "teacher") {
        const packed = await api(`/api/students/${roll}/sections`);
        state.sections = packed.sections || [];
      }
    }
  } catch {
    state.me = null;
  }
  startPoll();
  render();
}

function fmt(n) {
  if (n == null) return "—";
  return Number.isInteger(n) ? String(n) : String(n);
}

boot();
