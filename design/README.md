# 慢行 · SenseWalk — 完整设计包

> 与仓库真理文档 **v0.6**（[`DEVELOPMENT.md`](../DEVELOPMENT.md)、[`docs/plan.html`](../docs/plan.html)）对齐的 **PRD 级设计包**。  
> 本目录只含设计与交互稿，**不修改** `app/` 业务代码。

**版本**：design-pack · 2026-10-11 · 约束源：产品规则 v0.6  
**语言**：简体中文

---

## 怎么读（强制阅读顺序）

按产品设计优先级，**先场景与地形，再角色，最后交互/产品与演示**：

| 顺序 | 路径 | 内容 |
| --- | --- | --- |
| ① | [`01-scenes-terrain/`](./01-scenes-terrain/) | 五景身份、色板、声景、地形剖面、通用地形系统 |
| ② | [`02-characters/`](./02-characters/) | 默认「旅人」规格与可选变体 |
| ③ | [`03-product-prd/`](./03-product-prd/) | 完整 PRD、信息架构、感官解锁同程表 |
| ④ | [`04-interaction-mockups/`](./04-interaction-mockups/) | 关键路径、线框、可打开 HTML 演示 |

一页纸定位可先扫一眼 [`00-overview.md`](./00-overview.md)，再按上表深入。

---

## 硬约束（不可矛盾）

本包所有文档必须服从 v0.6：

- **距离门禁**：通关 ⟺ 有效距离 ≥ `requiredDistanceMeters`；不可跳过 / 加速 / 提前通关
- **双模式**：虚走（舒适摇杆）/ 实走（计步）；会话中途不可换景或换模式
- **舒适摇杆**：非单调曲线；甜点区 ≈ 0.45–0.65；**拉满 ≠ 最快**；硬顶 ≤ 1.4 m/s
- **景色从黑幕起**：会话内按 `atMeters` 层层展开；选景页不剧透完整风景
- **多场景声音身份**：雨林 / 森林 / 沙漠 / 城市 [/ 夜径]；机制相同、耳目不同
- **地形减压导向**：宽松、不扣命、可重试、重试不计刷距
- **耐心 / 减压**：成功指标温柔；无社交排行、无跳过道具

---

## 目录树

```
design/
  README.md                 ← 本索引
  00-overview.md
  01-scenes-terrain/
  02-characters/
  03-product-prd/
  04-interaction-mockups/
    demo/                   ← 浏览器打开 index.html
  assets/
```

## 演示入口

本地打开：[`04-interaction-mockups/demo/index.html`](./04-interaction-mockups/demo/index.html)

---

*设计包服从 DEVELOPMENT.md v0.6；若冲突，以 DEVELOPMENT.md 为准。*
