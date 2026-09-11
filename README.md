[README.md](https://github.com/user-attachments/files/32092659/README.md)
# 基于 Python 的社区团购智能选品与销量预测系统

>
> 一个面向社区团购场景的 B/S 架构管理系统：在传统商城功能之上，引入**随机森林销量预测**与**多维度智能选品评分**，帮助社区团长解决"选什么品、备多少货、什么时候补货"三类核心决策问题。

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.3-000000?logo=flask&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-5.7%2B-4479A1?logo=mysql&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-RandomForest-F7931E?logo=scikitlearn&logoColor=white)

---

## 目录

- [一、项目背景](#一项目背景)
- [二、功能特性](#二功能特性)
- [三、技术栈](#三技术栈)
- [四、系统架构](#四系统架构)
- [五、目录结构](#五目录结构)
- [六、核心算法设计](#六核心算法设计)
- [七、数据库设计](#七数据库设计)
- [八、快速开始](#八快速开始)
- [九、接口一览](#九接口一览)
- [十、项目亮点](#十项目亮点)
- [十一、已知问题与后续优化](#十一已知问题与后续优化)

---

## 一、项目背景

社区团购以"预售 + 自提"为核心模式，由社区团长负责选品、囤货与配送。相比传统电商，团长面临三个更尖锐的问题：

| 痛点 | 具体表现 | 本系统的解决思路 |
| --- | --- | --- |
| **选品靠经验** | 凭感觉上架，缺乏数据依据，容易压货 | 五维度加权推荐分（0–100）对在售商品统一打分排序 |
| **备货靠预估** | 备少了断货、备多了积压资金 | 随机森林回归预测未来 7 天销量，并结合安全库存给出建议采购量 |
| **库存无人管** | 滞销商品长期占用库存，缺货商品发现太晚 | 滞销预警（四级风险）+ 补货优先级（四级紧急度）自动巡检 |

系统把"**预测 → 评分 → 决策 → 采购 → 入库**"串成闭环，团长在智能选品页面上勾选商品即可一键生成采购订单，支付后库存自动回写。

---

## 二、功能特性

### 1. 用户端（前台商城）

- **账号体系**：注册、登录、登出、个人资料、头像上传、修改密码
- **商品浏览**：首页、分类、商品列表、商品详情、热销/新品专区、商品评价查看
- **交易链路**：购物车管理 → 收货地址管理 → 下单结算 → 支付 → 物流跟踪 → 确认收货 → 订单评价
- **订单操作**：取消申请、退货/退款申请、退款进度查询、撤销退款
- **互动与服务**：平台公告、投诉与申诉、与团长在线沟通

### 2. 社区团长工作台（供应商端）

- **商品管理**：商品上下架、批量操作、库存与进价维护
- **订单管理**：发货、物流录入、订单状态流转、取消申请审批
- **销售分析**：销售概览、销售趋势、商品销量排行、品类销售占比、顾客评价分析、库存预警
- **智能选品中心** ⭐：商品推荐、滞销预警、补货优先级、季节性推荐、一键批量采购
- **采购管理**：采购订单列表、明细调整、确认、支付入库、取消、删除
- **售后处理**：退款申请审批

### 3. 平台运营 / 管理后台

- **系统管理**：用户管理、团长（供应商）入驻审核、系统配置、公告发布、投诉处理
- **数据分析看板**：市场概览、价格趋势、热门商品、分类分布、销售趋势、库存与价格预警、需求预测、商品关联分析、区域销售分布、商品价格区间分析、用户评价汇总、品类竞争格局
- **运营报表**：平台运营数据汇总

### 4. 智能选品（核心模块）

对应页面：`/admin/supplier/smart-selection.html`，接口前缀 `/api/smart-selection`

| 功能 | 说明 |
| --- | --- |
| **商品推荐** | 对候选商品计算五维度综合推荐分（0–100），按分排序；**推荐分 ≥ 60 的商品在前端自动预勾选**，团长只需确认数量即可下单 |
| **滞销预警** | 通过**周转天数**与**动销天数**双维度评估，输出 `high / medium / low / normal` 四级风险，并给出"促销清仓 / 降价捆绑 / 持续观察"等可执行建议 |
| **补货优先级** | 依据**可售天数**（库存 ÷ 日均预测销量）划分「紧急 / 较高 / 一般 / 暂不需补货」四级 |
| **季节性推荐** | 基于当前月份的历史热销数据，推荐应季商品（自动排除团长已在售的商品） |
| **一键采购** | 勾选商品直接生成采购订单（按**进价**计算），走"草稿 → 确认 → 支付入库"流程 |
| **滞销打折** | 可为滞销商品设置折扣率（0–1），存储于 `py_supplier_discount` 表 |
| **库存健康度** | 环形图展示「健康 / 积压 / 缺货」商品结构占比 |

### 5. 销量预测（核心模块）

对应页面：`/admin/supplier/sales-analytics.html`，接口前缀 `/api/analytics/forecast/sales`

- **模型**：`RandomForestRegressor` 随机森林回归
- **预测粒度**：商品 × 日期，支持**全平台**与**单个社区团长**两种数据范围
- **预测步长**：默认未来 7 天（可传参调整），采用**递归预测**策略
- **产出**：每日总销量曲线、商品预测销量、建议采购量、安全库存、库存风险等级、RMSE / MAE / MAPE / R² 评估指标
- **工程化**：模型自动训练并持久化为 `.pkl`；预测结果内存 + 磁盘二级缓存，避免重复计算

### 6. 采购与退款闭环

- **采购订单**：状态机 `draft → confirmed → paid`（或 `cancelled`），仅草稿态可调整明细，仅已支付/已取消态可删除
- **支付即入库**：支付成功后自动将采购数量累加到商品库存（`py_product.stock`）
- **退款退货**：用户提交退款（`pending`）→ 管理员审核（`approved` / `rejected`）→ 通过后订单置为已取消；支持用户撤销待处理申请

---

## 三、技术栈

| 层次 | 技术选型 |
| --- | --- |
| 后端框架 | Python 3.8+ · Flask 2.3（Blueprint 蓝图分模块） |
| 数据库 | MySQL 5.7+ · PyMySQL（`DictCursor` 字典游标） |
| 数据分析 / 机器学习 | pandas · NumPy · scikit-learn（`RandomForestRegressor`） |
| 模型持久化 | pickle（`Predictive/artifacts/*.pkl`） |
| 前端 | Vue 2 · Element UI · ECharts · ApexCharts · jQuery · Axios（静态资源引入，无需构建） |
| 模板引擎 | Jinja2 + Flask 静态页面分发（`/front`、`/admin` 双入口） |
| 鉴权 | Flask Session + 自定义 `@login_required` 装饰器 + 数据范围隔离 |

> 依赖说明：仓库未包含 `requirements.txt`，完整依赖清单见[第八章](#八快速开始)。

---

## 四、系统架构

采用经典四层结构，上层只依赖下层，层间通过普通 Python 函数调用（不引入额外 ORM）：

```
┌──────────────────────────────────────────────────────────┐
│  浏览器（Vue 2 + Element UI + ECharts / ApexCharts）      │
│  前台 /front/**   后台 /admin/**   登录 /login            │
└───────────────────────────┬──────────────────────────────┘
                            │ HTTP / JSON（Axios）
┌───────────────────────────▼──────────────────────────────┐
│  控制器层 controller/**            （19 个 Blueprint）     │
│  · 路由与参数解析   · 登录态与角色校验   · 统一 JSON 包装   │
└───────────────────────────┬──────────────────────────────┘
┌───────────────────────────▼──────────────────────────────┐
│  服务层 service/**                                        │
│  · 业务规则与状态机   · SQL 查询   · 机器学习推理与训练     │
│  · sales_forecast_service（销量预测）                      │
│  · smart_selection_service（智能选品，依赖预测服务）        │
│  · purchase_service（采购） / mall/refund_service（退款）   │
└───────────────────────────┬──────────────────────────────┘
┌───────────────────────────▼──────────────────────────────┐
│  数据模型层 model/**  与  工具层 utils/**                  │
│  · model/mall/*：商品/订单/购物车/分类的 SQL 封装          │
│  · db_utils（连接与执行）· response（统一响应）             │
│  · auth_utils（鉴权）· data_scope（数据范围）· file_utils  │
└───────────────────────────┬──────────────────────────────┘
                            │ PyMySQL
                     ┌──────▼──────┐
                     │  MySQL 5.7  │
                     └─────────────┘
```

**统一响应格式**（`utils/response.py`）：

```jsonc
// 普通接口
{ "code": 200, "message": "OK", "data": { } }
// 分页接口
{ "code": 200, "message": "OK",
  "data": { "total": 100, "page": 1, "limit": 10, "rows": [ ] } }
```

**角色与数据范围**（`utils/data_scope.py`）：

| 角色标识 | 中文含义 | 数据范围 |
| --- | --- | --- |
| `system_admin` | 系统管理员 | 全平台 |
| `platform_operator` | 平台运营者 | 全平台 |
| `admin` | 管理员 | 分析接口按全平台处理 |
| `community_leader` / `supplier` | 社区团长 | 仅本社区（`supplierId` 隔离） |
| `user` | 普通用户 | 仅本人数据 |

> 说明：`data_scope` 的 `ROLE_DATA_SCOPE` 映射中只登记了 `system_admin`、`platform_operator`、`community_leader`、`user` 四个角色，未登记的角色会回退为「仅本人数据」；而分析接口的角色白名单中额外包含 `admin`。两者存在细微差异，详见[已知问题](#十一已知问题与后续优化)。

---

## 五、目录结构

```
code/
├── app.py                          # 应用入口：创建 Flask、注册蓝图、页面路由分发
├── config/
│   └── config.py                   # 数据库/上传/会话配置
├── controller/                     # 控制器层（路由）
│   ├── auth_controller.py          #   登录注册
│   ├── user_controller.py          #   用户管理
│   ├── admin_controller.py         #   平台管理 · 团长审核
│   ├── analytics_controller.py     #   数据分析 + 销量预测接口
│   ├── smart_selection_controller.py  # 智能选品接口
│   ├── purchase_controller.py      #   采购订单接口
│   ├── supplier_controller.py      #   团长工作台
│   ├── complaint_controller.py     #   投诉申诉
│   ├── announcement_controller.py  #   公告
│   ├── dashboard_controller.py     #   后台首页统计
│   ├── upload_controller.py        #   文件上传
│   └── mall/                       #   商城模块：商品/分类/购物车/订单/地址/沟通/退款/行为
├── service/                        # 服务层（业务逻辑）
│   ├── sales_forecast_service.py   # ⭐ 销量预测引擎（随机森林 + 特征工程 + 递归预测）
│   ├── smart_selection_service.py  # ⭐ 智能选品引擎（五维评分 + 滞销 + 补货 + 季节性）
│   ├── purchase_service.py         #   采购订单状态机
│   ├── analytics_service.py        #   平台/团长数据分析（19 个分析方法）
│   ├── analytics_service_fixed.py  #   分析服务的子类补丁（空数据回退修正）
│   ├── hdfs_service.py             #   数据同步到 HDFS 的容错层（预留，当前未被业务引用）
│   ├── auth_service.py / user_service.py / admin_service.py / supplier_service.py
│   └── mall/                       #   商品/订单/退款/行为等服务
├── model/mall/                     # 数据模型层：商品/订单/购物车/分类的 SQL 封装
├── utils/
│   ├── db_utils.py                 # 连接与查询/更新/插入/删除封装
│   ├── response.py                 # 统一响应格式（success / error / page_response）
│   ├── auth_utils.py               # @login_required 等鉴权装饰器
│   ├── data_scope.py               # 基于角色的数据范围隔离
│   └── file_utils.py
├── Predictive/artifacts/           # 模型与预测缓存产物（*.pkl）
├── sql/
│   ├── 0_80421shequtuangou.sql     # 基础库结构与初始数据
│   ├── add_warehouse_purchase.sql  # 采购/仓库/折扣表
│   └── add_cost_price_column.sql   # 商品进价字段
├── scripts/                        # 数据准备脚本
│   ├── adjust_data.py              #   调整商品与订单，使数据更贴近真实社区团购
│   ├── boost_data.py               #   增加销量差异化与热门商品
│   └── set_cost_price.py           #   批量设置进价（售价 × 4/5）
├── insert_historical_data.py       # 生成 2026-01-01 ~ 2026-04-30 历史订单（三种销量模式）
├── static/                         # 前端静态资源（js/css/font/banner/image/picture）
├── templates/
│   ├── login.html / register.html
│   ├── front/                      # 用户端页面（含 mall/ 商城子页）
│   └── admin/                      # 管理后台 + supplier/ 团长工作台页面
└── upload/                         # 用户上传文件
```

---

## 六、核心算法设计

### 6.1 销量预测模型

**实现位置**：`service/sales_forecast_service.py`

#### ① 数据集构建

从数据库拉取**已支付及之后状态**的订单（`paid / shipped / delivered / completed`），按「商品 × 日期」展开为完整日历数据集，并对无销量日期补 0，避免时间序列断点。

#### ② 特征工程（共 30 维）

| 特征类别 | 维度 | 特征 |
| --- | --- | --- |
| 商品基础 | 5 | `product_id`、`supplier_id`、`category_id`、`price`、`stock` |
| 商品标签 | 3 | `is_hot`、`is_new`、`discount_rate` |
| 时间特征 | 7 | `day_of_week`、`day_of_month`、`month`、`season`、`is_weekend`、`is_holiday`、`has_promotion` |
| 促销特征 | 2 | `order_discount_rate`、`promotion_strength`（商品折扣率与订单折扣率取大） |
| 滞后特征 | 4 | `lag_1`、`lag_3`、`lag_7`、`lag_14` |
| 滚动统计 | 5 | `rolling_mean_3`、`rolling_mean_7`、`rolling_mean_14`、`rolling_sum_14`、`rolling_max_7` |
| 周期特征 | 1 | `dow_avg`（该商品"星期几"历史均值，样本 < 7 天时回退到商品整体均值） |
| 节奏特征 | 2 | `recent_sale_7d`（近 7 天是否动销）、`days_since_sale`（距上次销售天数，上限 60） |
| 品类特征 | 1 | `cat_daily_avg`（同品类同日日均销量） |

> **防数据泄露**：所有滞后与滚动特征均使用 `shift(1)` 排除当天数据。

节假日特征依据内置的 `CHINA_HOLIDAY_MMDD` 集合（元旦、情人节、妇女节、劳动节、儿童节、国庆、双十一、双十二、圣诞）匹配月-日生成。

#### ③ 模型与超参数

```python
RandomForestRegressor(
    n_estimators=350,      # 350 棵决策树
    max_depth=7,           # 限制树深，防止过拟合
    min_samples_leaf=4,    # 叶节点最少 4 个样本
    min_samples_split=5,   # 节点分裂最少 5 个样本
    max_features="sqrt",   # 每棵树随机选取 sqrt(特征数) 个特征
    random_state=42,       # 固定随机种子，结果可复现
    n_jobs=-1,             # 启用全部 CPU 核心
)
```

预测值统一做非负截断（`np.clip(..., a_min=0)`）。

#### ④ 训练 / 测试划分

按**时间顺序**划分（非随机划分，避免未来信息泄露）：取最后 `test_days`（默认 14 天）为测试集，其余为训练集；测试集天数自适应，最多不超过总天数的 1/3（至少保留 1–2 天测试样本）；数据不足 5 个不同日期时不训练，直接返回提示。

#### ⑤ 评估指标

| 指标 | 含义 |
| --- | --- |
| RMSE | 均方根误差，对大偏差敏感 |
| MAE | 平均绝对误差，量纲与销量一致 |
| MAPE | 平均绝对百分比误差（实际值为 0 时分母取 1） |
| R² | 决定系数，衡量模型对销量方差的解释能力 |

#### ⑥ 递归多步预测

先预测第 1 天，把预测值回填为新的滞后/滚动特征，再预测第 2 天，依次递推至未来 N 天。训练数据与预测起始日之间的空缺日期（bridge）会先补齐，保证滞后特征连续。

#### ⑦ 采购决策输出

```
安全库存 = ceil(预测销量 × 0.15)          # SAFETY_STOCK_RATE = 15%
目标库存 = 预测销量 + 安全库存
建议采购量 = max(目标库存 − 当前库存, 0)
库存风险等级：库存 / 目标库存 < 0.5 → high ；< 1.0 → medium ；否则 low
```

#### ⑧ 模型产物与缓存

- 模型 + 历史数据 + 特征列 + 指标打包为 artifact，持久化为
  `Predictive/artifacts/platform_sales_forecast.pkl`（全平台）或 `supplier_{id}_sales_forecast.pkl`（单团长）
- 文件不存在或特征列版本不匹配时**自动触发训练**
- 预测结果走「内存缓存 → 磁盘缓存（`pred_*.pkl`）→ 重新计算」三级策略，缓存键含数据范围、训练时间、预测天数与预测起始日

### 6.2 智能选品推荐分（五维度加权模型）

**实现位置**：`service/smart_selection_service.py` → `_compute_recommendation_score`

```
推荐分(0–100) = 预测销量得分(35) + 历史销量得分(20)
              + 库存健康得分(20) + 价格系数得分(15) + 热度加分(10)
```

| 维度 | 满分 | 计算规则 | 设计意图 |
| --- | --- | --- | --- |
| ① 预测销量 | **35** | `35 × (该商品预测销量 ÷ 候选集最大预测销量)`，保留 1 位小数 | 权重最高，直接采用机器学习预测结果，代表未来销售潜力 |
| ② 历史销量 | **20** | `20 × (该商品累计销量 ÷ 候选集最大销量)` | 验证市场认可度，与预测形成"历史 + 未来"双重验证 |
| ③ 库存健康 | **20** | 见下方分档 | 评估"可销售性"，库存过少无法卖、过多占用资金 |
| ④ 价格系数 | **15** | 见下方分档 | 利润空间 = `(原价 − 现价) ÷ 原价`，空间越大团长促销余地越大 |
| ⑤ 热度加分 | **10** | `isHot` 加 5 分，`isNew` 加 5 分 | 平台已认证的热销品与正在推广的新品 |

**库存健康分档**：

| 库存区间 | 得分 | 含义 |
| --- | --- | --- |
| ≤ 0 | 0 | 无货可卖 |
| 1 – 9 | 5 | 严重不足 |
| 10 – 49 | 15 | 偏少但可用 |
| **50 – 199** | **20** | 最佳区间 |
| 200 – 499 | 15 | 偏多 |
| 500 – 999 | 10 | 积压趋势 |
| ≥ 1000 | 5 | 严重积压 |

**价格系数分档**：

| 利润空间 | 得分 |
| --- | --- |
| ≥ 30% | 15 |
| ≥ 15% | 12 |
| ≥ 5% | 8 |
| < 5%（微利或倒挂） | 5 |
| 无法计算（缺原价） | 5 |

最终得分封顶 100 分；**推荐分 ≥ 60 的商品在前端自动预勾选**——这是系统给出的"值得进"的直接结论。

归一化采用 Min-Max（除以候选集最大值），保证不同销量量级的商品之间分数可比。

### 6.3 滞销预警（双维度四级评估）

| 判定条件 | 风险等级 | 前端标签 | 处理建议 |
| --- | --- | --- | --- |
| 周转天数 > 14 **或** 动销天数 > 60 | `high` | 红 | 周转 > 14：建议立即促销清仓或下架；否则建议降价促销加快周转 |
| 周转天数 > 7 **或** 动销天数 > 30 | `medium` | 橙 | 建议适当降价或捆绑销售 |
| 周转天数 > 5 | `low` | 蓝 | 建议关注，提前备货 |
| 周转天数 ≤ 5 | `normal` | 绿 | 正常，持续观察 |

- **周转天数** = 库存 ÷ 日均销量，其中日均销量取「近 90 天该商品销量合计 ÷ 30」；日均销量为 0 时周转天数按 999 处理
- **动销天数** = 距最近一次销售的天数（近 90 天无销售记录时按 999 处理）

### 6.4 补货优先级（可售天数四级）

**可售天数 = 当前库存 ÷ 日均预测销量**

| 条件 | 级别 | 标签 |
| --- | --- | --- |
| 可售天数 < 3 **且** 有销量 | 1 | 🔴 紧急 |
| 可售天数 < 7 **且** 日均销量 > 0 | 2 | 🟠 较高 |
| 可售天数 < 14 | 3 | 🟡 一般 |
| 可售天数 ≥ 14 | 4 | 🟢 暂不需补货 |

> 设计要点：无任何销量数据的商品（新品或彻底滞销品）即使库存很少也**不会**被判为紧急，避免误报。

### 6.5 季节性推荐

按当前月份统计历史订单中各商品的销量与订单数，取当月有成交记录、且**团长尚未在售**的商品，按当月销量降序推荐，并标注"{当前月份}应季推荐"。

### 6.6 库存健康度

```
健康商品数   = 在售商品总数 − 积压商品数 − 缺货商品数
积压商品数   = 滞销预警中 riskLevel = high 的数量
缺货商品数   = 补货优先级中 level ≤ 2（紧急 + 较高）的数量
```

用于看板环形图，直观呈现库存结构。

---

## 七、数据库设计

数据库名：`shequtuangou`（与 `config/config.py` 中 `DB_CONFIG['database']` 保持一致）

### 基础表（12 张，来自 `sql/0_80421shequtuangou.sql`）

| 表名 | 说明 |
| --- | --- |
| `py_user` | 用户表（含 5 种角色、团长资质与审核状态字段） |
| `py_product` | 商品表（售价、库存、销量、热销/新品标记、所属团长） |
| `py_category` | 商品分类 |
| `py_order` | 订单主表（状态：`pending / paid / shipped / delivered / completed / cancelled / cancel_requested`） |
| `py_order_item` | 订单明细（数量、金额、评价评分） |
| `py_cart` | 购物车 |
| `py_address` | 收货地址 |
| `py_community` | 社区信息 |
| `py_announcements` | 平台公告 |
| `py_complaint` | 投诉与申诉 |
| `py_customer_communication` | 团长与顾客沟通记录 |
| `py_user_browse_history` | 用户浏览行为（用于热度与兴趣度推荐） |

### 追加迁移（需按顺序执行）

| 脚本 | 新增内容 |
| --- | --- |
| `sql/add_warehouse_purchase.sql` | `py_warehouse`（团长仓库/进价）、`py_purchase_order`（采购订单）、`py_purchase_order_item`（采购明细）、`py_supplier_discount`（滞销折扣） |
| `sql/add_cost_price_column.sql` | 为 `py_product` 增加 `costPrice` 进价字段，并初始化为 `售价 × 4/5` |

### ⚠️ 缺失的建表语句

以下两张表在代码中被引用，但仓库内的 SQL 脚本中**没有对应的建表语句**，直接运行会报错，需要手动创建：

| 表名 | 被谁引用 | 代码中涉及的字段 |
| --- | --- | --- |
| `py_refund` | `service/mall/refund_service.py` | `id`、`orderId`、`orderNo`、`userId`、`supplierId`、`refundNo`、`type`、`reason`、`amount`、`description`、`images`、`status`、`adminReply`、`adminId`、`createTime`、`updateTime` |
| `py_product_review_tags` | `service/analytics_service.py`（评价标签词云） | `productId`、`tagName`、`tagCategory`、`tagCount` |

---

## 八、快速开始

### 1. 环境要求

- Python 3.8 – 3.11
- MySQL 5.7 及以上
- 操作系统：Windows / Linux / macOS 均可

### 2. 初始化数据库

```bash
# 1) 创建数据库（字符集必须为 utf8mb4）
mysql -uroot -p -e "CREATE DATABASE shequtuangou DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"

# 2) 导入基础结构与初始数据
mysql -uroot -p shequtuangou < sql/0_80421shequtuangou.sql

# 3) 执行追加迁移（顺序不可颠倒）
mysql -uroot -p shequtuangou < sql/add_warehouse_purchase.sql
mysql -uroot -p shequtuangou < sql/add_cost_price_column.sql
```

> 若数据库名想沿用 SQL 文件名，请同步修改 `config/config.py` 中的 `DB_CONFIG['database']`。

### 3. 安装依赖

仓库未提供 `requirements.txt`，请手动安装。以下版本为项目开发环境所用版本，如遇兼容问题可适当调整：

```bash
pip install Flask==2.3.3 PyMySQL==1.1.0 pandas scikit-learn numpy
```

| 依赖 | 是否必需 | 用途 |
| --- | --- | --- |
| Flask | 必需 | Web 框架 |
| PyMySQL | 必需 | MySQL 驱动 |
| pandas | 必需 | 训练数据集构建与特征工程 |
| numpy | 必需 | 数值计算与指标 |
| scikit-learn | 必需 | 随机森林回归与评估指标 |
| hdfs | 可选 | `service/hdfs_service.py` 的数据同步层（当前未被业务代码引用） |

### 4. 修改配置

编辑 `config/config.py`，按实际环境填写：

```python
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': '123456',        # 改成你的密码
    'database': 'shequtuangou',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}
SECRET_KEY = 'your-secret-key-here'   # 务必改成随机字符串
```

### 5. 准备历史数据（可选）

系统依赖历史订单训练预测模型。若库中数据不足，可运行数据脚本生成带规律的模拟数据：

```bash
python insert_historical_data.py    # 生成 2026-01-01 ~ 2026-04-30 历史订单（三种销量模式）
python scripts/adjust_data.py       # 让商品与订单更贴近真实社区团购
python scripts/boost_data.py        # 增加销量差异化与热门商品
python scripts/set_cost_price.py    # 批量设置进价（售价 × 4/5）
```

### 6. 启动项目

```bash
python app.py
```

启动后访问 **http://127.0.0.1:5001**（应用监听 `0.0.0.0:5001`，`DEBUG` 由 `config.py` 控制）。

### 7. 主要页面入口

| 入口 | 路径 |
| --- | --- |
| 登录 / 注册 | `/login`、`/register` |
| 用户端商城首页 | `/` → `/front/mall/mall.html` |
| 用户端个人中心 | `/front/profile.html` |
| 管理后台首页 | `/admin/index.html` |
| 数据分析看板 | `/admin/data-analytics.html` |
| **智能选品中心** | `/admin/supplier/smart-selection.html` |
| **销量预测分析** | `/admin/supplier/sales-analytics.html` |
| 采购订单管理 | `/admin/supplier/purchase-orders.html` |
| 团长商品管理 | `/admin/supplier/products.html` |

### 8. 初始账号

账号数据位于 `sql/0_80421shequtuangou.sql` 的 `py_user` 表 `INSERT` 语句中，共有 5 类角色：`system_admin`、`platform_operator`、`admin`、`community_leader`、`user`。首次登录请根据角色选择对应后台入口。

### 9. 首次使用销量预测

模型的 `.pkl` 产物已随仓库提供（`Predictive/artifacts/`）。若需要按当前数据重新训练：

```
POST /api/analytics/forecast/sales/train?forecastDays=7&testDays=14
```

或直接调用预测接口——模型文件缺失或特征版本不匹配时会自动训练。

---

## 九、接口一览

所有接口统一返回 `{ code, message, data }`，需登录的接口通过 Session 鉴权。

| 模块 | 前缀 | 说明 |
| --- | --- | --- |
| 认证 | `/api/auth` | 登录、注册、登出、当前用户信息、登录态校验 |
| 用户 | `/api/user` | 用户增删改查、个人资料、改密、重置密码、头像上传 |
| 商品 | `/api/mall/product` | 列表、详情、热销、新品、评价、评价统计、关联推荐、上下架、批量删除 |
| 分类 | `/api/mall/category` | 分类列表、树形结构、增删改查 |
| 购物车 | `/api/mall/cart` | 列表、加购、改数量、删除、清空、数量统计 |
| 订单 | `/api/mall/order` | 下单、支付、收货、取消、取消申请审批、发货、物流、评价、统计、后台列表 |
| 地址 | `/api/mall/address` | 地址增删改查、默认地址设置 |
| 退款 | `/api/mall/refund` | 提交、我的退款、撤销、后台列表、审核 |
| 沟通 | `/api/mall/communication` | 团长与顾客会话、客户列表、购买历史 |
| 行为 | `/api/mall/behavior` | 用户行为统计、浏览历史（热度与兴趣度推荐） |
| 团长 | `/api/supplier` | 经营统计、热销商品、订单趋势、商品与订单列表、权限校验 |
| 采购 | `/api/supplier/purchase` | 采购订单列表、详情、调整、确认、支付、取消、删除 |
| 平台管理 | `/api/admin` | 团长列表、入驻审核与状态管理 |
| 公告 | `/api/announcement` | 前台列表/详情、后台增删改、置顶与状态切换 |
| 投诉 | `/api/complaint` | 提交、我的申诉、评价、关闭、撤销、后台回复与状态流转 |
| 后台统计 | `/api/dashboard` | 总览、用户统计、用户趋势、角色分布、最近动态 |
| **数据分析** | `/api/analytics` | 市场概览、价格趋势、热门商品、分类分布、销售趋势、库存/价格预警、需求预测、商品关联分析、区域销售、价格分布、评价汇总、品类竞争；`supplier/*` 为团长专属视角 |
| **销量预测** | `/api/analytics/forecast/sales` | `train`（训练）、`evaluation`（评估）、`batch`（批量预测）、`dashboard`（看板） |
| **智能选品** | `/api/smart-selection` | `dashboard`、`new-products`（商品推荐）、`slow-moving`（滞销预警）、`restock-priority`（补货优先级）、`seasonal`（季节性）、`batch-purchase`（一键采购）、`slow-moving/discount`（滞销折扣） |
| 文件 | `/open` | 图片上传与删除 |

**销量预测接口参数**：`forecastDays`（预测天数，默认 7）、`testDays`（测试集天数，默认 14）、`trendDays`（趋势天数，默认 30）；平台管理员可传 `supplierId` 指定团长，团长登录时自动限定本社区。

---

## 十、项目亮点

1. **预测与经营决策闭环**：销量预测 → 五维评分 → 一键采购 → 支付入库 → 库存回写，算法结论直接变成可执行动作，而不是停留在图表上。
2. **可解释的评分模型**：推荐分拆解为五个维度，接口同时返回 `scoreDetails` 各项得分，团长能看清"为什么推荐这个商品"。
3. **面向稀疏数据的特征工程**：滞后、滚动、周期、节奏、品类五类时序特征，并对样本不足的商品做均值回退，缓解社区团购商品销量稀疏、间歇性强的特点。
4. **工程化的模型管理**：模型持久化、特征版本校验、自动重训、内存 + 磁盘二级缓存，避免每次请求都重新训练。
5. **严格的数据隔离**：基于角色的数据范围控制（`data_scope`）贯穿控制器与服务层，团长之间的经营数据互不可见。
6. **完备的订单状态机**：销售订单与采购订单均有明确的状态流转与合法性校验，非法状态操作会被拒绝并返回可读原因。

---

## 十一、已知问题与后续优化

| 问题 | 影响 | 建议 |
| --- | --- | --- |
| 仓库缺少 `requirements.txt` | 环境搭建需手动装依赖 | 补充依赖清单文件（可直接使用第八章的命令生成） |
| `py_refund`、`py_product_review_tags` 无建表语句 | 退款功能与评价标签分析会报错 | 依据代码字段补充迁移 SQL |
| `analytics_service_fixed.py` 以**子类继承 + 重写**方式修正 8 个方法的空数据回退 | 两个文件逻辑分散，维护成本高 | 将修正合并回 `analytics_service.py`，删除补丁文件 |
| `data_scope` 的角色映射未登记 `admin`（回退为仅本人数据），而分析接口白名单包含 `admin` | 同一角色在不同模块的数据范围不一致 | 统一角色常量与映射表，集中维护角色权限 |
| `config.py` 中 `SECRET_KEY` 与数据库密码为明文默认值 | 存在安全风险 | 改为从环境变量读取，并将 `config.py` 加入 `.gitignore` |
| 模型文件（8.5 MB / 4.5 MB）已提交入库 | 仓库体积偏大，克隆缓慢 | 取消跟踪并改为首次访问自动训练；`.gitignore` 已忽略预测缓存 `pred_*.pkl` |
| `service/hdfs_service.py` 未被业务代码引用，且依赖 `config` 中未定义的 `HDFS_CONFIG` | 直接导入会报错 | 补齐配置作为可选数据同步层，或移出主分支 |
| `flask_output.log` 被提交入库 | 包含本机文件路径与调试器 PIN 等本地环境信息 | 从版本控制中移除，并将 `*.log` 加入 `.gitignore` |
| 部分服务把原始异常信息拼进返回消息 | 可能向客户端泄露内部细节 | 统一记录日志，对外返回通用提示 |
| 无单元测试与 API 文档文件 | 回归验证依赖手工测试 | 补充 pytest 测试与接口文档 |

---

## 说明

- 本项目为**毕业设计作品**，仓库内的商品、用户、订单等数据由 `insert_historical_data.py` 与 `scripts/*.py` **脚本模拟生成**，仅用于功能演示与算法验证，不涉及任何真实用户信息。
- 论文题目：《基于 Python 的社区团购智能选品与销量预测系统的设计与实现》

## License

本项目仅用于学习与教学用途。如需引用或二次开发，请注明出处。
