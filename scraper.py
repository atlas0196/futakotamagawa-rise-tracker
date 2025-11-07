#!/usr/bin/env python3
"""
二子玉川ライズ 中古マンション比較表作成スクリプト v4
価格変遷追跡機能追加
"""

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import time
import sys
from price_tracker import PriceTracker
from html_generator import generate_html

# 日本時間（JST）のタイムゾーン
JST = timezone(timedelta(hours=9))

# 自動検出を有効にするかどうか
AUTO_DISCOVER = True  # False にすると手動指定モードになる

# 手動指定モード用（AUTO_DISCOVER=False の場合のみ使用）
MANUAL_PROPERTY_URLS = [
    "https://www.livable.co.jp/mansion/C13252K32/",
    "https://www.livable.co.jp/mansion/C48258711/",
    "https://www.livable.co.jp/mansion/C1325X119/",
    "https://www.livable.co.jp/mansion/C13259K25/",
    "https://www.livable.co.jp/mansion/CV623ZG20/",
    "https://www.livable.co.jp/mansion/C48259B69/",
]

# 面積フィルタ（自動検出時のみ有効）
MIN_AREA = 0.0    # 最小面積（㎡）※制限なし
MAX_AREA = 999.0  # 最大面積（㎡）※制限なし

# シードURL（自動検出の起点となる物件）
SEED_URLS = [
    "https://www.livable.co.jp/mansion/C13252K32/",  # イースト
    "https://www.livable.co.jp/mansion/C48258711/",  # ウエスト
    "https://www.livable.co.jp/mansion/C13259K25/",  # セントラル
]


def extract_property_id(url: str) -> Optional[str]:
    """URLから物件IDを抽出"""
    match = re.search(r'/mansion/(C[A-Z0-9]+)/?', url)
    if match:
        return match.group(1)
    return None


