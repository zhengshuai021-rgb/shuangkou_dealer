#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双扣 - 八王千变 发牌器 v2.1
核心目标：保证每个人都有更多的炸弹

优化日志 v2.1 (2026-05-06):
  [#1] 队伍牌力平衡校验+重发
  [#2] 炸弹质量平衡（炸弹大小加权）
  [#3] 万能牌策略扩展到 2+2 王组合
  [#4] 剩余牌打散对子/三条再发
  [#5] deck 改用 set 标记已发，替代 O(n) 的 list.remove()
  [#6] 抽取连炸检测为独立方法 _find_chain_groups()
  [#7] 发牌后校验 4×28=112 张牌完整
"""

import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set

# ==================== 常量定义 ====================

# 牌面值（2 副牌：每个点数 8 张）
CARD_RANKS = ['3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A', '2']
# 大小王（八王：4 大王 +4 小王 =8 张，都是万能牌/癞子）
JOKERS_BIG = ['👑'] * 4  # 4 张大王
JOKERS_SMALL = ['🃏'] * 4  # 4 张小王

# 牌面值映射（用于比较大小）
RANK_VALUE = {rank: i for i, rank in enumerate(CARD_RANKS)}
RANK_VALUE['🃏'] = 13  # 小王
RANK_VALUE['👑'] = 14  # 大王

# 队伍平衡阈值
TEAM_BALANCE_BOMBS = 5      # 两队炸弹数差最大允许值
TEAM_BALANCE_SCORE = 10      # 两队贡献分差最大允许值
MAX_FULL_RETRIES = 3        # 完整重发最大次数


# ==================== 数据结构 ====================

@dataclass
class Card:
    """单张牌"""
    rank: str  # 牌面值
    suit: str = ''  # 花色（双扣中花色不重要，但保留用于区分）

    def __str__(self):
        return self.rank

    def __repr__(self):
        return f"Card({self.rank})"

    def value(self) -> int:
        """返回牌面值用于比较"""
        return RANK_VALUE.get(self.rank, 0)

    def uid(self) -> int:
        """唯一标识（对象 id），用于 set 追踪已发牌"""
        return id(self)


@dataclass
class Bomb:
    """炸弹"""
    cards: List[Card]
    rank: str

    @property
    def size(self) -> int:
        return len(self.cards)

    @property
    def multiplier(self) -> int:
        """返回炸弹倍数"""
        if self.size < 4:
            return 0
        if self.size == 4:
            return 1
        return 2 ** (self.size - 4)

    def value(self) -> int:
        """返回牌面值用于比较"""
        return RANK_VALUE.get(self.rank, 0)

    def __str__(self):
        return f"{self.rank * self.size}({self.size}张×{self.multiplier})"


@dataclass
class Hand:
    """一手牌"""
    cards: List[Card] = field(default_factory=list)

    def add(self, card: Card):
        self.cards.append(card)

    def sort(self):
        """按牌面值排序"""
        self.cards.sort(key=lambda c: c.value())

    def count_by_rank(self) -> Dict[str, int]:
        """统计每个点数的牌数"""
        counter = Counter(c.rank for c in self.cards)
        return dict(counter)

    def find_bombs(self) -> List[Bomb]:
        """找出所有炸弹（4 张及以上，不含万能牌补充）"""
        bombs = []
        counter = self.count_by_rank()
        for rank, count in counter.items():
            if count >= 4:
                bomb_cards = [c for c in self.cards if c.rank == rank]
                bombs.append(Bomb(cards=bomb_cards, rank=rank))
        return sorted(bombs, key=lambda b: b.value(), reverse=True)

    def count_effective_bombs(self, min_bombs: int = 2) -> int:
        """
        计算有效炸弹数（含万能牌补充）。
        规则：同点数牌数 + 万能牌数 ≥ 4 就算一个炸弹。
        万能牌优先补充数量最少的潜在炸弹。
        """
        counter = self.count_by_rank()
        jokers = sum(counter.get(j, 0) for j in ['👑', '🃏'])

        # 找出所有潜在炸弹（≥3 张同点数的组合，有可能用万能牌补足到 4）
        potentials = []
        for rank, count in counter.items():
            if rank not in ['👑', '🃏'] and count >= 3:
                potentials.append((rank, count))

        # 按数量从少到多排序（优先补充数量少的）
        potentials.sort(key=lambda x: x[1])

        remaining_jokers = jokers
        valid_bombs = 0

        for rank, count in potentials:
            if count >= 4:
                valid_bombs += 1
            elif remaining_jokers > 0:
                need = 4 - count
                if remaining_jokers >= need:
                    valid_bombs += 1
                    remaining_jokers -= need

        return valid_bombs

    def find_bombs_with_jokers(self) -> List[Bomb]:
        """
        找出所有炸弹（含万能牌补充的）。用于统计展示。
        支持：3+1、2+2、1+3 万能牌补充组合。
        """
        counter = self.count_by_rank()
        jokers = sum(counter.get(j, 0) for j in ['👑', '🃏'])

        bombs = []
        remaining_jokers = jokers

        # 先找天然炸弹（≥4 张）
        for rank, count in counter.items():
            if rank not in ['👑', '🃏'] and count >= 4:
                bomb_cards = [c for c in self.cards if c.rank == rank]
                bombs.append(Bomb(cards=bomb_cards, rank=rank))

        # 收集所有需要万能牌补足的潜在炸弹
        potentials = []
        for rank, count in counter.items():
            if rank not in ['👑', '🃏'] and 1 <= count <= 3:
                need = 4 - count
                potentials.append((rank, count, need))

        # 按需要万能牌数量从少到多排序（优先最容易补足的）
        potentials.sort(key=lambda x: (x[2], x[0]))

        for rank, count, need in potentials:
            if remaining_jokers >= need:
                bomb_cards = [c for c in self.cards if c.rank == rank]
                for _ in range(need):
                    joker_card = Card(rank='👑', suit='+癞子')
                    bomb_cards.append(joker_card)
                bombs.append(Bomb(cards=bomb_cards, rank=rank))
                remaining_jokers -= need

        return sorted(bombs, key=lambda b: b.value(), reverse=True)

    # --- [优化 #6] 抽取连炸检测为独立方法 ---

    def _find_chain_groups(self) -> List[List[int]]:
        """
        检测普通炸弹的连续组（连炸）。
        返回分组列表，每组是 rank 索引列表。
        """
        bombs = self.find_bombs()
        normal_bombs = [b for b in bombs if b.rank not in ['👑', '🃏']]
        if not normal_bombs:
            return []

        rank_indices = sorted([CARD_RANKS.index(b.rank) for b in normal_bombs])

        groups = []
        current_group = [rank_indices[0]]
        for i in range(1, len(rank_indices)):
            if rank_indices[i] == rank_indices[i - 1] + 1:
                current_group.append(rank_indices[i])
            else:
                groups.append(current_group)
                current_group = [rank_indices[i]]
        groups.append(current_group)
        return groups

    # --- 贡献分计算（复用 _find_chain_groups） ---

    def calc_contribution_score(self) -> int:
        """
        计算贡献分：按炸弹的"线数"计算，5线及以上才有贡献分。
        """
        bombs = self.find_bombs()
        if not bombs:
            return 0

        score = 0

        # 王炸贡献分
        for jb in bombs:
            if jb.rank in ['👑', '🃏']:
                line = jb.size + 3
                if line >= 5:
                    score += 2 ** (line - 5)

        # 普通炸弹连炸检测（复用独立方法）
        groups = self._find_chain_groups()
        normal_bombs = {b.rank: b for b in bombs if b.rank not in ['👑', '🃏']}

        for group in groups:
            if len(group) >= 3:
                min_size = min(normal_bombs[CARD_RANKS[idx]].size for idx in group)
                line = min_size + len(group)
                if line >= 5:
                    score += 2 ** (line - 5)
            else:
                for idx in group:
                    b = normal_bombs[CARD_RANKS[idx]]
                    if b.size >= 5:
                        score += 2 ** (b.size - 5)

        return score

    def get_contribution_detail(self) -> dict:
        """返回贡献分明细"""
        bombs = self.find_bombs()
        if not bombs:
            return {'chain_score': 0, 'single_score': 0, 'chains': [], 'singles': []}

        chain_score = 0
        single_score = 0
        chains_info = []
        singles_info = []

        for jb in bombs:
            if jb.rank in ['👑', '🃏']:
                line = jb.size + 3
                if line >= 5:
                    s = 2 ** (line - 5)
                    chain_score += s
                    chains_info.append(f"{jb.rank}x{jb.size}={line}线({s}分)")

        normal_bombs = {b.rank: b for b in bombs if b.rank not in ['👑', '🃏']}
        groups = self._find_chain_groups()

        for group in groups:
            if len(group) >= 3:
                min_size = min(normal_bombs[CARD_RANKS[idx]].size for idx in group)
                line = min_size + len(group)
                if line >= 5:
                    s = 2 ** (line - 5)
                    chain_score += s
                    ranks_str = '+'.join([CARD_RANKS[idx] for idx in group])
                    chains_info.append(f"[{ranks_str}]连炸={line}线({s}分)")
            else:
                for idx in group:
                    b = normal_bombs[CARD_RANKS[idx]]
                    if b.size >= 5:
                        s = 2 ** (b.size - 5)
                        single_score += s
                        singles_info.append(f"{CARD_RANKS[idx]}x{b.size}={b.size}线({s}分)")

        return {'chain_score': chain_score, 'single_score': single_score, 'chains': chains_info, 'singles': singles_info}

    # --- 其他统计方法 ---

    def count_sequences(self) -> int:
        """统计顺子数量（5+张连牌，无视花色，从大到小统计）"""
        counter = self.count_by_rank()
        for rank in list(counter.keys()):
            if rank not in ['👑', '🃏'] and counter[rank] >= 4:
                counter[rank] = 0

        seq_count = 0
        while True:
            found = False
            for start in range(len(CARD_RANKS) - 5, -1, -1):
                can_form = True
                for j in range(start, start + 5):
                    if counter.get(CARD_RANKS[j], 0) <= 0:
                        can_form = False
                        break
                if can_form:
                    for j in range(start, start + 5):
                        counter[CARD_RANKS[j]] -= 1
                    seq_count += 1
                    found = True
                    break
            if not found:
                break

        return seq_count

    def count_pairs(self) -> int:
        """统计对子数量（2张同点数，无视花色，从大到小统计）"""
        counter = self.count_by_rank()
        for rank in list(counter.keys()):
            if rank not in ['👑', '🃏'] and counter[rank] >= 4:
                counter[rank] = 0

        pair_count = 0
        for rank in reversed(CARD_RANKS):
            if rank in ['👑', '🃏']:
                continue
            count = counter.get(rank, 0)
            if count >= 2:
                pair_count += count // 2
        return pair_count

    def count_triplets(self) -> int:
        """统计三条数量（3张同点数，无视花色，从大到小统计）"""
        counter = self.count_by_rank()
        for rank in list(counter.keys()):
            if rank not in ['👑', '🃏'] and counter[rank] >= 4:
                counter[rank] = 0

        triplet_count = 0
        for rank in reversed(CARD_RANKS):
            if rank in ['👑', '🃏']:
                continue
            count = counter.get(rank, 0)
            if count >= 3:
                triplet_count += count // 3
        return triplet_count

    # --- [优化 #2] 炸弹质量分（大小加权） ---

    def bomb_quality_score(self) -> float:
        """
        炸弹质量分：考虑炸弹大小和连炸加成。
        公式：sum(2^(size-4)) + 连炸额外 bonus
        4张炸弹=1分, 5张=2分, 6张=4分...
        """
        bombs = self.find_bombs()
        score = 0.0
        for b in bombs:
            if b.size >= 4:
                score += 2 ** (b.size - 4)

        # 连炸 bonus：每多一环 ×1.5
        groups = self._find_chain_groups()
        for group in groups:
            if len(group) >= 3:
                bonus = len(group) - 2  # 3环=1, 4环=2...
                score *= (1 + 0.5 * bonus)

        return score

    def total_cards(self) -> int:
        return len(self.cards)

    def __str__(self):
        self.sort()
        return ' '.join(str(c) for c in self.cards)


@dataclass
class Player:
    """玩家"""
    id: int
    name: str
    hand: Hand = field(default_factory=Hand)
    team: int = 0  # 队伍 ID（0 或 1，对家同队）

    def __str__(self):
        bombs = self.hand.find_bombs()
        bomb_info = f"炸弹×{len(bombs)}" if bombs else "无炸弹"
        return f"{self.name}[{self.hand.total_cards()}张|{bomb_info}]"


# ==================== 发牌器核心 ====================

class ShuangkouDealer:
    """双扣 - 八王千变 发牌器"""

    def __init__(self, num_players: int = 4):
        self.num_players = num_players
        self.players: List[Player] = []
        self.deck: List[Card] = []
        # [优化 #5] 用 set 追踪已发牌，替代 O(n) 的 list.remove()
        self._dealt_ids: Set[int] = set()

    def create_deck(self) -> List[Card]:
        """创建牌堆：2 副牌 (104 张) + 4 大王 + 4 小王 = 112 张"""
        deck = []
        suits = ['♠', '♥', '♣', '♦']
        for _ in range(2):
            for suit in suits:
                for rank in CARD_RANKS:
                    deck.append(Card(rank=rank, suit=suit))
        for _ in range(4):
            deck.append(Card(rank='👑', suit=''))
        for _ in range(4):
            deck.append(Card(rank='🃏', suit=''))
        return deck

    # [优化 #5] 发牌标记方法
    def _deal_card_to(self, player: Player, card: Card):
        """发一张牌给玩家，同时标记已发"""
        player.hand.add(card)
        self._dealt_ids.add(card.uid())

    def _get_available_cards(self, cards: List[Card]) -> List[Card]:
        """从候选牌中过滤出未发的牌"""
        return [c for c in cards if c.uid() not in self._dealt_ids]

    def _shuffle_remaining(self) -> List[Card]:
        """获取并洗牌剩余未发的牌"""
        remaining = [c for c in self.deck if c.uid() not in self._dealt_ids]
        random.shuffle(remaining)
        return remaining

    def initialize_players(self):
        """初始化玩家"""
        self.players = []
        for i in range(self.num_players):
            player = Player(
                id=i,
                name=f"玩家{i + 1}",
                team=i % 2
            )
            self.players.append(player)

    def deal_chain_bombs(self, min_chains_per_player: int = 0):
        """优先发连炸（3+个点数相连的炸弹组）"""
        if min_chains_per_player <= 0:
            print(f"\n🔗 连炸配置为0，跳过连炸发牌")
            return 0

        self.deck = self.create_deck()
        self._dealt_ids.clear()

        rank_groups = defaultdict(list)
        for card in self.deck:
            rank_groups[card.rank].append(card)

        all_ranks = [r for r in CARD_RANKS if r not in ['👑', '🃏']]
        total_ranks = len(all_ranks)

        base = total_ranks // self.num_players
        extra = total_ranks % self.num_players
        sizes = [base + (1 if i < extra else 0) for i in range(self.num_players)]
        random.shuffle(sizes)

        offset = random.randint(0, total_ranks - 1)

        chains_assigned = 0
        player_chain_count = [0] * self.num_players

        print(f"\n🔗 开始分配连炸（每人至少 {min_chains_per_player} 组）...")
        print(f"   段大小分配：{sizes}，偏移量：{offset}")

        pos = offset
        for player_idx in range(self.num_players):
            seg_size = sizes[player_idx]
            if seg_size < 3:
                continue

            chain_ranks = []
            for j in range(seg_size):
                idx = pos % total_ranks
                chain_ranks.append(all_ranks[idx])
                pos += 1

            for rank in chain_ranks:
                cards = rank_groups[rank]
                available = self._get_available_cards(cards)
                if len(available) < 4:
                    continue
                selected = random.sample(available, 4)
                for card in selected:
                    self._deal_card_to(self.players[player_idx], card)

            player_chain_count[player_idx] += 1
            chains_assigned += 1
            ranks_str = '-'.join(chain_ranks)
            print(f"   玩家{player_idx+1}: [{ranks_str}] 连炸({seg_size}连环)")

        print(f"✅ 连炸分配完成：共 {chains_assigned} 组，每人连炸数：{player_chain_count}")
        return chains_assigned

    def deal_bombs_first(self, min_bombs_per_player: int = 2, bomb_size_range=None, jokers_per_player=None, chain_bombs_already_dealt: bool = False):
        """优先发炸弹策略（八王千变版本）"""
        if not chain_bombs_already_dealt:
            self.deck = self.create_deck()
            self._dealt_ids.clear()

        rank_groups = defaultdict(list)
        for card in self.deck:
            rank_groups[card.rank].append(card)

        joker_cards = []
        bomb_candidates = []

        for rank, cards in rank_groups.items():
            if rank in ['👑', '🃏']:
                joker_cards.extend(cards)
            else:
                # [优化 #5] 只取未发的牌（兼容连炸已发的情况）
                available = self._get_available_cards(cards)
                if len(available) >= 4:
                    bomb_candidates.append((rank, available))

        bomb_candidates.sort(key=lambda x: RANK_VALUE.get(x[0], 0))

        if bomb_size_range is None:
            bomb_size_range = [4, 4]
        bomb_min_size, bomb_max_size = bomb_size_range

        # [优化 #2] 炸弹分配考虑质量平衡
        bombs_assigned = 0
        player_bomb_count = [0] * self.num_players
        player_bomb_quality = [0.0] * self.num_players  # 炸弹质量分
        player_existing_cards = [p.hand.total_cards() for p in self.players]

        for rank, cards in bomb_candidates:
            total = len(cards)

            # [优化 #1 + #2] 优先给炸弹最少且质量最低的玩家
            min_bombs = min(player_bomb_count)
            candidates = [i for i in range(self.num_players) if player_bomb_count[i] == min_bombs]

            if len(candidates) > 1:
                # 炸弹数相同时，选质量分最低的
                i = min(candidates, key=lambda x: (player_bomb_quality[x], player_existing_cards[x]))
            else:
                i = candidates[0]

            if min_bombs >= min_bombs_per_player + 2:
                break

            possible_splits = []
            for s in range(2, total - 1):
                if total - s >= 2:
                    possible_splits.append(s)

            if possible_splits:
                split_size = random.choice(possible_splits)

                for card in cards[:split_size]:
                    self._deal_card_to(self.players[i], card)
                # 标记整个点数已发
                for card in cards:
                    self._dealt_ids.add(card.uid())
                player_bomb_count[i] += 1
                player_bomb_quality[i] += 2 ** (split_size - 4)
                bombs_assigned += 1

                other_candidates = [j for j in range(self.num_players) if player_bomb_count[j] == min(player_bomb_count)]
                if len(other_candidates) > 1:
                    other_idx = min(other_candidates, key=lambda x: (player_bomb_quality[x], player_existing_cards[x]))
                else:
                    other_idx = other_candidates[0]
                if other_idx == i:
                    other_idx = (i + 1) % self.num_players

                rest_size = total - split_size
                for card in cards[split_size:]:
                    self._deal_card_to(self.players[other_idx], card)
                player_bomb_count[other_idx] += 1
                player_bomb_quality[other_idx] += 2 ** (rest_size - 4)
                bombs_assigned += 1
            elif total >= 4:
                for card in cards:
                    self._deal_card_to(self.players[i], card)
                for card in cards:
                    self._dealt_ids.add(card.uid())
                player_bomb_count[i] += 1
                player_bomb_quality[i] += 2 ** (total - 4)
                bombs_assigned += 1

        print(f"✅ 炸弹分配完成：共分配 {bombs_assigned} 个炸弹")
        print(f"   每人炸弹数：{player_bomb_count}")
        print(f"   炸弹质量分：{[f'{q:.1f}' for q in player_bomb_quality]}")

        # 分配八王
        print(f"\n🃏 开始分配八王（万能牌）...")

        if jokers_per_player is None:
            joker_range = [2, 2]
        elif isinstance(jokers_per_player, int):
            joker_range = [jokers_per_player, jokers_per_player]
        elif isinstance(jokers_per_player, (list, tuple)) and len(jokers_per_player) == 2:
            joker_range = [int(jokers_per_player[0]), int(jokers_per_player[1])]
        else:
            joker_range = [2, 2]

        joker_distribution = self._generate_joker_distribution(joker_range)

        joker_idx = 0
        random.shuffle(joker_cards)
        for i in range(self.num_players):
            for _ in range(joker_distribution[i]):
                if joker_idx < len(joker_cards):
                    self._deal_card_to(self.players[i], joker_cards[joker_idx])
                    joker_idx += 1

        dist_str = '、'.join([f"玩家{i+1}×{joker_distribution[i]}" for i in range(self.num_players)])
        print(f"✅ 八王分配完成：{joker_idx} 张万能牌，分布：{dist_str}")

        # 校验有效炸弹数
        print(f"\n🔍 校验有效炸弹数（含万能牌补充）...")
        for i, player in enumerate(self.players):
            natural_bombs = len(player.hand.find_bombs_with_jokers())
            effective_bombs = player.hand.count_effective_bombs()
            status = "✅" if effective_bombs >= min_bombs_per_player else "⚠️"
            print(f"   玩家{i+1}: 天然炸弹 {natural_bombs} 个 → 有效炸弹 {effective_bombs} 个 {status}")

        return bombs_assigned

    # [优化 #4] 剩余牌打散对子/三条后再发
    def deal_remaining_cards(self):
        """发完剩余的牌，每人 28 张。先打散潜在对子/三条再随机发。"""
        remaining = self._shuffle_remaining()

        # 打散策略：按点数分组，同点数的牌间隔插入
        rank_buckets = defaultdict(list)
        for card in remaining:
            rank_buckets[card.rank].append(card)

        # 将同点数的牌分散到不同位置
        scattered = []
        max_bucket = max(len(v) for v in rank_buckets.values()) if rank_buckets else 0
        for i in range(max_bucket):
            for rank in CARD_RANKS:
                if rank in rank_buckets and i < len(rank_buckets[rank]):
                    scattered.append(rank_buckets[rank][i])

        random.shuffle(scattered)  # 最后再混洗一次

        cards_needed = [28 - p.hand.total_cards() for p in self.players]

        print(f"📋 剩余牌数：{len(scattered)} 张")
        print(f"   每人还需：{cards_needed} 张")

        player_idx = 0
        idx = 0
        while idx < len(scattered) and any(needed > 0 for needed in cards_needed):
            if cards_needed[player_idx] > 0:
                self._deal_card_to(self.players[player_idx], scattered[idx])
                cards_needed[player_idx] -= 1
                idx += 1

            player_idx = (player_idx + 1) % self.num_players

        total_dealt = sum(p.hand.total_cards() for p in self.players)
        print(f"✅ 发牌完成：共发出 {total_dealt} 张（每人 28 张）")

    def _generate_joker_distribution(self, joker_range: list) -> list:
        """生成八王分配方案，保证每人王数在范围内，总和=8张。"""
        j_min, j_max = joker_range
        num_players = self.num_players
        total_jokers = 8

        if j_min * num_players > total_jokers or j_max * num_players < total_jokers:
            return [2] * num_players

        for _ in range(100):
            dist = [random.randint(j_min, j_max) for _ in range(num_players)]
            if sum(dist) == total_jokers:
                return dist

        dist = [j_min] * num_players
        remaining = total_jokers - sum(dist)
        for i in range(remaining):
            dist[i % num_players] += 1
        return dist

    # [优化 #1] 队伍牌力平衡校验
    def validate_team_balance(self) -> Tuple[bool, str]:
        """
        校验两队牌力是否均衡。
        检查项：炸弹数差、贡献分差、炸弹质量分差。
        返回 (是否平衡, 不平衡原因)
        """
        team0_bombs = sum(len(p.hand.find_bombs()) for p in self.players if p.team == 0)
        team1_bombs = sum(len(p.hand.find_bombs()) for p in self.players if p.team == 1)
        bomb_diff = abs(team0_bombs - team1_bombs)

        if bomb_diff > TEAM_BALANCE_BOMBS:
            return False, f"炸弹数差 {bomb_diff} > {TEAM_BALANCE_BOMBS}（队0={team0_bombs}, 队1={team1_bombs}）"

        team0_score = sum(p.hand.calc_contribution_score() for p in self.players if p.team == 0)
        team1_score = sum(p.hand.calc_contribution_score() for p in self.players if p.team == 1)
        score_diff = abs(team0_score - team1_score)

        if score_diff > TEAM_BALANCE_SCORE:
            return False, f"贡献分差 {score_diff} > {TEAM_BALANCE_SCORE}（队0={team0_score}, 队1={team1_score}）"

        team0_quality = sum(p.hand.bomb_quality_score() for p in self.players if p.team == 0)
        team1_quality = sum(p.hand.bomb_quality_score() for p in self.players if p.team == 1)
        quality_diff = abs(team0_quality - team1_quality)

        if quality_diff > team0_quality * 0.6 and team0_quality > 0:
            return False, f"炸弹质量差过大（队0={team0_quality:.1f}, 队1={team1_quality:.1f}）"

        return True, "✅ 队伍平衡"

    # [优化 #7] 发牌后校验
    def validate_deal(self) -> Tuple[bool, str]:
        """校验发牌完整性：每人28张，总共112张，无重复牌。"""
        total = sum(p.hand.total_cards() for p in self.players)
        if total != 112:
            return False, f"总牌数 {total} != 112"

        for i, p in enumerate(self.players):
            if p.hand.total_cards() != 28:
                return False, f"玩家{i+1} 有 {p.hand.total_cards()} 张 != 28"

        # 检查重复牌
        all_keys = []
        for p in self.players:
            for c in p.hand.cards:
                all_keys.append(c.uid())
        if len(all_keys) != len(set(all_keys)):
            return False, "存在重复牌！"

        return True, "✅ 校验通过"

    # [优化 #1] 完整发牌（含队伍平衡校验+重发）
    def full_deal(self, min_bombs_per_player: int = 2, bomb_size_range=None,
                  jokers_per_player=None, min_chains_per_player: int = 0,
                  verbose: bool = True) -> List[Player]:
        """
        完整发牌 + 队伍平衡校验。如果不平衡则重发，最多 MAX_FULL_RETRIES 次。
        """
        for attempt in range(MAX_FULL_RETRIES):
            self.initialize_players()

            chain_dealt = False
            if min_chains_per_player > 0:
                self.deal_chain_bombs(min_chains_per_player)
                chain_dealt = True

            self.deal_bombs_first(min_bombs_per_player, bomb_size_range=bomb_size_range,
                                  jokers_per_player=jokers_per_player,
                                  chain_bombs_already_dealt=chain_dealt)
            self.deal_remaining_cards()

            # [优化 #7] 完整性校验
            valid, msg = self.validate_deal()
            if not valid:
                print(f"⚠️ 发牌校验失败（尝试 {attempt+1}/{MAX_FULL_RETRIES}）: {msg}，重发...")
                continue

            # [优化 #1] 队伍平衡校验
            balanced, reason = self.validate_team_balance()
            if balanced:
                if verbose:
                    self._print_result()
                return self.players

            print(f"⚠️ 队伍不平衡（尝试 {attempt+1}/{MAX_FULL_RETRIES}）: {reason}，重发...")

        # 超过最大重试次数，输出最后一次结果
        print(f"⚠️ 已重试 {MAX_FULL_RETRIES} 次，使用最后一次结果")
        if verbose:
            self._print_result()
        return self.players

    def _print_result(self):
        """打印发牌结果"""
        print("\n" + "=" * 60)
        print("📊 发牌结果")
        print("=" * 60)

        for player in self.players:
            bombs = player.hand.find_bombs()
            score = player.hand.calc_contribution_score()
            quality = player.hand.bomb_quality_score()
            print(f"\n{player.name} (队伍{player.team}):")
            print(f"   手牌：{player.hand}")
            print(f"   炸弹：{len(bombs)} 个 | 贡献分: {score} | 质量分: {quality:.1f}")
            for bomb in bombs:
                print(f"      - {bomb}")

        # 队伍汇总
        for team in [0, 1]:
            team_players = [p for p in self.players if p.team == team]
            team_bombs = sum(len(p.hand.find_bombs()) for p in team_players)
            team_score = sum(p.hand.calc_contribution_score() for p in team_players)
            print(f"\n队伍{team}: 炸弹 {team_bombs} 个 | 贡献分 {team_score}")

    # 兼容旧接口
    def deal(self, min_bombs_per_player: int = 2, bomb_size_range=None,
             jokers_per_player=None, min_chains_per_player: int = 0,
             verbose: bool = True) -> List[Player]:
        """完整发牌流程（调用 full_deal）"""
        print("=" * 60)
        print("🎴 双扣 - 八王千变 发牌器 v2.1")
        print("=" * 60)
        return self.full_deal(
            min_bombs_per_player=min_bombs_per_player,
            bomb_size_range=bomb_size_range,
            jokers_per_player=jokers_per_player,
            min_chains_per_player=min_chains_per_player,
            verbose=verbose
        )

    def analyze_hands(self) -> Dict:
        """分析发牌结果"""
        result = {
            'total_bombs': 0,
            'bombs_by_player': [],
            'bomb_sizes': [],
            'bomb_quality': [],
            'avg_bombs_per_player': 0
        }

        for player in self.players:
            bombs = player.hand.find_bombs()
            result['total_bombs'] += len(bombs)
            result['bombs_by_player'].append(len(bombs))
            result['bomb_quality'].append(player.hand.bomb_quality_score())
            for bomb in bombs:
                result['bomb_sizes'].append(bomb.size)

        result['avg_bombs_per_player'] = result['total_bombs'] / self.num_players

        return result


# ==================== 主程序 ====================

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='双扣 - 八王千变 发牌器 v2.1')
    parser.add_argument('--players', type=int, default=4, help='玩家人数（默认 4）')
    parser.add_argument('--bombs', type=int, default=2, help='每人最少炸弹数（默认 2）')
    parser.add_argument('--chains', type=int, default=0, help='每人最少连炸组数（默认 0）')
    parser.add_argument('--bomb-min', type=int, default=4, help='炸弹最小张数（默认 4）')
    parser.add_argument('--bomb-max', type=int, default=4, help='炸弹最大张数（默认 4）')
    parser.add_argument('--jokers', type=str, default='2', help='每人王数，如 2 或 1,3（默认 2）')
    parser.add_argument('--seed', type=int, default=None, help='随机种子（可复现）')

    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    # 解析 jokers 参数
    if ',' in args.jokers:
        parts = args.jokers.split(',')
        jokers = [int(parts[0]), int(parts[1])]
    else:
        jokers = int(args.jokers)

    dealer = ShuangkouDealer(num_players=args.players)
    dealer.deal(
        min_bombs_per_player=args.bombs,
        bomb_size_range=[args.bomb_min, args.bomb_max],
        jokers_per_player=jokers,
        min_chains_per_player=args.chains
    )

    analysis = dealer.analyze_hands()
    print("\n" + "=" * 60)
    print("📈 统计分析")
    print("=" * 60)
    print(f"总炸弹数：{analysis['total_bombs']} 个")
    print(f"每人炸弹数：{analysis['bombs_by_player']}")
    print(f"每人质量分：{[f'{q:.1f}' for q in analysis['bomb_quality']]}")
    print(f"平均每人：{analysis['avg_bombs_per_player']:.1f} 个炸弹")
    print(f"炸弹大小分布：{Counter(analysis['bomb_sizes'])}")


if __name__ == '__main__':
    main()
