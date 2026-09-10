# v1 归档：原板件拼装方案

本目录是 v2 开始前对 `garage-bookshelf/` 的完整文件级快照，而不是只依赖 Git 历史的旧版本引用。归档基线 Git commit 为 `f137631`（`audit #4`）。

归档时工作区另有未提交内容，均已原样纳入此快照：根目录 `.gitignore` 的 `load-test-stl/` 忽略规则；`audit/modular-concept/`；以及 `bambu-print/` 下的承重试验 3MF、生成器和说明文件。它们在归档时尚未属于 `f137631`，但没有被丢弃、重置或覆盖。

## 内容与使用入口

- [bambu-print/README.md](bambu-print/README.md)：原 v1 的打印与装配说明。
- `bambu-print/generate-models.mjs`、`generate-freecad-assembly.py`、`generate-label-mask.swift`：原生成流程。
- `bambu-print/stl/`、`*.3mf`、`garage-bookshelf-v4-装配检查.FCStd`：完整生成产物。
- [audit/检查报告.md](audit/检查报告.md) 及 `audit/review-*`：原验证记录。

归档时已按 SHA-256 对比原目录和本归档的 `generate-models.mjs` 以及 FreeCAD 装配文件，两者完全一致。v2 所有脚本均使用自己的相对 `v2/stl`、`v2/print` 和 `v2/audit` 路径。
