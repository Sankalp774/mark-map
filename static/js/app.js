const state = {
  me: null,
  paperId: "midterm",
  classData: null,
  student: null,
  sections: [],
  selectedRoll: "17",
  error: "",
  busy: "",
  nav: "desk",
  toast: null,
  shot: null,
  loginAgent: null,
  agentStack: false,
  graphPick: null,
  faqs: [],
  ask: { question: "", answer: null, faq_id: null },
};

const TEACHER_NAV = [
  ["desk", "Overview"],
  ["class", "Class map"],
  ["student", "Student"],
  ["graph", "Local graph"],
  ["loop", "Class loop"],
  ["requests", "Requests"],
  ["calendar", "Calendar"],
  ["ingest", "Ingest"],
];
const FAMILY_NAV = [
  ["map", "Report"],
  ["loop", "Class loop"],
  ["tasks", "Tasks"],
  ["calendar", "Calendar"],
  ["ask", "Ask the desk"],
];

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
    agentSky(),
    h("div", { class: "login-card" }, [
      h("p", { class: "wordmark" }, "Mark Map · Class operations"),
      h("h1", {}, "The marksheet becomes a live class desk."),
      h("p", { class: "lede" }, "Pick a class. Talk to the room. Parents and students talk back. Briefs still wait for every cell."),
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
    ]),
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
    }, fanned ? "Stack" : "Agents"),
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
          active && h("p", { class: "mac-does" }, a.does),
        ]),
      ]);
    })),
  ]);
}

function shell() {
  const role = state.me.user.role;
  return h("div", { class: "shell " + role }, [
    h("aside", { class: "sidenav", id: "sidenav" }),
    h("div", { class: "workspace" }, [
      h("header", { class: "topbar", id: "topbar" }),
      h("div", { class: "main-pane", id: "main-pane" }),
    ]),
  ]);
}

