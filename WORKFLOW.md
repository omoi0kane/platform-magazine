# ◆リポジトリ更新用のワークフロー自分用メモ◆
* まだ正式なワークフローは模索中。
* Udon Magazineを前提、PC向けに最適化（詳細後述）

## テクスチャ作成作業
* 表紙を除く各ページを1ページごとにpng化
* 表紙は裏・表を結合して1枚にする（※左側が表紙、右側が裏表紙）
* Texconvをダウンロード。適当なフォルダにtexconv.exeを配置
https://github.com/microsoft/DirectXTex/releases
* 以下のコマンドでtexconvを使いpngをdds形式に変換（BC1_UNORM: 圧縮形式(一番軽い)、-m 1: mipmapなし -w/-h: 変換サイズ、-o 出力先フォルダ）
```
texconv -f BC1_UNORM -m 1 -w 1360 -h 1920 -o output_folder *.png
```
* 当然表紙は倍のサイズなので別途変換のこと
* 以上、作成した1冊分のテクスチャをnet.omoi0kane.platform-magazine/Runtime/(各号)以下へ移動


## 本データ作成作業
* Udon MagazineのPrefabをHierarchyに配置
* Hierarchy上の(prefab)/Magazine内Udon Magazineコンポーネントにタイトル、著者、ページテクスチャを設定
* Platformの場合、Affinity Publisherの都合上、ページが3=>2=>5=>4=>7...と蛇行して並ぶので注意
* /Runtime/material以下にplatform_volxx.matファイルを作成。albedoを表紙/裏表紙テクスチャにする
* (prefab)/Magazine/BookのElement 1に作成した表紙マテリアルを適用
* 以上が完了したら(prefab)をエクスプローラーにドラッグしてPrefabを作成。Original Prefabにすること
* Prefab VariantにするとUdon Behaviourの値を保持できず、vpmで配布すると設定が消える（1敗）


## アップロード作業
* リリースの際はnet.omoi0kane.platform-magazine/package.jsonを書き換えてバージョンを上げる（忘れがち）
* git status => git switch feat/latest-prefab　でアプデ用ブランチに切り替え
* git add -A　で差分を全て追加
* git commit -m "comment"　でコメントとともにコミット=> git push
* アプデ用ブランチへpushしたら、Githubでプルリクを作成し詳細を記入
⃣* 管理者がプルリクを承認しマージ
*⃣ ActionからBuild Releaseワークフローを回す。バージョンが上がっていないとエラーが出るので注意
* 正常に進めばReleaseが作成され、Build Repo ListingによりVPM（VCC）側も更新される
* アップデートされたバージョンがVCCから取得可能になる


## いいわけ
* PC向けワールド推奨の理由：解像度がないと文字が読めないので書籍を置くのが現実的ではない
* よってテクスチャはPCを前提としたDDS BC1としている（Quest等ならATSC）
* Quest向けにビルドする場合は勝手に変換してくれるけど、ちょっと色味とかノイズとかダメかも。よって非推奨


## お問い合わせ先
Platform編集部　https://x.com/PlatformVR  
思惟かね　https://x.com/omoi0kane  
