# TalkingHead avatar test

3Dアバター表示 + TTS(Google/Azure) + リップシンクの動作確認用ページ。

## 起動方法

`importmap` を使っているため `file://` では動きません。

```bash
npx serve .
```

表示された `http://localhost:xxxx` をブラウザで開く。

## できること

- サンプルアバター、または任意の `.glb` ファイルの表示
- Google Cloud TTSで英語をしゃべらせる
- Azure Speech SDKで日本語をしゃべらせる（`wordBoundary` イベントでリップシンク）

## 注意

APIキーは画面から入力する方式。ソースコードに直接書き込んで公開しないこと。
