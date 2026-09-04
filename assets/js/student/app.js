/* ==========================================================================
   学生端 · 应用引导（路由守卫 / 顶栏 / 全局初始化）
   必须最先加载；视图模块随后各自 Router.register，最后由 start.js 启动路由。
   ========================================================================== */
(function () {
  'use strict';
    if (window.Auth && !Auth.requireAuth('student')) return;
  
    Theme.init();
    // 侧栏图标注入
    U.$$('.nav-item').forEach(n => n.insertAdjacentHTML('afterbegin', icon(n.dataset.icon, 'nav-item__icon')));
    U.$('#msgBtn').innerHTML = icon('message');
    initTopbar();
  
    /* ================================================================
       顶栏：更新时间 + 消息
       ================================================================ */
    API.student.dashboard().then(d => {
      U.$('#updateTag').textContent = '学情更新于 ' + d.coreMetrics.updatedAt;
    });
  
    U.$('#msgBtn').addEventListener('click', () => {
      API.student.messages().then(r => {
        Modal.open({
          title: '消息与通知',
          body: `<div class="list" style="margin:-20px">${r.list.map(m => `
            <div class="list__item">
              <span class="list__lead">${icon(m.from === '系统' ? 'info' : 'user', '')}</span>
              <div class="list__main">
                <b>${U.esc(m.title)} ${m.read ? '' : '<span class="badge badge--danger">未读</span>'}</b>
                <p style="margin:5px 0;line-height:1.7;color:var(--text-2)">${U.esc(m.content)}</p>
                <p class="fz-11 t-dim">${U.esc(m.from)} · ${m.time}</p>
              </div>
            </div>`).join('')}</div>`
        });
      });
    });
  window.__studentAuthed = true;
})();
