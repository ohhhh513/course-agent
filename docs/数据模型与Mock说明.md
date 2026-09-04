# 数据模型与 Mock 说明

> 适用对象：后端开发者（实现接口返回结构）、前端维护者。
> 核心原则：**`assets/js/mock/data.js` 的每个数据对象的字段，与 `接口文档.md` 中各接口 `response.data` 字段严格一致**。后端实现真实接口时，返回 JSON 的 `data` 字段结构必须与本文档 / mock 一致，前端即可零改动切换。

---

## 1. Mock 数据集总览

文件：`assets/js/mock/data.js`，以 `window.MOCK` 暴露。共 45 个顶层键，按业务模块划分如下（每个键即对应一个或多个接口的 `data` 来源）：

### 1.1 课程与用户
| Mock 键 | 服务接口 | 说明 |
| --- | --- | --- |
| `course` | `GET /course/{courseId}` | 课程基本信息 |
| `student` | `GET /auth/profile`（student 兜底） | 当前学生档案 |
| `teacher` | `GET /auth/profile`（teacher 兜底） | 当前教师档案（含 classes） |

### 1.2 学生端
| Mock 键 | 服务接口 | 说明 |
| --- | --- | --- |
| `studentDashboard` | `GET /student/dashboard` | 学习驾驶舱聚合 |
| `knowledgeGraph` | `GET /graph?type=knowledge` | 知识图谱 |
| `problemGraph` | `GET /graph?type=problem` | 问题图谱 |
| `goalGraph` | `GET /graph?type=goal` | 目标图谱 |
| `kpDetail` | `GET /graph/kp/{kpId}` | 知识点详情（按 kpId 索引） |
| `learningPath` | `GET /graph/path` | 推荐学习路径 |
| `resources` | `GET /student/resources` | 资源中心列表 |
| `masteryMatrix` | `GET /student/mastery/matrix` | 掌握矩阵（按章分组） |
| `abilityRadar` | `GET /student/ability/radar` | 能力雷达 |
| `growthTrack` | `GET /student/growth` | 成长轨迹 |
| `classCompare` | `GET /student/compare` | 班级对比 |
| `studentAlerts` | `GET /student/alerts` | 我的预警 |
| `messages` | `GET /student/messages` | 私信 / 系统通知 |
| `practiceModes` | `GET /practice/modes` | 练习模式 |
| `practiceQuestions` | `GET /practice/sessions/{id}/questions`、`POST /practice/answers` | 题库样本 |
| `practiceReport` | `POST /practice/sessions/{id}/finish` | 练习报告 |
| `wrongBook` | `GET /practice/wrong-book` | 错题本 |
| `wrongDetail` | `GET /practice/wrong-book/{qId}/detail` | 错题详情 |

### 1.3 AI 答疑
| Mock 键 | 服务接口 | 说明 |
| --- | --- | --- |
| `teachingMethods` | `GET /ai/methods` | 教学法列表 |
| `chatHistory` | `GET /ai/sessions` | 历史会话列表 |
| `chatMessages` | `GET /ai/sessions/{id}/messages` | 会话消息（含 citations） |
| `studentDashboard.suggestedQuestions` | `GET /ai/suggest-questions` | 猜你想问 |

### 1.4 教师端
| Mock 键 | 服务接口 | 说明 |
| --- | --- | --- |
| `teacherDashboard` | `GET /teacher/dashboard` | 教学驾驶舱 |
| `heatmap` | `GET /teacher/heatmap` | 掌握热力图 |
| `students` | `GET /teacher/students` | 学生列表 |
| `studentProfile` | `GET /teacher/students/{userId}/profile` | 个体学情 |
| `teacherAlerts` | `GET /teacher/alerts` | 预警列表 |
| `errorAnalysis` | `GET /analysis/errors`（`weakChain`/`causes` 为其子结构） | 错题与归因 |
| `genConfig` | `GET /question/gen/config` | 出题配置 |
| `generatedQuestions` | `POST /question/gen` | 生成题样本 |
| `questionBank` | `GET /question/bank` | 题库 |
| `interventions` | `GET /intervention/list` | 干预建议 |
| `interventionEffect` | `GET /intervention/{id}/effect` | 干预前后对比 |
| `strategyTemplates` | `GET /intervention/templates` | 策略库模板 |
| `reportList` | `GET /report/list` | 报告归档 |
| `reportDetail` | `GET /report/{id}`、`POST /report/generate` | 报告详情 |

