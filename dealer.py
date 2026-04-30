#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双扣 - 八王千变 发牌器
核心目标：保证每个人都有更多的炸弹
"""

import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

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
        
        Args:
            min_bombs: 最小炸弹数要求（用于判断哪些组合算有效炸弹）
            
        Returns:
            有效炸弹数量
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
                # 已经是炸弹
                valid_bombs += 1
            elif remaining_jokers > 0:
                # 用万能牌补足到 4 张
                need = 4 - count
                if remaining_jokers >= need:
                    valid_bombs += 1
                    remaining_jokers -= need
        
        return valid_bombs

    def find_bombs_with_jokers(self) -> List[Bomb]:
        """
        找出所有炸弹（含万能牌补充的）。
        用于统计展示。
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
        
        # 再找可用万能牌补足的潜在炸弹（3 张同点数）
        potentials = []
        for rank, count in counter.items():
            if rank not in ['👑', '🃏'] and count == 3:
                potentials.append((rank, count))
        
        potentials.sort(key=lambda x: x[0])  # 按牌面值排序
        
        for rank, count in potentials:
            if remaining_jokers > 0:
                bomb_cards = [c for c in self.cards if c.rank == rank]
                # 加一张万能牌代表补充（实际展示用）
                joker_card = Card(rank='👑', suit='+癞子')
                bomb_cards.append(joker_card)
                bombs.append(Bomb(cards=bomb_cards, rank=rank))
                remaining_jokers -= 1
        
        return sorted(bombs, key=lambda b: b.value(), reverse=True)
    

    def count_sequences(self) -> int:
        """
        统计顺子数量（5+张连牌，无视花色，从大到小统计）。
        炸弹用过的牌不参与顺子统计。
        用过的牌不重复统计。
        """
        counter = self.count_by_rank()
        # 减去炸弹用过的牌（天然炸弹 >= 4 张同点数）
        for rank in list(counter.keys()):
            if rank not in ['👑', '🃏'] and counter[rank] >= 4:
                counter[rank] -= counter[rank]  # 全部扣除
        
        rank_order = [r for r in CARD_RANKS]
        
        seq_count = 0
        while True:
            # 从大到小找第一个能组成顺子的起始位置
            found = False
            for start in range(len(rank_order) - 5, -1, -1):
                can_form = True
                for j in range(start, start + 5):
                    if counter.get(rank_order[j], 0) <= 0:
                        can_form = False
                        break
                if can_form:
                    # 组成顺子，扣除牌
                    for j in range(start, start + 5):
                        counter[rank_order[j]] -= 1
                    seq_count += 1
                    found = True
                    break
            if not found:
                break
        
        return seq_count

    def count_pairs(self) -> int:
        """
        统计对子数量（2张同点数，无视花色，从大到小统计）。
        炸弹用过的牌不能算，顺子用过的可以重复计算。
        算过的牌不能再算。
        """
        counter = self.count_by_rank()
        # 减去炸弹用过的牌
        for rank in list(counter.keys()):
            if rank not in ['👑', '🃏'] and counter[rank] >= 4:
                counter[rank] -= counter[rank]
        
        pair_count = 0
        for rank in reversed(CARD_RANKS):
            if rank in ['👑', '🃏']:
                continue
            count = counter.get(rank, 0)
            if count >= 2:
                pair_count += count // 2
        return pair_count

    def count_triplets(self) -> int:
        """
        统计三条数量（3张同点数，无视花色，从大到小统计）。
        炸弹用过的牌不能算，顺子和对子用过的可以重复计算。
        算过的牌不能再算。
        """
        counter = self.count_by_rank()
        # 减去炸弹用过的牌
        for rank in list(counter.keys()):
            if rank not in ['👑', '🃏'] and counter[rank] >= 4:
                counter[rank] -= counter[rank]
        
        triplet_count = 0
        for rank in reversed(CARD_RANKS):
            if rank in ['👑', '🃏']:
                continue
            count = counter.get(rank, 0)
            if count >= 3:
                triplet_count += count // 3
        return triplet_count

    def calc_contribution_score(self) -> int:
        """
        计算贡献分：只有5线及以上炸弹才有贡献分。
        贡献分倍率：5线=1, 6线=2, 7线=4, 8线=8... = 2^(线数-5)
        4线炸弹无贡献分。
        """
        bombs = self.find_bombs()
        score = 0
        for b in bombs:
            if b.size >= 5:
                score += 2 ** (b.size - 5)
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
        
    def create_deck(self) -> List[Card]:
        """创建牌堆：2 副牌 (104 张) + 4 大王 + 4 小王 = 112 张"""
        deck = []
        
        # 2 副普通牌（每副 52 张，共 104 张）
        suits = ['♠', '♥', '♣', '♦']
        for _ in range(2):  # 2 副牌
            for suit in suits:
                for rank in CARD_RANKS:
                    deck.append(Card(rank=rank, suit=suit))
        
        # 4 张大王（万能牌/癞子）
        for _ in range(4):
            deck.append(Card(rank='👑', suit=''))
        
        # 4 张小王（万能牌/癞子）
        for _ in range(4):
            deck.append(Card(rank='🃏', suit=''))
        
        return deck
    
    def initialize_players(self):
        """初始化玩家"""
        self.players = []
        for i in range(self.num_players):
            player = Player(
                id=i,
                name=f"玩家{i + 1}",
                team=i % 2  # 对家同队：0 和 2 一队，1 和 3 一队
            )
            self.players.append(player)
    
    def deal_bombs_first(self, min_bombs_per_player: int = 2, bomb_size_range=None, jokers_per_player=None):
        """
        优先发炸弹策略（八王千变版本）
        核心思路：
        1. 随机拆分炸弹（支持可变大小）
        2. 八王（8 张万能牌）随机分给每人（支持范围配置）
        3. 校验时算上万能牌：同点数牌 + 万能牌 ≥ 4 算炸弹
        
        Args:
            min_bombs_per_player: 每人最少炸弹数
            bomb_size_range: 炸弹大小范围 [min, max]，默认 [4, 4]
            jokers_per_player: 每人王数，可以是 int（固定）、[min, max]（范围）或 None（默认每人2张）
        """
        # 1. 创建牌堆并按点数分组
        self.deck = self.create_deck()
        
        # 2. 统计每个点数的牌数
        rank_groups = defaultdict(list)
        for card in self.deck:
            rank_groups[card.rank].append(card)
        
        # 3. 分离八王和普通炸弹
        joker_cards = []
        bomb_candidates = []
        
        for rank, cards in rank_groups.items():
            if rank in ['👑', '🃏']:
                joker_cards.extend(cards)
            elif len(cards) >= 4:
                bomb_candidates.append((rank, cards))
        
        # 按牌面值排序（从小到大）
        bomb_candidates.sort(key=lambda x: RANK_VALUE.get(x[0], 0))
        
        print(f"📊 可分配炸弹点数：{len(bomb_candidates)} 种 + 八王（8 张万能牌）")
        print(f"   普通炸弹：{[(r + '(' + str(len(c)) + '张)') for r, c in bomb_candidates]}")
        print(f"   八王（癞子）: 👑×4 + 🃏×4 = 8 张（可当任意牌）")
        
        # 解析炸弹大小范围配置（用于控制拆分多样性）
        if bomb_size_range is None:
            bomb_size_range = [4, 4]  # 默认固定4张
        bomb_min_size, bomb_max_size = bomb_size_range
        
        # 4. 给每个玩家分配炸弹（随机拆分大小）
        bombs_assigned = 0
        player_bomb_count = [0] * self.num_players
        
        for rank, cards in bomb_candidates:
            total = len(cards)  # 8 张
            
            # 找出当前炸弹最少的玩家
            min_bombs = min(player_bomb_count)
            if min_bombs >= min_bombs_per_player + 2:
                break  # 大家都够了，保留一些炸弹在牌堆中作为普通牌
            
            for i in range(self.num_players):
                if player_bomb_count[i] == min_bombs:
                    # 随机决定拆分方式（避免极端拆分，最小 2 张）
                    possible_splits = []
                    for s in range(2, total - 1):  # 2 ~ 6
                        if total - s >= 2:  # 两部分都至少 2 张
                            possible_splits.append(s)
                    
                    if possible_splits:  # 始终拆分，增加多样性
                        split_size = random.choice(possible_splits)
                        
                        # 第一部分给当前玩家
                        for card in cards[:split_size]:
                            self.players[i].hand.add(card)
                        player_bomb_count[i] += 1
                        bombs_assigned += 1
                        
                        # 剩余部分给另一个炸弹最少的玩家
                        other_min = min(player_bomb_count)
                        other_idx = player_bomb_count.index(other_min)
                        if other_idx != i:  # 确保不是同一个玩家
                            for card in cards[split_size:]:
                                self.players[other_idx].hand.add(card)
                            player_bomb_count[other_idx] += 1
                            bombs_assigned += 1
                        else:
                            # 如果所有玩家炸弹数相同，给下一个
                            other_idx = (i + 1) % self.num_players
                            for card in cards[split_size:]:
                                self.players[other_idx].hand.add(card)
                            player_bomb_count[other_idx] += 1
                            bombs_assigned += 1
                    elif total >= 4:
                        # 全部给一个玩家
                        for card in cards:
                            self.players[i].hand.add(card)
                        player_bomb_count[i] += 1
                        bombs_assigned += 1
                    
                    # 从牌堆移除已发的牌
                    for card in cards:
                        if card in self.deck:
                            self.deck.remove(card)
                    
                    break
        
        print(f"✅ 炸弹分配完成：共分配 {bombs_assigned} 个炸弹")
        print(f"   每人炸弹数：{player_bomb_count}")
        print(f"   炸弹大小范围：{bomb_min_size}~{bomb_max_size} 张")
        
        # 5. 分配八王（万能牌）
        print(f"\n🃏 开始分配八王（万能牌）...")
        
        # 解析 jokers_per_player 配置
        if jokers_per_player is None:
            joker_range = [2, 2]  # 默认每人2张
        elif isinstance(jokers_per_player, int):
            joker_range = [jokers_per_player, jokers_per_player]
        elif isinstance(jokers_per_player, (list, tuple)) and len(jokers_per_player) == 2:
            joker_range = [int(jokers_per_player[0]), int(jokers_per_player[1])]
        else:
            joker_range = [2, 2]
        
        # 生成每人王数（随机但总和=8）
        joker_distribution = self._generate_joker_distribution(joker_range)
        
        joker_idx = 0
        random.shuffle(joker_cards)  # 打乱王的顺序（大小王混合）
        for i in range(self.num_players):
            for _ in range(joker_distribution[i]):
                if joker_idx < len(joker_cards):
                    self.players[i].hand.add(joker_cards[joker_idx])
                    joker_idx += 1
        
        dist_str = '、'.join([f"玩家{i+1}×{joker_distribution[i]}" for i in range(self.num_players)])
        print(f"✅ 八王分配完成：{joker_idx} 张万能牌，分布：{dist_str}")
        
        # 5b. 校验：检查每人有效炸弹数（含万能牌补充）
        print(f"\n🔍 校验有效炸弹数（含万能牌补充）...")
        for i, player in enumerate(self.players):
            natural_bombs = len(player.hand.find_bombs_with_jokers())
            effective_bombs = player.hand.count_effective_bombs()
            status = "✅" if effective_bombs >= min_bombs_per_player else "⚠️"
            print(f"   玩家{i+1}: 天然炸弹 {natural_bombs} 个 → 有效炸弹 {effective_bombs} 个 {status}")
        
        # 从牌堆移除已发的八王
        for card in joker_cards[:joker_idx]:
            if card in self.deck:
                self.deck.remove(card)
        
        return bombs_assigned
    
    def deal_remaining_cards(self):
        """发完剩余的牌，每人 28 张"""
        # 洗牌
        random.shuffle(self.deck)
        
        # 计算每个玩家还需要多少张牌
        cards_needed = [28 - p.hand.total_cards() for p in self.players]
        
        print(f"📋 剩余牌数：{len(self.deck)} 张")
        print(f"   每人还需：{cards_needed} 张")
        
        # 轮流发牌
        player_idx = 0
        while self.deck and any(needed > 0 for needed in cards_needed):
            if cards_needed[player_idx] > 0:
                card = self.deck.pop()
                self.players[player_idx].hand.add(card)
                cards_needed[player_idx] -= 1
            
            player_idx = (player_idx + 1) % self.num_players
        
        # 检查是否发完
        total_dealt = sum(p.hand.total_cards() for p in self.players)
        print(f"✅ 发牌完成：共发出 {total_dealt} 张（每人 28 张）")
    
    def _generate_joker_distribution(self, joker_range: list) -> list:
        """
        生成八王分配方案，保证每人王数在范围内，总和=8张。
        
        Args:
            joker_range: [min, max] 每人王数范围
            
        Returns:
            每人分到的王数列表，如 [1, 3, 2, 2]
        """
        j_min, j_max = joker_range
        num_players = self.num_players
        total_jokers = 8
        
        # 检查范围是否合理：最小值*4 <= 8 <= 最大值*4
        if j_min * num_players > total_jokers or j_max * num_players < total_jokers:
            # 范围不合理，回退到平均分配（每人2张）
            return [2] * num_players
        
        # 多次尝试，生成满足条件的分配方案
        for _ in range(100):
            # 给每人随机分配 [j_min, j_max]
            dist = [random.randint(j_min, j_max) for _ in range(num_players)]
            if sum(dist) == total_jokers:
                return dist
        
        # 如果随机都失败，用贪心构造一个合法方案
        dist = [j_min] * num_players
        remaining = total_jokers - sum(dist)
        for i in range(remaining):
            dist[i % num_players] += 1
        return dist
    
    def deal(self, min_bombs_per_player: int = 2, bomb_size_range=None, jokers_per_player=None, verbose: bool = True) -> List[Player]:
        """
        完整发牌流程
        
        Args:
            min_bombs_per_player: 每人最少炸弹数
            bomb_size_range: 炸弹大小范围 [min, max]
            jokers_per_player: 每人王数
            verbose: 是否输出详细信息
        """
        print("=" * 60)
        print("🎴 双扣 - 八王千变 发牌器")
        print("=" * 60)
        
        # 1. 初始化玩家
        self.initialize_players()
        
        # 2. 优先发炸弹 + 分配八王
        self.deal_bombs_first(min_bombs_per_player, bomb_size_range=bomb_size_range, jokers_per_player=jokers_per_player)
        
        # 3. 发完剩余牌
        self.deal_remaining_cards()
        
        # 4. 输出结果
        if verbose:
            print("\n" + "=" * 60)
            print("📊 发牌结果")
            print("=" * 60)
            
            for player in self.players:
                bombs = player.hand.find_bombs()
                print(f"\n{player.name} (队伍{player.team}):")
                print(f"   手牌：{player.hand}")
                print(f"   炸弹：{len(bombs)} 个")
                for bomb in bombs:
                    print(f"      - {bomb}")
        
        return self.players
    
    def analyze_hands(self) -> Dict:
        """分析发牌结果"""
        result = {
            'total_bombs': 0,
            'bombs_by_player': [],
            'bomb_sizes': [],
            'avg_bombs_per_player': 0
        }
        
        for player in self.players:
            bombs = player.hand.find_bombs()
            result['total_bombs'] += len(bombs)
            result['bombs_by_player'].append(len(bombs))
            for bomb in bombs:
                result['bomb_sizes'].append(bomb.size)
        
        result['avg_bombs_per_player'] = result['total_bombs'] / self.num_players
        
        return result


# ==================== 主程序 ====================

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='双扣 - 八王千变 发牌器')
    parser.add_argument('--players', type=int, default=4, help='玩家人数（默认 4）')
    parser.add_argument('--bombs', type=int, default=2, help='每人最少炸弹数（默认 2）')
    parser.add_argument('--seed', type=int, default=None, help='随机种子（可复现）')
    
    args = parser.parse_args()
    
    if args.seed is not None:
        random.seed(args.seed)
    
    dealer = ShuangkouDealer(num_players=args.players)
    dealer.deal(min_bombs_per_player=args.bombs)
    
    # 分析结果
    analysis = dealer.analyze_hands()
    print("\n" + "=" * 60)
    print("📈 统计分析")
    print("=" * 60)
    print(f"总炸弹数：{analysis['total_bombs']} 个")
    print(f"每人炸弹数：{analysis['bombs_by_player']}")
    print(f"平均每人：{analysis['avg_bombs_per_player']:.1f} 个炸弹")
    print(f"炸弹大小分布：{Counter(analysis['bomb_sizes'])}")


if __name__ == '__main__':
    main()
