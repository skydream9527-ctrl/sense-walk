# Trae Design 协作追加的本地检查

日期：2026-10-13（America/Los_Angeles）。基于协作提交 `0e1687b7c6ea263b7d7c173d4a7820e8aee5dcfd` 追加；功能基线仍为8056e11。本文件记录bootstrap检查，不是Trae设计交付或独立产品审核。

实际执行结果：

| 检查 | 结果 | 范围 |
| --- | --- | --- |
| `python3 tools/collaboration.py render` / `check` | passed | 四角色入口、12任务依赖、私有状态、链接、生成看板一致 |
| `python3 -m unittest discover -s tools/qa -p 'test_collaboration.py' -v` | passed，27项 | 16项原协议用例与11项设计/引用边界；临时目录实际执行 |
| JSON示例解析 | passed | 所有templates下JSON示例可解析；占位值不算实际交付 |
| Ruby YAML解析 | passed | 协作workflow语法；不是云端运行结果 |
| `git diff --check` | passed | 无空白/补丁错误 |
| plan.html本地链接与浏览器查看 | passed | 127.0.0.1:8765，实际页面出现四角色分工、Trae入口与设计任务；桌面截图目检 |

设计专项反例验证：缺manifest、作者越界改app、源稿变更后哈希不符、用`..`绕过设计revision目录、独立批准缺精确哈希、新素材缺design_ref、引用未批准设计、引用别的已批准设计任务、旧spec哈希，均被拒绝。合法设计批准和合法指定设计引用可以通过。

测试使用明确标注的协议fixture字节，不假装生成图片或进行图片视觉QA。此轮没有实际Trae源稿/预览、MiniMax新素材、API调用、Android业务改动、真机或真人测试。既有217项Android云端单测证据保留在 [原始基线](B-20261013-01/README.md)，不算本次本地重复执行。推送后的Actions与源码打包状态以具体GitHub运行记录为准。
