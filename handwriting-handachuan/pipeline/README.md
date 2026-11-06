# handwriting nameplate pipeline

从 `step_3_layered_pictures` 的 4 张分层 PNG 一键产出 FreeCAD 模型、4 个 STL 和多色 3MF。

## 前提（人工完成，本管线不覆盖）

- step_1 拍照、step_2 修正、step_3 分层出 4 张 PNG：
  `paper_outline.png` / `ruled_lines.png` / `handwriting.png` / `date.png`
  （`date.png` 不参与建模，日期按配置干净重建）

## 运行

```bash
# 注意：FreeCAD 会拦截 --开关，脚本参数必须放在 "--" 之后
# 默认自动选择“有 step_3 素材”的最新日期目录：
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd \
    handwriting-handachuan/pipeline/run.py

# 显式指定项目目录 / 强制重新描摹（路径参数会让 FreeCAD 打一句无害的
# "File format not supported" 警告，可忽略；也可用环境变量造免警告）：
NAMEPLATE_PROJECT=handwriting-handachuan/20260911 \
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd \
    handwriting-handachuan/pipeline/run.py

# 或：
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd \
    handwriting-handachuan/pipeline/run.py -- --project handwriting-handachuan/20260911 --force-svg
```

可选参数：

- `--project DIR`：新的项目目录（含 step_3 PNG；默认本目录）
- `--config FILE`：配置文件（默认 `<project>/nameplate_config.json`，
  不存在则用 `pipeline/default_config.json`）
- `--force-svg`：强制重新生成 step_4 的 SVG（默认已存在则复用）

## 产物

| 路径 | 内容 |
|---|---|
| `step_4_layered_svgs/*.svg` | 描摹/重建的 4 个矢量层 |
| `step_5_freecad_model/nameplate.FCStd` | 白底板、灰横线+边框嵌条、蓝手写、黑日期 4 个对象 |
| `step_6_printables/*.stl` | 4 个独立可打印 STL |
| `step_6_printables/nameplate_multicolor.3mf` | 多色 3MF，耗材槽映射见下 |

## 耗材槽映射（3MF 内置）

1. 白 - 纸面底板
2. 灰 - 横线 + 边框嵌条
3. 蓝 - 手写字
4. 黑 - 日期

导入 Bambu Studio 后只需给 4 个耗材槽选颜色；对象→耗材的分配已写入
`Metadata/model_settings.config`。耗材本身的颜色/材质参数属于切片机
配置，3MF 不携带，需在 Studio 里设定。

## 新图片的典型流程

1. 新建日期目录（如 `20261104/`），放入 step_1–3 素材（照搬现有目录结构；
   最少只需 `step_3_layered_pictures/ruled_lines.png` 和 `handwriting.png`，
   `date.png` 不参与建模）。
2. 复制 `nameplate_config.json`，按需改：日期文字/大小/加粗、孔位孔径、
   纸面尺寸、日期锚点等。
3. 运行上面的命令（不带 `--project` 时自动选最新有素材的日期目录；
   脚本参数必须写在 `--` 之后，否则会被 FreeCAD 拦截）。
4. 检查 `step_6_printables` 产物并切片。

## 尺寸约定

- 像素→毫米映射：`x_mm = x_px * paper_width_mm / canvas_width_px`，
  `y` 反向同理；纸面尺寸以 config 为准（不自动从图片测量）。
- 高度：底板 1.8 mm；灰横线/边框凹槽 0.3 mm（嵌条同高、与顶面齐平）；
  手写、日期凸起 1.0 mm。
