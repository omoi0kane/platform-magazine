# メタバース写真旅行雑誌『Platform』VPM版

『Platform』をVRChatワールド内に設置し、ページをめくって読めるようにしたVPMパッケージです。

『Platform』については[公式Webサイト](https://platformvr.github.io/)をご覧ください。

## このパッケージでできること

- Vol.1〜Vol.17と各年の特別号を、VRChatワールドへ個別に設置できます。
- **Latest**を使うと、パッケージを更新することで最新号へ入れ替えられます。
- 特定の号を使い続けたい場合は、Vol.番号または特別号の固定パッケージを選べます。

## 必要なもの

- [VRChat Creator Companion（VCC）](https://vcc.docs.vrchat.com/)
- VCCで作成または管理しているVRChat Worldsプロジェクト
- [Udon Magazine](https://tsukina-7mochi.github.io/udon-magazine/) `0.2.0`
- VRChat Worlds SDK `3.8.2`以降

Udon Magazineは本誌の表示とページ送りに使用します。先にUdon MagazineのVPMリポジトリをVCCへ追加してください。

## 導入手順

1. [Udon Magazineの配布ページ](https://tsukina-7mochi.github.io/udon-magazine/)を開き、VPMリポジトリをVCCへ追加します。
2. [Platform Magazineの配布ページ](https://omoi0kane.github.io/platform-magazine/)を開き、**Add to VCC**を押します。
3. VCCで内容を確認し、リポジトリの追加を承認します。
4. VCCの **Projects** から対象のWorldsプロジェクトを選び、**Manage Project**を開きます。
5. **Platform**で検索し、設置したいパッケージの **＋** を押します。
   - 常に最新号を利用したい場合：名前に`Latest`を含むパッケージ
   - 特定の号を固定して利用したい場合：目的のVol.番号または特別号
6. Unityでプロジェクトを開き、Projectウィンドウの **Packages** から追加したPlatform Magazineパッケージを開きます。
7. `Runtime`内の`Platform_...prefab`を、ワールドのHierarchyへドラッグ＆ドロップします。
8. UnityのPlay ModeまたはVRChat上で、表紙・ページ送り・Pickup操作を確認してください。

VCCから自動で開けない場合は、VCCの **Settings → Packages → Add Repository** に次のURLを入力してください。

```text
https://omoi0kane.github.io/platform-magazine/index.json
```

## パッケージの選び方

### Latest

最新号へ追従するパッケージです。現在の内容はVol.17「バーチャル春巡り」です。新号公開後にVCCで更新すると、収録内容が新号へ切り替わります。

### Vol.番号・特別号

各号を固定して利用するパッケージです。新号が公開されても別の号へ自動的に切り替わりません。ワールド内に特定のバックナンバーを残したい場合はこちらを選んでください。

## パッケージ内容

各パッケージには、次のデータが含まれます。

- ワールドへ配置する冊子Prefab
- 表紙・裏表紙と本文ページ画像
- 表紙表示用Material
- Unity/VPMで必要な設定ファイル
- 利用規約

元のPDFファイルや制作作業用データは含まれていません。

## 注意事項

- 各号には高解像度の誌面画像が含まれます。複数号を導入すると、プロジェクト容量とワールドのビルドサイズが増加します。必要な号だけを追加してください。
- 初回導入時や更新時は、Unityによる画像のインポート・圧縮処理に時間がかかる場合があります。処理が完了するまでUnityを終了しないでください。
- Latestは更新により収録号が変わります。特定号を維持したいワールドでは固定号パッケージを利用してください。
- パッケージを更新した後は、公開前にUnityとVRChat上で表示・ページ送りを再確認してください。
- 本パッケージはVRChat公式製品ではありません。

## アップデート

VCCの **Manage Project** に更新表示が出た場合は、対象パッケージの更新ボタンからアップデートできます。固定号は修正がある場合のみ更新され、Latestは新号公開時にも更新されます。

## 利用規約

利用前に[`LICENSE`](LICENSE)をご確認ください。

本データはVRChat等のワールドへの設置と、規約に沿った再頒布を想定しています。販売、印刷、著作物の内容を変更した状態での再配布は禁止されています。その他の禁止事項・免責事項はLICENSEを優先します。

## お問い合わせ

- [Platform編集部（X）](https://x.com/PlatformVR)
- [思惟かね（X）](https://x.com/omoi0kane)

不具合を報告する際は、使用した号、package version、UnityおよびVRChat Worlds SDKのversion、発生した症状をお知らせください。

## 運営・開発者向け

生成・検証・公開手順は[`docs/internal/`](docs/internal/)に整理しています。通常の導入では読む必要はありません。
