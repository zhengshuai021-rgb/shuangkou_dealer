#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双扣发牌器测试脚本
测试不同配置下的发牌效果
"""

from dealer import ShuangkouDealer, CARD_RANKS
from collections import Counter
import random

def test_basic_deal():
    """测试基础发牌"""
    print("\n" + "=" * 60)
    print("🧪 测试 1: 基础发牌（每人至少 2 个炸弹）")
    print("=" * 60)
    
    dealer = ShuangkouDealer(num_players=4)
    dealer.deal(min_bombs_per_player=2, verbose=True)
    
    analysis = dealer.analyze_hands()
    assert analysis['total_bombs'] >= 8, f"炸弹总数应该 >= 8，实际 {analysis['total_bombs']}"
    print(f"\n✅ 测试通过：总炸弹数 {analysis['total_bombs']} 个")


def test_high_bombs():
    """测试高炸弹密度"""
    print("\n" + "=" * 60)
    print("🧪 测试 2: 高炸弹密度（每人至少 3 个炸弹）")
    print("=" * 60)
    
    dealer = ShuangkouDealer(num_players=4)
    dealer.deal(min_bombs_per_player=3, verbose=True)
    
    analysis = dealer.analyze_hands()
    print(f"\n📊 结果：总炸弹数 {analysis['total_bombs']} 个")
    print(f"   每人：{analysis['bombs_by_player']}")


def test_bomb_distribution():
    """测试炸弹大小分布"""
    print("\n" + "=" * 60)
    print("🧪 测试 3: 炸弹大小分布统计")
    print("=" * 60)
    
    all_bomb_sizes = []
    
    for i in range(10):
        dealer = ShuangkouDealer(num_players=4)
        dealer.deal(min_bombs_per_player=2, verbose=False)
        analysis = dealer.analyze_hands()
        all_bomb_sizes.extend(analysis['bomb_sizes'])
    
    size_counter = Counter(all_bomb_sizes)
    print(f"\n📊 10 次发牌统计（共 {len(all_bomb_sizes)} 个炸弹）:")
    for size in sorted(size_counter.keys()):
        count = size_counter[size]
        pct = count / len(all_bomb_sizes) * 100
        print(f"   {size}张炸弹：{count} 个 ({pct:.1f}%)")


def test_card_count():
    """测试牌数正确性"""
    print("\n" + "=" * 60)
    print("🧪 测试 4: 牌数验证")
    print("=" * 60)
    
    dealer = ShuangkouDealer(num_players=4)
    dealer.deal(min_bombs_per_player=2, verbose=False)
    
    total_cards = sum(p.hand.total_cards() for p in dealer.players)
    print(f"\n📊 牌数统计:")
    print(f"   总牌数：{total_cards} 张（应为 112 张）")
    print(f"   每人：{[p.hand.total_cards() for p in dealer.players]} 张（应各 28 张）")
    
    assert total_cards == 112, f"总牌数错误：{total_cards}"
    assert all(p.hand.total_cards() == 28 for p in dealer.players), "每人牌数应为 28 张"
    print(f"\n✅ 测试通过")


def test_team_distribution():
    """测试队伍牌力分布"""
    print("\n" + "=" * 60)
    print("🧪 测试 5: 队伍牌力平衡")
    print("=" * 60)
    
    dealer = ShuangkouDealer(num_players=4)
    dealer.deal(min_bombs_per_player=2, verbose=False)
    
    team0_bombs = 0
    team1_bombs = 0
    
    for player in dealer.players:
        bombs = len(player.hand.find_bombs())
        if player.team == 0:
            team0_bombs += bombs
        else:
            team1_bombs += bombs
    
    print(f"\n📊 队伍炸弹分布:")
    print(f"   队伍 0（玩家 1、3）: {team0_bombs} 个炸弹")
    print(f"   队伍 1（玩家 2、4）: {team1_bombs} 个炸弹")
    print(f"   差距：{abs(team0_bombs - team1_bombs)} 个")


def test_chain_bombs_skip():
    """测试连炸预设关闭（默认行为）"""
    print("\n" + "=" * 60)
    print("🧪 测试 6: 连炸预设关闭（min_chains_per_player=0）")
    print("=" * 60)
    
    dealer = ShuangkouDealer(num_players=4)
    dealer.deal(min_bombs_per_player=2, min_chains_per_player=0, verbose=True)
    
    total_cards = sum(p.hand.total_cards() for p in dealer.players)
    assert total_cards == 112, f"总牌数错误：{total_cards}"
    print(f"\n✅ 测试通过：连炸预设已跳过，总牌数 {total_cards} 张")


def test_chain_bombs_enabled():
    """测试连炸预设开启"""
    print("\n" + "=" * 60)
    print("🧪 测试 7: 连炸预设开启（min_chains_per_player=1）")
    print("=" * 60)
    
    dealer = ShuangkouDealer(num_players=4)
    dealer.deal(min_bombs_per_player=2, min_chains_per_player=1, verbose=True)
    
    total_cards = sum(p.hand.total_cards() for p in dealer.players)
    assert total_cards == 112, f"总牌数错误：{total_cards}"
    assert all(p.hand.total_cards() == 28 for p in dealer.players), "每人牌数应为 28 张"
    print(f"\n✅ 测试通过：连炸预设已启用，每人 28 张牌")


def test_chain_bombs_multiple_games():
    """测试连炸预设多局稳定性"""
    print("\n" + "=" * 60)
    print("🧪 测试 8: 连炸预设多局稳定性（100 局）")
    print("=" * 60)
    
    errors = 0
    for i in range(100):
        try:
            dealer = ShuangkouDealer(num_players=4)
            dealer.deal(min_bombs_per_player=2, min_chains_per_player=1, verbose=False)
            total_cards = sum(p.hand.total_cards() for p in dealer.players)
            if total_cards != 112:
                errors += 1
                print(f"   ❌ 第 {i+1} 局：总牌数 {total_cards} != 112")
        except Exception as e:
            errors += 1
            print(f"   ❌ 第 {i+1} 局异常：{e}")
    
    print(f"\n📊 100 局统计：")
    print(f"   成功：{100 - errors} 局")
    print(f"   失败：{errors} 局")
    
    assert errors == 0, f"有 {errors} 局发牌失败"
    print(f"\n✅ 测试通过：100 局全部成功")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "🎴" * 30)
    print("双扣 - 八王千变 发牌器 测试套件 v2.0")
    print("🎴" * 30)
    
    test_card_count()
    test_basic_deal()
    test_high_bombs()
    test_bomb_distribution()
    test_team_distribution()
    test_chain_bombs_skip()
    test_chain_bombs_enabled()
    test_chain_bombs_multiple_games()
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)


if __name__ == '__main__':
    run_all_tests()
