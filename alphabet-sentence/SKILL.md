---
name: alphabet-sentence
description: 按英文句子生成 3D 打印字母盘：统计句子中 A–Z 与撇号的用量，用内置字母网格拼出可直接在 Bambu Studio 打开、切片打印的 3MF。Use when the user wants to 3D print a sentence, phrase, name or word as individual letters, or mentions 字母盘、拼字、字母 3MF、Alphabet.3mf、sentence/word letter plate。
---

# 句子字母盘

把一句英文变成一盘打印件：统计每个字母需要几个，从内置的 26 个字母网格（15×15×5 mm，MakerWorld「字母表」by Toxvaerd，CC-BY）里复制对应字母，按 A→Z、撇号最后排成网格，写出一个 Bambu Studio 工程 3MF。撇号 `'` 由脚本生成（原字母表没有）。

## 触发场景

- 用户想打印一句话、短语、名字、单词的字母件，例如「把 I've seen you here 做成字母打印盘」
- 用户提到字母盘、拼字、字母 3MF、Alphabet.3mf、句子字母

不适用：需要数字或 A–Z 以外的字符；需要拼成整块铭牌（本技能输出的是分离的字母件）。

## 先确认打印机

**运行前必须确认打印机**。用户没明确说机型时，用 question 工具问一句，选项按顺序：

1. `X2D（默认）` —— Bambu Lab X2D 0.4 喷嘴
2. `P1S` —— Bambu Lab P1S 0.4 喷嘴
3. 其他机型 —— 请用户给一份 Bambu Studio 的 `project_settings.config` JSON 路径

用户说「默认 / 都行 / 直接生成」时用 X2D。打印机只影响工程里的机器/工艺/耗材配置（`Metadata/project_settings.config`），不影响字母网格本身。

## 用法

```sh
cd <3d-designs 仓库>/alphabet-sentence
python3 gen.py "I've seen you here" -o <目标目录>/ive-seen-you-here.3mf --printer x2d
```

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `-o/--output` | `<句子>.3mf`（当前目录） | 输出路径，建议显式指定到用户目录 |
| `--printer` | `x2d` | 打印机预设：`x2d` / `p1s`，或直接给 `project_settings` JSON 路径 |
| `--spacing` | `20` mm | 字母格距；字母本体 15 mm |
| `--columns` | 自动 | 每行个数，默认按总件数取近似方形 |
| `--base` | 内置 `assets/alphabet-base.3mf`（缺失时用 `~/Downloads/Alphabet.3mf`） | 字母网格来源 |

执行后脚本会打印用件清单、打印机、布局尺寸和输出绝对路径，把这份清单和路径回报给用户。

## 统计规则

- 大小写统一按大写统计；`'` `’` `‘` `` ` `` 统一按撇号计。
- 只保留 **A–Z 和撇号**；空格不计，其他标点/数字/中文忽略并在终端提示。
- 同一字母的多个副本相邻摆放，整体按 A→Z、撇号最后排序。
- 板尺寸和排除区自动按所选打印机预设读取：X2D 为 256×256 mm、无排除区；P1S 为 256×256 mm、前左 18×28 mm 排除区。超出板面或压到排除区时脚本警告，按下一节「分盘」处理。

## 分盘（件数过多时）

字符过多、单盘放不下时**不要硬塞**，按盘拆开打印：

1. 先试一次收紧：`--spacing` 降到 17–18 mm、`--columns` 调大。字母本体 15 mm，间距不要低于 16 mm，否则不好取件。
2. 仍放不下就分盘：把用件清单按顺序切成几组，每组单独跑一次脚本，输出名加盘号（如 `lyrics-p1.3mf`、`lyrics-p2.3mf`），每盘都做一次切片验证。
3. 同一字母的多个副本可以拆到不同盘；尽量让每盘件数接近，单盘不超过约 100 件（20 mm 间距、10 列的经验值）。

经验容量：X2D / P1S 的 256×256 板，20 mm 间距、10 列时大约能放 90–110 件字母。

## 字母映射（勿改）

原字母表 26 个网格为 `3D/Objects/object_N.model`，没有字母命名。下表由网格截面识别并结合原盘排版逐件核对，脚本按此映射复制：

| 字母 | 文件 | 字母 | 文件 | 字母 | 文件 | 字母 | 文件 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A | object_19 | H | object_21 | O | object_25 | V | object_7 |
| B | object_1 | I | object_15 | P | object_10 | W | object_4 |
| C | object_18 | J | object_22 | Q | object_26 | X | object_6 |
| D | object_12 | K | object_11 | R | object_9 | Y | object_5 |
| E | object_17 | L | object_23 | S | object_2 | Z | object_24 |
| F | object_20 | M | object_13 | T | object_8 | | |
| G | object_16 | N | object_14 | U | object_3 | | |

## 撇号

宽 3.03 mm（与字母 I 同宽）× 高 6 mm × 深 5 mm，位于 15 mm 单元上部，底面与其他字母平齐。样式是竖直细条（用户确认过的默认）。

## 验证

- 结构自检：生成后用 `unzip -l` 确认 `Metadata/project_settings.config`、`3D/3dmodel.model`、每个用到的 `3D/Objects/*.model` 都在。
- 有 Bambu Studio 时建议实际切片验证（macOS，约 1 分钟）：

```sh
/Applications/BambuStudio.app/Contents/MacOS/BambuStudio --slice 0 --export-3mf /绝对路径/校验.3mf /绝对路径/输出.3mf
```

切片成功（退出码 0 且产物里有 `Metadata/plate_1.gcode`）即说明摆放、网格和打印设置都被接受。注意 `--export-3mf` 必须用绝对路径，相对路径会静默不产出。
或用 `--info` 快速检查网格，应全部 `manifold = yes`。

已知基线（X2D，PLA）：
- `"I've seen you here"` = 15 件（E×5、H/I/N/O/R/S/U/V/Y/撇号各 1），约 8.0 g、29 分钟；
- 《Girls Got Rhythm》五段歌词 = 92 件，约 48.9 g、2 小时 27 分。

X2D 预设切片的结束 G 代码会打印两条 `Invalid T command (T65279/T65535)` 告警，这是该机型的 AMS 退料指令，参考工程同样出现，不影响结果（退出码 0 即正常）。

## 回报格式

向用户简要说明：用件清单（`E ×5 …`）、布局（列×行、占用尺寸）、输出路径；如做了切片验证，附上件数/耗材/时间。不要贴大段 XML 或完整日志。

## 依赖与许可

- 仅需 Python 3 标准库；Bambu Studio 只用于可选的切片验证。
- 本技能目录位于 3d-designs 仓库内，未注册为全局技能；如需 opencode 自动加载，可在配置的 `skills.paths` 里加上该目录。
- 内置字母网格来自 MakerWorld「字母表」（Designer: Toxvaerd，License: CC-BY），再分发请保留归属；生成文件头部的 Title/Description 已包含说明。
- 内置打印机预设：X2D（`assets/settings-x2d.json`）由 Bambu Studio 02.09 的「Bambu Lab X2D 0.4 nozzle」+「0.20mm Standard @BBL X2D」+ Bambu PLA Basic 生成，并补喷嘴运行期字段；P1S（`assets/settings-p1s.json`）取自原 Alphabet 工程。两者均为 PLA、0.2 mm 层高、2 层墙、15% 填充。
- 自定义打印机 JSON 必须自洽：脚本会校验 `filament_colour` 与 `filament_extruder_variant` / `filament_self_index` 的长度（长度不一致时 GUI 打开会报 `Invalid configuration file`，CLI 切片却可能通过）。
