'use strict';

  /* ================================================================
     视图 4 · AI 出题与题库管理
     ================================================================ */
  const Question = {
    tab: 'gen',
    gen: { kpIds: [], types: ['single'], difficulty: 3, count: 6 },
    bankFilter: 'all', bankKeyword: '',
    render() {
      const el = U.$('#view-question');
      el.innerHTML = `
      <div class="tabs" id="qTabs" style="margin-bottom:16px">
        <button class="is-active" data-t="gen">${icon('sparkle')} AI 智能出题</button>
        <button data-t="bank">${icon('file')} 题库管理</button>
      </div>
      <div id="qBody"></div>`;
      U.$$('#qTabs button', el).forEach(b => b.addEventListener('click', () => {
        U.$$('#qTabs button', el).forEach(x => x.classList.remove('is-active'));
        b.classList.add('is-active'); this.tab = b.dataset.t;
        this.tab === 'gen' ? this.renderGen() : this.renderBank();
      }));
      this.renderGen();
    },

    renderGen() {
      const box = U.$('#qBody');
      API.question.genConfig({ classId: state.classId }).then(cfg => {
        this._cfg = cfg;
        box.innerHTML = `
        <div class="gen-layout">
          <div class="stack" style="gap:14px">
            <div class="card">
              <div class="card__head"><h3>${icon('upload')} 素材库</h3></div>
              <div class="card__body">
                <div class="upload" id="genUpload">
                  <div style="color:var(--brand-400)">${icon('upload')}</div>
                  <b>上传教材 / 课件 / 视频</b><span>PDF · PPT · MP4，AI 自动解析并挂载知识点</span>
                </div>
                <div class="stack" style="gap:6px;margin-top:10px">
                  ${cfg.materials.map(m => `
                    <div class="file-item">${icon(m.type === 'video' ? 'video' : m.type === 'doc' ? 'file' : 'ppt')}
                      <b>${U.esc(m.name)}</b>
                      <span class="fz-11 t-dim nowrap">${m.size}</span>
                      ${m.status === 'parsing'
                        ? `<span class="badge badge--warn">解析中 ${m.progress}%</span>`
                        : `<span class="badge badge--ok">已解析 · ${m.kpCount} 知识点</span>`}</div>`).join('')}
                </div>
              </div>
            </div>
            <div class="card">
              <div class="card__head"><h3>${icon('settings')} 出题配置</h3></div>
              <div class="card__body stack" style="gap:12px">
                <div><p class="fz-12 t-dim" style="margin-bottom:6px">指定知识点（可多选）</p>
                  <div class="chips" id="genKp">${cfg.kpOptions.map(k =>
                    `<button class="chip" data-kp="${k.kpId}">${U.esc(k.name)}</button>`).join('')}</div></div>
                <div><p class="fz-12 t-dim" style="margin-bottom:6px">题型</p>
                  <div class="chips" id="genType">${cfg.typeOptions.map(t =>
                    `<button class="chip ${t.key === 'single' ? 'is-active' : ''}" data-ty="${t.key}">${t.name}</button>`).join('')}</div></div>
                <div class="grid g-2" style="gap:12px">
                  <div><p class="fz-12 t-dim" style="margin-bottom:6px">难度 <span class="mono" id="genDiffLbl">${this.gen.difficulty} 星</span></p>
                    <input type="range" min="1" max="5" value="${this.gen.difficulty}" id="genDiff" style="width:100%"></div>
                  <div><p class="fz-12 t-dim" style="margin-bottom:6px">题量</p>
                    <div class="seg" id="genCount"><button data-c="3">3</button><button data-c="6" class="is-active">6</button><button data-c="10">10</button></div></div>
                </div>
                <button class="btn btn--primary btn--block" id="genBtn">${icon('sparkle')} 生成习题</button>
              </div>
            </div>
          </div>
          <div class="stack" style="gap:12px">
            <div class="callout callout--brand">${icon('info')}<div>AI 将依据课程标准自动标注每题的<b>知识点定位树</b>（前后置关系 + 重难点），并附<b>材料溯源</b>（fileId + 定位），确保可解释、可溯源。</div></div>
            <div id="genResult"><div class="card"><div class="card__body card__body--flush" style="padding:18px">${R.empty('配置后点击「生成习题」', 'AI 将产出并预览题目与解析', 'sparkle')}</div></div></div>
          </div>
        </div>`;

        U.$('#genUpload').addEventListener('click', () => {
          Modal.open({
            title: '上传出题素材',
            body: `<div class="upload" style="cursor:default">${icon('upload')}<b>选择文件（演示）</b><span>真实环境此处触发分片上传与异步解析</span></div>
              <div class="kv" style="margin-top:14px"><div class="kv__row"><span>支持格式</span><span>PDF / PPT / PPTX / MP4</span></div>
              <div class="kv__row"><span>解析产物</span><span>知识点挂载 · 难度标注 · 溯源定位</span></div></div>`,
            footer: `<button class="btn" data-close>关闭</button><button class="btn btn--primary" id="upOk">模拟上传</button>`,
            onMount(ov, close) {
              U.$('#upOk', ov).addEventListener('click', () => { API.question.upload({ name: '新素材.pdf' }).then(() => { Toast.ok('素材已上传', '开始异步解析'); close(); }); });
            }
          });
        });

        U.$$('#genKp .chip', box).forEach(c => c.addEventListener('click', () => {
          c.classList.toggle('is-active');
          const id = c.dataset.kp;
          if (this.gen.kpIds.includes(id)) this.gen.kpIds = this.gen.kpIds.filter(x => x !== id);
          else this.gen.kpIds.push(id);
        }));
        U.$$('#genType .chip', box).forEach(c => c.addEventListener('click', () => {
          U.$$('#genType .chip', box).forEach(x => x.classList.remove('is-active'));
          c.classList.add('is-active'); this.gen.types = [c.dataset.ty];
        }));
        U.$('#genDiff', box).addEventListener('input', e => { this.gen.difficulty = +e.target.value; U.$('#genDiffLbl', box).textContent = e.target.value + ' 星'; });
        U.$$('#genCount button', box).forEach(b => b.addEventListener('click', () => {
          U.$$('#genCount button', box).forEach(x => x.classList.remove('is-active'));
          b.classList.add('is-active'); this.gen.count = +b.dataset.c;
        }));
        U.$('#genBtn', box).addEventListener('click', () => {
          if (!this.gen.kpIds.length) return Toast.warn('请至少选择一个知识点');
          U.$('#genResult').innerHTML = '<div class="card"><div class="card__body">正在基于 ' + this.gen.kpIds.length + ' 个知识点生成 ' + this.gen.count + ' 道习题…</div></div>';
          API.question.generate({
            materialIds: cfg.materials.map(m => m.fileId),
            kpIds: this.gen.kpIds, types: this.gen.types,
            difficulty: this.gen.difficulty, count: this.gen.count, skillId: 'SK004'
          }).then(r => {
            Toast.ok('AI 生成完成', '共 ' + r.questions.length + ' 题 · 用时 ' + (r.elapsedMs / 1000).toFixed(1) + 's');
            this.renderGenerated(r.questions);
          });
        });
      });
    },

    renderGenerated(list) {
      const box = U.$('#genResult');
      box.innerHTML = `
      <div class="card__head" style="padding:14px 16px"><h3>${icon('sparkle')} 生成预览（${list.length} 题）</h3>
        <span class="spacer"></span>
        <button class="btn btn--sm btn--outline" id="gApprove">${icon('check')} 批量审核发布</button>
        <button class="btn btn--sm btn--primary" id="gPack">${icon('target')} 生成靶向补练包</button></div>
      ${list.map((q, i) => `
        <div class="gen-q">
          <div class="gen-q__head">
            <span class="badge badge--brand">${i + 1}</span>
            <b>${q.type === 'judge' ? '判断题' : '单选题'}</b>
            <span class="badge badge--outline">难度 ${U.stars(q.difficulty)}</span>
            <span class="badge badge--outline">${U.esc(q.kpPath.join(' › '))}</span>
            ${q.isKey ? '<span class="badge badge--warn">◆ 重难点</span>' : ''}
            <span class="spacer"></span>
            <span class="badge ${q.status === 'approved' ? 'badge--ok' : 'badge--warn'}">${q.status === 'approved' ? '已审核' : '待审核'}</span>
          </div>
          <div class="gen-q__body">
            <div>${q.stem}</div>
            <div class="gen-q__opts">${q.options.map(o => `<div class="gen-q__opt ${o.right ? 'is-answer' : ''}"><i>${o.key}</i> ${o.text}${o.right ? ' ✓ 正确答案' : ''}</div>`).join('')}</div>
            <div class="callout callout--brand" style="margin-top:10px;padding:9px 11px">${icon('bulb')}
              <div><b>解析：</b>${q.analysis}<br><span class="fz-11 t-dim">溯源：${U.esc(q.sourceRef.fileId)} · ${U.esc(q.sourceRef.locator)} · 预计正确率 ${q.estimatedCorrectRate}%</span></div></div>
          </div>
        </div>`).join('')}`;
      U.$('#gApprove', box).addEventListener('click', () => {
        API.question.review({ qIds: list.map(q => q.qId), action: 'publish' }).then(r =>
          Toast.ok('已审核发布', r.affected + ' 道习题进入题库'));
      });
      U.$('#gPack', box).addEventListener('click', () => {
        API.question.createPack({ kpIds: list.map(q => q.kpId), count: this.gen.count, difficulty: this.gen.difficulty }).then(r =>
          Toast.ok('靶向补练包已生成', '包号 ' + r.packId + ' · 已推送'));
      });
    },

    renderBank() {
      const box = U.$('#qBody');
      box.innerHTML = `
      <div class="card">
        <div class="card__head">
          <h3>${icon('file')} 题库（${U.esc(state.classId)}）</h3>
          <span class="spacer"></span>
          <div class="search" style="width:180px">${icon('search2')}<input class="input" id="bankSearch" placeholder="题号 / 题干 / 知识点"></div>
          <div class="seg" id="bankSeg">
            <button data-s="all" class="is-active">全部</button><button data-s="pending">待审核</button>
            <button data-s="approved">已审</button><button data-s="published">已发布</button><button data-s="archived">归档</button></div>
          <button class="btn btn--sm btn--primary" id="bankImport">${icon('upload')} 批量导入</button>
        </div>
        <div class="card__body card__body--flush"><div class="tbl-wrap"><table class="tbl" id="bankTbl"></table></div></div>
      </div>`;

      U.$$('#bankSeg button', box).forEach(b => b.addEventListener('click', () => {
        U.$$('#bankSeg button', box).forEach(x => x.classList.remove('is-active'));
        b.classList.add('is-active'); this.bankFilter = b.dataset.s; this.loadBank();
      }));
      U.$('#bankSearch', box).addEventListener('input', e => { this.bankKeyword = e.target.value.trim(); this.loadBank(); });
      U.$('#bankImport', box).addEventListener('click', () =>
        API.question.importBatch({}).then(r => Toast.ok('导入完成', r.success + ' 成功 / ' + r.failed + ' 失败 · 共 ' + r.total + ' 题')));
      this.loadBank();
    },

    loadBank() {
      API.question.bank({ status: this.bankFilter, keyword: this.bankKeyword }).then(r => {
        const t = U.$('#bankTbl'); if (!t) return;
        const stMap = { pending: ['待审核', 'badge--warn'], approved: ['已审', 'badge--ok'], published: ['已发布', 'badge--brand'], archived: ['归档', 'badge--outline'] };
        t.innerHTML = `
          <thead><tr><th>题号</th><th>题干</th><th>题型</th><th>知识点</th><th>难度</th><th class="t-right">正确率</th><th>状态</th><th></th></tr></thead>
          <tbody>${r.list.map(q => {
            const [lbl, bd] = stMap[q.status] || ['—', 'badge--outline'];
            return `<tr>
              <td class="mono fz-12">${q.qId}</td>
              <td class="clamp-2" style="max-width:280px">${U.esc(q.stem)}</td>
              <td>${q.type}</td><td>${U.esc(q.kp)}</td>
              <td>${U.stars(q.difficulty)}</td>
              <td class="t-right num ${q.correctRate === null ? 't-dim' : (q.correctRate < 60 ? 't-danger' : '')}">${q.correctRate === null ? '—' : q.correctRate + '%'}</td>
              <td><span class="badge ${bd}">${lbl}</span>${q.isKey ? ' <span class="badge badge--warn">◆</span>' : ''}</td>
              <td class="t-right"><button class="btn btn--xs btn--ghost" data-edit="${q.qId}">编辑</button>
                <button class="btn btn--xs btn--ghost" data-del="${q.qId}">删除</button></td>
            </tr>`;
          }).join('')}</tbody>`;
        U.$$('[data-edit]', t).forEach(b => b.addEventListener('click', () => this.editQ(b.dataset.edit, r.list)));
        U.$$('[data-del]', t).forEach(b => b.addEventListener('click', () => {
          API.question.remove({ qId: b.dataset.del }).then(() => { Toast.ok('已删除习题'); this.loadBank(); });
        }));
      });
    },

    editQ(qId, list) {
      const q = list.find(x => x.qId === qId);
      Modal.open({
        title: '编辑习题 · ' + qId, size: 'wide',
        body: `<div class="kv" style="margin-bottom:12px">
            <div class="kv__row"><span>知识点</span><span>${U.esc(q.kp)}</span></div>
            <div class="kv__row"><span>难度</span><span>${U.stars(q.difficulty)}</span></div>
            <div class="kv__row"><span>来源</span><span>${q.source}</span></div></div>
          <label class="fz-12 t-dim" style="display:block;margin-bottom:6px">题干</label>
          <textarea class="code-edit" id="eqStem">${q.stem}</textarea>`,
        footer: `<button class="btn" data-close>取消</button><button class="btn btn--primary" id="eqSave">保存修订</button>`,
        onMount(ov, close) {
          U.$('#eqSave', ov).addEventListener('click', () =>
            API.question.update({ qId, stem: U.$('#eqStem', ov).value }).then(() => { Toast.ok('已保存修订'); close(); }));
        }
      });
    }
  };

Router.register('question', { title: 'AI 出题与题库管理', mount: () => Question.render() });
