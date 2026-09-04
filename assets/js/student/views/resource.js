'use strict';

  /* ================================================================
     视图 3 · 学习资源中心
     ================================================================ */
  const ResourceView = {
    filter: 'all', keyword: '',
    _pendingKp: '', // 跳转定位：来自知识点掌握矩阵点击后预填的 KP 名称
    render() {
      const el = U.$('#view-resource');
      el.innerHTML = `
      <div class="grid g-12" style="margin-bottom:16px">
        <div class="card">
          <div class="card__head">
            <h3>${icon('route')} 推荐学习路径</h3>
            <span class="spacer"></span>
            <button class="btn btn--ghost btn--sm" id="pathExpandAll" type="button">全部折叠</button>
            <span class="badge badge--brand">图谱驱动</span>
          </div>
          <div class="card__body card__body--flush"><div class="path" id="pathList">${U.skeleton(300)}</div></div>
        </div>

        <div class="card">
          <div class="card__head">
            <h3>${icon('folder')} 资源聚合</h3>
            <span class="spacer"></span>
            <div class="search" style="width:200px">
              ${icon('search2')}<input class="input" id="resSearch" placeholder="搜索资源标题 / 知识点">
            </div>
          </div>
          <div class="card__body">
            <div class="chips" id="resChips" style="margin-bottom:14px">
              <button class="chip is-active" data-f="all">全部</button>
              <button class="chip" data-f="video">${'教学视频'}</button>
              <button class="chip" data-f="ppt">课堂PPT</button>
              <button class="chip" data-f="doc">教材文献</button>
            </div>
            <div class="res-grid" id="resGrid">${U.skeleton(200)}</div>
          </div>
        </div>
      </div>`;

      // 处理来自矩阵的跳转定位
      if (this._pendingKp) {
        this.keyword = this._pendingKp;
        this._pendingKp = '';
        const input = U.$('#resSearch');
        if (input) input.value = this.keyword;
      }

      // 学习路径 — 按章节分组，每章节可独立折叠/展开
      API.graph.learningPath().then(list => {
        const statusMap = { done: ['已完成', 'badge--ok', 'path__item--done'], doing: ['进行中', 'badge--brand', 'path__item--doing'], todo: ['未开始', 'badge--outline', ''], warn: ['待强化', 'badge--danger', ''] };

        const renderItem = p => {
          const [txt, bd, cls] = statusMap[p.status];
          return `<div class="path__item ${cls}">
            <div class="path__step">${p.status === 'done' ? '✓' : p.step}</div>
            <div class="path__main">
              <div class="row"><b>${U.esc(p.name)}</b><span class="spacer"></span><span class="badge ${bd}">${txt}</span></div>
              <div class="path__meta">
                <span>${p.hours} 学时</span><span>·</span><span>${p.resCount} 个资源</span>
                ${p.mastery ? `<span>·</span><span class="${U.level(p.mastery) === 'weak' ? 't-danger' : ''}">掌握 ${p.mastery}%</span>` : ''}
                ${p.locked ? `<span class="badge badge--outline">🔒 未解锁</span>` : ''}
              </div>
              ${p.progress ? `<div style="margin-top:7px;max-width:260px">${U.bar(p.progress, 'fair', 'sm')}</div>` : ''}
            </div>
          </div>`;
        };

        // 按章节聚合，保持原有顺序
        const groups = [];
        const order = {};
        list.forEach(p => {
          const ch = p.chapter || '其他章节';
          if (!(ch in order)) { order[ch] = groups.length; groups.push({ name: ch, items: [] }); }
          groups[order[ch]].items.push(p);
        });

        const html = groups.map(g => {
          const items = g.items;
          const done = items.filter(x => x.status === 'done').length;
          const avgM = items.length ? Math.round(items.reduce((s, x) => s + (x.mastery || 0), 0) / items.length) : 0;
          const totalHours = items.reduce((s, x) => s + (x.hours || 0), 0);
          const totalRes = items.reduce((s, x) => s + (x.resCount || 0), 0);
          const pct = items.length ? Math.round((done / items.length) * 100) : 0;
          const pctLevel = pct === 100 ? 'is-good' : pct === 0 ? 'is-low' : 'is-fair';
          const summary = `${done}/${items.length} 已完成 · 平均掌握 ${avgM}%`;
          // 默认全部章节展开，方便一眼看见全部章节的内容
          const collapsed = false;
          const itemsHtml = items.map(renderItem).join('');
          return `
            <div class="path__group ${collapsed ? 'is-collapsed' : ''}" data-chapter="${U.esc(g.name)}">
              <button class="path__chapter" type="button" aria-expanded="${!collapsed}">
                <div class="path__ch-row1">
                  <i class="path__caret" aria-hidden="true">▸</i>
                  <span class="path__chapter-name">${U.esc(g.name)}</span>
                  <span class="path__chapter-count">${items.length} 个知识点</span>
                  <span class="spacer"></span>
                  <span class="path__chapter-meta">${summary}</span>
                </div>
                <div class="path__ch-row2">
                  <div class="path__ch-progress" aria-hidden="true"><i class="${pctLevel}" style="width:${pct}%"></i></div>
                  <span class="path__ch-stats">共 ${totalHours} 学时 · ${totalRes} 个资源 · 章节完成 <b class="t-num">${pct}%</b></span>
                </div>
              </button>
              <div class="path__items">${itemsHtml}</div>
            </div>`;
        }).join('');

        const root = U.$('#pathList');
        root.innerHTML = html;

        // 章节折叠
        U.$$('.path__chapter', root).forEach(btn => {
          btn.addEventListener('click', () => {
            const g = btn.closest('.path__group');
            const c = g.classList.toggle('is-collapsed');
            btn.setAttribute('aria-expanded', String(!c));
            syncExpandAll();
          });
        });

        // 全部展开/折叠
        const expBtn = U.$('#pathExpandAll');
        function syncExpandAll() {
          if (!expBtn) return;
          const groups = U.$$('.path__group', root);
          const allCollapsed = groups.length > 0 && groups.every(g => g.classList.contains('is-collapsed'));
          expBtn.textContent = allCollapsed ? '全部展开' : '全部折叠';
        }
        if (expBtn) {
          syncExpandAll();
          expBtn.onclick = () => {
            const allCollapsed = U.$$('.path__group', root).every(g => g.classList.contains('is-collapsed'));
            U.$$('.path__group', root).forEach(g => {
              if (allCollapsed) g.classList.remove('is-collapsed');
              else g.classList.add('is-collapsed');
              const btn = g.querySelector('.path__chapter');
              if (btn) btn.setAttribute('aria-expanded', allCollapsed ? 'true' : 'false');
            });
            syncExpandAll();
          };
        }
      });

      const bind = () => {
        U.$$('#resChips .chip', el).forEach(c => c.addEventListener('click', () => {
          U.$$('#resChips .chip', el).forEach(x => x.classList.remove('is-active'));
          c.classList.add('is-active');
          this.filter = c.dataset.f; this.load();
        }));
        let tm;
        U.$('#resSearch').addEventListener('input', e => {
          clearTimeout(tm);
          tm = setTimeout(() => { this.keyword = e.target.value.trim(); this.load(); }, 260);
        });
      };
      bind();
      this.load();
    },
    load() {
      API.student.resources({ type: this.filter, keyword: this.keyword }).then(r => {
        const box = U.$('#resGrid');
        if (!box) return;
        box.innerHTML = r.list.length ? r.list.map(R.res).join('') : R.empty('没有匹配的资源', '试试更换筛选条件或关键词', 'search2');
        // 按当前 keyword 定位高亮匹配的 KP 卡片
        if (this.keyword) {
          const targets = U.$$('.res[data-kp]', box).filter(c => c.dataset.kp === this.keyword);
if (targets.length) {
          targets.forEach(c => c.classList.add('is-highlight'));
          try { targets[0].scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch (e) { /* 兼容旧环境 */ }
        }
        }
        U.$$('.res', box).forEach(c => c.addEventListener('click', () => {
          const res = r.list.find(x => x.resId === c.dataset.res);
          Modal.open({
            title: res.title,
            body: `<div style="aspect-ratio:16/9;border-radius:var(--r-md);background:linear-gradient(135deg,rgba(99,102,241,.2),rgba(139,92,246,.1));display:grid;place-items:center;margin-bottom:16px">
                <div style="text-align:center"><div style="width:52px;margin:0 auto 10px;color:var(--brand-300)">${icon('play')}</div>
                <p class="fz-12 t-dim">资源播放器占位（真实环境对接 MOOC / 资源平台）</p></div></div>
              <div class="kv">
                <div class="kv__row"><span>资源类型</span><span>${{ video: '教学视频', ppt: '课堂PPT', doc: '教材文献', quiz: '课程题库' }[res.type]}</span></div>
                <div class="kv__row"><span>关联知识点</span><span>${U.esc(res.kp)}</span></div>
                <div class="kv__row"><span>来源</span><span>${U.esc(res.source)}</span></div>
                <div class="kv__row"><span>学习进度</span><span>${res.progress}%</span></div>
              </div>`,
            footer: `<button class="btn" data-close>关闭</button><button class="btn btn--primary" data-close>继续学习</button>`
          });
        }));
      });
    }
  };

Router.register('resource', { title: '学习资源中心', mount: () => ResourceView.render() });
