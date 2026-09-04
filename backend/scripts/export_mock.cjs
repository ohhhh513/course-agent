/* 把前端 mock/data.js 导出为 JSON，作为后端种子数据的单一真相源。
   运行：node scripts/export_mock.cjs
   产物：app/data/mock_data.json
   说明：前端 window.MOCK = (function(){...})() 是 IIFE，注入一个假 window 即可拿到 MOCK。 */
const fs = require('fs');
const path = require('path');

const SRC = path.join(__dirname, '..', '..', 'assets', 'js', 'mock', 'data.js');
const OUT = path.join(__dirname, '..', 'app', 'data', 'mock_data.json');

const src = fs.readFileSync(SRC, 'utf8');
const sandboxWindow = {};
// 在隔离作用域内执行 data.js，使其把结果挂到我们提供的 window 上
new Function('window', src)(sandboxWindow);

if (!sandboxWindow.MOCK) {
  console.error('导出失败：未找到 window.MOCK');
  process.exit(1);
}
fs.writeFileSync(OUT, JSON.stringify(sandboxWindow.MOCK, null, 2));
console.log('已导出 ' + Object.keys(sandboxWindow.MOCK).length + ' 个键 -> ' + OUT);
