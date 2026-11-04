# 项目维护者指南

本指南面向修改模型、生成打印件以及协助定制的维护者。首次接手先读[验证进展与待办](../PROJECT_STATUS.md)，组装者使用[组装说明](assembly.md)和[定制需求说明](customization.md)。

## 正式源文件与组件

正式总装是[garage-bookshelf-v5-assembly.FCStd](../cad/garage-bookshelf-v5-assembly.FCStd)，含主体、默认两块文字载板和通用托座样件。按[主体](../cad/main/README.md)、[文字载板](../cad/sign-carriers/README.md)、[车型卡槽](../cad/parking-inserts/README.md)索引找到对应源文件；当前不复制三份可编辑总装。

总装中的`DesignParameters`是实际参数；`src/garage_bookshelf/parameters.py`含历史默认值，不能据此整机重建并覆盖当前模型。`cad/model-spec.json`列出零件角色和检查尺寸，变更角色、数量或检查尺寸时同步维护。

## 运行环境

当前工具针对macOS上的FreeCAD与Bambu Studio，路径为：

- FreeCAD Python：`/Applications/FreeCAD.app/Contents/Resources/bin/python`。
- Bambu Studio CLI：`/Applications/BambuStudio.app/Contents/MacOS/BambuStudio`。
- 排盘、打包及工具测试使用Python 3.11+；CAD操作使用FreeCAD自带Python，配套`lib/`由工具入口定位。只读软件渲染还需要该环境中的NumPy和Pillow。
- 冻结打印预设在`assets/print-profiles/`。迁移到不同安装位置时核对工具中的路径，不把系统Python当作FreeCAD运行环境。

以下命令均在`garage-bookshelf/v5/`运行。首次接手先运行只读检查和工具测试：

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python tools/validate_cad.py
python3 -m unittest discover -s tests -v
python3 tools/verify_printing.py
```

检查应通过且不保存正式CAD；当前预期51个Body、42个整机打印件，角色与数量见[CAD说明](../cad/README.md)。`verify_printing.py`只读核对组件清单、现行文件哈希及其历史来源，并检查车型CAD、七项实测输入、原始图片、冻结字形和逐款报告的对应关系；旧BMW参考格式单独兼容，不重新切片。

## 修改主体

1. 在FreeCAD打开正式总装，按[设计说明](design.md)找到需要修改的参数或原生特征。
2. 主体参数在`DesignParameters`；饰片厚度、承托及胶槽在`SkinParameters`；条带宽度和斜率在`MColorParameters`；连接片在`ReinforcementParameters`。
3. 完整重算、检查并保存；有意修改检查尺寸或零件清单时同步更新`cad/model-spec.json`和`printing/plate-plan.json`。确认默认文字载板与通用底脚仍能安装。
4. 再次运行CAD检查，然后按[打印生成指南](printing.md)从新的导出开始生成。CAD哈希变化后不能复用旧生成目录作为新设计的验证结果。
5. 更新设计说明、组件索引和文件清单，把变更经过写入`CHANGELOG.md`，向组装者指出需要替换的具体组件。组件层面的验证范围、问题或待办变化时更新`PROJECT_STATUS.md`；新增款式及逐款验证入口只登记在组件索引中，版本README维护稳定的查找入口，详见[状态汇总规约](../../README.md#状态汇总与更新规约)。

恢复CAD显示可在FreeCAD中运行`tools/Preview.FCMacro`；默认不保存。只读预览用`tools/render.py`，输出进入`build/`。

## 协助定制

先按[定制需求说明](customization.md)收集文字、车型实测和试配条件，再按[文字载板规范](interfaces/sign-carriers.md)或[车型卡槽规范](interfaces/parking-inserts.md)制作。两种广告牌接口分别维护；新增文字或车型通常只增加定制款，不创建新的主体版本。

车型卡槽必须沿用[BMW Z4 E89实测四轮弧形槽方法](interfaces/parking-inserts.md)，实现参考为`studies/measured-tray-s51-b23-d10-t5p1/build_tray.py`。采集该车型的七项轮胎实测值，参数化推导轴距、轮距和轮心，保留通用底脚，完成四轮净空、十车位和单托座重开切片检查；未知的车型尺寸不能以外观估计值代替。

每款记录源文件、接口版本、CAD和3MF哈希、打印参数、验证范围及实物试配状态。既有试件资料可以参考，但不能代替统一规范的检查。确认保留后按[证据存放规约](../../README.md#当前交付的证据存放规约)把选定文件放入对应款式目录，更新`printing/catalog.json`，并在组件索引提供验证入口。

新增车型可使用`tools/make_parking_insert.py`，输入为独立款式的`measurements.json`及同目录的`model-label-outline.json`；示例及复现命令见[车型CAD索引](../cad/parking-inserts/README.md)。车型与修订标识只使用小写字母、数字及分隔单词的单个连字符，不含路径。先用系统Python执行`--freeze-label <measurements.json>`冻结Arial Bold车型字形，再用FreeCAD Python执行`--spec <measurements.json> --output build/<新运行名>`。工具在加载CAD前拒绝非法标识，写入前再检查目标位于本次build输出目录内且文件尚不存在。建模与验证沿用BMW方法；输出目录必须为空，既有BMW参考文件保持原样。

## 生成、交付与历史资料

自动生成写入新的`build/<运行名>/`，临时切片及G-code放`build/tmp/`。`tools/package_release.py`也只在build内创建候选交付，不覆盖已确认文件；完整命令见打印生成指南。

人工调整的3MF保存到对应组件或定制款目录，并记录差异及重开切片结果。当前款式的原始日志、冻结配置和检查网格放其`evidence/`，验证报告与切片结果放款式根目录；被替换的旧交付及证据再归`archive/`。既有历史证据保持原址、原哈希及原验证日期，由当前索引或报告显式引用。

`tools/implement_separate_skins.py`、`tools/implement_flush_inlays.py`、`tools/add_reinforcement_plates.py`均为已执行的一次性迁移，日常维护不重复运行。历史完整builder尚未追平当前设计，不用于覆盖正式总装。
