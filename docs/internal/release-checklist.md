# Internal release checklist

Platform Magazine運営者向けの公開チェックリストです。一般利用者向けの導入方法は[README](../../README.md)を参照してください。

## 1. 入力固定

- [ ] 原本を読み取り専用で配置した
- [ ] `book.yaml`の号名、package ID、version、著者が正しい
- [ ] `latest_version`が過去のLatest Releaseより新しく、tagが衝突しない
- [ ] 再頒布許諾を確認し、manifestへ記録した
- [ ] 表紙ファイルを明示した
- [ ] `natural` / `affinity_spreads` / `affinity_spread_pages` / `explicit`のページ順を選んだ

## 2. ローカル生成・検証

```sh
uv sync --frozen --all-groups
uv run platform-book prepare books/<id>/book.yaml
uv run platform-book build books/<id>/book.yaml
uv run pytest
```

- [ ] `contact-sheet.jpg`で表紙、欠番、上下、ページ順を確認した
- [ ] `validation.md`にエラーがない
- [ ] `resolved-manifest.yaml`のsource SHA-256とページ順を保存した
- [ ] 2回生成したZIPのSHA-256が一致した

## 3. Unity / VCC gate

- [ ] 対応VRChat Worldsプロジェクトへ固定号ZIPを導入した
- [ ] `latest` ZIPを別の使い捨てプロジェクトへ導入した
- [ ] Unity import / compileが成功した
- [ ] PrefabがActiveで、表紙・ページ送り・最終ページが正常
- [ ] PC上で文字の視認性、buildサイズ、VRAM使用量を確認した

## 4. GitHub draft

各パッケージを別tag・別Releaseとしてdraft作成する。

```sh
# dry-runで2つのtag・ZIP・SHA-256を確認する。
uv run platform-book stage-release books/vol16/book.yaml --target <merged-commit-sha>
# 確認後、draftだけを作成する。公開はしない。
uv run platform-book stage-release books/vol16/book.yaml --target <merged-commit-sha> --execute
```

- [ ] tag、Release、package.jsonのversionが一致
- [ ] package.jsonをRelease asset名`package.json`として添付
- [ ] ユーザーがdraft内容とUnity検証結果を承認

## 5. 公開・listing

- [ ] 明示承認後に固定号Releaseをpublish
- [ ] 明示承認後にlatest Releaseをpublish
- [ ] `Build VPM listing` workflowを1回だけ手動実行
- [ ] 公開`index.json`に両package/versionが存在
- [ ] 公開ZIPを再取得してSHA-256照合
- [ ] VCCから新規導入・更新を最終確認
