#!/bin/bash
#
# RISE比較表 - 安全な更新スクリプト
# GitHubの最新版を取得してから更新を実行
#

set -e  # エラーが発生したら即座に終了

echo "========================================"
echo "RISE比較表 安全更新スクリプト"
echo "========================================"
echo ""

# 現在のディレクトリを確認
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "📁 作業ディレクトリ: $SCRIPT_DIR"
echo ""

# ステップ1: 最新版を取得
echo "🔄 ステップ1: GitHubから最新版を取得中..."
if git pull origin main; then
    echo "✅ 最新版の取得完了"
else
    echo "❌ Git pull失敗"
    echo "   → 手動で解決してください: git pull origin main"
    exit 1
fi
echo ""

# ステップ2: データ更新
echo "📊 ステップ2: 物件データを取得中..."
if python3 scraper.py; then
    echo "✅ データ取得完了"
else
    echo "❌ スクリプト実行失敗"
    echo "   → エラー内容を確認してください"
    exit 1
fi
echo ""

# ステップ3: 変更内容を確認
echo "📝 ステップ3: 変更内容を確認..."
git status --short
echo ""

# ステップ4: コミット
echo "💾 ステップ4: 変更をコミット中..."
git add -A

if git diff --staged --quiet; then
    echo "⚠️  変更がありません - コミットをスキップ"
else
    COMMIT_MSG="データ更新: $(TZ='Asia/Tokyo' date '+%Y-%m-%d %H:%M') JST"
    git commit -m "$COMMIT_MSG"
    echo "✅ コミット完了: $COMMIT_MSG"
fi
echo ""

# ステップ5: GitHubにpush
echo "🚀 ステップ5: GitHubにpush中..."
if git push origin main; then
    echo "✅ Push完了"
else
    echo "❌ Push失敗"
    echo "   → 手動で解決してください: git push origin main"
    exit 1
fi
echo ""

# 完了メッセージ
echo "========================================"
echo "✅ すべて完了！"
echo "========================================"
echo ""
echo "🌐 Vercelサイトは約30秒後に更新されます："
echo "   https://futakotamagawa-rise-tracker.vercel.app/"
echo ""
echo "📊 ローカルで確認："
echo "   open index.html"
echo ""





