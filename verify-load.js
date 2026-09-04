'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const JS = path.join(__dirname, 'assets/js');

function fakeEl() {
  return {
    innerHTML: '', textContent: '', style: {}, value: '',
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    setAttribute() {}, getAttribute() { return null; }, appendChild() {},
    addEventListener() {}, removeEventListener() {}, insertAdjacentHTML() {},
    remove() {}, querySelector: () => null, querySelectorAll: () => [], closest: () => null,
    scrollIntoView() {}, scrollTop: 0, focus() {}, cloneNode() { return fakeEl(); },
  };
}
function mkApi() {
  const p = () => new Promise(() => {}); // 永不 resolve，避免触发 render 需要真实 DOM
  return new Proxy(function () {}, {
    get(t, k) { if (k === 'then') return undefined; if (k === Symbol.toPrimitive) return undefined; return mkApi(); },
    apply() { return p(); },
  });
}
const Router = { views: {}, titles: {}, current: null,
  register(k, c) { this.views[k] = c; }, init() {}, go() {}, };

const sandbox = {
  window: null, document: {
    querySelector: () => fakeEl(), querySelectorAll: () => [], getElementById: () => fakeEl(),
    createElement: () => fakeEl(), head: { appendChild() {} }, body: { appendChild() {} },
    addEventListener() {}, documentElement: { setAttribute() {} },
  },
  location: { href: '', hash: '' }, performance: { now: () => 0 },
  requestAnimationFrame: () => 0, CustomEvent: function () {}, console,
  U: { $: () => fakeEl(), $$: () => [], level: () => 'fair', esc: s => String(s), bar: () => '', ring: () => '', skeleton: () => '', countUp() {}, delta: () => '', levelColor: {}, levelBadge: {}, levelName: {}, alertName: {}, alertBadge: {}, alertCard: {}, stars: () => '', fmtDuration: () => '' },
  icon: () => '', Router,
  API: mkApi(), MOCK: { teacher: { classes: [] }, studentAlerts: [] },
  Toast: { ok() {}, info() {}, warn() {}, err() {}, show() {} },
  Charts: new Proxy({}, { get: () => () => {} }),
  Modal: { open: () => ({ close() {} }), drawer: () => ({ close() {} }) },
  Theme: { init() {}, set() {}, get: () => 'light', toggle() {} },
  initTopbar: () => {}, R: { todo: () => '', lamp: () => '', res: () => '', empty: () => '' },
  Auth: { requireAuth: () => true, getSession: () => null, applyUserBadge() {}, logout() {} },
  setTimeout, clearTimeout, setInterval, clearInterval,
};
sandbox.window = sandbox;
vm.createContext(sandbox);

function concat(files) {
  return files.map(f => fs.readFileSync(path.join(JS, f), 'utf8')).join('\n;\n');
}

const studentFiles = [
  'student/app.js', 'student/views/dashboard.js', 'student/views/graph.js',
  'student/views/resource.js', 'student/views/chat.js', 'student/views/practice.js',
  'student/views/mastery.js', 'student/views/alerts.js', 'student/start.js',
];
const teacherFiles = [
  'teacher/app.js', 'teacher/views/dash.js', 'teacher/views/monitor.js',
  'teacher/views/analysis.js', 'teacher/views/question.js',
  'teacher/views/intervention.js', 'teacher/views/report.js', 'teacher/start.js',
];

// 集合比较（与注册顺序无关，避免硬编码排序导致误报）
function run(name, files, expectArr) {
  Router.views = {};
  try {
    vm.runInContext(concat(files), sandbox, { filename: name });
  } catch (e) {
    console.log('FAIL ' + name + ': ' + e.message);
    process.exitCode = 1;
    return;
  }
  const got = Object.keys(Router.views).sort().join(',');
  const expect = expectArr.slice().sort().join(',');
  const ok = got === expect;
  console.log((ok ? 'PASS ' : 'FAIL ') + name + ' routes=[' + got + ']');
  if (!ok) { console.log('   expected=[' + expect + ']'); process.exitCode = 1; }
}

run('student', studentFiles, ['dashboard','graph','resource','ai','practice','mastery','alerts']);
run('teacher', teacherFiles, ['dashboard','monitor','analysis','question','intervention','report']);
console.log('window.__studentAuthed=' + sandbox.window.__studentAuthed + '  window.__teacherAuthed=' + sandbox.window.__teacherAuthed);
