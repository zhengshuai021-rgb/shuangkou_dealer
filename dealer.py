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
        """找出所有炸弹（4 张及以上）"""
        bombs = []
        counter = self.count_by_rank()
        for rank, count in counter.items():
            if count >= 4:
                bomb_cards = [c for c in self.cards if c.rank == rank]
                bombs.append(Bomb(cards=bomb_cards, rank=rank))
        return sorted(bombs, key=lambda b: b.value(), reverse=True)
    
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
    
    def deal_bombs_first(self, min_bombs_per_player: int = 2):
        """
        优先发炸弹策略（八王千变版本）
        核心思路：
        1. 先确保每人有指定数量的普通炸弹
        2. 八王（8 张万能牌）均匀分给每人 2 张
        3. 再发其他牌
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
        
        # 4. 给每个玩家分配炸弹
        bombs_assigned = 0
        player_bomb_count = [0] * self.num_players
        
        for rank, cards in bomb_candidates:
            # 找出当前炸弹最少的玩家
            min_bombs = min(player_bomb_count)
            if min_bombs >= min_bombs_per_player:
                break  # 所有人都已达到最小炸弹数
            
            # 给炸弹最少的玩家发这个炸弹
            for i in range(self.num_players):
                if player_bomb_count[i] == min_bombs:
                    # 发牌（全部 8 张或拆分）
                    cards_to_deal = cards[:8] if len(cards) >= 8 else cards
                    
                    # 可以拆分成两个 4 张炸弹
                    if len(cards_to_deal) >= 8 and player_bomb_count[i] < min_bombs_per_player:
                        # 发 4 张
                        for card in cards_to_deal[:4]:
                            self.players[i].hand.add(card)
                        player_bomb_count[i] += 1
                        bombs_assigned += 1
                        
                        # 剩下 4 张给另一个玩家
                        other_player = (i + 1) % self.num_players
                        for card in cards_to_deal[4:8]:
                            self.players[other_player].hand.add(card)
                        player_bomb_count[other_player] += 1
                        bombs_assigned += 1
                    elif len(cards_to_deal) >= 4:
                        # 发一个完整炸弹
                        for card in cards_to_deal[:4]:
                            self.players[i].hand.add(card)
                        player_bomb_count[i] += 1
                        bombs_assigned += 1
                    
                    # 从牌堆移除已发的牌
                    for card in cards_to_deal:
                        if card in self.deck:
                            self.deck.remove(card)
                    
                    break
        
        print(f"✅ 炸弹分配完成：共分配 {bombs_assigned} 个炸弹")
        print(f"   每人炸弹数：{player_bomb_count}")
        
        # 5. 分配八王（万能牌）- 每人 2 张
        print(f"\n🃏 开始分配八王（万能牌）...")
        joker_idx = 0
        for i in range(self.num_players):
            # 每人分 2 张王
            for _ in range(2):
                if joker_idx < len(joker_cards):
                    self.players[i].hand.add(joker_cards[joker_idx])
                    joker_idx += 1
        
        print(f"✅ 八王分配完成：{joker_idx} 张万能牌，每人 2 张")
        
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
    
    def deal(self, min_bombs_per_player: int = 2, verbose: bool = True) -> List[Player]:
        """
        完整发牌流程
        
        Args:
            min_bombs_per_player: 每人最少炸弹数
            verbose: 是否输出详细信息
        """
        print("=" * 60)
        print("🎴 双扣 - 八王千变 发牌器")
        print("=" * 60)
        
        # 1. 初始化玩家
        self.initialize_players()
        
        # 2. 优先发炸弹
        self.deal_bombs_first(min_bombs_per_player)
        
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
