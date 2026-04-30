# 双扣 - 八王千变 发牌流程

## Mermaid 流程图

```mermaid
flowchart TD
    Start(["开始发牌"]) --> InitPlayers["1. 初始化 4 名玩家 28 张/人"]

    InitPlayers --> InitDeck["2. 创建牌堆 112 张 2副x52 + 8王"]

    InitDeck --> GroupCards["3. 按点数分组 13种点数各8张 分离8王"]

    GroupCards --> ParseConfig["解析配置 bomb_size_range min~max min_bombs"]

    ParseConfig --> BombLoop["4. 循环遍历炸弹候选 3~2 共13种"]

    BombLoop --> StopCheck{"炸弹最少玩家 >= min_bombs+2?"}

    StopCheck -->|是| JokerStep
    StopCheck -->|否| FindMin["找炸弹最少的玩家 i"]

    FindMin --> SplitCalc["计算拆分方案 2~6张 两部分都>=2"]

    SplitCalc --> AlwaysSplit{"可拆分?"}

    AlwaysSplit -->|是 始终拆分| PickSize["随机选拆分点 split_size"]
    PickSize --> DealFirst["第一部分 split_size张 -> 玩家 i"]
    DealFirst --> FindOther["找另一炸弹最少玩家 j"]
    FindOther --> SameIdx{"i == j?"}
    SameIdx -->|否| DealSecond["剩余 -> 玩家 j"]
    SameIdx -->|是| DealNext["剩余 -> 玩家 i+1 取模"]
    DealSecond --> RemoveCards
    DealNext --> RemoveCards

    AlwaysSplit -->|否| AllOne["全部8张 -> 玩家 i"]
    AllOne --> RemoveCards["从牌堆移除已发牌"]

    RemoveCards --> BombLoop

    JokerStep["5. 解析万能牌配置"] --> JokerType{"jokers_per_player 类型?"}
    JokerType -->|int| Fixed["每人固定数量"]
    JokerType -->|范围| Range["范围随机分配"]
    JokerType -->|null| Default["默认每人2张"]

    Fixed --> JokerOk
    Default --> JokerOk

    Range --> JokerCheck{"范围合法? min*4<=8<=max*4"}
    JokerCheck -->|否| Fallback["回退 每人2张"]
    JokerCheck -->|是| RandomTry["随机100次 每人rand min~max 和=8?"]
    RandomTry -->|成功| UseDist["采用该方案"]
    RandomTry -->|失败| Greedy["贪心 先每人min 剩余+1到8"]
    Fallback --> UseDist
    Greedy --> UseDist

    UseDist --> JokerOk["打乱八王 按方案分配"]

    JokerOk --> RemCards["6. 发剩余牌 洗牌后轮流发到28张"]

    RemCards --> Validate["7. 校验有效炸弹 含万能牌补充"]

    Validate --> BombOK{"每人有效炸弹 >= min_bombs?"}
    BombOK -->|是| Result["发牌完成 每人28张"]
    BombOK -->|否| Warning["显示警告 实际使用补充逻辑"]

    Warning --> Result

    Result --> End(["结束"])

    style Start fill:#e1f5fe
    style End fill:#c8e6c9
    style BombLoop fill:#fff3e0
    style AlwaysSplit fill:#fff3e0
    style JokerCheck fill:#f3e5f5
    style RandomTry fill:#f3e5f5
    style Greedy fill:#f3e5f5
    style Validate fill:#e8f5e9
```

---

## 流程说明

### 1. 牌堆组成
| 类型 | 数量 | 说明 |
|------|------|------|
| 普通牌 | 104 张 | 2 副牌 x 52 张（13 点数 x 4 花色） |
| 大王 | 4 张 | 万能牌/癞子 |
| 小王 | 4 张 | 万能牌/癞子 |
| **总计** | **112 张** | 4 人 x 28 张 |

### 2. 炸弹分配策略（核心逻辑）

**配置项**：`bomb_size_range` 默认 [4, 4]，当前配置 [4, 6]

**循环规则**：
- 遍历 13 种点数（3 -> 4 -> ... -> A -> 2），每种 8 张
- 找当前炸弹数最少的玩家 i
- **终止条件**：当最少玩家的炸弹数 >= min_bombs + 2 时停止（保留一些炸弹在牌堆）

**拆分逻辑**（始终拆分，增加多样性）：
| 步骤 | 说明 |
|------|------|
| 1. 计算拆分方案 | 拆分点范围 2~6，确保两部分都 >= 2 张 |
| 2. 随机选拆分点 | `split_size = random.choice(possible_splits)` |
| 3. 第一部分 -> 玩家 i | 当前炸弹最少的玩家 |
| 4. 剩余部分 -> 玩家 j | 另一个炸弹最少的玩家（若 i==j 则取 i+1） |

**拆分效果**（1000 局统计）：
| 炸弹大小 | 占比 |
|---------|------|
| 4 张 | ~57% |
| 5 张 | ~22% |
| 6 张 | ~21% |

### 3. 八王分配策略

**配置项**：`jokers_per_player` 当前配置 [0, 4]

| 配置类型 | 示例 | 说明 |
|----------|------|------|
| 固定值 | `2` | 每人固定 2 张 |
| 范围 | `[0, 4]` | 每人 0~4 张，总和=8 |
| 默认 | `null` | 每人 2 张 |

**范围分配逻辑**：
1. **合法性检查**：min x 4 <= 8 <= max x 4，不合法则回退到每人 2 张
2. **随机尝试**：100 次随机分配，每人 rand(min, max)，总和=8 即成功
3. **贪心构造**（随机失败时）：先每人分 min 张，剩余逐个 +1 直到 8 张

### 4. 有效炸弹校验

**新增校验逻辑**（含万能牌补充）：
- 统计每个玩家手牌中同点数牌的数量
- **有效炸弹判定**：同点数牌 + 万能牌 >= 4 张，算 1 个炸弹
- 例：玩家有 3 张 K + 1 张小王 = 1 个有效炸弹

**校验结果**：
- 每人有效炸弹 >= min_bombs -> 发牌成功
- 不足 -> 显示警告，但继续发牌（由外层重试机制处理）

### 5. 剩余牌分配
- 剩余牌堆洗牌
- 计算每人还需牌数（目标 28 张）
- 轮流发牌直到每人满 28 张

### 6. 最终结果
每人 28 张牌，包含：
- 至少 min_bombs 个炸弹（可含万能牌补充）
- 0~4 张万能牌（取决于配置）
- 其余普通牌
