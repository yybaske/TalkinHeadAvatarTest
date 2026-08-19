import express from "express";
import cors from "cors";

const app = express();
app.use(cors());
app.use(express.json());

// ---- ダミーの知識ベース(本来はベクトルDBに差し替える部分) ----
const knowledgeBase = [
  { id: 1, keyword: "営業時間", text: "サポート窓口の営業時間は平日9:00〜18:00です。" },
  { id: 2, keyword: "料金",     text: "料金プランはライト・スタンダード・プロの3種類があります。" },
  { id: 3, keyword: "返品",     text: "返品は商品到着後7日以内であれば承っております。" },
  { id: 4, keyword: "解約",     text: "解約はマイページの「契約管理」からいつでも手続き可能です。" },
];

// ---- ダミー検索(本来はベクトル類似度検索に差し替える部分) ----
function mockSearch(question) {
  const hits = knowledgeBase.filter(doc => question.includes(doc.keyword));
  return hits.length > 0 ? hits : [];
}

// ---- ダミーLLM(本来はClaude等のAPI呼び出しに差し替える部分) ----
function mockGenerate(question, docs) {
  if (docs.length === 0) {
    return `「${question}」について、現時点では該当する情報が見つかりませんでした。担当者にお繋ぎしますか？`;
  }
  const context = docs.map(d => d.text).join(" ");
  return `お問い合わせについてお答えします。${context}`;
}

app.post("/api/chat", (req, res) => {
  const { question } = req.body;
  if (!question) {
    return res.status(400).json({ error: "question is required" });
  }

  // 実際のRAGパイプラインと同じ形の処理順序(中身だけダミー)
  const docs = mockSearch(question);
  const answer = mockGenerate(question, docs);

  res.json({
    answer,
    sources: docs.map(d => ({ id: d.id, text: d.text }))
  });
});

app.listen(3001, () => {
  console.log("Dummy backend running: http://localhost:3001");
});
