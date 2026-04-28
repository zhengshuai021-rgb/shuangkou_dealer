# 双扣 - 八王千变 发牌流程

## Mermaid 流程图

```mermaid
flowchart TD
    Start(["开始发牌"]) --> InitPlayers["1. 初始化 4 名玩家\n队伍 0: 玩家 1、3\n队伍 1: 玩家 2、4"]

    InitPlayers --> InitDeck["2. 创建牌堆\n2 副牌 × 52 张 = 104 张\n👑 大王 × 4\n🃏 小王 × 4\n━━━━━━━━━━━━━\n总计 112 张"]

    InitDeck --> GroupCards["3. 按点数分组\n13 种点数（3-A-2），每种 8 张\n分离八王 8 张"]

    GroupCards --> BombLoop["4. 循环分配炸弹\n策略：炸弹最少的玩家优先"]

    BombLoop --> MinCheck{"所有玩家炸弹数 ≥ MinBombs?"}

    MinCheck -->|否| FindMin["找当前炸弹最少的玩家"]
    FindMin --> DealBomb{"该点数炸弹是 8 张?"}
    DealBomb -->|是，拆分| SplitBomb["拆成两个 4 张炸弹\n玩家 i 得前 4 张\n玩家 i+1 得后 4 张"]
    DealBomb -->|否| SingleBomb["发一个 4 张炸弹给该玩家"]
    SplitBomb --> RemoveBomb["从牌堆移除已发牌"]
    SingleBomb --> RemoveBomb
    RemoveBomb --> BombLoop

    MinCheck -->|是| JokerParse["5. 解析万能牌配置"]

    JokerParse --> JokerType{"jokers_per_player 类型?"}
    JokerType -->|int 固定值| Fixed["每人固定数量"]
    JokerType -->|范围 min~max| Range["范围随机分配"]
    JokerType -->|null| Default["默认每人 2 张"]

    Fixed --> JokerCheck
    Default --> JokerCheck

    Range --> JokerCheck{"范围是否合法?\nmin × 4 ≤ 8 ≤ max × 4"}
    JokerCheck -->|否| Fallback["回退：每人 2 张"]
    JokerCheck -->|是| RandomTry["随机尝试 100 次\n每人 rand(min, max)\n总和 = 8?"]
    RandomTry -->|成功| UseDist["采用该分配方案"]
    RandomTry -->|失败| Greedy["贪心构造\n先每人分 min 张\n剩余逐个 +1 直到 8 张"]
    Fallback --> UseDist
    Greedy --> UseDist

    UseDist --> ShuffleJoker["打乱八王顺序\n👑 🃏 混合洗牌"]
    ShuffleJoker --> DealJoker["按方案发给玩家\n例：[1, 3, 2, 2]"]

    DealJoker --> RemCards["6. 发剩余牌"]
    RemCards --> ShuffleRem["剩余牌堆洗牌"]
    ShuffleRem --> CalcNeed["计算每人还需牌数\n目标：每人 28 张"]
    CalcNeed --> DealRound["轮流发牌\n直到每人满 28 张"]

    DealRound --> Result["7. 发牌完成\n每人 28 张，共 112 张"]
    Result --> End(["结束"])

    style Start fill:#e1f5fe
    style End fill:#c8e6c9
    style BombLoop fill:#fff3e0
    style JokerCheck fill:#f3e5f5
    style RandomTry fill:#f3e5f5
    style Greedy fill:#f3e5f5
```

---

## 流程说明

### 1. 牌堆组成
| 类型 | 数量 | 说明 |
|------|------|------|
| 普通牌 | 104 张 | 2 副牌 × 52 张（13 点数 × 4 花色） |
| 大王 👑 | 4 张 | 万能牌/癞子 |
| 小王 🃏 | 4 张 | 万能牌/癞子 |
| **总计** | **112 张** | 4 人 × 28 张 |

### 2. 炸弹分配策略
**目标**：每人至少 `MinBombs` 个炸弹

**规则**：
- 遍历 13 种点数（从小到大：3 → 4 → ... → A → 2）
- 每次找当前炸弹最少的玩家
- 分配方式：
  - **8 张炸弹**：拆成两个 4 张，分给相邻两个玩家
  - **4 张炸弹**：直接给一个玩家
- 当所有玩家炸弹数都 ≥ MinBombs 时停止

### 3. 八王分配策略（核心改动）

**配置项**：`jokers_per_player`

| 配置类型 | 示例 | 说明 |
|----------|------|------|
| 固定值 | `2` | 每人固定 2 张 |
| 范围 | `[0, 4]` | 每人 0~4 张，总和=8 |
| 默认 | `null` | 每人 2 张 |

**范围分配逻辑**：
1. **合法性检查**：`min × 4 ≤ 8 ≤ max × 4`
   - 不合法 → 回退到每人 2 张
2. **随机尝试**：100 次随机分配
   - 每人随机 `randint(min, max)`
   - 总和 = 8 → 成功
3. **贪心构造**（随机失败时）：
   - 先每人分 min 张
   - 剩余牌逐个 +1 直到 8 张

**示例**（范围 [0, 4]）：
- 可能结果：`[1, 3, 2, 2]`、`[0, 4, 2, 2]`、`[4, 0, 1, 3]` 等

### 4. 剩余牌分配
- 剩余牌堆洗牌
- 计算每人还需牌数（目标 28 张）
- 轮流发牌直到每人满 28 张

### 5. 最终结果
每人 28 张牌，包含：
- 至少 MinBombs 个炸弹
- 0~4 张万能牌（取决于配置）
- 其余普通牌
