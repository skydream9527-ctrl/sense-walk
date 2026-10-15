# H-SW-001-R2 更正 · base SHA 笔误

对已推送的 [H-SW-001-R2.md](H-SW-001-R2.md) 的更正（追加新文件，不改原文，依据
PROTOCOL/D-005：已发布 handoff 的误述用新 revision/correction 追加）。

## 更正内容

H-SW-001-R2.md 第 4 行的 base 写成
`550eb63b0ad14dae39d03b3e5b97ed0080080057bda`（43 字符，多写了 `0080` 一段）。

**正确值**（与 H-SW-001-R2.json 的 `base_commit` 一致，即 2026-10-14 时的
origin/main）：

```
550eb63b0ad14dae39d03b3e5b97ed0080057bda
```

以 JSON 为准；md 为笔误，无其他含义变化。