---

## 2. 核心实体字段定义

> 以下为前端强依赖的字段。完整字段以 `mock/data.js` 实际对象为准；后端可增字段，不可缺下列字段（或提供等价兜底）。

### 2.1 User（用户）
见 `鉴权与会话方案.md` §5。登录 / profile 返回。

### 2.2 Course（课程）
```js
{ courseId, name, code, term, teacher, credit,
  chapters, knowledgePoints, resources, questions }
```

### 2.3 Graph / GraphNode / GraphLink（三大图谱）
```js
Graph = {
  graphType: 'knowledge'|'problem'|'goal',
  categories: [ { name, color } ],           // 节点分类与配色
  nodes: [ {
    id, name,
    chapter?,                                 // 章节（知识图谱有）
    category,                                // 对应 categories 下标
    mastery,                                 // 0~100 掌握率
    difficulty,                              // 1~5 难度
    isKey,                                   // 是否重难点
    hours                                    // 建议学时
  } ],
  links: [ { source, target, relation } ]    // relation: pre|advance|parallel|split|map|error|support
}
```

### 2.4 KpDetail（知识点详情）
```js
{ name, summary, completionRate, masteryRate, classAvgMastery,
  resources: [ { type, title, duration?, pages?, progress } ],
  relatedProblems: [ { qId, title, errorRate, mastery } ] }
```

### 2.5 LearningPath（推荐路径）
```js
[ { step, name, status:'done|doing|todo|warn', hours, resCount, mastery, progress, locked } ]
```

### 2.6 Dashboard（驾驶舱）
学生 `studentDashboard`：
```js
{ overview: { courseProgress, currentNode:{kpId,name}, streakDays, streakHistory:[0~4...],
              currentStreak, maxStreak, totalDays, todayStudyMinutes, status:'ok|warn|danger' },
  coreMetrics: { completionRate, masteryRate, goalAchieveRate, updatedAt },
  todos: [ { id, type, level, title, desc, action, target, kpId? } ],
  weakPoints: [ { kpId, name, masteryRate, chapter, errorCount, trend, level } ],
  suggestedQuestions: [ string ],
  recentActivities: [ { id, type, title, meta, time, level } ] }
```
教师 `teacherDashboard`：
```js
{ classOverview:{...}, liveFeed:[...], todos:[...], kpRanking:[...] }
```

### 2.7 StudentOverview / Heatmap
```js
Heatmap = {
  kpAxis: [ { kpId, name } ],
  studentAxis: [ { userId, name } ],
  data: [ [ kpIndex, studentIndex, masteryRate ] ],   // 三元组
  weakest: [ { kpId, name, avgMastery } ] }
```

### 2.8 Alert（预警）
```js
{ alertId, level:'red|yellow|green', student, kp, type,
  trigger, trendData:[...], status:'open|reviewed|ignored' }
```

### 2.9 StudentProfile（个体学情）
```js
{ user:{...}, portrait:{...}, schedule:[...], activity:[...],
  answerDetail:[...], freqWrong:[...] }
```

### 2.10 Question（习题 / 生成题）
```js
GeneratedQuestion = {
  qId, type, difficulty, status:'pending|approved|published|archived',
  stem, options:[...], analysis,
  kpPath:[...], preKp:[...], postKp:[...],          // 知识点定位树 / 前后置
  isKey, sourceRef:{ fileId, locator }, estimatedCorrectRate }
```