function fillNav() {
  const nav = document.querySelector("#sidenav");
  if (!nav) return;
  const items = state.me.user.role === "teacher" ? TEACHER_NAV : FAMILY_NAV;
  const cur = state.me.current_class || {};
  const unread = (state.me.workspace || {}).unread || 0;
  nav.innerHTML = "";
  const kids = [
    h("div", { class: "brand" }, "Mark Map"),
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
  items.forEach(([id, label]) => {
    const badge = id === "loop" && unread ? ` (${unread})` : "";
    kids.push(h("button", {
      class: "navbtn" + (state.nav === id ? " active" : ""),
      onclick: () => { state.nav = id; render(); },
    }, label + badge));
  });
  kids.push(h("button", { class: "navbtn", style: "margin-top:auto", onclick: logout }, "Sign out"));
  nav.append(...kids);
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
  return h("div", {}, [
    h("div", { class: "toolbar" }, [
      btn("Load class (Term 1 + Midterm)", loadDemo, "primary"),
      btn("Read sample screenshot", loadScreenshot, "ghost"),
      btn("Run desk", runDesk, "ghost"),
    ]),
    h("div", { class: "stats-row" }, [
      stat("Scripts ready", k.n ? `${k.ready}/${k.n}` : "—"),
      stat("Incomplete", k.incomplete ?? "—"),
      stat("Needs review", k.needs_review ?? "—"),
      stat("Hotspot", k.hotspot ? `Q${k.hotspot.number} · ${k.hotspot.percent}%` : "—"),
    ]),
    h("div", { class: "alerts" }, alerts.map((a) => h("div", { class: `pill ${a.level}` }, a.text))),
    h("div", { class: "two-col" }, [
      h("div", { class: "card" }, [
        h("h3", {}, "Live operations"),
        h("p", { class: "sub" }, "Broadcasts, calendar, and graph actions write to the same JSON store the briefs read."),
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

function graphPane() {
  if (!state.student?.brain) return emptyLoad();
  const canvas = h("canvas", { class: "brain-canvas", width: "900", height: "460" });
  const inspector = h("div", { class: "inspector", id: "graph-inspector" }, graphInspectorKids());
  const card = h("div", { class: "card brain-card" }, [
    h("h3", {}, `${state.student.paper?.title || "Midterm"} · local graph`),
    h("p", { class: "sub", style: "color:#a8a29e" }, "Force-directed. Click Q9 to address the leak or award bonus. Weak edges stay red until you act."),
    canvas,
    inspector,
    h("div", { class: "backlinks" }, Object.entries(state.student.brain.backlinks || {}).map(([ch, qs]) =>
      h("div", {}, [h("span", { class: "wiki" }, `[[${ch}]]`), ` ← ${(qs || []).join(", ")}`])
    )),
  ]);
  queueMicrotask(() => mountBrain(canvas, state.student.brain));
  return card;
}

function graphInspectorKids() {
  const pick = state.graphPick;
  if (!pick) return [h("div", {}, "Click a question node. Addressing Q9 creates a task for that student. Bonus cannot fill an empty cell.")];
  const kids = [
    h("div", { class: "section-kicker" }, pick.kind),
    h("div", { style: "font-size:18px;margin:6px 0" }, String(pick.label || "").replace(/[\[\]]/g, "")),
    pick.chapter && h("div", {}, `Chapter [[${pick.chapter}]] · ${pick.band || ""}`),
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
  return h("div", { class: "two-col" }, [
    h("div", {}, [
      h("div", { class: "card" }, [
        h("h3", {}, "Request to all parents"),
        h("form", { class: "form-grid", onsubmit: (e) => sendBroadcast(e, "parents", pTitle, pBody) }, [
          pTitle, pBody, h("button", { class: "primary", type: "submit" }, "Send to parents"),
        ]),
      ]),
      h("div", { class: "card", style: "margin-top:12px" }, [
        h("h3", {}, "Request to all students"),
        h("form", { class: "form-grid", onsubmit: (e) => sendBroadcast(e, "students", sTitle, sBody) }, [
          sTitle, sBody, h("button", { class: "primary", type: "submit" }, "Send to students"),
        ]),
      ]),
      h("div", { class: "card", style: "margin-top:12px" }, [
        h("h3", {}, "Personal task / suggestion"),
        h("form", { class: "form-grid", onsubmit: (e) => sendTask(e, rollSel, tTitle, tBody) }, [
          rollSel, tTitle, tBody, h("button", { class: "primary", type: "submit" }, "Assign to this student"),
        ]),
      ]),
    ]),
    h("div", { class: "card" }, [
      h("h3", {}, "Outbox"),
      ...(ws.broadcasts || []).slice(0, 8).map((b) =>
        h("div", { class: "msg" }, [h("strong", {}, `${b.audience}: ${b.title}`), h("div", {}, b.body), h("div", { class: "when" }, b.at)])
      ),
      ...(ws.tasks || []).slice(0, 8).map((t) =>
        h("div", { class: "msg" }, [h("strong", {}, `Task · ${t.roll || "all"} · ${t.title}`), h("div", {}, t.body)])
      ),
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
      h("p", { class: "sub" }, "OCR reads SECTION Term 1 / SECTION Midterm and Q-lines. The sample report is generated from Ravi’s actual cells — not invented."),
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
    h("div", { class: "section-kicker" }, shot.ok ? `Read · ${shot.engine}` : `Failed · ${shot.engine || "none"}`),
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
    brief && (brief.blocked ? h("div", { class: "brief blocked" }, brief.reason) : h("div", { class: "brief" }, brief.family || "")),
    brainCardStatic(block.brain, `${block.title} · local graph`),
  ]);
}

function tasksPane() {
  const tasks = ((state.me.workspace || {}).tasks || []);
  if (!tasks.length) return h("div", { class: "card" }, [h("h3", {}, "Tasks"), h("p", {}, "No tasks yet.")]);
  return h("div", { class: "card" }, [
    h("h3", {}, "Assigned work"),
    ...tasks.map((t) => h("div", { class: "msg" }, [
      h("strong", {}, `${t.status === "done" ? "Done" : "Open"} · ${t.title}`),
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
      class: "form-grid",
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
  return h("div", { class: "two-col" }, [
    h("div", {}, [
      h("div", { class: "card" }, [
        h("h3", {}, "Class loop"),
        h("p", { class: "sub" }, "Requests, acknowledgements, and replies in this class. This is a conversation, not a notice board."),
        ...broadcasts.map((b) => h("div", { class: "msg" }, [
          h("strong", {}, `${b.audience} · ${b.title}`),
          h("div", {}, b.body),
          h("div", { class: "when" }, `${b.teacher || "Teacher"} · ${(b.acks || []).length} acknowledged · ${(b.replies || []).length} replies`),
          ...(b.replies || []).map((r) => h("div", { class: "bubble " + r.role }, `${r.name}: ${r.body}`)),
          !teacher && h("div", { class: "row-actions" }, [
            h("button", { class: "ghost", onclick: () => ackBroadcast(b.id) }, "Acknowledge"),
          ]),
          replyBox(b.id),
        ])),
        !broadcasts.length && h("p", { class: "sub" }, "No class requests yet. Teacher can send one from Requests."),
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
        ...threads.map((t) => h("div", { class: "msg" }, [
          h("strong", {}, `Thread · roll ${t.roll}`),
          ...(t.messages || []).slice(-8).map((m) => h("div", { class: "bubble " + m.role }, `${m.name}: ${m.body}`)),
        ])),
      ]),
    ]),
    h("div", { class: "card" }, [
      h("h3", {}, "Live"),
      h("p", { class: "sub" }, `${ws.unread || 0} unread in this class. The loop refreshes while you stay signed in.`),
      ...(ws.tasks || []).slice(0, 6).map((t) => h("div", { class: "msg" }, t.title)),
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
    h("p", { class: "sub" }, "Answers come from the marksheet, calendar, and tasks. The desk will not invent a mark or talk personality."),
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
      h("thead", {}, h("tr", {}, ["Q", "Max", "Chapter", "Source"].map((t) => h("th", {}, t)))),
      h("tbody", {}, paper.questions.map((q) => h("tr", {}, [
        h("td", {}, `Q${q.number}`),
        h("td", {}, String(q.max_marks)),
        h("td", {}, chapterEditor(paper.id, q)),
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
        onclick: () => { state.selectedRoll = r.roll; state.nav = "student"; selectStudent(r.roll); },
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
    yearCard(s.year || []),
    chaptersCard(a.chapters),
    lossesCard(a.losses),
    h("div", { class: "briefs" }, [
      teacher && h("div", { class: b.blocked ? "brief blocked" : "brief" }, [h("h4", {}, "Teacher brief"), b.blocked ? b.reason : b.teacher]),
      h("div", { class: b.blocked ? "brief blocked" : "brief" }, [h("h4", {}, "Family brief"), b.blocked ? b.reason : b.family]),
    ]),
  ]);
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

function lossesCard(losses) {
  if (!losses?.length) return null;
  return h("p", { class: "sub" }, "Mark losses: " + losses.slice(0, 3).map((l) => `Q${l.number} ${l.chapter} −${fmt(l.lost)}`).join(" · "));
}

function brainCardStatic(graph, title) {
  if (!graph?.nodes?.length) return null;
  const canvas = h("canvas", { class: "brain-canvas", width: "720", height: "380" });
  const card = h("div", { class: "card brain-card" }, [
    h("h3", {}, title || "Local graph"),
    canvas,
  ]);
  queueMicrotask(() => mountBrain(canvas, graph, false));
  return card;
}

let brainRaf = 0;
function mountBrain(canvas, graph, interactive = true) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  cancelAnimationFrame(brainRaf);
  const w = canvas.width;
  const h = canvas.height;
  const chapters = (graph.nodes || []).filter((n) => n.kind === "chapter");
  const questions = (graph.nodes || []).filter((n) => n.kind === "question");
  const nodes = (graph.nodes || []).map((n) => {
    let x = w / 2; let y = h / 2;
    if (n.kind === "paper") y = 50;
    if (n.kind === "chapter") {
      const i = chapters.findIndex((c) => c.id === n.id);
      const ang = (i / Math.max(chapters.length, 1)) * Math.PI * 2 - Math.PI / 2;
      x = w / 2 + Math.cos(ang) * 160;
      y = h / 2 + Math.sin(ang) * 120;
    }
    if (n.kind === "question") {
      const i = questions.findIndex((c) => c.id === n.id);
      const ang = (i / Math.max(questions.length, 1)) * Math.PI * 2 - Math.PI / 2;
      x = w / 2 + Math.cos(ang) * 280;
      y = h / 2 + Math.sin(ang) * 175;
    }
    return { ...n, x, y, vx: 0, vy: 0, r: n.kind === "student" ? 13 : n.kind === "chapter" ? 9 : 6 };
  });
  const edges = graph.edges || [];
  function step() {
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i]; const b = nodes[j];
        let dx = a.x - b.x; let dy = a.y - b.y;
        let d = Math.hypot(dx, dy) || 0.1;
        const force = 220 / (d * d);
        dx /= d; dy /= d;
        a.vx += dx * force; a.vy += dy * force;
        b.vx -= dx * force; b.vy -= dy * force;
      }
    }
    for (const e of edges) {
      const a = nodes.find((n) => n.id === e.source);
      const b = nodes.find((n) => n.id === e.target);
      if (!a || !b) continue;
      const dx = b.x - a.x; const dy = b.y - a.y;
      a.vx += dx * 0.01; a.vy += dy * 0.01;
      b.vx -= dx * 0.01; b.vy -= dy * 0.01;
    }
    for (const n of nodes) {
      if (n.kind === "student") { n.x = w / 2; n.y = h / 2; n.vx = 0; n.vy = 0; continue; }
      n.vx *= 0.82; n.vy *= 0.82;
      n.x = Math.max(24, Math.min(w - 24, n.x + n.vx));
      n.y = Math.max(24, Math.min(h - 24, n.y + n.vy));
    }
    draw();
    brainRaf = requestAnimationFrame(step);
  }
  function draw() {
    ctx.fillStyle = "#0d0f14";
    ctx.fillRect(0, 0, w, h);
    const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
    for (const e of edges) {
      const a = byId[e.source]; const b = byId[e.target];
      if (!a || !b) continue;
      ctx.strokeStyle = e.kind === "weak" ? "rgba(248,113,113,0.6)" : e.kind === "strong" ? "rgba(74,222,128,0.55)" : "rgba(100,116,139,0.35)";
      ctx.lineWidth = e.kind === "weak" || e.kind === "strong" ? 2 : 1;
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
    }
    for (const n of nodes) {
      const picked = state.graphPick && state.graphPick.id === n.id;
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.r + (picked ? 3 : 0), 0, Math.PI * 2);
      ctx.fillStyle = n.kind === "student" ? "#f59e0b" : n.kind === "paper" ? "#e7e5e4" : n.addressed ? "#38bdf8" : n.band === "weak" ? "#ef4444" : n.band === "strong" ? "#22c55e" : "#60a5fa";
      ctx.fill();
      ctx.fillStyle = "#e7e5e4";
      ctx.font = "12px IBM Plex Sans, sans-serif";
      ctx.fillText(String(n.label || "").replace(/[\[\]]/g, ""), n.x + 12, n.y + 4);
    }
  }
  if (interactive) {
    canvas.onclick = (ev) => {
      const rect = canvas.getBoundingClientRect();
      const x = (ev.clientX - rect.left) * (canvas.width / rect.width);
      const y = (ev.clientY - rect.top) * (canvas.height / rect.height);
      const hit = nodes.find((n) => Math.hypot(n.x - x, n.y - y) < n.r + 8);
      if (hit) {
        state.graphPick = hit;
        const host = document.querySelector("#graph-inspector");
        if (host) { host.innerHTML = ""; graphInspectorKids().forEach((k) => host.append(k)); }
      }
    };
  }
  step();
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
    toast(data.ok ? `Screenshot read via ${data.engine}. Term 1 and Midterm split.` : (data.error || "Parse failed"));
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
    toast("Desk alerts refreshed.");
  } catch (err) {
    state.error = err.message;
  } finally {
    state.busy = "";
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

async function boot() {
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
