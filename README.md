# Platform Magazine VPM Publishing Pipeline

メタバース写真旅行雑誌『Platform』の書籍データを、VRChat Worlds向けVPMパッケージへ決定論的に変換・検証・配信するリポジトリです。

> 現行`0.0.8`は制作途中のテスト成果物です。既存構造との互換性は維持せず、号別パッケージ方式へ移行しています。

## 生成物

1冊の入力から次の2パッケージを生成します。

- 固定号：`net.omoi0kane.platform-magazine.volXX`
- 最新号：`net.omoi0kane.platform-magazine.latest`

`latest`は、Udon Behaviour値がPrefab Variantで失われた過去事例を避けるため、Unity実機検証が完了するまでは固定号と同じデータを持つ自己完結型です。
固定号の`version`とは別に`latest_version`を持ち、新号ごとにLatestのversion/tagを進めます。

## クイックスタート

```sh
uv sync --frozen --all-groups
uv run platform-book prepare books/volXX/book.yaml
uv run platform-book build books/volXX/book.yaml
uv run pytest
```

入力manifestの例は[`examples/book.yaml`](examples/book.yaml)、詳細手順は[`docs/publishing-workflow.md`](docs/publishing-workflow.md)を参照してください。

## 安全性と公開gate

- 原本PDF／画像は読み取り専用で扱います。
- manifestには再頒布許諾の明示が必要です。
- 出力先は管理markerがない既存ディレクトリを削除しません。
- ページ順、GUID、`.meta`、Prefab参照、ZIP構造、サイズを検証します。
- ZIPは固定timestamp・ソート済みentryで再現可能に生成します。
- **Unity/VCCへのimport、Prefab動作、ページ送り、表示品質の確認が終わるまでReleaseしません。**
- Release公開とVPM listing更新はユーザーの明示承認後に行います。

## CI

- `validate.yml`：PR／mainでロック済み環境から全テストを実行
- `build-listing.yml`：公開済みGitHub ReleaseからVPM listingを再構築しGitHub Pagesへ配置

## 配布先

号別パッケージの初回検証・Release完了後、以下からVCCへ追加できるようにします。

<https://omoi0kane.github.io/platform-magazine/>

依存するUdon Magazine：<https://tsukina-7mochi.github.io/udon-magazine/>

## 利用規約

本リポジトリの[`LICENSE`](LICENSE)を参照してください。生成VPMパッケージにも同じLICENSEを同梱します。