### 2.11 Intervention（干预）
```js
{ ivId, status:'pending|running|done', level, scope:'common|individual',
  title, target, reason, steps:[...], expectEffect, execution? }
```

### 2.12 ReportSection（报告章节）
```js
{ title, paragraphs:[...], bullets:[...] }
```
报告整体：`{ reportId, status, detail:{ title, sections:[ ReportSection ] } }`

---

## 3. 前端强依赖的关键字段路径（后端务必提供）

下列路径在前端渲染中被直接读取，缺失会导致页面异常：

| 页面 / 视图 | 必填字段路径 |
| --- | --- |
| 学生驾驶舱 | `overview.coreMetrics.*`、`todos[]`、`weakPoints[]`、`streakHistory` |
| 三图谱 | `categories[]`、`nodes[].{id,name,mastery,category,isKey}`、`links[].{source,target,relation}` |
| 资源中心 | `list[].{resId,title,type,kp,views,progress,duration?\|pages?\|count?}` |
| AI 答疑 | `content`（HTML 串）、`citations[]`、`outOfScope`、`messageId` |
| 智能练习 | `questions[].{qId,type,stem,options,answer,analysis}`、`practiceReport` |
| 我的学情 | `masteryMatrix`、`abilityRadar`、`growthTrack`、`classCompare` |
| 预警中心 | `studentAlerts[].{alertId,level,student,kp,type,status}` |
| 教学驾驶舱 | `teacherDashboard.classOverview`、`liveFeed`、`todos`、`kpRanking` |
| 学情监测看板 | `heatmap.{kpAxis,studentAxis,data,weakeSt}`、`students[]`、`studentProfile` |
| 归因分析 | `errorAnalysis.{errorTypes?,highFreq,weakChain,causes}` |
| AI 出题 | `genConfig`、`generatedQuestions[]`、`questionBank[]` |
| 教学干预 | `interventions[]`、`interventionEffect`、`strategyTemplates[]` |
| 学情报告 | `reportList[]`、`reportDetail.sections[]` |

---

## 4. 枚举与格式约定

| 类别 | 取值 |
| --- | --- |
| `role` | `student` / `teacher` |
| 图谱 `graphType` | `knowledge` / `problem` / `goal` |
| 图谱 `relation` | `pre`(前置) / `advance`(进阶) / `parallel`(并行) / `split`(拆分) / `map`(映射) / `error`(易错) / `support`(支撑) |
| 预警 `level` | `red`(紧急) / `yellow`(关注) / `green`(正常) |
| 预警 `status` | `open` / `reviewed` / `ignored` |
| 干预 `status` | `pending` / `running` / `done` |
| 干预 `scope` | `common`(共性) / `individual`(个性) |
| 习题 `status` | `pending` / `approved` / `published` / `archived` |
| 资源 `type` | `video` / `ppt` / `doc` / `quiz` |
| 时间 | ISO 或 `'YYYY-MM-DD HH:mm'` 字符串 |
| 百分比 | 数值 0~100（非字符串 `"62%"`） |
| 颜色 | CSS 颜色字符串（`#22c55e` 或 `linear-gradient(...)`） |

---

## 5. 联调提示

1. **字段对齐优先于接口数量**：后端不必一次实现全部 60+ 接口，但已实现的接口返回结构必须与本文档一致。
2. **数组字段**：列表类接口统一返回 `{ total, list:[...] }` 结构（见 `接口文档.md` 各列表接口）。
3. **AI 答疑 mock 为关键词命中**：`mockAnswer()` 仅对「遍历 / 负权 Dijkstra / 循环队列 / 哈夫曼」四类问题返回带 citations 的答案，其余返回 `outOfScope:true` 降级文案。真实环境由后端大模型 + 检索生成。
4. **AI 出题 mock 为预设题**：`generatedQuestions` 是写死的样本；真实环境由后端调用大模型按素材/知识点生成，并回填 `kpPath/preKp/postKp/sourceRef` 等溯源字段。
