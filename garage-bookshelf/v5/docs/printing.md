# 当前打印方案：完整15盘

使用[当前完整15盘](../printing/current/README.md)替换05、06、13、14、15。已经打印或正在打印的01–04、07–12继续使用现有文件，无需重印，也不覆盖个人修改的03盘。

| 盘 | 内容 | 设置 |
|---|---|---|
| 05/06 | 带承托槽和胶槽的黑色主体 | 0.20mm、4圈墙、25%填充、仅热床支撑 |
| 13/14/15 | 浅蓝/深蓝/红饰片，各4片 | 0.20mm、3圈墙、全厚0.60mm，无支撑/擦料塔 |
| 01–04、07–12 | 其余24个打印件 | 继续使用现有文件、现有设置 |

五盘约17小时02分、919.1g；按80元/kg材料费73.52元，不含胶、电费、人工及损耗。沿用十盘基线的整套估算为42小时59分、1915.7g；个人调整过的盘以自己的切片为准。

05/06凹槽深0.6mm，与0.6mm饰片配套；1.5mm宽承托台阶内另下沉0.2mm存胶。先拼主体、干装饰片，再向胶槽放少量胶并压到无胶台阶。三处转角避让详见[装配说明](assembly.md)。旧recommended、外贴版及重复压缩包已删除。

## 重新生成

1. FreeCAD Python执行`tools/export.py --output build/<run>/export`，强制完整重算并检查47个Body、38个打印件，导出46实体STEP和两种坐标的STL。
2. `python3 tools/make_print_projects.py --export-dir build/<run>/export --only 05-module-2 06-module-3 13-book-skins-lightblue 14-book-skins-darkblue 15-book-skins-red --output build/<run>/single`生成五盘中间项目并重开切片。
3. FreeCAD Python执行`tools/make_colored_projects.py --export-dir build/<run>/export --single-color-dir build/<run>/single --output build/<run>/colored`保存配色并独立重开切片。最终使用colored目录中的3MF。
4. 完整15盘重生成可省略`--only`，随后用`tools/package_release.py`创建新的完整快照；不会覆盖人工维护项目或旧快照。

当前完整15盘已将五盘修正件和另外十盘原文件合并。其余十盘逐件核对输入STL与当前导出完全一致，项目和设置不改动，记录在当前目录内的`reused-plates.json`。`printing/current-release.json`直接指向完整版本，无旧发布依赖。以后通过`tools/package_release.py`打包新版本。

常规STL不含颜色，最终3MF含实际Bambu配色数据。STEP保留8个外购硬件；打印STL/3MF不含硬件、托座样件和零厚度色面。尚未实物干装和粘接，不交付G-code。
