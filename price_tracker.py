#!/usr/bin/env python3
"""
価格変遷追跡モジュール
前回データとの差分を検出し、変更履歴を記録
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class PriceTracker:
    """価格変遷追跡クラス"""
    
    def __init__(self, data_file: str = "price_tracker.json", history_dir: str = "history"):
        self.data_file = data_file
        self.history_dir = history_dir
        
        # 履歴ディレクトリを作成
        if not os.path.exists(history_dir):
            os.makedirs(history_dir)
    
    def load_previous_data(self) -> Dict:
        """前回のデータを読み込む"""
        if not os.path.exists(self.data_file):
            return {}
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"前回データの読み込みに失敗: {e}")
            return {}
    
    def save_current_data(self, properties: List[Dict]):
        """現在のデータを保存"""
        tracker_data = {}
        today = datetime.now().strftime('%Y-%m-%d')
        
        for prop in properties:
            if 'error' in prop:
                continue
            
            kanri_no = prop.get('kanri_no')
            if not kanri_no:
                continue
            
            # 既存の履歴を読み込む
            previous = self.load_previous_data()
            
            if kanri_no in previous:
                # 既存物件の場合、履歴に追加
                history = previous[kanri_no].get('history', [])
            else:
                # 新規物件の場合
                history = []
            
            # 今日のデータを追加（重複チェック）
            if not history or history[-1]['date'] != today:
                history.append({
                    'date': today,
                    'price': prop.get('price'),
                    'price_per_sqm': prop.get('price_per_sqm'),
                    'price_per_tsubo': prop.get('price_per_tsubo'),
                    'area': prop.get('area'),
                })
            
            # 統計情報を計算
            prices = [h['price'] for h in history if h.get('price')]
            
            tracker_data[kanri_no] = {
                'history': history,
                'first_seen': history[0]['date'] if history else today,
                'initial_price': history[0].get('price') if history else prop.get('price'),
                'current_price': prop.get('price'),
                'current_area': prop.get('area'),
                'max_price': max(prices) if prices else None,
                'min_price': min(prices) if prices else None,
                'total_change': prop.get('price', 0) - history[0].get('price', 0) if history else 0,
                'building': prop.get('building'),
                'floor': prop.get('floor'),
                'madori': prop.get('madori'),
                'staff': prop.get('staff'),
            }
        
        # ファイルに保存
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(tracker_data, f, ensure_ascii=False, indent=2)
        
        # 日次スナップショットも保存
        snapshot_file = os.path.join(self.history_dir, f"{today}.json")
        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump({
                'date': today,
                'properties': [p for p in properties if 'error' not in p]
            }, f, ensure_ascii=False, indent=2)
    
    def detect_changes(self, current_properties: List[Dict]) -> Dict:
        """
        前回データと今回データを比較して変更を検出
        
        Returns:
            {
                'price_changes': [...],
                'new_properties': [...],
                'ended_properties': [...],
                'reform_changes': [...],
                'staff_changes': [...]
            }
        """
        previous = self.load_previous_data()
        
        # 現在の物件IDセット
        current_ids = {p.get('kanri_no') for p in current_properties if 'error' not in p and p.get('kanri_no')}
        previous_ids = set(previous.keys())
        
        changes = {
            'price_changes': [],
            'new_properties': [],
            'ended_properties': [],
            'reform_changes': [],
            'staff_changes': [],
        }
        
        # 価格変更・リフォーム変更・担当者変更を検出
        for prop in current_properties:
            if 'error' in prop:
                continue
            
            kanri_no = prop.get('kanri_no')
            if not kanri_no:
                continue
            
            if kanri_no in previous:
                prev_data = previous[kanri_no]
                
                # 価格変更
                current_price = prop.get('price')
                previous_price = prev_data.get('current_price')
                
                if current_price and previous_price and current_price != previous_price:
                    change_amount = current_price - previous_price
                    change_rate = (change_amount / previous_price) * 100
                    
                    changes['price_changes'].append({
                        'kanri_no': kanri_no,
                        'building': prop.get('building'),
                        'floor': prop.get('floor'),
                        'madori': prop.get('madori'),
                        'area': prop.get('area'),
                        'before': previous_price,
                        'after': current_price,
                        'change_amount': change_amount,
                        'change_rate': change_rate,
                    })
                
                # リフォーム状況変更（もし実装する場合）
                # 現在のスクリプトではリフォーム情報を保存していないため、今後の拡張
                
                # 担当者変更
                current_staff = prop.get('staff')
                previous_staff = prev_data.get('staff')
                if current_staff and previous_staff and current_staff != previous_staff:
                    changes['staff_changes'].append({
                        'kanri_no': kanri_no,
                        'building': prop.get('building'),
                        'floor': prop.get('floor'),
                        'before': previous_staff,
                        'after': current_staff,
                    })
            else:
                # 新規物件
                changes['new_properties'].append({
                    'kanri_no': kanri_no,
                    'price': prop.get('price'),
                    'area': prop.get('area'),
                    'building': prop.get('building'),
                    'floor': prop.get('floor'),
                    'madori': prop.get('madori'),
                    'price_per_tsubo': prop.get('price_per_tsubo'),
                })
        
        # 販売終了物件
        for kanri_no in previous_ids - current_ids:
            prev_data = previous[kanri_no]
            changes['ended_properties'].append({
                'kanri_no': kanri_no,
                'building': prev_data.get('building'),
                'floor': prev_data.get('floor'),
                'madori': prev_data.get('madori'),
                'final_price': prev_data.get('current_price'),
            })
        
        return changes
    
    def generate_change_report(self, changes: Dict) -> str:
        """変更レポートをMarkdown形式で生成"""
        today = datetime.now().strftime('%Y年%m月%d日')
        
        lines = [
            f"# 変更検出レポート ({today})\n",
        ]
        
        # サマリー
        has_changes = any(changes.values())
        if not has_changes:
            lines.append("## 📊 変更なし\n")
            lines.append("前回からの変更はありませんでした。\n")
            return "\n".join(lines)
        
        # 価格変更
        if changes['price_changes']:
            lines.append("## 💰 価格変更\n")
            lines.append("| 管理番号 | 物件 | 変更前 | 変更後 | 変動額 | 変動率 |")
            lines.append("|---|---|---|---|---|---|")
            
            for change in changes['price_changes']:
                direction = "🔴" if change['change_amount'] < 0 else "🔵"
                lines.append(
                    f"| {change['kanri_no']} | "
                    f"{change['building']} {change['floor']} {change['madori']} | "
                    f"{change['before']:,}万円 | "
                    f"{change['after']:,}万円 | "
                    f"{direction} {change['change_amount']:+,}万円 | "
                    f"{change['change_rate']:+.1f}% |"
                )
            lines.append("")
        
        # 新規物件
        if changes['new_properties']:
            lines.append("## 🆕 新規追加物件\n")
            lines.append("| 管理番号 | 販売価格 | 専有面積 | 坪単価 | 棟名 | 階数 | 間取り |")
            lines.append("|---|---|---|---|---|---|---|")
            
            for prop in changes['new_properties']:
                lines.append(
                    f"| {prop['kanri_no']} | "
                    f"{prop['price']:,}万円 | "
                    f"{prop['area']:.2f}㎡ | "
                    f"{prop['price_per_tsubo']:.1f}万円/坪 | "
                    f"{prop['building']} | "
                    f"{prop['floor']} | "
                    f"{prop['madori']} |"
                )
            lines.append("")
        
        # 販売終了物件
        if changes['ended_properties']:
            lines.append("## ❌ 販売終了物件\n")
            lines.append("| 管理番号 | 物件 | 最終価格 |")
            lines.append("|---|---|---|")
            
            for prop in changes['ended_properties']:
                lines.append(
                    f"| {prop['kanri_no']} | "
                    f"{prop['building']} {prop['floor']} {prop['madori']} | "
                    f"{prop['final_price']:,}万円 |"
                )
            lines.append("")
        
        # 担当者変更
        if changes['staff_changes']:
            lines.append("## 👤 担当者変更\n")
            lines.append("| 管理番号 | 物件 | 変更前 | 変更後 |")
            lines.append("|---|---|---|---|")
            
            for change in changes['staff_changes']:
                lines.append(
                    f"| {change['kanri_no']} | "
                    f"{change['building']} {change['floor']} | "
                    f"{change['before']} | "
                    f"{change['after']} |"
                )
            lines.append("")
        
        return "\n".join(lines)
    
    def get_price_history(self, kanri_no: str) -> List[Dict]:
        """特定物件の価格履歴を取得"""
        data = self.load_previous_data()
        if kanri_no in data:
            return data[kanri_no].get('history', [])
        return []
    
    def get_all_properties_summary(self) -> Dict:
        """すべての物件のサマリーを取得"""
        return self.load_previous_data()


if __name__ == "__main__":
    """テスト実行"""
    tracker = PriceTracker()
    
    # テストデータ
    test_properties = [
        {
            'kanri_no': 'C13252K32',
            'price': 15800,
            'area': 70.32,
            'price_per_sqm': 224.69,
            'price_per_tsubo': 741.5,
            'building': 'イースト',
            'floor': '17/42',
            'madori': '2LDK',
            'staff': '行方',
        }
    ]
    
    print("=== 価格追跡テスト ===")
    changes = tracker.detect_changes(test_properties)
    report = tracker.generate_change_report(changes)
    print(report)
    
    tracker.save_current_data(test_properties)
    print("\n✓ データ保存完了")


