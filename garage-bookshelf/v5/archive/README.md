# v4历史归档

这里保存v4的原始阶段资料，不能作为当前正式CAD或整机打印发行入口。

| 目录 | 内容 |
|---|---|
| `migrations/` | 各轮一次性改造源代码；仍在使用的调色/渲染逻辑已提取进src |
| `legacy-tools/` | 未追平的旧完整builder、旧46件验证/11盘打印入口和旧GUI/渲染脚本 |
| `variants/removable-signs/` | 早期燕尾＋打印锁销字牌分支，已被正式M3方案取代 |
| `proposals/` | 旧纸样、提案图、M Power候选CAD及旧查看用3MF |
| `print-baseline/` | 旧STEP、两种坐标STL、旧11盘剩余说明/清单/图片；当时3MF已经删除 |
| `reports/` | 各轮几何、外观、切片和渲染证据，保留原源版本结论 |
| `snapshots/` | 选定的增量前CAD；开浅槽前快照已移到对应研究reference/，仅存一份 |
| `docs/v4/` | v4总说明、打印状态和配色说明的历史副本 |

归档Python入口已加直接执行保护；旧FCMacro按文本保存，不会通过它打开v4。
原始源文件SHA256及每个v4文件去向在[source-index.json](source-index.json)。
为避免伪造新验证，历史JSON中的原始路径/哈希不被改写；可通过索引找到迁移后的文件。
复制的资料存在349条源映射；旧交付目录共同的13个文件去重到同一份目标。
缓存、Finder元数据、自动FCBak和根result.json未迁入；v4原文件全部保留。
