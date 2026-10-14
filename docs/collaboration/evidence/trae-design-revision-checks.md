# 设计多轮引用检查补充

日期：2026-10-13（America/Los_Angeles）。基于 `8ef1446b93c12f7b7b9a768ea101c4ec1fd7b4b2` 补充 [D-003](../decisions/D-003-design-revision-history.md)。前轮 [27项检查记录](trae-design-extension-checks.md) 保留，本轮最终校验为31项。

实际执行 `python3 tools/collaboration.py check`、`python3 -m unittest discover -s tools/qa -p 'test_collaboration.py' -v`、`git diff --check`，全部通过。新增4项实际临时目录用例：

- 设计R2批准、素材R2引用后，R1历史引用继续可校验。
- 当前素材R2继续引用旧设计R1，被拒绝。
- 历史设计引用没有当时的独立批准，仍被拒绝。
- 协调者明确退回rework的旧素材记录保持可查看，等待新稿。

此前27项继续通过。用例是文件协议验证，不是实际图片或Android验收；本轮没有生图、实际设计稿或新设备测试。云端结果以此修正提交的Actions为准。
