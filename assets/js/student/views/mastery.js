'use strict';

  /* ================================================================
     视图 6 · 我的学情
     ================================================================ */
  const Mastery = {
    render() {
      const el = U.$('#view-mastery');
      el.innerHTML = `
      <div class="grid g-3" id="mStats" style="margin-bottom:16px">${U.skeleton(100)}</div>

      <div class="card" style="margin-bottom:16px">
        <div class="card__head">
          <h3>${icon('grid')} 知识点掌握矩阵</h3>
          <span class="spacer"></span>
          <div class="scale">
            ${['excellent', 'good', 'fair', 'weak', 'none'].map(l =>
        `<span class="scale__item"><i class="scale__sw" style="background:${U.levelColor[l]}"></i>${U.levelName[l]}</span>`).join('')}
          </div>
          <button class="btn btn--xs btn--ghost" id="mxToggleAll" type="button">全部折叠</button>
        </div>
        <div class="card__body card__body--flush">
          <div class="mx-head"><span>知识点</span><span>完成率</span><span>掌握率</span><span>练习情况</span><span>等级</span></div>
          <div class="matrix" id="matrixBox">${U.skeleton(400)}</div>
        </div>
      </div>

      <div class="grid g-2" style="margin-bottom:16px">
        <div class="card">
          <div class="card__head card__head--col"><h3>${icon('target')} 能力目标达成度</h3>
            <span class="badge badge--outline">目标图谱驱动</span></div>
          <div class="card__body"><div class="chart" id="radarChart"></div></div>
        </div>
        <div class="card">
          <div class="card__head"><h3>${icon('trend')} 成长轨迹（周）</h3><span class="spacer"></span></div>
          <div class="card__body"><div class="chart" id="growthChart"></div></div>
        </div>
      </div>

      <div class="grid g-2">
        <div class="card">
          <div class="card__head"><h3>${icon('alert')} 薄弱点清单</h3><span class="spacer"></span>
            <button class="btn btn--sm btn--outline" data-goto="practice">一键靶向练习</button></div>
          <div class="card__body card__body--flush"><div class="list" id="weakList"></div></div>
        </div>
        <div class="card">
          <div class="card__head"><h3>${icon('users')} 班级对比定位</h3><span class="spacer"></span>
            <span class="badge badge--brand" id="rankBadge"></span></div>
          <div class="card__body">
            <div class="chart chart--sm" id="compareChart"></div>
            <div class="tbl-wrap" style="margin-top:10px"><table class="tbl tbl--compact" id="compareTbl"></table></div>
          </div>
        </div>
      </div>`;

      // 指标
      API.student.dashboard().then(d => {
        const m = d.coreMetrics;
        U.$('#mStats').innerHTML = `
          <div class="stat" style="--_c:var(--brand-500)"><div class="stat__label">知识点完成率</div>
            <div class="stat__value"><span data-cnt="${m.completionRate}">0</span><small>%</small></div>
            <div class="stat__hint">已完成 ${Math.round(46 * m.completionRate / 100)} / 46 个知识点</div></div>
          <div class="stat" style="--_c:var(--ok)"><div class="stat__label">知识点掌握率</div>
            <div class="stat__value"><span data-cnt="${m.masteryRate}">0</span><small>%</small></div>
            <div class="stat__hint">达标线 60% · 已达标 32 个</div></div>
          <div class="stat" style="--_c:var(--accent-500)"><div class="stat__label">能力目标达成度</div>
            <div class="stat__value"><span data-cnt="${m.goalAchieveRate}">0</span><small>%</small></div>
            <div class="stat__hint">目标基线 80% · 差距 ${(80 - m.goalAchieveRate).toFixed(1)}pp</div></div>`;
        U.$$('[data-cnt]', el).forEach(s => U.countUp(s, +s.dataset.cnt, 1));

        U.$('#weakList').innerHTML = d.weakPoints.map(w => `
          <div class="list__item list__item--lv-${w.level}">
            <div class="list__main">
              <div class="row"><b>${U.esc(w.name)}</b><span class="badge ${U.levelBadge[U.level(w.masteryRate)]}">${w.masteryRate}%</span></div>
              <p>${U.esc(w.chapter)} · 累计错 ${w.errorCount} 题 · 近7日 ${w.trend > 0 ? '+' : ''}${w.trend}pp</p>
              <div style="margin-top:6px;max-width:280px">${U.bar(w.masteryRate)}</div>
            </div>
            <div class="list__trail">
              <button class="btn btn--xs btn--outline" data-goto="practice">去练习</button>
              <button class="btn btn--xs btn--ghost" data-ask2="请帮我讲解「${U.esc(w.name)}」">问 AI</button>
            </div>
          </div>`).join('');
        U.$$('[data-goto]', el).forEach(b => b.addEventListener('click', () => Router.go(b.dataset.goto)));
        U.$$('[data-ask2]', el).forEach(b => b.addEventListener('click', () => { Router.go('ai'); setTimeout(() => Chat.ask(b.dataset.ask2), 260); }));
      });

      // 矩阵（按章节可折叠）
      API.student.masteryMatrix().then(list => {
        const box = U.$('#matrixBox');
        box.innerHTML = list.map((ch, ci) => `
          <div class="mx-group" data-ch="${ci}">
            <button type="button" class="matrix__chapter mx-toggle" aria-expanded="true">
              <span class="mx-caret">${icon('chevronRight')}</span>
              <span class="mx-ch-name">${U.esc(ch.chapter)}</span>
              <span class="spacer"></span>
              <span class="fz-11 t-dim">章节完成率 <b class="mono">${ch.completionRate}%</b> · 掌握率 <b class="mono">${ch.masteryRate}%</b></span>
            </button>
            <div class="mx-body">
              ${ch.items.map(k => `
                <div class="mx-row" data-kp-id="${U.esc(k.kpId)}" data-kp-name="${U.esc(k.name)}" role="button" tabindex="0">
                  <div class="mx-row__name">
                    <b>${U.esc(k.name)}</b>
                    ${k.isKey ? '<span class="badge badge--warn">◆</span>' : ''}
                  </div>
                  <div class="mx-cell">
                    <div class="mx-cell__top"><span class="t-dim">完成</span><span>${k.completion}%</span></div>
                    ${U.bar(k.completion, k.completion >= 100 ? 'excellent' : k.completion > 0 ? 'fair' : 'none', 'sm')}
                  </div>
                  <div class="mx-cell">
                    <div class="mx-cell__top"><span class="t-dim">掌握</span><span style="color:${U.levelColor[k.level]}">${k.mastery}%</span></div>
                    ${U.bar(k.mastery, k.level, 'sm')}
                  </div>
                  <div class="fz-12 t-dim mono">${k.questions ? k.correct + '/' + k.questions : '—'}</div>
                  <div><span class="badge ${U.levelBadge[k.level]}">${U.levelName[k.level]}</span></div>
                </div>`).join('')}
            </div>
          </div>`).join('');

        // 逐章折叠 / 展开
        const syncToggleAll = () => {
          const allBtn = U.$('#mxToggleAll');
          if (!allBtn) return;
          const total = U.$$('.mx-group', box).length;
          const collapsed = U.$$('.mx-group.is-collapsed', box).length;
          allBtn.textContent = (collapsed === 0) ? '全部折叠' : '全部展开';
        };
        U.$$('.mx-toggle', box).forEach(btn => btn.addEventListener('click', () => {
          const g = btn.closest('.mx-group');
          const isCollapsed = g.classList.toggle('is-collapsed');
          btn.setAttribute('aria-expanded', String(!isCollapsed));
          syncToggleAll();
        }));
        // 全部折叠 / 展开
        const allBtn = U.$('#mxToggleAll');
        if (allBtn) allBtn.addEventListener('click', () => {
          const anyExpanded = U.$$('.mx-group:not(.is-collapsed)', box).length > 0;
          U.$$('.mx-group', box).forEach(g => {
            g.classList.toggle('is-collapsed', anyExpanded);
            const t = g.querySelector('.mx-toggle');
            if (t) t.setAttribute('aria-expanded', String(!anyExpanded));
          });
          allBtn.textContent = anyExpanded ? '全部展开' : '全部折叠';
        });

        // 点击知识点行 → 跳转至学习资源中心并定位到该 KP
        U.$$('.mx-row', box).forEach(row => {
          const go = () => {
            const kpName = row.dataset.kpName;
            if (!kpName) return;
            ResourceView._pendingKp = kpName;
            Router.go('resource');
          };
          row.addEventListener('click', go);
          row.addEventListener('keydown', e => {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); }
          });
        });
      });

      // 雷达 / 成长
      API.student.abilityRadar().then(d => Charts.radar('#radarChart', d));
      API.student.growth().then(d => Charts.line('#growthChart', d, { area: true, max: 100, fmt: '{value}%' }));

      // 对比
      API.student.compare().then(c => {
        U.$('#rankBadge').textContent = `班级第 ${c.myRank} / ${c.totalStudents} 名（前 ${100 - c.percentile}%）`;
        Charts.groupBar('#compareChart', {
          categories: c.items.slice(0, 4).map(i => i.metric),
          series: [
            { name: '我的', data: c.items.slice(0, 4).map(i => i.mine), color: Charts.tokens().brand },
            { name: '班级平均', data: c.items.slice(0, 4).map(i => i.classAvg), color: Charts.tokens().dim },
            { name: '班级最高', data: c.items.slice(0, 4).map(i => i.classBest), color: Charts.tokens().ok }
          ]
        });
        U.$('#compareTbl').innerHTML = `
          <thead><tr><th>指标</th><th class="t-right">我的</th><th class="t-right">班级平均</th><th class="t-right">差值</th></tr></thead>
          <tbody>${c.items.map(i => `<tr>
            <td>${i.metric}</td>
            <td class="t-right num fw-6">${i.mine}</td>
            <td class="t-right num t-dim">${i.classAvg}</td>
            <td class="t-right num ${i.diff >= 0 ? 't-ok' : 't-danger'}">${i.diff > 0 ? '+' : ''}${i.diff}</td>
          </tr>`).join('')}</tbody>`;
      });
    }
  };

Router.register('mastery', { title: '我的学情', mount: () => Mastery.render() });
