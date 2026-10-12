# 感官解锁同程表（音 / 振 / 景）

> 机制与场景无关：同一叙事弧，换音色、视觉元素、地形事件与里程碑米数。  
> **耳目同程** — 禁止只开声音不开景色，或一键铺满视觉。

---

## 1. 相对进度总轴

| 相对进度 | 听觉 / 触觉 | 景色（视觉） |
| --- | --- | --- |
| 0% | 静默 | **黑幕 / 虚空** |
| ~10% | 该场景脚步淡入 | 第一层氛围形 |
| ~30% | 该场景环境淡入 | 主体景物 |
| ~50% | 该场景振动 | 细节丰富 |
| 100% | 可通关 | 景色保持完整（不切屏炫技） |

停走 → 进度停。淡入用 `fadeMs` / opacity 插值，避免一步跳变。

---

## 2. 分场景绝对米数表

### 雨林 450 m

| atMeters | 音/振 | 视觉 layer |
| --- | --- | --- |
| 0 | silence | void |
| 45 | footsteps 0.24 | mist |
| 135 | ambience 0.36 | trunks_canopy |
| 225 | haptics drip_soft | vines_light |
| 450 | 通关门禁 | 保持 |

### 森林 400 m

| atMeters | 音/振 | 视觉 |
| --- | --- | --- |
| 0 | silence | void |
| 40 | footsteps | 轮廓树木 |
| 120 | ambience | 树干/林间光 |
| 200 | haptics footstep_soft | 落叶/路径细节 |
| 400 | 通关 | 保持 |

### 沙漠 600 m

| atMeters | 音/振 | 视觉 |
| --- | --- | --- |
| 0 | silence | void |
| 60 | footsteps | 天际线 |
| 180 | ambience 风沙 | 沙丘轮廓 |
| 300 | haptics footstep_sand | 沙纹/热浪感 |
| 600 | 通关 | 保持 |

### 城市 500 m

| atMeters | 音/振 | 视觉 |
| --- | --- | --- |
| 0 | silence | void |
| 50 | footsteps | 远景轮廓 |
| 150 | ambience 低通车流 | 街灯/建筑剪影 |
| 250 | haptics curb_tap | 近景街道 |
| 500 | 通关 | 保持 |

### 夜径 350 m（可选）

| atMeters | 音/振 | 视觉 |
| --- | --- | --- |
| 0 | silence | void |
| 35 | footsteps | 微弱路径 |
| 100 | ambience 夜虫 | 月光/远灯 |
| 175 | haptics pulse_slow | 夜景层次 |
| 350 | 通关 | 保持 |

---

## 3. 禁止项（感官）

| 禁止 | 原因 |
| --- | --- |
| 选景页预播完整风景 | 剧透过程奖励 |
| 会话内「显示全部景色」 | 等同跳过 |
| 用时间或手势跳过视觉相位 | 破坏距离门禁哲学 |
| 音视进度脱钩（长期只听不见） | 破坏耳目同程 |
| 城市层吵杂超限 | 减压失败 |

---

## 4. 配置字段（权威）

- `requiredDistanceMeters`  
- `phases[].atMeters`（迁移期可双读旧 `atSec`）  
- 视觉：`layer: "visual"` 或 `visualPhases[]`  
- v0.6：`pathProfile`、`stickCurveId`（默认 `comfort_v1`）  

原则不变：**音视同源 atMeters，黑幕起笔，逐步丰富。**
