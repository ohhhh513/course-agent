'use strict';

  /* ================================================================
     视图 3 · 学情归因与错题分析
     ================================================================ */
  const Analysis = {
    render() {
      const el = U.$('#view-analysis');
      el.innerHTML = U.skeleton(420);
      API.analysis.errors({ classId: state.classId }).then(d => {
        el.innerHTML = `
        <div class="callout callout--brand" style="margin-bottom:16px">${icon('flask')}
          <div><b>分析范围</b>${U.esc(d.scope.chapter)} · ${U.esc(d.scope.timeRange)} · ${d.scope.classId}
          · 系统通过对错题记录聚类与 AI 归因，识别共性薄弱与个性异常。</div></div>

        <div class="card" style="margin-bottom:16px">
          <div class="card__head"><h3>${icon('alert')} 高频错题 Top 5</h3></div>
          <div class="card__body card__body--flush"><div class="list">
            ${d.topWrongQuestions.map(q => `
              <div class="list__item">
                <div class="list__main"><b class="clamp-2">${U.esc(q.stem)}</b>
                  <p>${U.esc(q.kp)} · 难度 ${U.stars(q.difficulty)} · 主要错项 ${q.mainWrongOption}</p></div>
                <div class="list__trail"><span class="badge badge--danger">错 ${q.wrongRate}%</span><span class="badge badge--outline mono">${q.count}次</span></div>
              </div>`).join('')}
          </div></div>
        </div>

        <div class="card" style="margin-bottom:16px">
          <div class="card__head"><h3>${icon('link')} 知识点关联薄弱链路</h3></div>
          <div class="card__body">
            <div class="chain">
              <div class="chain__node chain__node--root"><b>${U.esc(d.weakChain.root.name)}</b><span>前置 · 掌握 ${d.weakChain.root.mastery}%</span></div>
              <div class="chain__arrow">${icon('chevronRight')}</div>
              <div class="chain__node chain__node--mid"><b>${U.esc(d.weakChain.mid.name)}</b><span>前置 · 掌握 ${d.weakChain.mid.mastery}%</span></div>
              <div class="chain__arrow">${icon('chevronRight')}</div>
              <div class="chain__node chain__node--leaf"><b>${U.esc(d.weakChain.leaf.name)}</b><span>目标 · 掌握 ${d.weakChain.leaf.mastery}%</span></div>
            </div>
            <div class="callout callout--warn" style="margin-top:14px">${icon('bulb')}<div>${U.esc(d.weakChain.explain)}</div></div>
          </div>
        </div>

        <div class="card" style="margin-bottom:16px">
          <div class="card__head"><h3>${icon('bulb')} AI 归因建议（成因概率降序）</h3><span class="spacer"></span>
            <span class="badge badge--brand">4 类成因</span></div>
          <div class="card__body card__body--flush">
            ${d.causes.map(c => `
              <div class="cause">
                <div class="cause__main">
                  <div class="row"><h4>${U.esc(c.title)}</h4>
                    <span class="spacer"></span><span class="badge ${c.level === 'danger' ? 'badge--danger' : c.level === 'warn' ? 'badge--warn' : 'badge--ok'}">${c.level === 'danger' ? '高优先' : c.level === 'warn' ? '中优先' : '低优先'}</span></div>
                  <p>${U.esc(c.desc)}</p>
                  <div class="fz-12 t-dim" style="margin-bottom:5px">证据</div>
                  <ul class="fz-12" style="margin:0 0 8px;padding-left:16px;color:var(--text-2)">${c.evidence.map(e => `<li>${U.esc(e)}</li>`).join('')}</ul>
                  <div class="callout callout--brand" style="padding:9px 11px">${icon('bulb')}<div><b>教学建议：</b>${c.advice.map(a => `<span class="badge badge--outline" style="margin:2px 4px 2px 0">${U.esc(a)}</span>`).join('')}</div></div>
                </div>
              </div>`).join('')}
          </div>
        </div>

        <div class="grid g-2">
          <div class="card">
            <div class="card__head"><h3>${icon('users')} 共性薄弱（班级层面）</h3></div>
            <div class="card__body stack" style="gap:12px">
              ${d.commonVsIndividual.common.map(c => `
                <div><div class="row fz-13" style="margin-bottom:5px"><b>${U.esc(c.kp)}</b><span class="spacer"></span>
                  <span class="badge badge--danger">${c.affected} 人 · ${c.ratio}%</span></div>
                  <div class="fz-12 t-dim">${U.esc(c.desc)}</div></div>`).join('')}
            </div>
          </div>
          <div class="card">
            <div class="card__head"><h3>${icon('user')} 个性异常（个体层面）</h3></div>
            <div class="card__body stack" style="gap:12px">
              ${d.commonVsIndividual.individual.map(s => `
                <div class="todo todo__ico--${s.issue.includes('未登录') || s.issue.includes('滞后') ? 'danger' : 'warn'}" style="background:var(--surface-2)">
                  <div class="todo__ico ${s.issue.includes('未登录') || s.issue.includes('滞后') ? 'todo__ico--danger' : 'todo__ico--warn'}">${icon('user')}</div>
                  <div class="todo__main"><b>${U.esc(s.student)}</b><span>${U.esc(s.issue)} · ${U.esc(s.desc)}</span></div>
                  <button class="btn btn--sm btn--outline" data-uid="${s.userId}">查看</button>
                </div>`).join('')}
            </div>
          </div>
        </div>`;

        U.$$('[data-uid]', el).forEach(b => b.addEventListener('click', () => Monitor.openProfile(b.dataset.uid)));
      });
    }
  };

Router.register('analysis', { title: '归因与错题分析', mount: () => Analysis.render() });
