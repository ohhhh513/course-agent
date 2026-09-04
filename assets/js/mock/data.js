/* ==========================================================================
   课程智能体系统 · Mock 数据集
   课程样例：《数据结构与算法》（计算机学院 2026 春季学期）
   说明：数据结构与《接口文档.md》中各接口的 data 字段严格一致，
        便于后端按此契约实现真实接口后直接替换。
   ========================================================================== */
window.MOCK = (function () {

  /* ---------------- 课程 / 用户 ---------------- */
  const course = {
    courseId: 'C2026DS001',
    name: '数据结构与算法',
    code: 'CS20301',
    term: '2026 春季学期',
    teacher: '李文博',
    credit: 4,
    chapters: 8,
    knowledgePoints: 46,
    resources: 132,
    questions: 860
  };

  const student = {
    userId: 'S20260317',
    name: '陈思远',
    avatar: '陈',
    no: '2023110317',
    className: '计算机 2301 班',
    role: 'student',
    streakDays: 12,
    totalStudyMinutes: 3420
  };

  const teacher = {
    userId: 'T100286',
    name: '李文博',
    avatar: '李',
    title: '副教授',
    dept: '计算机科学与技术学院',
    role: 'teacher',
    classes: [
      { classId: 'CL2301', name: '计算机 2301 班', studentCount: 42 },
      { classId: 'CL2302', name: '计算机 2302 班', studentCount: 45 },
      { classId: 'CL2303', name: '软件工程 2301 班', studentCount: 38 }
    ]
  };

  /* ---------------- 学生首页 · 驾驶舱 ---------------- */
  /* ----- 52 周学习贡献图（GitHub 风格）-----
     起点 2025-09-22（周一），52 周 × 7 天 = 364 天，覆盖 2025 秋 - 2026 夏。
     取值：0=未学习 / 1-4=学习强度（数字越大颜色越深），最后一格固定为"今天"。 */
  const _mulberry32 = (seed) => {
    let s = seed | 0;
    return () => {
      s = (s + 0x6D2B79F5) | 0;
      let t = Math.imul(s ^ (s >>> 15), 1 | s);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  };
  const _STREAK_WEEKS = 52;
  const _STREAK_DAYS = _STREAK_WEEKS * 7;
  const _rng = _mulberry32(20260922);
  const _streakHistory = new Array(_STREAK_DAYS).fill(0);
  // 基础节奏：早期稀疏 → 中期稳步 → 近期高活跃，周末略降
  for (let i = 0; i < _STREAK_DAYS; i++) {
    const dow = i % 7;
    const recent = i >= _STREAK_DAYS - 64;
    const early = i < 30;
    let p;
    if (early) p = 0.40;
    else if (recent) p = 0.88;
    else p = (dow >= 5) ? 0.40 : 0.78;
    _streakHistory[i] = (_rng() < p) ? 1 + Math.floor(_rng() * 4) : 0;
  }
  // 注入一段 14 天高强度段（演示最大连续天数），边界断 0 突出
  for (let i = 150; i < 164; i++) _streakHistory[i] = 3 + Math.floor(_rng() * 2);
  _streakHistory[149] = 0; _streakHistory[164] = 0;
  // 注入当前连续 12 天打卡（含今日），前 1 天断 0 隔离
  for (let i = _STREAK_DAYS - 12; i < _STREAK_DAYS - 1; i++) _streakHistory[i] = 3 + Math.floor(_rng() * 2);
  _streakHistory[_STREAK_DAYS - 13] = 0;
  // 今日：最高强度
  _streakHistory[_STREAK_DAYS - 1] = 4;
  // 统计指标
  let _currentStreak = 0;
  for (let i = _STREAK_DAYS - 1; i >= 0; i--) { if (_streakHistory[i] > 0) _currentStreak++; else break; }
  let _maxStreak = 0, _run = 0;
  for (let i = 0; i < _STREAK_DAYS; i++) {
    if (_streakHistory[i] > 0) { _run++; if (_run > _maxStreak) _maxStreak = _run; } else _run = 0;
  }
  const _totalDays = _streakHistory.filter(v => v > 0).length;

  const studentDashboard = {
    overview: {
      courseProgress: 62.5,
      currentNode: { kpId: 'KP31', name: '二叉树的遍历' },
      streakDays: _currentStreak,
      streakHistoryStart: '2025-09-22',
      streakHistory: _streakHistory,
      currentStreak: _currentStreak,
      maxStreak: _maxStreak,
      totalDays: _totalDays,
      todayStudyMinutes: 48,
      status: 'warn' // ok | warn | danger
    },
    coreMetrics: {
      completionRate: 62.5,   // 知识点完成率
      masteryRate: 74.2,      // 掌握率
      goalAchieveRate: 68.9,  // 能力目标达成度
      updatedAt: '2026-08-28 06:00'
    },
    todos: [
      { id: 'TD1', type: 'recommend', level: 'brand', title: '今日推荐学习：二叉树的遍历', desc: '前置「二叉树基本概念」已达标 · 预计 35 分钟', action: '开始学习', target: 'learn', kpId: 'KP31' },
      { id: 'TD2', type: 'homework', level: 'warn', title: '第 4 章作业待提交', desc: '剩余 2 天 12 小时 · 共 12 题，已完成 5 题', action: '继续作答', target: 'practice' },
      { id: 'TD3', type: 'alert', level: 'danger', title: '预警：图的最短路径算法掌握率 41%', desc: '低于班级平均 27 个百分点，建议立即补救', action: '去补救', target: 'alerts' },
      { id: 'TD4', type: 'practice', level: 'ok', title: '错题重练：3 道栈与队列错题', desc: '上次错误集中在「循环队列判空判满」', action: '去重练', target: 'practice' }
    ],
    weakPoints: [
      { kpId: 'KP52', name: '最短路径 Dijkstra 算法', masteryRate: 41, chapter: '第5章 图', errorCount: 7, trend: -8, level: 'danger' },
      { kpId: 'KP44', name: '哈夫曼树与哈夫曼编码', masteryRate: 55, chapter: '第4章 树', errorCount: 4, trend: -3, level: 'warn' },
      { kpId: 'KP23', name: '循环队列的判空与判满', masteryRate: 61, chapter: '第3章 栈与队列', errorCount: 3, trend: 2, level: 'warn' }
    ],
    suggestedQuestions: [
      '二叉树的前序、中序、后序遍历有什么本质区别？',
      'Dijkstra 算法为什么不能处理负权边？',
      '循环队列为什么要牺牲一个存储单元？',
      '如何用递归和非递归两种方式实现中序遍历？',
      '哈夫曼编码是如何保证前缀码性质的？'
    ],
    recentActivities: [
      { id: 'A1', type: 'video', title: '观看《二叉树的定义与性质》', meta: '18 分钟 / 22 分钟', time: '今天 14:32', level: 'ok' },
      { id: 'A2', type: 'practice', title: '完成「树的基本概念」随机练习', meta: '10 题 · 正确率 80%', time: '今天 11:05', level: 'ok' },
      { id: 'A3', type: 'chat', title: 'AI 答疑：完全二叉树与满二叉树的区别', meta: '6 轮对话 · 引用 3 处原文', time: '昨天 21:47', level: 'ok' },
      { id: 'A4', type: 'practice', title: '「图的存储结构」靶向强化', meta: '8 题 · 正确率 50%', time: '昨天 20:12', level: 'warn' },
      { id: 'A5', type: 'doc', title: '阅读《算法导论》第 22 章节选', meta: '12 页', time: '08-26 19:30', level: 'ok' }
    ]
  };

  /* ---------------- 三大图谱 ---------------- */
  // 知识图谱
  const knowledgeGraph = {
    graphType: 'knowledge',
    categories: [
      { name: '已掌握', color: '#22c55e' },
      { name: '学习中', color: '#6366f1' },
      { name: '待加强', color: '#f59e0b' },
      { name: '未开始', color: '#64748b' },
      { name: '薄弱预警', color: '#ef4444' }
    ],
    nodes: [
      { id: 'KP01', name: '算法与复杂度', chapter: 1, category: 0, mastery: 92, difficulty: 2, isKey: true, hours: 4 },
      { id: 'KP02', name: '时间复杂度分析', chapter: 1, category: 0, mastery: 88, difficulty: 3, isKey: true, hours: 4 },
      { id: 'KP11', name: '线性表定义', chapter: 2, category: 0, mastery: 95, difficulty: 1, isKey: false, hours: 2 },
      { id: 'KP12', name: '顺序表', chapter: 2, category: 0, mastery: 90, difficulty: 2, isKey: true, hours: 4 },
      { id: 'KP13', name: '单链表', chapter: 2, category: 0, mastery: 85, difficulty: 3, isKey: true, hours: 6 },
      { id: 'KP14', name: '双向 / 循环链表', chapter: 2, category: 2, mastery: 68, difficulty: 3, isKey: false, hours: 4 },
      { id: 'KP21', name: '栈的定义与实现', chapter: 3, category: 0, mastery: 87, difficulty: 2, isKey: true, hours: 4 },
      { id: 'KP22', name: '队列的定义与实现', chapter: 3, category: 0, mastery: 82, difficulty: 2, isKey: true, hours: 4 },
      { id: 'KP23', name: '循环队列判空判满', chapter: 3, category: 2, mastery: 61, difficulty: 4, isKey: true, hours: 2 },
      { id: 'KP24', name: '栈的典型应用', chapter: 3, category: 0, mastery: 79, difficulty: 3, isKey: false, hours: 4 },
      { id: 'KP31', name: '二叉树基本概念', chapter: 4, category: 1, mastery: 72, difficulty: 3, isKey: true, hours: 4 },
      { id: 'KP32', name: '二叉树的遍历', chapter: 4, category: 1, mastery: 66, difficulty: 4, isKey: true, hours: 6 },
      { id: 'KP33', name: '线索二叉树', chapter: 4, category: 3, mastery: 0, difficulty: 4, isKey: false, hours: 4 },
      { id: 'KP34', name: '树与森林的转换', chapter: 4, category: 3, mastery: 0, difficulty: 3, isKey: false, hours: 4 },
      { id: 'KP44', name: '哈夫曼树与编码', chapter: 4, category: 2, mastery: 55, difficulty: 4, isKey: true, hours: 4 },
      { id: 'KP41', name: '图的定义与术语', chapter: 5, category: 0, mastery: 80, difficulty: 2, isKey: false, hours: 2 },
      { id: 'KP42', name: '图的存储结构', chapter: 5, category: 2, mastery: 63, difficulty: 3, isKey: true, hours: 4 },
      { id: 'KP43', name: '图的遍历 DFS/BFS', chapter: 5, category: 1, mastery: 70, difficulty: 4, isKey: true, hours: 6 },
      { id: 'KP51', name: '最小生成树', chapter: 5, category: 2, mastery: 58, difficulty: 4, isKey: true, hours: 4 },
      { id: 'KP52', name: '最短路径 Dijkstra', chapter: 5, category: 4, mastery: 41, difficulty: 5, isKey: true, hours: 6 },
      { id: 'KP53', name: '拓扑排序', chapter: 5, category: 3, mastery: 0, difficulty: 4, isKey: false, hours: 4 },
      { id: 'KP61', name: '查找的基本概念', chapter: 6, category: 3, mastery: 0, difficulty: 1, isKey: false, hours: 2 },
      { id: 'KP62', name: '二分查找', chapter: 6, category: 3, mastery: 0, difficulty: 3, isKey: true, hours: 4 },
      { id: 'KP63', name: '二叉排序树', chapter: 6, category: 3, mastery: 0, difficulty: 4, isKey: true, hours: 6 },
      { id: 'KP64', name: '哈希表', chapter: 6, category: 3, mastery: 0, difficulty: 4, isKey: true, hours: 4 },
      { id: 'KP71', name: '插入 / 冒泡排序', chapter: 7, category: 3, mastery: 0, difficulty: 2, isKey: false, hours: 4 },
      { id: 'KP72', name: '快速排序', chapter: 7, category: 3, mastery: 0, difficulty: 4, isKey: true, hours: 4 },
      { id: 'KP73', name: '堆排序', chapter: 7, category: 3, mastery: 0, difficulty: 5, isKey: true, hours: 4 }
    ],
    links: [
      { source: 'KP01', target: 'KP02', relation: 'pre' },
      { source: 'KP02', target: 'KP12', relation: 'pre' },
      { source: 'KP11', target: 'KP12', relation: 'pre' },
      { source: 'KP11', target: 'KP13', relation: 'pre' },
      { source: 'KP13', target: 'KP14', relation: 'advance' },
      { source: 'KP12', target: 'KP21', relation: 'pre' },
      { source: 'KP13', target: 'KP21', relation: 'pre' },
      { source: 'KP21', target: 'KP22', relation: 'parallel' },
      { source: 'KP22', target: 'KP23', relation: 'advance' },
      { source: 'KP21', target: 'KP24', relation: 'advance' },
      { source: 'KP13', target: 'KP31', relation: 'pre' },
      { source: 'KP31', target: 'KP32', relation: 'pre' },
      { source: 'KP32', target: 'KP33', relation: 'advance' },
      { source: 'KP31', target: 'KP34', relation: 'advance' },
      { source: 'KP32', target: 'KP44', relation: 'advance' },
      { source: 'KP31', target: 'KP41', relation: 'pre' },
      { source: 'KP41', target: 'KP42', relation: 'pre' },
      { source: 'KP42', target: 'KP43', relation: 'pre' },
      { source: 'KP43', target: 'KP51', relation: 'pre' },
      { source: 'KP42', target: 'KP52', relation: 'pre' },
      { source: 'KP43', target: 'KP52', relation: 'pre' },
      { source: 'KP02', target: 'KP52', relation: 'pre' },
      { source: 'KP43', target: 'KP53', relation: 'advance' },
      { source: 'KP12', target: 'KP61', relation: 'pre' },
      { source: 'KP61', target: 'KP62', relation: 'pre' },
      { source: 'KP31', target: 'KP63', relation: 'pre' },
      { source: 'KP61', target: 'KP64', relation: 'advance' },
      { source: 'KP02', target: 'KP71', relation: 'pre' },
      { source: 'KP71', target: 'KP72', relation: 'advance' },
      { source: 'KP31', target: 'KP73', relation: 'pre' }
    ]
  };

  // 问题图谱
  const problemGraph = {
    graphType: 'problem',
    categories: [
      { name: '驱动问题', color: '#8b5cf6' },
      { name: '子问题', color: '#38bdf8' },
      { name: '关联知识点', color: '#6366f1' },
      { name: '高频错题簇', color: '#ef4444' }
    ],
    nodes: [
      { id: 'PB1', name: '如何为地图导航设计最优路线？', category: 0, level: 1, relatedKp: 6, errorRate: 38 },
      { id: 'PB1-1', name: '如何抽象城市路网？', category: 1, level: 2, relatedKp: 2, errorRate: 21 },
      { id: 'PB1-2', name: '如何存储带权图？', category: 1, level: 2, relatedKp: 2, errorRate: 33 },
      { id: 'PB1-3', name: '如何求单源最短路径？', category: 1, level: 2, relatedKp: 3, errorRate: 52 },
      { id: 'KP41', name: '图的定义与术语', category: 2, level: 3 },
      { id: 'KP42', name: '图的存储结构', category: 2, level: 3 },
      { id: 'KP52', name: '最短路径 Dijkstra', category: 2, level: 3 },
      { id: 'EC1', name: '错题簇：贪心松弛顺序混乱', category: 3, level: 4, count: 26 },
      { id: 'EC2', name: '错题簇：邻接矩阵/表选择错误', category: 3, level: 4, count: 18 },
      { id: 'PB2', name: '如何实现表达式求值器？', category: 0, level: 1, relatedKp: 4, errorRate: 24 },
      { id: 'PB2-1', name: '中缀如何转后缀？', category: 1, level: 2, relatedKp: 2, errorRate: 29 },
      { id: 'PB2-2', name: '如何用栈完成求值？', category: 1, level: 2, relatedKp: 2, errorRate: 18 },
      { id: 'KP21', name: '栈的定义与实现', category: 2, level: 3 },
      { id: 'KP24', name: '栈的典型应用', category: 2, level: 3 },
      { id: 'EC3', name: '错题簇：运算符优先级判断', category: 3, level: 4, count: 14 },
      { id: 'PB3', name: '如何压缩一段文本？', category: 0, level: 1, relatedKp: 3, errorRate: 31 },
      { id: 'PB3-1', name: '如何构造最优前缀码？', category: 1, level: 2, relatedKp: 2, errorRate: 35 },
      { id: 'KP44', name: '哈夫曼树与编码', category: 2, level: 3 },
      { id: 'EC4', name: '错题簇：WPL 计算失误', category: 3, level: 4, count: 21 }
    ],
    links: [
      { source: 'PB1', target: 'PB1-1', relation: 'split' },
      { source: 'PB1', target: 'PB1-2', relation: 'split' },
      { source: 'PB1', target: 'PB1-3', relation: 'split' },
      { source: 'PB1-1', target: 'KP41', relation: 'map' },
      { source: 'PB1-2', target: 'KP42', relation: 'map' },
      { source: 'PB1-3', target: 'KP52', relation: 'map' },
      { source: 'KP52', target: 'EC1', relation: 'error' },
      { source: 'KP42', target: 'EC2', relation: 'error' },
      { source: 'PB2', target: 'PB2-1', relation: 'split' },
      { source: 'PB2', target: 'PB2-2', relation: 'split' },
      { source: 'PB2-1', target: 'KP24', relation: 'map' },
      { source: 'PB2-2', target: 'KP21', relation: 'map' },
      { source: 'KP24', target: 'EC3', relation: 'error' },
      { source: 'PB3', target: 'PB3-1', relation: 'split' },
      { source: 'PB3-1', target: 'KP44', relation: 'map' },
      { source: 'KP44', target: 'EC4', relation: 'error' }
    ]
  };

  // 目标图谱
  const goalGraph = {
    graphType: 'goal',
    categories: [
      { name: '课程总目标', color: '#8b5cf6' },
      { name: '单元目标', color: '#06b6d4' },
      { name: '知识点目标', color: '#6366f1' }
    ],
    nodes: [
      { id: 'G0', name: '具备数据结构建模与算法设计能力', category: 0, achieve: 68.9, weight: 100 },
      { id: 'G1', name: '掌握线性结构的组织与运算', category: 1, achieve: 86.4, weight: 25 },
      { id: 'G2', name: '掌握树形结构的构建与遍历', category: 1, achieve: 64.3, weight: 30 },
      { id: 'G3', name: '掌握图结构的表示与经典算法', category: 1, achieve: 55.8, weight: 30 },
      { id: 'G4', name: '具备算法效率分析能力', category: 1, achieve: 89.0, weight: 15 },
      { id: 'G1-1', name: '能实现顺序表与链表基本运算', category: 2, achieve: 90.0, weight: 12 },
      { id: 'G1-2', name: '能用栈/队列解决实际问题', category: 2, achieve: 81.5, weight: 13 },
      { id: 'G2-1', name: '能构建二叉树并实现三种遍历', category: 2, achieve: 66.0, weight: 16 },
      { id: 'G2-2', name: '能应用哈夫曼树解决编码问题', category: 2, achieve: 55.0, weight: 8 },
      { id: 'G2-3', name: '能完成树与森林的转换', category: 2, achieve: 0, weight: 6 },
      { id: 'G3-1', name: '能选择合适的图存储结构', category: 2, achieve: 63.0, weight: 10 },
      { id: 'G3-2', name: '能实现 DFS/BFS 并解决连通性问题', category: 2, achieve: 70.0, weight: 10 },
      { id: 'G3-3', name: '能应用最短路径与最小生成树算法', category: 2, achieve: 45.5, weight: 10 },
      { id: 'G4-1', name: '能推导算法时间/空间复杂度', category: 2, achieve: 89.0, weight: 15 }
    ],
    links: [
      { source: 'G0', target: 'G1', relation: 'support' },
      { source: 'G0', target: 'G2', relation: 'support' },
      { source: 'G0', target: 'G3', relation: 'support' },
      { source: 'G0', target: 'G4', relation: 'support' },
      { source: 'G1', target: 'G1-1', relation: 'support' },
      { source: 'G1', target: 'G1-2', relation: 'support' },
      { source: 'G2', target: 'G2-1', relation: 'support' },
      { source: 'G2', target: 'G2-2', relation: 'support' },
      { source: 'G2', target: 'G2-3', relation: 'support' },
      { source: 'G3', target: 'G3-1', relation: 'support' },
      { source: 'G3', target: 'G3-2', relation: 'support' },
      { source: 'G3', target: 'G3-3', relation: 'support' },
      { source: 'G4', target: 'G4-1', relation: 'support' }
    ]
  };

  /* ---------------- 知识点详情 ---------------- */
  const kpDetail = {
    KP52: {
      kpId: 'KP52', name: '最短路径 Dijkstra 算法', chapter: '第5章 图',
      difficulty: 5, isKey: true, hours: 6,
      summary: 'Dijkstra 算法用于求解带非负权值有向图中单源点到其余各顶点的最短路径，基于贪心策略与逐步松弛思想，时间复杂度 O(n²)（邻接矩阵）。',
      completionRate: 55, masteryRate: 41, classAvgMastery: 68,
      pre: [{ kpId: 'KP42', name: '图的存储结构', mastery: 63 }, { kpId: 'KP43', name: '图的遍历', mastery: 70 }, { kpId: 'KP02', name: '时间复杂度分析', mastery: 88 }],
      post: [{ kpId: 'KP54', name: 'Floyd 多源最短路径', mastery: 0 }],
      resources: [
        { resId: 'R201', type: 'video', title: 'Dijkstra 算法原理与手工模拟', duration: '24:18', source: '课程录课 · 第5章', progress: 30 },
        { resId: 'R202', type: 'ppt', title: '第5章 图（下）课堂课件', pages: 42, source: '课堂PPT', progress: 100 },
        { resId: 'R203', type: 'doc', title: '《数据结构（C语言版）》P188-P193', pages: 6, source: '教材文献', progress: 0 },
        { resId: 'R204', type: 'video', title: '易错点串讲：负权边为何失效', duration: '08:45', source: '补救微课', progress: 0 }
      ],
      questionCount: 32, wrongCount: 7,
      relatedProblems: ['如何为地图导航设计最优路线？']
    }
  };

  /* ---------------- 学习路径 ---------------- */
  const learningPath = [
    // 第1章 绪论（已完成）
    { step: 1, kpId: 'KP01', name: '算法与复杂度', chapter: '第1章 绪论', status: 'done', hours: 4, mastery: 92, resCount: 3 },
    { step: 2, kpId: 'KP02', name: '时间复杂度分析', chapter: '第1章 绪论', status: 'done', hours: 4, mastery: 88, resCount: 2 },

    // 第2章 线性表（已完成）
    { step: 3, kpId: 'KP11', name: '线性表定义', chapter: '第2章 线性表', status: 'done', hours: 2, mastery: 95, resCount: 2 },
    { step: 4, kpId: 'KP12', name: '顺序表', chapter: '第2章 线性表', status: 'done', hours: 4, mastery: 90, resCount: 4 },
    { step: 5, kpId: 'KP13', name: '单链表', chapter: '第2章 线性表', status: 'done', hours: 6, mastery: 85, resCount: 5 },
    { step: 6, kpId: 'KP14', name: '双向 / 循环链表', chapter: '第2章 线性表', status: 'done', hours: 4, mastery: 68, resCount: 3 },

    // 第3章 栈与队列（基本完成，1 个薄弱点）
    { step: 7, kpId: 'KP21', name: '栈的定义与实现', chapter: '第3章 栈与队列', status: 'done', hours: 4, mastery: 87, resCount: 3 },
    { step: 8, kpId: 'KP22', name: '队列的定义与实现', chapter: '第3章 栈与队列', status: 'done', hours: 4, mastery: 82, resCount: 3 },
    { step: 9, kpId: 'KP24', name: '栈的典型应用', chapter: '第3章 栈与队列', status: 'done', hours: 4, mastery: 79, resCount: 3 },
    { step: 10, kpId: 'KP23', name: '循环队列判空判满', chapter: '第3章 栈与队列', status: 'warn', hours: 2, mastery: 61, resCount: 2 },

    // 第4章 树与二叉树（在学）
    { step: 11, kpId: 'KP31', name: '二叉树基本概念', chapter: '第4章 树与二叉树', status: 'done', hours: 4, mastery: 72, resCount: 5 },
    { step: 12, kpId: 'KP32', name: '二叉树的遍历', chapter: '第4章 树与二叉树', status: 'doing', hours: 6, mastery: 66, resCount: 7, progress: 45 },
    { step: 13, kpId: 'KP44', name: '哈夫曼树与编码', chapter: '第4章 树与二叉树', status: 'todo', hours: 4, mastery: 55, resCount: 4 },
    { step: 14, kpId: 'KP33', name: '线索二叉树', chapter: '第4章 树与二叉树', status: 'todo', hours: 4, mastery: 0, resCount: 3 },
    { step: 15, kpId: 'KP34', name: '树与森林的转换', chapter: '第4章 树与二叉树', status: 'todo', hours: 4, mastery: 0, resCount: 3, locked: true, lockReason: '需先完成「二叉树的遍历」' },

    // 第5章 图（在学，需强化）
    { step: 16, kpId: 'KP41', name: '图的定义与术语', chapter: '第5章 图', status: 'done', hours: 2, mastery: 80, resCount: 3 },
    { step: 17, kpId: 'KP42', name: '图的存储结构', chapter: '第5章 图', status: 'doing', hours: 4, mastery: 63, resCount: 5, progress: 70 },
    { step: 18, kpId: 'KP52', name: '最短路径 Dijkstra', chapter: '第5章 图', status: 'warn', hours: 6, mastery: 41, resCount: 4 },
    { step: 19, kpId: 'KP43', name: '图的遍历 DFS/BFS', chapter: '第5章 图', status: 'todo', hours: 6, mastery: 70, resCount: 3 },
    { step: 20, kpId: 'KP51', name: '最小生成树', chapter: '第5章 图', status: 'todo', hours: 4, mastery: 58, resCount: 3 },
    { step: 21, kpId: 'KP53', name: '拓扑排序', chapter: '第5章 图', status: 'todo', hours: 4, mastery: 0, resCount: 2 },

    // 第6章 查找（未开始，下一章）
    { step: 22, kpId: 'KP61', name: '查找的基本概念', chapter: '第6章 查找', status: 'todo', hours: 2, mastery: 0, resCount: 2 },
    { step: 23, kpId: 'KP62', name: '二分查找', chapter: '第6章 查找', status: 'todo', hours: 4, mastery: 0, resCount: 3 },
    { step: 24, kpId: 'KP63', name: '二叉排序树', chapter: '第6章 查找', status: 'todo', hours: 6, mastery: 0, resCount: 3 },
    { step: 25, kpId: 'KP64', name: '哈希表', chapter: '第6章 查找', status: 'todo', hours: 4, mastery: 0, resCount: 3 }
  ];

  /* ---------------- 资源中心 ---------------- */
  const resources = [
    { resId: 'R101', type: 'video', title: '第4章 树与二叉树 · 概念导入', kp: '二叉树基本概念', duration: '22:10', progress: 100, views: 1240, source: 'MOOC 课程录课' },
    { resId: 'R102', type: 'video', title: '二叉树的三种遍历（递归实现）', kp: '二叉树的遍历', duration: '31:25', progress: 45, views: 1102, source: 'MOOC 课程录课' },
    { resId: 'R103', type: 'video', title: '二叉树遍历的非递归实现', kp: '二叉树的遍历', duration: '26:40', progress: 0, views: 876, source: 'MOOC 课程录课' },
    { resId: 'R104', type: 'ppt', title: '第4章 树与二叉树 课堂课件', kp: '第4章 树', pages: 68, progress: 100, views: 1560, source: '课堂PPT' },
    { resId: 'R105', type: 'doc', title: '《数据结构（C语言版）》第6章', kp: '第4章 树', pages: 46, progress: 60, views: 980, source: '教材文献' },
    { resId: 'R106', type: 'quiz', title: '第4章 章节自测（20题）', kp: '第4章 树', count: 20, progress: 0, views: 720, source: '课程题库' },
    { resId: 'R107', type: 'video', title: 'Dijkstra 算法原理与手工模拟', kp: '最短路径 Dijkstra', duration: '24:18', progress: 30, views: 1024, source: 'MOOC 课程录课' },
    { resId: 'R108', type: 'video', title: '易错点串讲：负权边为何失效', kp: '最短路径 Dijkstra', duration: '08:45', progress: 0, views: 340, source: '补救微课' },
    { resId: 'R109', type: 'ppt', title: '第5章 图（下）课堂课件', kp: '第5章 图', pages: 42, progress: 100, views: 1320, source: '课堂PPT' },
    { resId: 'R110', type: 'doc', title: '《算法导论》第24章 单源最短路径', kp: '最短路径 Dijkstra', pages: 32, progress: 0, views: 456, source: '拓展文献' },
    { resId: 'R111', type: 'quiz', title: '图论综合训练包（35题）', kp: '第5章 图', count: 35, progress: 20, views: 610, source: '课程题库' },
    { resId: 'R112', type: 'video', title: '循环队列判空判满专题', kp: '循环队列判空判满', duration: '12:30', progress: 100, views: 890, source: '补救微课' }
  ];

  /* ---------------- AI 答疑 ---------------- */
  const teachingMethods = [
    { key: 'lecture', name: '讲授法', desc: '系统讲解概念与原理，结构清晰', icon: 'book' },
    { key: 'guided', name: '引导式', desc: '不直接给答案，层层提问引导思考', icon: 'compass' },
    { key: 'case', name: '案例式', desc: '结合实际工程案例说明', icon: 'briefcase' },
    { key: 'heuristic', name: '启发式', desc: '从反例与矛盾中启发理解', icon: 'bulb' },
    { key: 'fun', name: '趣味式', desc: '类比与故事化表达，降低认知门槛', icon: 'smile' }
  ];

  const chatHistory = [
    { sessionId: 'CH2026082801', title: '完全二叉树与满二叉树的区别', time: '昨天 21:47', rounds: 6, kp: '二叉树基本概念' },
    { sessionId: 'CH2026082702', title: '邻接矩阵和邻接表怎么选', time: '08-27 19:22', rounds: 4, kp: '图的存储结构' },
    { sessionId: 'CH2026082601', title: '循环队列为什么少用一个单元', time: '08-26 15:08', rounds: 8, kp: '循环队列判空判满' },
    { sessionId: 'CH2026082501', title: '快排最坏情况是什么时候', time: '08-25 22:30', rounds: 3, kp: '快速排序' }
  ];

  // 预置对话（含溯源）
  const chatMessages = [
    {
      role: 'ai', method: 'guided',
      content: '<p>同学你好 👋 我是本课程的 AI 助教，已完整学习本课程的 <strong>教材、68 页课堂课件、132 个教学资源</strong> 以及历年教学案例与学生高频问题。</p><p>我注意到你当前的薄弱点是 <strong>最短路径 Dijkstra 算法</strong>（掌握率 41%），要不要从这里开始？你也可以直接问我任何问题。</p>',
      time: '14:20', citations: []
    },
    {
      role: 'me',
      content: 'Dijkstra 算法为什么不能处理负权边？',
      time: '14:21'
    },
    {
      role: 'ai', method: 'guided',
      content: `<p>这是个非常好的问题，我们不直接给结论，先一起想一步 🤔</p>
        <p>Dijkstra 的核心是一个<strong>贪心假设</strong>：<em>每次从未确定集合中取出当前 dist 最小的顶点 u，就可以断定 dist[u] 已经是最终最短路径。</em></p>
        <p>请你思考：<strong>这个假设成立的前提是什么？</strong></p>
        <ol>
          <li>如果所有边权都 ≥ 0，那么从 u 再往后走，路径长度只会<strong>越来越大</strong>，所以 dist[u] 不可能再被更新 —— 假设成立；</li>
          <li>但如果存在<strong>负权边</strong>，从 u 出发继续走反而可能让总长度<strong>变小</strong>，那么"提前锁定 u"就错了。</li>
        </ol>
        <p>给你一个最小反例，试着自己跑一遍：顶点 A→B 权 1，A→C 权 4，<strong>C→B 权 -3</strong>。请问 Dijkstra 求 A 到 B 的结果是多少？真实最短是多少？</p>
        <p>想好后告诉我你的答案，我们再往下推 👇</p>`,
      time: '14:21',
      citations: [
        { resId: 'R109', source: '第5章 图（下）课堂课件', locator: 'P28 · 算法正确性证明', quote: '若图中所有边的权值均为非负值，则每次选取的当前最短路径顶点，其最短路径长度不会因后续松弛而减小，故贪心选择成立。', kp: '最短路径 Dijkstra' },
        { resId: 'R110', source: '《算法导论》第24章 单源最短路径', locator: 'P658 · 定理 24.6', quote: 'Dijkstra 算法要求所有边权非负。当存在负权边时，需改用 Bellman-Ford 算法，其可在 O(VE) 时间内检测负权回路。', kp: '最短路径 Dijkstra' },
        { resId: 'R203', source: '《数据结构（C语言版）》P188-P193', locator: 'P191 · 注意事项', quote: '本算法不适用于带负权值的图，因为该情形下"当前最短"不具有最优子结构性质。', kp: '最短路径 Dijkstra' }
      ]
    }
  ];

  /* ---------------- 练习 / 题库 ---------------- */
  const practiceModes = [
    { key: 'weak', name: '薄弱点强化', desc: '系统按掌握率自动组卷，命中薄弱知识点', icon: 'target', recommend: true, count: 10 },
    { key: 'order', name: '顺序练习', desc: '按章节与知识点前后置顺序逐题推进', icon: 'list', count: 20 },
    { key: 'random', name: '随机练习', desc: '在已学范围内随机抽题，检验综合掌握', icon: 'shuffle', count: 15 },
    { key: 'wrong', name: '错题重练', desc: '重做历史错题，验证是否真正掌握', icon: 'refresh', count: 12 }
  ];

  const practiceQuestions = [
    {
      qId: 'Q1024', type: 'single', difficulty: 4, score: 5,
      stem: '在带权有向图中使用 Dijkstra 算法求单源最短路径，若图中存在权值为 <code>-2</code> 的边，则下列说法正确的是：',
      options: [
        { key: 'A', text: '算法仍然正确，只是效率降低' },
        { key: 'B', text: '算法可能得到错误结果，应改用 Bellman-Ford 算法' },
        { key: 'C', text: '算法一定进入死循环' },
        { key: 'D', text: '只要不存在负权回路，Dijkstra 一定正确' }
      ],
      answer: 'B',
      analysis: 'Dijkstra 依赖"当前 dist 最小的顶点其最短路径已确定"这一贪心假设，该假设成立的前提是<strong>所有边权非负</strong>。存在负权边时，已被标记为确定的顶点仍可能被后续松弛更新，从而导致结果错误。注意：即使不存在负权回路，Dijkstra 也可能出错（排除 D），因此需改用 Bellman-Ford（O(VE)）或 SPFA。',
      kpPath: ['第5章 图', '图的最短路径', '最短路径 Dijkstra'],
      kpId: 'KP52', preKp: ['图的存储结构', '图的遍历 DFS/BFS'], isKey: true,
      classCorrectRate: 52, avgSeconds: 96, errorType: '概念混淆'
    },
    {
      qId: 'Q1025', type: 'single', difficulty: 3, score: 5,
      stem: '一棵完全二叉树共有 <code>1000</code> 个结点，则该树中叶子结点的个数为：',
      options: [
        { key: 'A', text: '499' },
        { key: 'B', text: '500' },
        { key: 'C', text: '501' },
        { key: 'D', text: '502' }
      ],
      answer: 'B',
      analysis: '完全二叉树中，度为 1 的结点最多只有 1 个。n = 1000 为偶数，说明存在 1 个度为 1 的结点，即 n₁ = 1。由 n = n₀ + n₁ + n₂ 且 n₀ = n₂ + 1，得 1000 = n₀ + 1 + (n₀ - 1)，解出 n₀ = 500。',
      kpPath: ['第4章 树与二叉树', '二叉树的性质', '完全二叉树性质'],
      kpId: 'KP31', preKp: ['二叉树基本概念'], isKey: true,
      classCorrectRate: 68, avgSeconds: 78, errorType: '公式记忆错误'
    },
    {
      qId: 'Q1026', type: 'single', difficulty: 4, score: 5,
      stem: '容量为 <code>MAXSIZE</code> 的循环队列，采用"牺牲一个单元"方式区分队空与队满，则队满的条件是：',
      options: [
        { key: 'A', text: 'rear == front' },
        { key: 'B', text: '(rear + 1) % MAXSIZE == front' },
        { key: 'C', text: 'rear - front == MAXSIZE' },
        { key: 'D', text: '(front + 1) % MAXSIZE == rear' }
      ],
      answer: 'B',
      analysis: '牺牲一个存储单元后：队空条件为 <code>rear == front</code>；队满条件为 <code>(rear + 1) % MAXSIZE == front</code>，此时实际最多存放 MAXSIZE - 1 个元素。选项 D 方向颠倒，属于典型的指针方向混淆错误。',
      kpPath: ['第3章 栈与队列', '队列的实现', '循环队列判空判满'],
      kpId: 'KP23', preKp: ['队列的定义与实现'], isKey: true,
      classCorrectRate: 61, avgSeconds: 65, errorType: '指针方向混淆'
    }
  ];

  const practiceReport = {
    reportId: 'PR20260828001',
    mode: 'weak', total: 10, correct: 7, wrong: 3,
    accuracy: 70, durationSeconds: 842, avgSeconds: 84,
    classAccuracy: 64, scoreGain: 3.2,
    kpChanges: [
      { kpId: 'KP52', name: '最短路径 Dijkstra', before: 38, after: 41, delta: 3 },
      { kpId: 'KP23', name: '循环队列判空判满', before: 55, after: 61, delta: 6 },
      { kpId: 'KP31', name: '二叉树基本概念', before: 70, after: 72, delta: 2 },
      { kpId: 'KP44', name: '哈夫曼树与编码', before: 58, after: 55, delta: -3 }
    ],
    errorTypes: [
      { type: '概念混淆', count: 2 },
      { type: '公式记忆错误', count: 1 }
    ],
    nextSuggestion: '建议先观看《易错点串讲：负权边为何失效》（8分45秒），再完成 6 道 Dijkstra 靶向题。'
  };

  const wrongBook = [
    { qId: 'Q0912', stem: '已知一棵哈夫曼树共有 9 个叶子结点，则该树的总结点数为（  ）', myAnswer: 'B', answer: 'C', wrongCount: 2, errorType: '公式记忆错误', kp: '哈夫曼树与编码', kpId: 'KP44', difficulty: 4, lastTime: '08-27 20:15', mastered: false },
    { qId: 'Q0847', stem: '用邻接表存储含 n 个顶点 e 条边的无向图，其边结点总数为（  ）', myAnswer: 'A', answer: 'D', wrongCount: 3, errorType: '概念混淆', kp: '图的存储结构', kpId: 'KP42', difficulty: 3, lastTime: '08-27 19:40', mastered: false },
    { qId: 'Q0763', stem: '对含 10 个顶点的连通图执行 Dijkstra 算法，需进行几轮主循环（  ）', myAnswer: 'C', answer: 'B', wrongCount: 2, errorType: '算法流程不清', kp: '最短路径 Dijkstra', kpId: 'KP52', difficulty: 5, lastTime: '08-26 21:02', mastered: false },
    { qId: 'Q0698', stem: '循环队列中 front 指向队头元素，rear 指向队尾元素的下一位置，则队列长度为（  ）', myAnswer: 'D', answer: 'B', wrongCount: 1, errorType: '指针方向混淆', kp: '循环队列判空判满', kpId: 'KP23', difficulty: 4, lastTime: '08-25 16:30', mastered: true },
    { qId: 'Q0621', stem: '中序遍历二叉排序树可得到一个（  ）序列', myAnswer: 'C', answer: 'A', wrongCount: 1, errorType: '概念混淆', kp: '二叉树的遍历', kpId: 'KP32', difficulty: 3, lastTime: '08-24 14:12', mastered: true }
  ];

  /* 错题详情 · 按 qId 提供完整字段 */
  const wrongDetail = {
    Q0912: {
      qId: 'Q0912', type: 'single', difficulty: 4, score: 5,
      stem: '已知一棵哈夫曼树共有 <code>9</code> 个叶子结点，则该树的总结点数为（  ）',
      options: [
        { key: 'A', text: '15' }, { key: 'B', text: '17' }, { key: 'C', text: '19' }, { key: 'D', text: '21' }
      ],
      answer: 'C',
      analysis: '哈夫曼树只有度为 0 和度为 2 的结点。设叶子结点 n₀，总结点数 N = n₀ + n₂。又由二叉树性质 n₀ = n₂ + 1，得 N = 2n₀ − 1 = 2×9 − 1 = <strong>17</strong>。本题易错点是把"叶子"误当作"度为 1 的结点"，从而错选 19。',
      kpPath: ['第4章 树与二叉树', '哈夫曼树', '哈夫曼树与编码'],
      kpId: 'KP44', preKp: ['二叉树基本概念', '树的带权路径长度'], isKey: true,
      classCorrectRate: 47, avgSeconds: 120, errorType: '公式记忆错误',
      history: [
        { time: '08-27 20:15', answer: 'B', correct: false },
        { time: '08-22 11:08', answer: 'B', correct: false }
      ],
      similar: [
        { qId: 'Q0913', stem: '5 个叶子结点的哈夫曼树总共有多少个结点？', kp: '哈夫曼树与编码' },
        { qId: 'Q0914', stem: '下列关于哈夫曼树的描述，正确的是（  ）', kp: '哈夫曼树与编码' }
      ],
      resources: [
        { type: 'video', name: '易错点串讲：哈夫曼树结点关系', meta: '06:18' },
        { type: 'doc', name: '哈夫曼编码课件 · 第 12 页', meta: 'PDF · 12p' }
      ],
      tips: '牢记公式：哈夫曼树总结点数 = 2×叶子数 − 1。'
    },
    Q0847: {
      qId: 'Q0847', type: 'single', difficulty: 3, score: 5,
      stem: '用邻接表存储含 <code>n</code> 个顶点 <code>e</code> 条边的无向图，其边结点总数为（  ）',
      options: [
        { key: 'A', text: 'n' }, { key: 'B', text: 'e' }, { key: 'C', text: '2e' }, { key: 'D', text: 'n + e' }
      ],
      answer: 'D',
      analysis: '邻接表中：n 个顶点对应 n 个头结点（顶点表）；每条无向边在两个顶点的链表中各出现 1 次，共 2e 个边结点。题中询问"<strong>边结点</strong>总数"，应仅含 2e 个边结点；若问整体结点数才是 n + 2e。',
      kpPath: ['第5章 图', '图的存储', '图的存储结构'],
      kpId: 'KP42', preKp: ['图的基本概念'], isKey: false,
      classCorrectRate: 58, avgSeconds: 88, errorType: '概念混淆',
      history: [
        { time: '08-27 19:40', answer: 'A', correct: false },
        { time: '08-24 21:35', answer: 'A', correct: false },
        { time: '08-19 10:02', answer: 'B', correct: false }
      ],
      similar: [
        { qId: 'Q0848', stem: '用邻接矩阵存储无向图至少需要多大空间？', kp: '图的存储结构' },
        { qId: 'Q0849', stem: '十字链表适合存储哪种图？', kp: '图的存储结构' }
      ],
      resources: [
        { type: 'video', name: '邻接表 · 边结点计数技巧', meta: '04:52' },
        { type: 'ppt', name: '图的存储结构 · 课件', meta: '24 页' }
      ],
      tips: '区分清楚"边结点"与"顶点表头结点"的计数差异。'
    },
    Q0763: {
      qId: 'Q0763', type: 'single', difficulty: 5, score: 6,
      stem: '对含 <code>10</code> 个顶点的连通图执行 Dijkstra 算法，需进行几轮主循环（  ）',
      options: [
        { key: 'A', text: '8' }, { key: 'B', text: '9' }, { key: 'C', text: '10' }, { key: 'D', text: '11' }
      ],
      answer: 'B',
      analysis: 'Dijkstra 每轮确定 1 个顶点的最短路径。n 个顶点的连通图，主循环进行 <strong>n − 1</strong> 轮（源点无需再选），因此 10 个顶点对应 9 轮。',
      kpPath: ['第5章 图', '图的最短路径', '最短路径 Dijkstra'],
      kpId: 'KP52', preKp: ['图的遍历', '贪心算法'], isKey: true,
      classCorrectRate: 41, avgSeconds: 142, errorType: '算法流程不清',
      history: [
        { time: '08-26 21:02', answer: 'C', correct: false },
        { time: '08-21 09:18', answer: 'C', correct: false }
      ],
      similar: [
        { qId: 'Q0764', stem: 'Dijkstra 与 Prim 在结构上的主要区别是？', kp: '最短路径 Dijkstra' }
      ],
      resources: [
        { type: 'video', name: 'Dijkstra 主循环逐轮推演', meta: '12:05' }
      ],
      tips: '口诀："n 顶点，n−1 轮"。'
    },
    Q0698: {
      qId: 'Q0698', type: 'single', difficulty: 4, score: 5,
      stem: '循环队列中 <code>front</code> 指向队头元素，<code>rear</code> 指向队尾元素的下一位置，则队列长度为（  ）',
      options: [
        { key: 'A', text: 'rear − front' }, { key: 'B', text: '(rear − front + MAXSIZE) % MAXSIZE' },
        { key: 'C', text: '(rear − front − 1 + MAXSIZE) % MAXSIZE' }, { key: 'D', text: '(rear − front + 1) % MAXSIZE' }
      ],
      answer: 'B',
      analysis: '当 rear 可能小于 front 时（绕回情况），需加上 MAXSIZE 再取模以保证结果非负：<strong>(rear − front + MAXSIZE) % MAXSIZE</strong>。',
      kpPath: ['第3章 栈与队列', '队列的实现', '循环队列判空判满'],
      kpId: 'KP23', preKp: ['队列的定义与实现'], isKey: true,
      classCorrectRate: 55, avgSeconds: 102, errorType: '指针方向混淆',
      history: [
        { time: '08-25 16:30', answer: 'D', correct: false }
      ],
      similar: [
        { qId: 'Q0699', stem: '牺牲一个存储单元后队满条件是？', kp: '循环队列判空判满' }
      ],
      resources: [
        { type: 'video', name: '循环队列三要素 · 判空/判满/长度', meta: '07:30' }
      ],
      tips: '记住"加模减模"——绕回必加 MAXSIZE。'
    },
    Q0621: {
      qId: 'Q0621', type: 'single', difficulty: 3, score: 4,
      stem: '中序遍历二叉排序树可得到一个（  ）序列',
      options: [
        { key: 'A', text: '有序' }, { key: 'B', text: '无序' },
        { key: 'C', text: '层次' }, { key: 'D', text: '逆序' }
      ],
      answer: 'A',
      analysis: '二叉排序树的性质：<strong>中序遍历得到关键字递增的有序序列</strong>。这是 BST 最核心的结论。',
      kpPath: ['第4章 树与二叉树', '二叉排序树', '二叉树的遍历'],
      kpId: 'KP32', preKp: ['二叉树遍历'], isKey: true,
      classCorrectRate: 73, avgSeconds: 54, errorType: '概念混淆',
      history: [
        { time: '08-24 14:12', answer: 'C', correct: false }
      ],
      similar: [
        { qId: 'Q0622', stem: '平衡二叉树的平衡因子取值范围是？', kp: '二叉树的遍历' }
      ],
      resources: [
        { type: 'doc', name: '二叉排序树 · 关键性质总结', meta: 'PDF · 4p' }
      ],
      tips: 'BST 三序遍历中只有中序保持有序。'
    }
  };

  /* ---------------- 我的学情 ---------------- */
  const masteryMatrix = [
    {
      chapter: '第1章 绪论', completionRate: 100, masteryRate: 90,
      items: [
        { kpId: 'KP01', name: '算法与复杂度', completion: 100, mastery: 92, level: 'excellent', questions: 18, correct: 17, isKey: true },
        { kpId: 'KP02', name: '时间复杂度分析', completion: 100, mastery: 88, level: 'excellent', questions: 24, correct: 21, isKey: true }
      ]
    },
    {
      chapter: '第2章 线性表', completionRate: 100, masteryRate: 84.5,
      items: [
        { kpId: 'KP11', name: '线性表定义', completion: 100, mastery: 95, level: 'excellent', questions: 12, correct: 12, isKey: false },
        { kpId: 'KP12', name: '顺序表', completion: 100, mastery: 90, level: 'excellent', questions: 20, correct: 18, isKey: true },
        { kpId: 'KP13', name: '单链表', completion: 100, mastery: 85, level: 'good', questions: 28, correct: 24, isKey: true },
        { kpId: 'KP14', name: '双向 / 循环链表', completion: 100, mastery: 68, level: 'fair', questions: 16, correct: 11, isKey: false }
      ]
    },
    {
      chapter: '第3章 栈与队列', completionRate: 100, masteryRate: 77.3,
      items: [
        { kpId: 'KP21', name: '栈的定义与实现', completion: 100, mastery: 87, level: 'excellent', questions: 22, correct: 19, isKey: true },
        { kpId: 'KP22', name: '队列的定义与实现', completion: 100, mastery: 82, level: 'good', questions: 20, correct: 16, isKey: true },
        { kpId: 'KP23', name: '循环队列判空判满', completion: 100, mastery: 61, level: 'fair', questions: 14, correct: 8, isKey: true },
        { kpId: 'KP24', name: '栈的典型应用', completion: 100, mastery: 79, level: 'good', questions: 18, correct: 14, isKey: false }
      ]
    },
    {
      chapter: '第4章 树与二叉树', completionRate: 52, masteryRate: 48.6,
      items: [
        { kpId: 'KP31', name: '二叉树基本概念', completion: 100, mastery: 72, level: 'good', questions: 26, correct: 19, isKey: true },
        { kpId: 'KP32', name: '二叉树的遍历', completion: 65, mastery: 66, level: 'fair', questions: 20, correct: 13, isKey: true },
        { kpId: 'KP44', name: '哈夫曼树与编码', completion: 40, mastery: 55, level: 'weak', questions: 12, correct: 6, isKey: true },
        { kpId: 'KP33', name: '线索二叉树', completion: 0, mastery: 0, level: 'none', questions: 0, correct: 0, isKey: false },
        { kpId: 'KP34', name: '树与森林的转换', completion: 0, mastery: 0, level: 'none', questions: 0, correct: 0, isKey: false }
      ]
    },
    {
      chapter: '第5章 图', completionRate: 58, masteryRate: 46.4,
      items: [
        { kpId: 'KP41', name: '图的定义与术语', completion: 100, mastery: 80, level: 'good', questions: 14, correct: 11, isKey: false },
        { kpId: 'KP42', name: '图的存储结构', completion: 85, mastery: 63, level: 'fair', questions: 22, correct: 13, isKey: true },
        { kpId: 'KP43', name: '图的遍历 DFS/BFS', completion: 78, mastery: 70, level: 'good', questions: 24, correct: 17, isKey: true },
        { kpId: 'KP51', name: '最小生成树', completion: 45, mastery: 58, level: 'weak', questions: 10, correct: 5, isKey: true },
        { kpId: 'KP52', name: '最短路径 Dijkstra', completion: 55, mastery: 41, level: 'weak', questions: 18, correct: 7, isKey: true },
        { kpId: 'KP53', name: '拓扑排序', completion: 0, mastery: 0, level: 'none', questions: 0, correct: 0, isKey: false }
      ]
    },
    {
      chapter: '第6章 查找', completionRate: 0, masteryRate: 0,
      items: [
        { kpId: 'KP61', name: '查找的基本概念', completion: 0, mastery: 0, level: 'none', questions: 0, correct: 0, isKey: false },
        { kpId: 'KP62', name: '二分查找', completion: 0, mastery: 0, level: 'none', questions: 0, correct: 0, isKey: true },
        { kpId: 'KP63', name: '二叉排序树', completion: 0, mastery: 0, level: 'none', questions: 0, correct: 0, isKey: true },
        { kpId: 'KP64', name: '哈希表', completion: 0, mastery: 0, level: 'none', questions: 0, correct: 0, isKey: true }
      ]
    }
  ];

  const abilityRadar = {
    indicators: [
      { name: '线性结构运用', max: 100 },
      { name: '树形结构构建', max: 100 },
      { name: '图结构与算法', max: 100 },
      { name: '复杂度分析', max: 100 },
      { name: '算法设计与实现', max: 100 },
      { name: '工程问题建模', max: 100 }
    ],
    series: [
      { name: '我的达成度', data: [86, 64, 56, 89, 62, 58] },
      { name: '班级平均', data: [82, 71, 68, 80, 70, 65] },
      { name: '目标基线', data: [80, 80, 80, 80, 75, 75] }
    ]
  };

  const growthTrack = {
    dimension: 'week',
    xAxis: ['第1周', '第2周', '第3周', '第4周', '第5周', '第6周', '第7周', '第8周'],
    series: [
      { name: '知识点完成率', data: [12, 22, 31, 38, 45, 52, 58, 62.5], color: '#6366f1' },
      { name: '掌握率', data: [65, 68, 72, 75, 78, 76, 75, 74.2], color: '#22c55e' },
      { name: '能力目标达成度', data: [40, 46, 52, 57, 61, 64, 67, 68.9], color: '#8b5cf6' }
    ],
    milestones: [
      { x: '第4周', label: '第2章测评 92 分' },
      { x: '第6周', label: '触发图论薄弱预警' }
    ]
  };

  const classCompare = {
    myRank: 18, totalStudents: 42, percentile: 57,
    items: [
      { metric: '知识点完成率', mine: 62.5, classAvg: 68.4, classBest: 96, diff: -5.9 },
      { metric: '知识点掌握率', mine: 74.2, classAvg: 76.1, classBest: 94, diff: -1.9 },
      { metric: '能力目标达成度', mine: 68.9, classAvg: 72.3, classBest: 93, diff: -3.4 },
      { metric: '练习正确率', mine: 70.0, classAvg: 64.8, classBest: 92, diff: 5.2 },
      { metric: '周均学习时长(分钟)', mine: 285, classAvg: 240, classBest: 520, diff: 45 }
    ]
  };

  /* ---------------- 学生预警 ---------------- */
  const studentAlerts = [
    {
      alertId: 'AL20260828001', level: 'red', type: 'mastery_low',
      title: '「最短路径 Dijkstra 算法」掌握率严重偏低',
      desc: '当前掌握率 41%，低于课程达标线 60%，低于班级平均 27 个百分点。',
      trigger: '规则 R-M02：核心知识点掌握率 < 50% 且连续 2 次练习正确率 < 45%',
      detail: { current: 41, threshold: 60, classAvg: 68, errorCount: 7, relatedQuestions: 18 },
      createdAt: '2026-08-28 06:12', status: 'open',
      suggestions: [
        { type: 'video', text: '观看补救微课《易错点串讲：负权边为何失效》（8分45秒）', resId: 'R204' },
        { type: 'review', text: '回顾前置知识点「图的存储结构」（当前 63%，建议先补齐）', kpId: 'KP42' },
        { type: 'practice', text: '完成靶向练习包「Dijkstra 手工模拟 6 题」', packId: 'PK2026001' },
        { type: 'ai', text: '向 AI 助教发起引导式提问：贪心假设成立的前提是什么' }
      ]
    },
    {
      alertId: 'AL20260827002', level: 'yellow', type: 'progress_lag',
      title: '第5章学习进度滞后于教学计划',
      desc: '教学计划本周应完成至「最小生成树」，你当前停留在「图的存储结构」，滞后约 4 学时。',
      trigger: '规则 R-P01：实际进度落后教学计划 ≥ 3 学时',
      detail: { planned: '最小生成树', actual: '图的存储结构', lagHours: 4 },
      createdAt: '2026-08-27 06:05', status: 'open',
      suggestions: [
        { type: 'path', text: '按推荐路径优先完成「图的存储结构」剩余 30% 内容', kpId: 'KP42' },
        { type: 'plan', text: '本周追加 2 次 45 分钟专注学习，可于周末补齐进度' }
      ]
    },
    {
      alertId: 'AL20260826003', level: 'yellow', type: 'error_cluster',
      title: '「哈夫曼树」相关题目错误集中',
      desc: '近 7 天该知识点共作答 12 题，错 6 题，错误集中在 WPL 加权路径长度计算。',
      trigger: '规则 R-E01：同一知识点 7 日内错题数 ≥ 5 且错误类型集中度 > 60%',
      detail: { total: 12, wrong: 6, mainErrorType: 'WPL 计算失误', concentration: 0.67 },
      createdAt: '2026-08-26 06:08', status: 'open',
      suggestions: [
        { type: 'doc', text: '重读教材 P152《哈夫曼树的构造与 WPL 计算》', resId: 'R105' },
        { type: 'practice', text: '完成「WPL 专项 5 题」，逐题核对构造过程', packId: 'PK2026002' }
      ]
    },
    {
      alertId: 'AL20260825004', level: 'green', type: 'resolved',
      title: '「循环队列判空判满」预警已解除',
      desc: '经补救微课 + 5 道靶向练习后，掌握率从 48% 提升至 61%，已回归正常区间。',
      trigger: '规则 R-R01：掌握率回升至阈值以上并稳定 3 日',
      detail: { before: 48, after: 61, days: 3 },
      createdAt: '2026-08-25 06:00', status: 'closed',
      suggestions: [{ type: 'keep', text: '保持每周 1 次错题回顾，防止遗忘回落' }]
    }
  ];

  /* ---------------- 教师端 · 教学驾驶舱 ---------------- */
  const teacherDashboard = {
    classOverview: {
      classId: 'CL2301', className: '计算机 2301 班', studentCount: 42,
      avgCompletionRate: 68.4, avgMasteryRate: 76.1, avgGoalAchieve: 72.3,
      alertStudentCount: 9, alertRatio: 21.4,
      activeToday: 31, submitToday: 58,
      deltaCompletion: 4.2, deltaMastery: -1.3, deltaGoal: 2.1,
      updatedAt: '2026-08-28 06:00'
    },
    liveFeed: [
      { id: 'F1', type: 'submit', text: '王志豪 提交了「图论综合训练包」', meta: '10/12 正确 · 用时 18 分钟', time: '2 分钟前', level: 'ok' },
      { id: 'F2', type: 'alert', text: '新增红色预警：陈思远 · Dijkstra 掌握率 41%', meta: '规则 R-M02 触发', time: '9 分钟前', level: 'danger' },
      { id: 'F3', type: 'submit', text: '刘欣然 完成第4章章节自测', meta: '18/20 正确', time: '15 分钟前', level: 'ok' },
      { id: 'F4', type: 'alert', text: '新增黄色预警：赵梓涵 · 进度滞后 5 学时', meta: '规则 R-P01 触发', time: '32 分钟前', level: 'warn' },
      { id: 'F5', type: 'chat', text: '本节课 AI 答疑量激增：最小生成树 相关提问 24 次', meta: '较昨日 +180%', time: '1 小时前', level: 'warn' },
      { id: 'F6', type: 'submit', text: '孙博文 完成错题重练', meta: '8/8 正确 · 3 个错题标记为已掌握', time: '1 小时前', level: 'ok' }
    ],
    todos: [
      { id: 'TT1', level: 'danger', title: '9 条预警待处理', desc: '其中红色 3 条、黄色 6 条，最早一条已挂起 2 天', action: '去处理', target: 'alerts' },
      { id: 'TT2', level: 'brand', title: '4 条 AI 干预建议待确认', desc: '涉及 Dijkstra、哈夫曼树 2 个共性薄弱点', action: '去确认', target: 'intervention' },
      { id: 'TT3', level: 'warn', title: '12 道 AI 生成习题待审核', desc: '第5章图论靶向题包，生成于今日 09:20', action: '去审核', target: 'question' },
      { id: 'TT4', level: 'ok', title: '第5章阶段性学情报告可生成', desc: '数据已完整覆盖 8 个知识点', action: '生成报告', target: 'report' }
    ],
    kpRanking: [
      { kpId: 'KP52', name: '最短路径 Dijkstra', mastery: 52.3, students: 42, weakCount: 19 },
      { kpId: 'KP44', name: '哈夫曼树与编码', mastery: 58.1, students: 42, weakCount: 15 },
      { kpId: 'KP51', name: '最小生成树', mastery: 61.7, students: 42, weakCount: 12 },
      { kpId: 'KP23', name: '循环队列判空判满', mastery: 64.5, students: 42, weakCount: 11 },
      { kpId: 'KP42', name: '图的存储结构', mastery: 68.9, students: 42, weakCount: 8 }
    ]
  };

  /* ---------------- 教师端 · 热力图 ---------------- */
  const heatmap = {
    dimension: 'week',
    kpAxis: ['算法复杂度', '顺序表', '单链表', '栈', '队列', '循环队列', '二叉树概念', '二叉树遍历', '哈夫曼树', '图的存储', 'DFS/BFS', '最小生成树', 'Dijkstra'],
    studentAxis: ['陈思远', '王志豪', '刘欣然', '赵梓涵', '孙博文', '周雨桐', '吴嘉豪', '郑晓彤', '林浩然', '黄诗涵', '徐子墨', '何雨泽'],
    // [kpIndex, studentIndex, masteryRate]
    data: [
      [0,0,92],[1,0,90],[2,0,85],[3,0,87],[4,0,82],[5,0,61],[6,0,72],[7,0,66],[8,0,55],[9,0,63],[10,0,70],[11,0,58],[12,0,41],
      [0,1,95],[1,1,94],[2,1,92],[3,1,90],[4,1,88],[5,1,85],[6,1,88],[7,1,84],[8,1,80],[9,1,86],[10,1,88],[11,1,82],[12,1,78],
      [0,2,90],[1,2,88],[2,2,86],[3,2,89],[4,2,85],[5,2,78],[6,2,84],[7,2,80],[8,2,72],[9,2,80],[10,2,82],[11,2,74],[12,2,68],
      [0,3,72],[1,3,68],[2,3,60],[3,3,65],[4,3,58],[5,3,42],[6,3,52],[7,3,44],[8,3,35],[9,3,40],[10,3,45],[11,3,30],[12,3,22],
      [0,4,88],[1,4,85],[2,4,82],[3,4,86],[4,4,80],[5,4,70],[6,4,78],[7,4,74],[8,4,62],[9,4,72],[10,4,75],[11,4,64],[12,4,55],
      [0,5,85],[1,5,80],[2,5,78],[3,5,82],[4,5,76],[5,5,68],[6,5,74],[7,5,70],[8,5,58],[9,5,66],[10,5,70],[11,5,60],[12,5,48],
      [0,6,78],[1,6,72],[2,6,68],[3,6,70],[4,6,64],[5,6,52],[6,6,60],[7,6,54],[8,6,44],[9,6,50],[10,6,55],[11,6,42],[12,6,32],
      [0,7,92],[1,7,90],[2,7,88],[3,7,88],[4,7,86],[5,7,80],[6,7,86],[7,7,82],[8,7,76],[9,7,82],[10,7,84],[11,7,78],[12,7,70],
      [0,8,80],[1,8,76],[2,8,72],[3,8,75],[4,8,70],[5,8,60],[6,8,68],[7,8,62],[8,8,50],[9,8,58],[10,8,62],[11,8,52],[12,8,40],
      [0,9,86],[1,9,84],[2,9,80],[3,9,84],[4,9,78],[5,9,72],[6,9,80],[7,9,76],[8,9,66],[9,9,74],[10,9,78],[11,9,68],[12,9,60],
      [0,10,70],[1,10,64],[2,10,58],[3,10,62],[4,10,55],[5,10,45],[6,10,50],[7,10,46],[8,10,32],[9,10,42],[10,10,48],[11,10,35],[12,10,25],
      [0,11,88],[1,11,86],[2,11,84],[3,11,85],[4,11,82],[5,11,76],[6,11,82],[7,11,78],[8,11,70],[9,11,78],[10,11,80],[11,11,72],[12,11,64]
    ],
    kpAvg: [85.0, 81.4, 77.8, 80.8, 75.3, 65.8, 72.8, 68.0, 58.3, 65.9, 69.8, 59.6, 50.3],
    weakest: [{ index: 12, name: 'Dijkstra', avg: 50.3 }, { index: 8, name: '哈夫曼树', avg: 58.3 }, { index: 11, name: '最小生成树', avg: 59.6 }]
  };

  /* ---------------- 教师端 · 学生列表 ---------------- */
  const students = [
    { userId: 'S20260317', name: '陈思远', no: '2023110317', avatar: '陈', completion: 62.5, mastery: 74.2, goal: 68.9, alertLevel: 'red', alertCount: 3, lastActive: '2 小时前', studyMinutes: 285, rank: 18 },
    { userId: 'S20260301', name: '王志豪', no: '2023110301', avatar: '王', completion: 94.0, mastery: 88.6, goal: 91.2, alertLevel: 'green', alertCount: 0, lastActive: '2 分钟前', studyMinutes: 520, rank: 1 },
    { userId: 'S20260308', name: '刘欣然', no: '2023110308', avatar: '刘', completion: 88.5, mastery: 84.1, goal: 86.4, alertLevel: 'green', alertCount: 0, lastActive: '15 分钟前', studyMinutes: 468, rank: 3 },
    { userId: 'S20260322', name: '赵梓涵', no: '2023110322', avatar: '赵', completion: 38.2, mastery: 48.7, goal: 43.5, alertLevel: 'red', alertCount: 5, lastActive: '3 天前', studyMinutes: 96, rank: 41 },
    { userId: 'S20260315', name: '孙博文', no: '2023110315', avatar: '孙', completion: 76.8, mastery: 78.3, goal: 75.6, alertLevel: 'green', alertCount: 0, lastActive: '1 小时前', studyMinutes: 372, rank: 9 },
    { userId: 'S20260329', name: '周雨桐', no: '2023110329', avatar: '周', completion: 71.4, mastery: 73.5, goal: 70.2, alertLevel: 'yellow', alertCount: 1, lastActive: '5 小时前', studyMinutes: 310, rank: 14 },
    { userId: 'S20260333', name: '吴嘉豪', no: '2023110333', avatar: '吴', completion: 52.6, mastery: 58.9, goal: 54.3, alertLevel: 'red', alertCount: 4, lastActive: '1 天前', studyMinutes: 168, rank: 35 },
    { userId: 'S20260306', name: '郑晓彤', no: '2023110306', avatar: '郑', completion: 91.2, mastery: 86.4, goal: 88.7, alertLevel: 'green', alertCount: 0, lastActive: '30 分钟前', studyMinutes: 490, rank: 2 },
    { userId: 'S20260341', name: '林浩然', no: '2023110341', avatar: '林', completion: 64.8, mastery: 67.2, goal: 63.1, alertLevel: 'yellow', alertCount: 2, lastActive: '8 小时前', studyMinutes: 254, rank: 24 },
    { userId: 'S20260311', name: '黄诗涵', no: '2023110311', avatar: '黄', completion: 82.3, mastery: 80.5, goal: 79.8, alertLevel: 'green', alertCount: 0, lastActive: '4 小时前', studyMinutes: 415, rank: 6 },
    { userId: 'S20260337', name: '徐子墨', no: '2023110337', avatar: '徐', completion: 41.5, mastery: 51.3, goal: 46.8, alertLevel: 'red', alertCount: 4, lastActive: '2 天前', studyMinutes: 120, rank: 39 },
    { userId: 'S20260304', name: '何雨泽', no: '2023110304', avatar: '何', completion: 86.7, mastery: 82.8, goal: 84.1, alertLevel: 'green', alertCount: 0, lastActive: '20 分钟前', studyMinutes: 440, rank: 5 }
  ];

  const studentProfile = {
    userId: 'S20260317', name: '陈思远', no: '2023110317', className: '计算机 2301 班',
    metrics: { completion: 62.5, mastery: 74.2, goal: 68.9, rank: 18, totalStudents: 42, accuracy: 70.4 },
    studyTimeDist: {
      xAxis: ['00-06', '06-09', '09-12', '12-15', '15-18', '18-21', '21-24'],
      data: [12, 28, 45, 30, 68, 92, 110]
    },
    activityTrend: {
      xAxis: ['08-22', '08-23', '08-24', '08-25', '08-26', '08-27', '08-28'],
      minutes: [45, 62, 20, 78, 55, 40, 48],
      questions: [8, 15, 4, 22, 12, 6, 10]
    },
    kpDetail: [
      { kpId: 'KP52', name: '最短路径 Dijkstra', mastery: 41, questions: 18, wrong: 7, minutes: 96, level: 'weak' },
      { kpId: 'KP44', name: '哈夫曼树与编码', mastery: 55, questions: 12, wrong: 6, minutes: 62, level: 'weak' },
      { kpId: 'KP51', name: '最小生成树', mastery: 58, questions: 10, wrong: 5, minutes: 48, level: 'weak' },
      { kpId: 'KP23', name: '循环队列判空判满', mastery: 61, questions: 14, wrong: 6, minutes: 55, level: 'fair' },
      { kpId: 'KP42', name: '图的存储结构', mastery: 63, questions: 22, wrong: 9, minutes: 88, level: 'fair' },
      { kpId: 'KP32', name: '二叉树的遍历', mastery: 66, questions: 20, wrong: 7, minutes: 105, level: 'fair' }
    ],
    wrongDetail: [
      { qId: 'Q0763', kp: '最短路径 Dijkstra', errorType: '算法流程不清', count: 2, difficulty: 5 },
      { qId: 'Q0912', kp: '哈夫曼树与编码', errorType: '公式记忆错误', count: 2, difficulty: 4 },
      { qId: 'Q0847', kp: '图的存储结构', errorType: '概念混淆', count: 3, difficulty: 3 }
    ]
  };

  /* ---------------- 教师端 · 预警列表 ---------------- */
  const teacherAlerts = [
    { alertId: 'AL20260828001', level: 'red', student: '陈思远', userId: 'S20260317', type: '掌握率过低', kp: '最短路径 Dijkstra', desc: '掌握率 41%，低于达标线 60%', trigger: 'R-M02：核心知识点掌握率<50% 且连续2次正确率<45%', trendData: [52, 48, 45, 43, 41], createdAt: '2026-08-28 06:12', status: 'open' },
    { alertId: 'AL20260828002', level: 'red', student: '赵梓涵', userId: 'S20260322', type: '进度严重滞后', kp: '第5章 图', desc: '滞后教学计划 12 学时，3 天未登录', trigger: 'R-P02：滞后≥8学时 或 连续3日无学习行为', trendData: [70, 58, 48, 42, 38], createdAt: '2026-08-28 06:10', status: 'open' },
    { alertId: 'AL20260828003', level: 'red', student: '徐子墨', userId: 'S20260337', type: '错题集中', kp: '哈夫曼树与编码', desc: '近 7 天该知识点错 8 题，错误集中于 WPL 计算', trigger: 'R-E01：7日内错题≥5 且 错误类型集中度>60%', trendData: [60, 56, 54, 52, 51], createdAt: '2026-08-28 06:09', status: 'open' },
    { alertId: 'AL20260827004', level: 'yellow', student: '吴嘉豪', userId: 'S20260333', type: '掌握率下滑', kp: '图的存储结构', desc: '掌握率一周内由 68% 降至 55%', trigger: 'R-M03：掌握率 7 日跌幅 ≥ 10 个百分点', trendData: [68, 66, 62, 58, 55], createdAt: '2026-08-27 06:15', status: 'open' },
    { alertId: 'AL20260827005', level: 'yellow', student: '林浩然', userId: 'S20260341', type: '学习时长不足', kp: '—', desc: '本周学习时长 88 分钟，低于班级平均 62%', trigger: 'R-T01：周学习时长低于班级平均 50% 以上', trendData: [240, 200, 160, 120, 88], createdAt: '2026-08-27 06:12', status: 'open' },
    { alertId: 'AL20260827006', level: 'yellow', student: '周雨桐', userId: 'S20260329', type: '进度滞后', kp: '第5章 图', desc: '滞后教学计划 4 学时', trigger: 'R-P01：滞后 ≥ 3 学时', trendData: [78, 76, 74, 72, 71], createdAt: '2026-08-27 06:08', status: 'reviewed' },
    { alertId: 'AL20260826007', level: 'yellow', student: '陈思远', userId: 'S20260317', type: '错题集中', kp: '哈夫曼树与编码', desc: '近 7 天错 6 题，集中于 WPL 计算', trigger: 'R-E01', trendData: [62, 60, 58, 56, 55], createdAt: '2026-08-26 06:08', status: 'open' },
    { alertId: 'AL20260826008', level: 'yellow', student: '吴嘉豪', userId: 'S20260333', type: '答疑求助频繁', kp: '最小生成树', desc: '单日 AI 答疑 14 轮仍未达标，疑似理解障碍', trigger: 'R-A01：单知识点答疑≥10轮 且 后测正确率<50%', trendData: [3, 5, 8, 11, 14], createdAt: '2026-08-26 06:05', status: 'ignored' }
  ];

  /* ---------------- 教师端 · 归因与错题分析 ---------------- */
  const errorAnalysis = {
    scope: { classId: 'CL2301', chapter: '第5章 图', timeRange: '近 14 天' },
    errorTypeDist: [
      { type: '概念混淆', count: 68, ratio: 28.3 },
      { type: '算法流程不清', count: 54, ratio: 22.5 },
      { type: '公式记忆错误', count: 41, ratio: 17.1 },
      { type: '前置知识缺失', count: 36, ratio: 15.0 },
      { type: '计算失误', count: 25, ratio: 10.4 },
      { type: '题意理解偏差', count: 16, ratio: 6.7 }
    ],
    topWrongQuestions: [
      { qId: 'Q1024', stem: 'Dijkstra 算法遇负权边时的正确处理方式', kp: '最短路径 Dijkstra', wrongRate: 48, count: 20, mainWrongOption: 'D', difficulty: 4, type: '概念混淆' },
      { qId: 'Q0763', stem: '含 10 个顶点连通图执行 Dijkstra 的主循环轮数', kp: '最短路径 Dijkstra', wrongRate: 43, count: 18, mainWrongOption: 'C', difficulty: 5, type: '算法流程不清' },
      { qId: 'Q0912', stem: '9 个叶子结点的哈夫曼树总结点数', kp: '哈夫曼树与编码', wrongRate: 40, count: 17, mainWrongOption: 'B', difficulty: 4, type: '公式记忆错误' },
      { qId: 'Q0847', stem: '邻接表存储无向图的边结点总数', kp: '图的存储结构', wrongRate: 36, count: 15, mainWrongOption: 'A', difficulty: 3, type: '概念混淆' },
      { qId: 'Q0805', stem: 'Prim 与 Kruskal 算法适用场景对比', kp: '最小生成树', wrongRate: 33, count: 14, mainWrongOption: 'C', difficulty: 4, type: '概念混淆' }
    ],
    weakChain: {
      root: { kpId: 'KP02', name: '时间复杂度分析', mastery: 84, type: 'pre' },
      mid: { kpId: 'KP42', name: '图的存储结构', mastery: 68.9, type: 'pre' },
      leaf: { kpId: 'KP52', name: '最短路径 Dijkstra', mastery: 50.3, type: 'target' },
      explain: '班级在「图的存储结构」上邻接矩阵/邻接表的适用场景区分不清（掌握率 68.9%），直接导致 Dijkstra 实现时数据结构选择错误，进而在复杂度分析上连锁出错。'
    },
    causes: [
      {
        causeId: 'CA1', level: 'danger',
        title: '前置知识缺失：邻接矩阵与邻接表的选择依据不清',
        desc: '68% 的 Dijkstra 错题中，学生在第一步"选择存储结构"即出错。归因显示这些学生在「图的存储结构」知识点的掌握率均低于 70%。',
        evidence: ['关联错题 20 道，其中 14 道错在存储结构选择', '前置知识点掌握率与本知识点正确率相关系数 r = 0.78', 'AI 答疑记录中该问题被提问 31 次'],
        advice: ['课堂用 5 分钟对比表格重讲两种存储结构的时空复杂度边界', '推送补救微课《邻接矩阵 vs 邻接表：什么时候用哪个》', '为掌握率<70% 的 8 名学生布置前置靶向练习包']
      },
      {
        causeId: 'CA2', level: 'warn',
        title: '算法流程未内化：贪心松弛的执行顺序混乱',
        desc: '学生能背出算法步骤，但在手工模拟时无法正确维护 S 集合与 dist 数组，说明程序性知识未形成。',
        evidence: ['手工模拟类题目正确率仅 38%，选择题正确率 62%，差距显著', '错题簇 EC1「贪心松弛顺序混乱」累计 26 人次'],
        advice: ['课堂增加一次 10 分钟集体手工模拟（建议用 6 顶点带权图）', '布置"填表式"过程题，强制学生写出每轮 dist 数组快照', '开放 AI 助教启发式模式，让学生自己发现松弛顺序错误']
      },
      {
        causeId: 'CA3', level: 'warn',
        title: '题目难度梯度过陡',
        desc: '本章练习中难度 4-5 星题目占比 61%，缺少 2-3 星过渡题，导致中位学生直接受挫。',
        evidence: ['难度分布：1星 4%、2星 12%、3星 23%、4星 38%、5星 23%', '中位段学生（掌握率 60-75%）在 4 星题正确率骤降至 41%'],
        advice: ['使用 AI 出题补充 10 道 2-3 星过渡题，形成难度阶梯', '将现有 5 星综合题调整为课后选做']
      },
      {
        causeId: 'CA4', level: 'ok',
        title: '练习量不足',
        desc: '9 名学生本章练习题量低于 10 题，缺少足够练习支撑。',
        evidence: ['9 名学生练习量 < 10 题，其平均掌握率 47.2%', '练习量 > 25 题的学生平均掌握率 81.5%'],
        advice: ['向练习量不足学生推送温和提醒与最小练习包（每日 5 题）']
      }
    ],
    commonVsIndividual: {
      common: [
        { kp: '最短路径 Dijkstra', affected: 19, ratio: 45.2, desc: '班级共性薄弱，需课堂集体干预' },
        { kp: '哈夫曼树与编码', affected: 15, ratio: 35.7, desc: '班级共性薄弱，需课堂集体干预' }
      ],
      individual: [
        { student: '赵梓涵', userId: 'S20260322', issue: '全面滞后 + 3 日未登录', desc: '个体异常，需一对一联系' },
        { student: '徐子墨', userId: 'S20260337', issue: '练习量严重不足（本章 6 题）', desc: '个体异常，需督促练习' },
        { student: '吴嘉豪', userId: 'S20260333', issue: '答疑频繁但后测不达标', desc: '疑似理解路径障碍，建议面谈' }
      ]
    }
  };

  /* ---------------- 教师端 · AI 出题 ---------------- */
  const genConfig = {
    materials: [
      { fileId: 'M001', name: '第5章 图（下）课堂课件.pptx', size: '8.4 MB', type: 'ppt', status: 'parsed', kpCount: 6 },
      { fileId: 'M002', name: '数据结构（C语言版）第7章.pdf', size: '12.1 MB', type: 'doc', status: 'parsed', kpCount: 9 },
      { fileId: 'M003', name: 'Dijkstra 算法原理与手工模拟.mp4', size: '186 MB', type: 'video', status: 'parsing', kpCount: 0, progress: 62 }
    ],
    kpOptions: [
      { kpId: 'KP41', name: '图的定义与术语' },
      { kpId: 'KP42', name: '图的存储结构' },
      { kpId: 'KP43', name: '图的遍历 DFS/BFS' },
      { kpId: 'KP51', name: '最小生成树' },
      { kpId: 'KP52', name: '最短路径 Dijkstra' },
      { kpId: 'KP53', name: '拓扑排序' }
    ],
    typeOptions: [
      { key: 'single', name: '单选题' },
      { key: 'multi', name: '多选题' },
      { key: 'judge', name: '判断题' },
      { key: 'blank', name: '填空题' },
      { key: 'code', name: '算法设计题' }
    ]
  };

  const generatedQuestions = [
    {
      qId: 'GQ001', type: 'single', difficulty: 3, status: 'pending',
      stem: '在含 n 个顶点、e 条边的稀疏有向图中，若要频繁遍历某顶点的所有出边，则最合适的存储结构是：',
      options: [
        { key: 'A', text: '邻接矩阵', right: false },
        { key: 'B', text: '邻接表', right: true },
        { key: 'C', text: '边集数组', right: false },
        { key: 'D', text: '十字链表', right: false }
      ],
      analysis: '稀疏图使用邻接矩阵会造成 O(n²) 空间浪费；邻接表按顶点组织出边链，遍历某顶点所有出边的时间为 O(出度)，是最优选择。边集数组需扫描全部边 O(e)；十字链表主要用于同时需要快速访问入边与出边的场景。',
      kpPath: ['第5章 图', '图的存储结构', '邻接表'],
      kpId: 'KP42', preKp: ['图的定义与术语'], postKp: ['图的遍历 DFS/BFS'], isKey: true,
      sourceRef: { fileId: 'M001', locator: 'P12 · 存储结构对比表' },
      estimatedCorrectRate: 72
    },
    {
      qId: 'GQ002', type: 'single', difficulty: 4, status: 'pending',
      stem: '对下图执行 Dijkstra 算法（源点 V0），第 2 轮主循环结束后被并入集合 S 的顶点是：<br><span class="mono t-dim">V0→V1:4  V0→V2:1  V2→V1:2  V1→V3:5  V2→V3:8</span>',
      options: [
        { key: 'A', text: 'V1', right: false },
        { key: 'B', text: 'V2', right: false },
        { key: 'C', text: 'V1（dist=3，经 V2 松弛后）', right: true },
        { key: 'D', text: 'V3', right: false }
      ],
      analysis: '第 1 轮选 V2（dist=1）并入 S，随后松弛得 dist[V1] = 1 + 2 = 3（优于直连 4）。第 2 轮在剩余顶点中 dist 最小者为 V1（dist=3），故并入 V1。此题重点考查<strong>松弛发生在并入之后</strong>这一执行顺序。',
      kpPath: ['第5章 图', '图的最短路径', '最短路径 Dijkstra'],
      kpId: 'KP52', preKp: ['图的存储结构', '图的遍历 DFS/BFS'], postKp: ['Floyd 多源最短路径'], isKey: true,
      sourceRef: { fileId: 'M002', locator: 'P188 · 算法 7.10 与例 7.9' },
      estimatedCorrectRate: 45
    },
    {
      qId: 'GQ003', type: 'judge', difficulty: 2, status: 'approved',
      stem: 'Dijkstra 算法每轮主循环都会重新计算所有顶点的 dist 值。',
      options: [
        { key: 'T', text: '正确', right: false },
        { key: 'F', text: '错误', right: true }
      ],
      analysis: '每轮只对<strong>刚并入 S 的顶点的邻接点</strong>执行松弛操作，而非全部顶点，这也是其复杂度为 O(n²) 而非 O(n³) 的原因。',
      kpPath: ['第5章 图', '图的最短路径', '最短路径 Dijkstra'],
      kpId: 'KP52', preKp: ['图的存储结构'], postKp: [], isKey: false,
      sourceRef: { fileId: 'M001', locator: 'P24 · 算法复杂度分析' },
      estimatedCorrectRate: 78
    }
  ];

  const questionBank = [
    { qId: 'Q1024', stem: 'Dijkstra 算法遇负权边时的正确处理方式', type: '单选题', kp: '最短路径 Dijkstra', difficulty: 4, isKey: true, useCount: 42, correctRate: 52, status: 'published', source: 'AI 生成', createdAt: '2026-08-20' },
    { qId: 'Q1025', stem: '完全二叉树 1000 个结点的叶子结点数', type: '单选题', kp: '二叉树基本概念', difficulty: 3, isKey: true, useCount: 68, correctRate: 68, status: 'published', source: '教师录入', createdAt: '2026-08-12' },
    { qId: 'Q1026', stem: '循环队列牺牲一个单元时的队满条件', type: '单选题', kp: '循环队列判空判满', difficulty: 4, isKey: true, useCount: 55, correctRate: 61, status: 'published', source: 'AI 生成', createdAt: '2026-08-10' },
    { qId: 'Q0912', stem: '9 个叶子结点的哈夫曼树总结点数', type: '单选题', kp: '哈夫曼树与编码', difficulty: 4, isKey: true, useCount: 40, correctRate: 60, status: 'published', source: '题库导入', createdAt: '2026-08-08' },
    { qId: 'Q0847', stem: '邻接表存储无向图的边结点总数', type: '单选题', kp: '图的存储结构', difficulty: 3, isKey: false, useCount: 38, correctRate: 64, status: 'published', source: 'AI 生成', createdAt: '2026-08-06' },
    { qId: 'GQ001', stem: '稀疏有向图频繁遍历出边的最优存储结构', type: '单选题', kp: '图的存储结构', difficulty: 3, isKey: true, useCount: 0, correctRate: null, status: 'pending', source: 'AI 生成', createdAt: '2026-08-28' },
    { qId: 'GQ002', stem: 'Dijkstra 第 2 轮并入 S 的顶点', type: '单选题', kp: '最短路径 Dijkstra', difficulty: 4, isKey: true, useCount: 0, correctRate: null, status: 'pending', source: 'AI 生成', createdAt: '2026-08-28' },
    { qId: 'GQ003', stem: 'Dijkstra 每轮是否重算所有 dist', type: '判断题', kp: '最短路径 Dijkstra', difficulty: 2, isKey: false, useCount: 0, correctRate: null, status: 'approved', source: 'AI 生成', createdAt: '2026-08-28' },
    { qId: 'Q0805', stem: 'Prim 与 Kruskal 算法适用场景对比', type: '多选题', kp: '最小生成树', difficulty: 4, isKey: true, useCount: 32, correctRate: 67, status: 'published', source: '教师录入', createdAt: '2026-08-04' },
    { qId: 'Q0698', stem: '循环队列长度计算公式', type: '单选题', kp: '循环队列判空判满', difficulty: 4, isKey: false, useCount: 44, correctRate: 58, status: 'archived', source: '题库导入', createdAt: '2026-07-28' }
  ];

  /* ---------------- 教师端 · 教学干预 ---------------- */
  const interventions = [
    {
      ivId: 'IV20260828001', status: 'pending', level: 'danger',
      alertId: 'AL20260828001', scope: 'common',
      title: '针对班级共性薄弱点「最短路径 Dijkstra」的集体干预',
      target: '计算机 2301 班 · 19 名掌握率低于 60% 的学生',
      reason: 'AI 归因：42% 概率为前置知识「图的存储结构」缺失，31% 概率为算法流程未内化。',
      steps: [
        '课堂插入 10 分钟集体手工模拟（6 顶点带权图，学生填 dist 快照表）',
        '推送补救微课《邻接矩阵 vs 邻接表：什么时候用哪个》（12 分钟）',
        '生成并布置 10 道 2-3 星难度过渡题，形成难度阶梯',
        '3 日后自动复测，对比掌握率变化'
      ],
      expectEffect: '预计掌握率由 50.3% 提升至 68%~72%',
      resources: [{ resId: 'R204', name: '易错点串讲：负权边为何失效' }, { resId: 'R108', name: '邻接矩阵 vs 邻接表' }],
      packId: 'PK2026001', createdAt: '2026-08-28 06:20'
    },
    {
      ivId: 'IV20260828002', status: 'pending', level: 'danger',
      alertId: 'AL20260828002', scope: 'individual',
      title: '赵梓涵 · 全面滞后个体干预',
      target: '赵梓涵（2023110322）· 滞后 12 学时，3 日未登录',
      reason: 'AI 归因：学习行为中断为主因，需人工介入而非资源推送。',
      steps: [
        '教师私信 + 电话联系，了解中断原因',
        '重新规划最小学习路径（仅保留 6 个核心知识点）',
        '设置每日 20 分钟微目标，降低启动门槛',
        '连续 5 日打卡后恢复标准路径'
      ],
      expectEffect: '预计 2 周内进度追平至滞后 ≤ 4 学时',
      resources: [], packId: null, createdAt: '2026-08-28 06:18'
    },
    {
      ivId: 'IV20260827003', status: 'running', level: 'warn',
      alertId: 'AL20260827004', scope: 'common',
      title: '「哈夫曼树 WPL 计算」专项补练',
      target: '计算机 2301 班 · 15 名学生',
      reason: 'AI 归因：公式记忆错误占 65%，属程序性知识不熟练。',
      steps: ['推送教材 P152 精读任务', '布置 WPL 专项 5 题（强制写出构造过程）', '2 日后复测'],
      expectEffect: '预计掌握率由 58.3% 提升至 72%',
      resources: [{ resId: 'R105', name: '《数据结构》第6章 P152' }],
      packId: 'PK2026002', createdAt: '2026-08-27 08:30',
      execution: { pushedAt: '2026-08-27 09:00', reached: 15, completed: 11, completeRate: 73.3, retestDone: 9, masteryBefore: 58.3, masteryAfter: 69.1 }
    },
    {
      ivId: 'IV20260824004', status: 'done', level: 'ok',
      alertId: 'AL20260825004', scope: 'common',
      title: '「循环队列判空判满」补救微课 + 靶向练习',
      target: '计算机 2301 班 · 11 名学生',
      reason: 'AI 归因：指针方向混淆占 71%。',
      steps: ['推送补救微课（12 分钟）', '布置靶向练习 5 题', '3 日后复测'],
      expectEffect: '预计掌握率由 52% 提升至 65%',
      resources: [{ resId: 'R112', name: '循环队列判空判满专题' }],
      packId: 'PK2026003', createdAt: '2026-08-24 10:15',
      execution: { pushedAt: '2026-08-24 10:30', reached: 11, completed: 11, completeRate: 100, retestDone: 11, masteryBefore: 52.0, masteryAfter: 71.4 }
    }
  ];

  const interventionEffect = {
    ivId: 'IV20260824004',
    xAxis: ['干预前3日', '干预前1日', '干预日', '干预后1日', '干预后3日', '干预后7日'],
    series: [
      { name: '干预组掌握率', data: [50.2, 52.0, 52.0, 61.5, 68.3, 71.4], color: '#22c55e' },
      { name: '对照组掌握率', data: [51.0, 51.8, 52.2, 53.4, 55.1, 56.8], color: '#64748b' }
    ],
    summary: '干预组 7 日内掌握率提升 19.4 个百分点，对照组仅提升 5.8 个百分点，干预有效性显著（提升差 13.6pp）。'
  };

  const strategyTemplates = [
    { tplId: 'TPL001', name: '前置知识缺失补齐三步法', scene: '前置知识缺失', desc: '定位缺失前置点 → 推送最小补齐资源 → 前置达标后再回到目标知识点', useCount: 24, successRate: 82, avgLift: 15.6, tags: ['共性', '资源推送'] },
    { tplId: 'TPL002', name: '程序性知识填表强化法', scene: '算法流程不清', desc: '强制学生输出中间过程快照（如 dist 数组、栈状态），将隐式流程显式化', useCount: 18, successRate: 78, avgLift: 13.2, tags: ['共性', '作业设计'] },
    { tplId: 'TPL003', name: '难度阶梯重构法', scene: '难度梯度过陡', desc: 'AI 补充 2-3 星过渡题，将 4-5 星题调整为选做，重建难度分布', useCount: 12, successRate: 75, avgLift: 11.8, tags: ['共性', 'AI 出题'] },
    { tplId: 'TPL004', name: '学习中断唤醒法', scene: '学习行为中断', desc: '人工联系 + 最小路径重规划 + 每日微目标，降低重启门槛', useCount: 9, successRate: 67, avgLift: 22.4, tags: ['个体', '人工介入'] },
    { tplId: 'TPL005', name: '错题簇集中歼灭法', scene: '错题集中', desc: '按错误类型聚类错题，一次性推送同类型专项包 + 归因讲解', useCount: 21, successRate: 85, avgLift: 17.1, tags: ['共性', '错题本'] },
    { tplId: 'TPL006', name: '同伴互助配对法', scene: '个体理解障碍', desc: '将答疑频繁但后测不达标学生与高掌握率学生配对讲解', useCount: 6, successRate: 71, avgLift: 14.5, tags: ['个体', '协作学习'] }
  ];

  /* ---------------- 教师端 · 学情报告 ---------------- */
  const reportList = [
    { reportId: 'RP20260828001', title: '计算机 2301 班 · 第5章 图 阶段学情报告', scope: '班级 / 章节', period: '2026-08-15 ~ 2026-08-28', createdAt: '2026-08-28 10:20', creator: '李文博', status: 'ready', pages: 12 },
    { reportId: 'RP20260815002', title: '计算机 2301 班 · 第4章 树与二叉树 阶段学情报告', scope: '班级 / 章节', period: '2026-08-01 ~ 2026-08-14', createdAt: '2026-08-15 09:12', creator: '李文博', status: 'ready', pages: 10 },
    { reportId: 'RP20260801003', title: '三个班级 · 期中横向对比报告', scope: '多班级 / 全课程', period: '2026-07-01 ~ 2026-07-31', createdAt: '2026-08-01 16:40', creator: '李文博', status: 'ready', pages: 18 },
    { reportId: 'RP20260718004', title: '计算机 2302 班 · 第3章 栈与队列 阶段学情报告', scope: '班级 / 章节', period: '2026-07-05 ~ 2026-07-18', createdAt: '2026-07-18 11:05', creator: '李文博', status: 'archived', pages: 9 }
  ];

  const reportDetail = {
    reportId: 'RP20260828001',
    title: '计算机 2301 班 · 第5章「图」阶段学情分析报告',
    meta: { className: '计算机 2301 班', studentCount: 42, chapter: '第5章 图', period: '2026-08-15 ~ 2026-08-28', generatedAt: '2026-08-28 10:20', generator: 'AI 学情分析引擎 v1.4' },
    sections: [
      {
        title: '一、整体掌握度',
        paragraphs: ['本阶段班级共覆盖 6 个知识点，平均知识点完成率 68.4%，平均掌握率 76.1%，能力目标达成度 72.3%。相较第4章，完成率提升 4.2 个百分点，掌握率小幅下降 1.3 个百分点，主要受「最短路径」与「最小生成树」两个高难度知识点拉低影响。'],
        bullets: ['达标（掌握率 ≥ 80%）知识点 2 个：图的定义与术语、图的遍历', '待加强（60%~80%）知识点 2 个：图的存储结构、最小生成树', '薄弱（< 60%）知识点 2 个：最短路径 Dijkstra（50.3%）、哈夫曼树与编码（58.3%）']
      },
      {
        title: '二、共性短板与归因',
        paragraphs: ['系统对本阶段 240 条错题记录执行聚类与归因分析，识别出 4 类主要成因，其中「前置知识缺失」占比最高（42%）。'],
        bullets: ['前置知识缺失（42%）：邻接矩阵/邻接表适用场景区分不清，直接导致 Dijkstra 实现选型错误', '算法流程未内化（31%）：手工模拟题正确率 38%，显著低于选择题 62%', '难度梯度过陡（18%）：4-5 星题占比 61%，缺少 2-3 星过渡题', '练习量不足（9%）：9 名学生本章练习量 < 10 题']
      },
      {
        title: '三、个体预警情况',
        paragraphs: ['本阶段共触发 9 条预警，涉及 6 名学生，其中红色预警 3 条、黄色预警 6 条，全部已完成人工复核。'],
        bullets: ['红色：陈思远（Dijkstra 41%）、赵梓涵（滞后 12 学时）、徐子墨（错题集中）', '黄色：吴嘉豪、林浩然、周雨桐（掌握率下滑 / 时长不足 / 进度滞后）', '预警平均触达时长 3.2 分钟，满足分钟级实时性要求']
      },
      {
        title: '四、干预效果验证',
        paragraphs: ['本阶段执行 4 项干预措施，其中 2 项已完成效果验证。以「循环队列判空判满」补救干预为例，干预组 7 日内掌握率由 52.0% 提升至 71.4%（+19.4pp），同期对照组仅提升 5.8pp，干预有效性显著。'],
        bullets: ['已完成 2 项：循环队列补救（+19.4pp）、哈夫曼树 WPL 专项（+10.8pp，进行中）', '待确认 2 项：Dijkstra 集体干预、赵梓涵个体干预', '策略库新增有效模板 1 个：错题簇集中歼灭法（成功率 85%）']
      },
      {
        title: '五、能力目标达成度',
        paragraphs: ['基于目标图谱，本章支撑「掌握图结构的表示与经典算法」单元目标，当前达成度 55.8%，低于 80% 基线，需在后续教学中重点补强。'],
        bullets: ['G3-1 能选择合适的图存储结构：63.0%（待加强）', 'G3-2 能实现 DFS/BFS 并解决连通性问题：70.0%（待加强）', 'G3-3 能应用最短路径与最小生成树算法：45.5%（薄弱，需重点干预）']
      },
      {
        title: '六、下阶段教学建议',
        paragraphs: [],
        bullets: ['课堂：用 5 分钟对比表重讲两种图存储结构，插入 10 分钟集体手工模拟', '资源：推送 2 个补救微课，重构本章难度阶梯（AI 补充 10 道 2-3 星题）', '干预：确认执行 Dijkstra 集体干预方案，对 3 名红色预警学生实施一对一跟踪', '复测：9 月 3 日安排第5章限时复测，验证干预有效性']
      }
    ]
  };

  /* ---------------- 通知（教师私信学生） ---------------- */
  const messages = [
    { msgId: 'MSG001', from: '李文博（教师）', to: '陈思远', title: '关于 Dijkstra 算法的学习建议', content: '我看到你在 Dijkstra 上遇到困难。建议先把「图的存储结构」补齐，再看那个 8 分钟的负权边微课。周四下午我在办公室，可以来找我当面推一遍手工模拟。', time: '2026-08-28 10:35', read: false },
    { msgId: 'MSG002', from: '系统', to: '陈思远', title: '第5章复测通知', content: '9 月 3 日 14:00 将进行第5章限时复测，共 20 题，限时 40 分钟。', time: '2026-08-28 08:00', read: true }
  ];

  return {
    course, student, teacher,
    studentDashboard, knowledgeGraph, problemGraph, goalGraph, kpDetail,
    learningPath, resources,
    teachingMethods, chatHistory, chatMessages,
    practiceModes, practiceQuestions, practiceReport, wrongBook, wrongDetail,
    masteryMatrix, abilityRadar, growthTrack, classCompare, studentAlerts,
    teacherDashboard, heatmap, students, studentProfile, teacherAlerts,
    errorAnalysis, genConfig, generatedQuestions, questionBank,
    interventions, interventionEffect, strategyTemplates,
    reportList, reportDetail, messages
  };
})();
