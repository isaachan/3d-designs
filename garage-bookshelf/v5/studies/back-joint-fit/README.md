# v5迁移说明

A–F原始小样保存在artifacts/，正式CAD后来选择F组；原说明中“未试配”属于生成小样时的状态。generate.py和package.py的默认重生成目录为build/studies/back-joint-fit/，可用--output指定另一个build/子目录，必须先generate再package。

以下为原研究/试件说明，数值与验证均保留其原始适用版本。

---

# v4 书架背板接头试配小样

**打印文件已清理（2026-10-23）：** 当前 v4 的 3MF 和打印 ZIP 已删除，待 CAD 定稿后重新生成。正式工程为 `garage-bookshelf-v4-assembly.FCStd`；下文打印清单、切片数据与验证结果保留为历史记录，当前状态见 [PRINT_STATUS.md](../../archive/docs/v4/PRINT_STATUS.md)。

一盘6组、12件，比较原版接头、修正锥度、侧隙与槽底余量。正式v4榫槽未修改。

- `artifacts/back-joint-six-fit-tests.3mf`（已删除）
- [参数、打印方法及试配记录表](artifacts/试配说明.md)
- [CAD](artifacts/back-joint-fit-samples.FCStd)
- [验证记录](artifacts/validation.json)

已完成实体、装配路径、封闭网格及3MF重开离线切片验证。预计2.41小时、81.6 g PLA；尚未实物试配。

## 重建

在安装FreeCAD与Bambu Studio的macOS上，按顺序执行：

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python generate.py
/Applications/FreeCAD.app/Contents/Resources/bin/python package.py
```

`generate.py`生成12件STL、组装CAD和参数；`package.py`使用v4已有打印预设生成一盘3MF并重开切片。临时切片结果及G-code只写入忽略的`work/`。不会连接打印机，也不会修改正式主体或榫槽。

`artifacts/back-joint-fit-test-kit.zip`为本次已验证产物的交付快照；脚本重建后需另行更新该ZIP和说明中的估算值。
