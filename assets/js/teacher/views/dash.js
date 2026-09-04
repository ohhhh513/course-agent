'use strict';

  /* ================================================================
     视图 1 · 教学驾驶舱
     ================================================================ */
  const Dash = {
    render() {
      const el = U.$('#view-dashboard');
      el.innerHTML = U.skeleton(420);
      API.teacher.dashboard({ classId: state.classId }).then(d => {
        const ov = d.classOverview;
        el.innerHTML = `
        <div class="hero">
          <div class="hero__main">
            <div class="row" style="margin-bottom:6px">
              ${R.lamp(ov.alertRatio >= 20 ? 'red' : 'yellow', '预警占比 ' + ov.alertRatio + '%')}
              <span class="badge badge--outline">${ov.studentCount} 名学生</span>
              <span class="badge badge--brand">${ov.className}</span>
            </div>
            <h2>${ov.className} · 教学驾驶舱</h2>
            <p>数据更新于 <b class="t-brand">${ov.updatedAt}</b> · 今日活跃 <b>${ov.activeToday}</b> 人 · 提交 <b>${ov.submitToday}</b> 次</p>
          </div>
          <div class="hero__stats">
            <div class="hero__stat"><b class="mono">${ov.avgMasteryRate}%</b><span>平均掌握率</span>${U.delta(ov.deltaMastery)}</div>
            <div class="hero__stat"><b class="mono">${ov.avgCompletionRate}%</b><span>平均完成率</span>${U.delta(ov.deltaCompletion)}</div>
            <div class="hero__stat"><b class="mono">${ov.avgGoalAchieve}%</b><span>目标达成度</span>${U.delta(ov.deltaGoal)}</div>
          </div>
        </div>

        <div class="grid g-21" style="margin-bottom:16px">
          <div class="card">
            <div class="card__head"><h3>${icon('bell')} 待办事项</h3><span class="spacer"></span>
              <span class="badge badge--danger">${d.todos.length} 项</span></div>
            <div class="card__body stack" style="gap:10px">${d.todos.map(R.todo).join('')}</div>
          </div>
          <div class="card">
            <div class="card__head"><h3>${icon('trend')} 实时动态</h3><span class="spacer"></span>
              <span class="badge badge--ok">实时</span></div>
            <div class="card__body card__body--flush">
              <div class="list" style="max-height:360px;overflow:auto">
                ${d.liveFeed.map(f => `
                  <div class="list__item">
                    <span class="list__lead" style="color:${f.level === 'danger' ? 'var(--danger)' : f.level === 'warn' ? 'var(--warn)' : 'var(--ok)'}">
                      ${icon(f.type === 'submit' ? 'check' : f.type === 'alert' ? 'alert' : 'message')}</span>
                    <div class="list__main"><b>${U.esc(f.text)}</b><p>${U.esc(f.meta)}</p></div>
                    <span class="list__trail fz-11 t-dim">${f.time}</span>
                  </div>`).join('')}
              </div>
            </div>
          </div>
        </div>

        <div class="grid g-2">
          <div class="card">
            <div class="card__head"><h3>${icon('target')} 班级共性薄弱知识点排行</h3><span class="spacer"></span>
              <span class="badge badge--danger">Top 5</span></div>
            <div class="card__body">
              ${d.kpRanking.map(k => `
                <div style="margin-bottom:15px">
                  <div class="row fz-13" style="margin-bottom:5px"><b>${U.esc(k.name)}</b><span class="spacer"></span>
                    <span class="mono fz-12 ${k.mastery < 60 ? 't-danger' : 't-warn'}">${k.mastery}%</span></div>
                  ${U.bar(k.mastery, k.mastery < 60 ? 'weak' : 'fair', 'sm')}
                  <div class="fz-11 t-dim" style="margin-top:4px">${k.weakCount} / ${k.students} 名学生未达标</div>
                </div>`).join('')}
            </div>
          </div>
          <div class="card">
            <div class="card__head"><h3>${icon('grid')} 班级学情总览</h3></div>
            <div class="card__body">
              <div class="chart" id="dashDonut"></div>
              <div class="callout callout--brand" style="margin-top:4px">${icon('info')}
                <div>红色预警学生 <b>${ov.alertStudentCount}</b> 名（占比 ${ov.alertRatio}%），建议优先处理驾驶舱待办中的干预建议。</div></div>
            </div>
          </div>
        </div>`;

        Charts.donut('#dashDonut', [
          { name: '预警学生', value: ov.alertStudentCount, color: Charts.tokens().danger },
          { name: '正常学生', value: Math.max(0, ov.studentCount - ov.alertStudentCount), color: Charts.tokens().ok }
        ], { centerValue: ov.alertStudentCount, centerLabel: '预警学生' });

        U.$$('.todo', el).forEach(t => t.addEventListener('click', () => { if (t.dataset.target) Router.go(t.dataset.target); }));
      });
    }
  };

Router.register('dashboard', { title: '教学驾驶舱', mount: () => Dash.render() });