def discover_related_properties(property_url: str, visited: set, headers: dict) -> List[str]:
    """物件ページから「同じ建物の他の物件」リンクを取得"""
    if not property_url.startswith('http'):
        property_url = f"https://www.livable.co.jp{property_url}"
    
    property_id = extract_property_id(property_url)
    if not property_id or property_url in visited:
        return []
    
    visited.add(property_url)
    
    try:
        response = requests.get(property_url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        related_links = []
        
        # 「他の物件」セクションを探す
        headings = soup.find_all(['h2', 'h3'], string=re.compile(r'他の物件|この建物|イースト|ウエスト|セントラル'))
        
        for heading in headings:
            next_elem = heading.find_next(['ul', 'div', 'section'])
            if next_elem:
                links = next_elem.find_all('a', href=re.compile(r'/mansion/C[A-Z0-9]+'))
                for link in links:
                    href = link.get('href')
                    if href and '/mansion/C' in href:
                        if href.startswith('/'):
                            href = f"https://www.livable.co.jp{href}"
                        related_links.append(href)
        
        # フォールバック: ページ全体から物件リンクを抽出
        if not related_links:
            for link in soup.find_all('a', href=re.compile(r'/mansion/C[A-Z0-9]+')):
                href = link.get('href')
                if href:
                    if any(x in href for x in ['mailto:', 'javascript:', 'line.me', 'twitter.com', 'facebook.com']):
                        continue
                    if href.startswith('/'):
                        href = f"https://www.livable.co.jp{href}"
                    if href != property_url:
                        related_links.append(href)
        
        return list(set(related_links))
        
    except Exception as e:
        return []


def auto_discover_properties(seed_urls: List[str], headers: dict) -> List[str]:
    """シードURLから幅優先探索で全物件を発見"""
    from collections import deque
    
    queue = deque(seed_urls)
    visited = set()
    discovered = set()
    
    print("="*60)
    print("物件自動検出を開始...")
    print("="*60)
    
    while queue:
        current_url = queue.popleft()
        
        if not current_url.startswith('http'):
            current_url = f"https://www.livable.co.jp{current_url}"
        
        property_id = extract_property_id(current_url)
        if not property_id or current_url in discovered:
            continue
        
        discovered.add(current_url)
        print(f"  ✓ {property_id} を発見 ({len(discovered)}件目)")
        
        related = discover_related_properties(current_url, visited, headers)
        
        for url in related:
            if url not in discovered:
                queue.append(url)
        
        if queue:
            time.sleep(0.5)  # レート制限（自動検出時は少し速く）
    
    print(f"  → 合計 {len(discovered)} 件の物件を発見")
    print("="*60)
    print()
    
    return sorted(list(discovered))


def find_dl_value(soup: BeautifulSoup, keyword: str) -> Optional[str]:
    """dl/dt/dd構造から特定のキーワードに対応する値を取得"""
    dt_elem = soup.find('dt', string=re.compile(keyword, re.IGNORECASE))
    if dt_elem:
        dd_elem = dt_elem.find_next_sibling('dd')
        if dd_elem:
            return dd_elem.get_text(strip=True)
    return None


def scrape_property(url: str) -> Dict:
    """物件情報を取得"""
    print(f"取得中: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 管理番号（URLから取得）
        kanri_no = url.rstrip('/').split('/')[-1]
        
        property_data = {
            'url': url,
            'kanri_no': kanri_no,
        }
        
        # 価格の抽出
        price_value = find_dl_value(soup, r'価格')
        if price_value:
            # "1億5,800万円" のような形式に対応
            if '億' in price_value:
                oku_match = re.search(r'(\d+)億([\d,]+)?万円', price_value)
                if oku_match:
                    oku = int(oku_match.group(1)) * 10000
                    man = int(oku_match.group(2).replace(',', '')) if oku_match.group(2) else 0
                    property_data['price'] = oku + man
            else:
                price_match = re.search(r'([\d,]+)万円', price_value)
                if price_match:
                    property_data['price'] = int(price_match.group(1).replace(',', ''))
        
        # 間取りの抽出
        madori_value = find_dl_value(soup, r'間取り')
        if madori_value:
            property_data['madori'] = madori_value.strip()
        
        # 専有面積の抽出
        area_value = find_dl_value(soup, r'専有面積')
        if area_value:
            # "壁芯70.32m2" のようなフォーマットから数値を抽出
            area_match = re.search(r'([\d.]+)\s*m', area_value)
            if area_match:
                property_data['area'] = float(area_match.group(1))
        
        # 所在地から棟名を抽出
        location_value = find_dl_value(soup, r'所在地')
        if location_value:
            if 'イースト' in location_value:
                property_data['building'] = 'イースト'
            elif 'ウエスト' in location_value:
                property_data['building'] = 'ウエスト'
            elif 'セントラル' in location_value:
                property_data['building'] = 'セントラル'
        
        # タイトルからも棟名を抽出（バックアップ）
        if 'building' not in property_data:
            title = soup.find('h1')
            if title:
                title_text = title.get_text()
                if 'イースト' in title_text:
                    property_data['building'] = 'イースト'
                elif 'ウエスト' in title_text:
                    property_data['building'] = 'ウエスト'
                elif 'セントラル' in title_text:
                    property_data['building'] = 'セントラル'
        
        # 階数の抽出
        floor_value = find_dl_value(soup, r'所在階数|所在階')
        if floor_value:
            # デバッグ用（後で削除）
            # print(f"  DEBUG: floor_value = {repr(floor_value)}")
            # "17階 / 地上42階 地下1階" のようなフォーマットから "17/42" を抽出
            floor_match = re.search(r'(\d+)階.*?地上(\d+)階', floor_value)
            if floor_match:
                property_data['floor'] = f"{floor_match.group(1)}/{floor_match.group(2)}"
            else:
                # より柔軟なパターン: "17階" のみでも取得
                simple_floor_match = re.search(r'(\d+)階', floor_value)
                if simple_floor_match:
                    property_data['floor'] = simple_floor_match.group(1)
        
        # 築年月の抽出
        built_value = find_dl_value(soup, r'築年月')
        if built_value:
            property_data['built'] = built_value.strip()
        
        # 向きの抽出
        direction_value = find_dl_value(soup, r'向き')
        if direction_value:
            property_data['direction'] = direction_value.strip()
        
        # リフォームの抽出（設備・条件や備考から推測）
        reform_value = find_dl_value(soup, r'リフォーム|リノベーション')
        equipment_value = find_dl_value(soup, r'設備・条件')
        remarks_value = find_dl_value(soup, r'備考')
        
        property_data['reform'] = '無'  # デフォルトは「無」
        
        # リフォーム情報をチェック
        for value in [reform_value, equipment_value, remarks_value]:
            if value and ('リフォーム' in value or 'リノベーション' in value or '改修' in value):
                if '済' in value or '有' in value:
                    property_data['reform'] = '有'
                    break
        
        # お気に入り登録数の抽出
        favorite_count = None
        
        # パターン1: 「◯件 お気に入り」のような表記を探す
        favorite_text = soup.find(string=re.compile(r'件\s*お気に入り'))
        if favorite_text:
            # 「30件 お気に入り」のような形式から数値を抽出
            parent_text = favorite_text.parent.get_text(strip=True) if favorite_text.parent else str(favorite_text)
            count_match = re.search(r'(\d+)\s*件\s*お気に入り', parent_text)
            if count_match:
                favorite_count = int(count_match.group(1))
        
        # パターン2: ハートアイコンの近くにある数値を探す
        if favorite_count is None:
            # class名に「favorite」や「like」を含む要素を探す
            favorite_elems = soup.find_all(['span', 'div', 'p'], class_=re.compile(r'favorite|like', re.IGNORECASE))
            for elem in favorite_elems:
                text = elem.get_text(strip=True)
                # 「1 件 お気に入り」のようなパターン
                count_match = re.search(r'(\d+)\s*件', text)
                if count_match and 'お気に入り' in text:
                    favorite_count = int(count_match.group(1))
                    break
        
        # パターン3: より広範囲に「お気に入り」というテキストの近くを探す
        if favorite_count is None:
            all_text = soup.get_text()
            # 「30 回閲覧」と「1 件 お気に入り」のようなパターンを探す
            matches = re.finditer(r'(\d+)\s*件\s*お気に入り', all_text)
            for match in matches:
                favorite_count = int(match.group(1))
                break
        
        property_data['favorite_count'] = favorite_count if favorite_count is not None else 0
        
        # 担当者の抽出
        contact_section = soup.find('p', string=re.compile(r'私が担当'))
        if contact_section:
            staff_elem = contact_section.find_next('p')
            if staff_elem:
                staff_name = staff_elem.get_text(strip=True)
                if staff_name:
                    property_data['staff'] = staff_name
        
        # 担当者が見つからない場合、別の方法で探す
        if 'staff' not in property_data:
            staff_elems = soup.find_all('p', class_=re.compile('contact-person__name'))
            for elem in staff_elems:
                text = elem.get_text(strip=True)
                if text and not re.match(r'^[a-zA-Z]+$', text):  # ローマ字読みを除外
                    property_data['staff'] = text
                    break
        
        # 平米単価・坪単価の計算
        if 'price' in property_data and 'area' in property_data:
            property_data['price_per_sqm'] = property_data['price'] / property_data['area']
            property_data['price_per_tsubo'] = property_data['price'] / (property_data['area'] / 3.3)
        
        # print(f"✓ {kanri_no}: 取得成功")  # main関数側で出力
        return property_data
        
    except Exception as e:
        print(f"✗ エラー ({url}): {e}")
        return {'url': url, 'kanri_no': url.rstrip('/').split('/')[-1], 'error': str(e)}


def generate_comparison_table(properties: List[Dict]) -> str:
    """比較表を生成"""
    
    # エラーがない物件のみをフィルタリング
    valid_properties = [p for p in properties if 'error' not in p and 'price_per_sqm' in p]
    
    if not valid_properties:
        return "# エラー\n\n有効な物件情報が取得できませんでした。"
    
    # 平米単価でソート
    sorted_properties = sorted(valid_properties, key=lambda x: x.get('price_per_sqm', float('inf')))
    
    # Markdown表の作成
    output = []
    output.append("# 二子玉川ライズ 中古マンション比較表\n")
    output.append(f"**作成日時**: {datetime.now(JST).strftime('%Y年%m月%d日 %H:%M')}\n")
    output.append("## 比較表（平米単価順）\n")
    
    # テーブルヘッダー
    headers = ["管理番号", "販売価格", "平米単価", "坪単価", "間取り", "専有面積", "棟名", "階数", "築年月", "向き", "リフォーム", "お気に入り", "担当者"]
    output.append("| " + " | ".join(headers) + " |")
    output.append("|" + "|".join(["---"] * len(headers)) + "|")
    
    # データ行
    for prop in sorted_properties:
        row = [
            prop.get('kanri_no', '-'),
            f"{prop.get('price', 0):,}万円" if 'price' in prop else '-',
            f"{prop.get('price_per_sqm', 0):.2f}万円/㎡" if 'price_per_sqm' in prop else '-',
            f"{prop.get('price_per_tsubo', 0):.1f}万円/坪" if 'price_per_tsubo' in prop else '-',
            prop.get('madori', '-'),
            f"{prop.get('area', 0):.2f}㎡" if 'area' in prop else '-',
            prop.get('building', '-'),
            prop.get('floor', '-'),
            prop.get('built', '-'),
            prop.get('direction', '-'),
            prop.get('reform', '-'),
            str(prop.get('favorite_count', '-')),
            prop.get('staff', '-'),
        ]
        output.append("| " + " | ".join(row) + " |")
    
    # 物件リンク一覧
    output.append("\n## 二子玉川ライズ 中古マンション物件一覧\n")
    
    for i, prop in enumerate(sorted_properties, 1):
        area_str = f"{prop.get('area', 0):.2f}㎡" if 'area' in prop else "-"
        output.append(f"{i}. **{prop.get('kanri_no', '-')}** - {prop.get('building', '-')} {prop.get('floor', '-')} {prop.get('madori', '-')} {area_str}")
        output.append(f"   {prop.get('url', '')}\n")
    
    # エラーがあった物件を表示
    error_properties = [p for p in properties if 'error' in p]
    if error_properties:
        output.append("\n## 取得に失敗した物件\n")
        for prop in error_properties:
            output.append(f"- **{prop.get('kanri_no', '-')}**: {prop.get('error', '不明なエラー')}")
            output.append(f"  {prop.get('url', '')}\n")
    
    # 問い合わせ先
    output.append("\n---\n")
    output.append("**問い合わせ先:**  ")
    output.append("東急リバブル 二子玉川センター  ")
    output.append("TEL: 0120-938-291（無料）  ")
    output.append("営業時間: 10:00～18:00  ")
    output.append("定休日: 毎週火曜日・水曜日")
    
    return "\n".join(output)


def main():
    """メイン処理"""
    print("=" * 60)
    print("二子玉川ライズ 中古マンション比較表作成 v4")
    print("=" * 60)
    print()
    
    # 価格追跡モジュールを初期化
    tracker = PriceTracker()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # 物件URLを取得（自動検出 or 手動指定）
    all_urls = []  # 発見した全物件のURL
    
    if AUTO_DISCOVER:
        print("🔍 自動検出モード")
        all_urls = auto_discover_properties(SEED_URLS, headers)
        
        # 棟名でフィルタリング（まず全物件の情報を取得）
        print("📏 棟名フィルタリング中...")
        print(f"   条件: 二子玉川ライズのみ（イースト/ウエスト/セントラル）")
        print()
        
        filtered_properties = []
        for i, url in enumerate(all_urls, 1):
            property_id = extract_property_id(url)
            print(f"[{i}/{len(all_urls)}] {property_id}: ", end="", flush=True)
            
            property_data = scrape_property(url)
            
            # 面積と棟名でフィルタリング
            if 'area' in property_data:
                area = property_data['area']
                building = property_data.get('building', '')
                
                # 面積チェック
                if MIN_AREA <= area < MAX_AREA:
                    # 棟名チェック（二子玉川ライズのみ）
                    if building in ['イースト', 'ウエスト', 'セントラル']:
                        print(f"✓ {area:.2f}㎡ {building} - 条件に合致")
                        filtered_properties.append(property_data)
                    else:
                        print(f"✗ {area:.2f}㎡ 棟名なし - 二子玉川ライズ以外")
                else:
                    print(f"✗ {area:.2f}㎡ - 範囲外")
            else:
                print("✗ 面積情報なし")
            
            if i < len(all_urls):
                time.sleep(1)
        
        properties = filtered_properties
        
        print()
        print("="*60)
        print(f"フィルタ結果: {len(properties)}/{len(all_urls)} 件が条件に合致")
        print("="*60)
        print()
        
    else:
        print("📝 手動指定モード")
        print(f"   対象: {len(MANUAL_PROPERTY_URLS)} 件")
        print()
        
        all_urls = MANUAL_PROPERTY_URLS
        
        # 各物件情報を取得
        properties = []
        for i, url in enumerate(MANUAL_PROPERTY_URLS, 1):
            property_id = extract_property_id(url)
            print(f"[{i}/{len(MANUAL_PROPERTY_URLS)}] {property_id}: ", end="", flush=True)
            property_data = scrape_property(url)
            properties.append(property_data)
            print()
            
            # サーバーに負荷をかけないよう少し待機
            if i < len(MANUAL_PROPERTY_URLS):
                time.sleep(1)
    
    # 変更検出
    print("=" * 60)
    print("変更検出中...")
    changes = tracker.detect_changes(properties)
    
    has_changes = any(changes.values())
    if has_changes:
        print("✓ 変更を検出しました")
        print(f"  - 価格変更: {len(changes['price_changes'])}件")
        print(f"  - 新規物件: {len(changes['new_properties'])}件")
        print(f"  - 販売終了: {len(changes['ended_properties'])}件")
        print(f"  - 担当者変更: {len(changes['staff_changes'])}件")
    else:
        print("変更はありませんでした")
    print("=" * 60)
    print()
    
    # 変更レポートを生成
    if has_changes:
        change_report = tracker.generate_change_report(changes)
        change_report_file = f"changes_{datetime.now(JST).strftime('%Y%m%d')}.md"
        with open(change_report_file, 'w', encoding='utf-8') as f:
            f.write(change_report)
        print(f"✓ 変更レポートを作成: {change_report_file}\n")
        print(change_report)
        print()
    
    # 価格履歴を保存
    tracker.save_current_data(properties)
    print("✓ 価格履歴を保存しました: price_tracker.json\n")
    
    # 比較表を生成
    print("=" * 60)
    print("比較表を生成中...")
    comparison_table = generate_comparison_table(properties)
    
    # ファイルに出力
    output_file = f"comparison_table_{datetime.now(JST).strftime('%Y%m%d_%H%M%S')}.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(comparison_table)
    
    # latest.md も更新
    with open('latest.md', 'w', encoding='utf-8') as f:
        f.write(comparison_table)
    
    # index.html を生成
    html_content = generate_html(properties, total_discovered=len(all_urls) if AUTO_DISCOVER else len(MANUAL_PROPERTY_URLS))
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✓ 比較表を作成しました: {output_file}")
    print(f"✓ latest.md を更新しました")
    print(f"✓ index.html を更新しました")
    print("=" * 60)
    print()
    print(comparison_table)


if __name__ == "__main__":
    main()

