#!/usr/bin/env python3
"""
HTML比較表生成モジュール
最新データでindex.htmlを動的に生成
"""

from datetime import datetime, timezone, timedelta
from typing import List, Dict


def generate_html(properties: List[Dict], total_discovered: int = 0) -> str:
    """
    物件データからHTMLを生成
    
    Args:
        properties: 物件データのリスト
        total_discovered: 自動検出で発見した物件の総数
    
    Returns:
        完全なHTMLドキュメント
    """
    
    # 有効な物件のみをフィルタリングしてソート
    valid_properties = [p for p in properties if 'error' not in p and 'price_per_sqm' in p]
    sorted_properties = sorted(valid_properties, key=lambda x: x.get('price_per_sqm', float('inf')))
    
    # 日本時間（JST = UTC+9）で表示
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst)
    timestamp = now.strftime('%Y年%m月%d日 %H:%M')
    
    # HTMLテーブル行を生成
    table_rows = []
    for i, prop in enumerate(sorted_properties, 1):
        favorite = prop.get('favorite_count', 0)
        favorite_display = str(favorite) if favorite else '-'
        
        row = f"""                    <tr>
                        <td><span class="rank">{i}位</span></td>
                        <td><span class="property-id">{prop.get('kanri_no', '-')}</span></td>
                        <td><span class="price">{prop.get('price', 0):,}万円</span></td>
                        <td><span class="unit-price">{prop.get('price_per_sqm', 0):.2f}万円/㎡</span></td>
                        <td><span class="tsubo-price">{prop.get('price_per_tsubo', 0):.1f}万円/坪</span></td>
                        <td>{prop.get('madori', '-')}</td>
                        <td>{prop.get('area', 0):.2f}㎡</td>
                        <td><span class="badge badge-{get_building_class(prop.get('building', ''))}">{prop.get('building', '-')}</span></td>
                        <td>{prop.get('floor', '-')}</td>
                        <td>{prop.get('built', '-')}</td>
                        <td>{prop.get('direction', '-')}</td>
                        <td><span class="badge badge-reform-{'yes' if prop.get('reform') == '有' else 'no'}">{prop.get('reform', '-')}</span></td>
                        <td>{favorite_display}</td>
                        <td>{prop.get('staff', '-')}</td>
                    </tr>"""
        table_rows.append(row)
    
    # 物件リンク一覧を生成
    link_items = []
    for prop in sorted_properties:
        link = f"""            <div class="link-item">
                <span><strong>{prop.get('kanri_no', '-')}</strong> - {prop.get('building', '-')} {prop.get('floor', '-')} {prop.get('madori', '-')} {prop.get('area', 0):.2f}㎡</span>
                <a href="{prop.get('url', '#')}" target="_blank">詳細を見る →</a>
            </div>"""
        link_items.append(link)
    
    # HTML全体を生成
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RISE比較表</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        :root {{
            --bg-primary: #f8fafc;
            --bg-secondary: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --accent-primary: #3b82f6;
            --accent-secondary: #8b5cf6;
            --border-color: #e2e8f0;
            --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            --shadow-lg: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
        }}

        [data-theme="dark"] {{
            --bg-primary: #0f172a;
            --bg-secondary: #1e293b;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --border-color: #334155;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans JP', sans-serif;
            background: linear-gradient(135deg, var(--bg-primary) 0%, #e0e7ff 100%);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 2rem 1rem;
            transition: all 0.3s ease;
        }}

        [data-theme="dark"] body {{
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        .header {{
            text-align: center;
            margin-bottom: 3rem;
            animation: fadeInDown 0.6s ease;
        }}

        .header h1 {{
            font-size: 2.5rem;
            font-weight: 800;
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
        }}

        .header .subtitle {{
            color: var(--text-secondary);
            font-size: 1rem;
            margin-top: 0.5rem;
        }}

        .controls {{
            display: flex;
            justify-content: flex-end;
            margin-bottom: 2rem;
            gap: 1rem;
        }}

        .theme-toggle {{
            background: var(--bg-secondary);
            border: 2px solid var(--border-color);
            color: var(--text-primary);
            padding: 0.5rem 1rem;
            border-radius: 0.5rem;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.3s ease;
            box-shadow: var(--shadow);
        }}

        .theme-toggle:hover {{
            transform: translateY(-2px);
            box-shadow: var(--shadow-lg);
        }}

        .table-container {{
            background: var(--bg-secondary);
            border-radius: 1rem;
            overflow: hidden;
            box-shadow: var(--shadow-lg);
            animation: fadeInUp 0.6s ease;
            margin-bottom: 2rem;
        }}

        .table-header {{
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: white;
            padding: 1.5rem;
            text-align: center;
        }}

        .table-header h2 {{
            font-size: 1.5rem;
            font-weight: 700;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        thead {{
            background: var(--bg-primary);
        }}

        th {{
            padding: 1rem;
            text-align: left;
            font-weight: 600;
            color: var(--text-secondary);
            border-bottom: 2px solid var(--border-color);
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        tbody tr {{
            border-bottom: 1px solid var(--border-color);
            transition: all 0.2s ease;
        }}

        tbody tr:hover {{
            background: var(--bg-primary);
            transform: scale(1.01);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        }}

        td {{
            padding: 1rem;
            font-size: 0.95rem;
        }}

        .rank {{
            font-weight: 600;
            font-size: 0.95rem;
            color: var(--text-secondary);
        }}

        .property-id {{
            font-family: 'Courier New', monospace;
            font-weight: 400;
            color: var(--text-primary);
        }}

        .price {{
            font-weight: 700;
            color: var(--text-primary);
            font-size: 0.95rem;
        }}

        .unit-price {{
            color: var(--text-primary);
            font-weight: 400;
            font-size: 0.95rem;
        }}

        .tsubo-price {{
            color: var(--accent-primary);
            font-weight: 700;
            font-size: 0.95rem;
        }}

        .badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-align: center;
        }}

        .badge-east {{
            background: #dbeafe;
            color: #1e40af;
        }}

        .badge-west {{
            background: #fce7f3;
            color: #9f1239;
        }}

        .badge-central {{
            background: #dcfce7;
            color: #166534;
        }}

        .badge-reform-yes {{
            background: #d1fae5;
            color: #065f46;
        }}

        .badge-reform-no {{
            background: #fee2e2;
            color: #991b1b;
        }}

        [data-theme="dark"] .badge-east {{
            background: #1e3a8a;
            color: #bfdbfe;
        }}

        [data-theme="dark"] .badge-west {{
            background: #831843;
            color: #fbcfe8;
        }}

        [data-theme="dark"] .badge-central {{
            background: #14532d;
            color: #bbf7d0;
        }}

        [data-theme="dark"] .badge-reform-yes {{
            background: #064e3b;
            color: #a7f3d0;
        }}

        [data-theme="dark"] .badge-reform-no {{
            background: #7f1d1d;
            color: #fecaca;
        }}

        .links-container {{
            background: var(--bg-secondary);
            border-radius: 1rem;
            padding: 2rem;
            box-shadow: var(--shadow-lg);
            margin-bottom: 2rem;
            animation: fadeInUp 0.8s ease;
        }}

        .links-container h2 {{
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
            color: var(--text-primary);
        }}

        .link-item {{
            display: flex;
            align-items: center;
            padding: 1rem;
            margin-bottom: 0.5rem;
            background: var(--bg-primary);
            border-radius: 0.5rem;
            border: 1px solid var(--border-color);
            transition: all 0.2s ease;
        }}

        .link-item:hover {{
            transform: translateX(8px);
            border-color: var(--accent-primary);
            box-shadow: var(--shadow);
        }}

        .link-item a {{
            color: var(--accent-primary);
            text-decoration: none;
            font-weight: 500;
            margin-left: auto;
        }}

        .link-item a:hover {{
            text-decoration: underline;
        }}

        .contact-info {{
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: white;
            border-radius: 1rem;
            padding: 2rem;
            box-shadow: var(--shadow-lg);
            animation: fadeInUp 1s ease;
        }}

        .contact-info h3 {{
            font-size: 1.5rem;
            margin-bottom: 1rem;
            font-weight: 700;
        }}

        .contact-info p {{
            margin-bottom: 0.5rem;
            font-size: 1rem;
        }}

        .contact-info strong {{
            display: inline-block;
            min-width: 100px;
        }}

        @keyframes fadeInDown {{
            from {{
                opacity: 0;
                transform: translateY(-20px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        @keyframes fadeInUp {{
            from {{
                opacity: 0;
                transform: translateY(20px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}

        @media (max-width: 1200px) {{
            table {{
                font-size: 0.85rem;
            }}
            th, td {{
                padding: 0.75rem 0.5rem;
            }}
        }}

        @media (max-width: 768px) {{
            .header h1 {{
                font-size: 1.75rem;
            }}
            
            .table-container {{
                overflow-x: auto;
            }}
            
            table {{
                min-width: 1000px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>RISE比較表</h1>
            <p class="subtitle">作成日時: {timestamp} | 自動検出: {len(sorted_properties)}件</p>
        </div>

        <div class="controls">
            <button class="theme-toggle" onclick="toggleTheme()">🌙 ダークモード切替</button>
        </div>

        <div class="table-container">
            <div class="table-header">
                <h2>📊 比較表（平米単価順）</h2>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>順位</th>
                        <th>管理番号</th>
                        <th>販売価格</th>
                        <th>平米単価</th>
                        <th>坪単価</th>
                        <th>間取り</th>
                        <th>専有面積</th>
                        <th>棟名</th>
                        <th>階数</th>
                        <th>築年月</th>
                        <th>向き</th>
                        <th>リフォーム</th>
                        <th>お気に入り</th>
                        <th>担当者</th>
                    </tr>
                </thead>
                <tbody>
{chr(10).join(table_rows)}
                </tbody>
            </table>
        </div>

        <div class="links-container">
            <h2>🔗 物件リンク一覧</h2>
{chr(10).join(link_items)}
        </div>

        <div class="contact-info">
            <h3>📞 問い合わせ先</h3>
            <p><strong>会社:</strong> 東急リバブル 二子玉川センター</p>
            <p><strong>電話:</strong> 0120-938-291（無料）</p>
            <p><strong>営業時間:</strong> 10:00〜18:00</p>
            <p><strong>定休日:</strong> 毎週火曜日・水曜日</p>
        </div>
    </div>

    <script>
        function toggleTheme() {{
            const html = document.documentElement;
            const currentTheme = html.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        }}

        // ページロード時にテーマを復元
        window.addEventListener('DOMContentLoaded', () => {{
            const savedTheme = localStorage.getItem('theme') || 'light';
            document.documentElement.setAttribute('data-theme', savedTheme);
        }});
    </script>
</body>
</html>"""
    
    return html


def get_building_class(building: str) -> str:
    """棟名からCSSクラス名を取得"""
    building_map = {
        'イースト': 'east',
        'ウエスト': 'west',
        'セントラル': 'central',
    }
    return building_map.get(building, '')


if __name__ == "__main__":
    """テスト用"""
    test_props = [
        {
            'kanri_no': 'C13252K32',
            'price': 15800,
            'price_per_sqm': 224.69,
            'price_per_tsubo': 741.5,
            'madori': '2LDK',
            'area': 70.32,
            'building': 'イースト',
            'floor': '17/42',
            'built': '2010年5月',
            'direction': '南東',
            'reform': '無',
            'favorite_count': 3,
            'staff': '行方',
            'url': 'https://www.livable.co.jp/mansion/C13252K32/',
        }
    ]
    
    html = generate_html(test_props)
    
    with open('test_output.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("✓ test_output.html を生成しました")

