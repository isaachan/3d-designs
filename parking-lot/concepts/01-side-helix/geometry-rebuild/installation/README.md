# 4F 收口与黑色支架安装方案

**当前支撑方案已改为[直接复用车库分段柱](column-reuse/README.md)。** 新增 [17 · 复用柱分解图](column-reuse/17-column-reuse-exploded.png)、[18 · 三根柱的复用范围](column-reuse/18-column-reuse-layout.png)、[19 · 同接口半剖](column-reuse/19-column-tab-section.png)。B 坡道柱采用原柱段＋带孔托臂片；C 侧牌柱也改成原柱段＋垫片。

**下文 13–15 图、定位肩／两半抱箍说明及 `mounting-study.*` 是前一轮方案，仅保留比较，已被当前方案替代。** 12 图的 4F 收口和 16 图的底法兰、A 柱接口仍可参考。最新整机预览为 [09 图](../09-geometry-overall.png)，最新支撑 CAD、检查与生成入口见 [column-reuse](column-reuse/README.md)。

2026-11-02。本轮直接修改几何，保留 70 mm 主坡道和接入通道。安装连接为新增方案样模，尚非最终打印交付。

## 图纸

| 图 | 内容 |
|---|---|
| [12 · 4F 终点收齐](12-4f-terminal-detail.png) | 取消用户指出的红色死端；虚线为删除范围 |
| [13 · 支架位置总览](13-support-location.png) | A 车库四柱、B1/B2/B3 坡道三柱、C 侧广告牌立杆 |
| [14 · 坡道托臂分解安装](14-ramp-mount-exploded.png) | 内半箍托臂、外半箍、柱肩、路板嵌件及四颗连接螺钉 |
| [15 · 坡道安装剖面](15-ramp-mount-sections.png) | 轨道—托臂固定剖面、抱箍—立柱承托剖面 |
| [16 · 底座与车库柱安装](16-base-and-garage-installation.png) | 底法兰固定、原 garage 分段柱销孔与托环 |

## 4F 收口

原来的最顶层在接入口之后仍延长到一个带挡墙的死端。这段没有继续上行的用途，现已裁掉。

新的终点沿 **Y=40 mm** 平面收齐，与顶层接入通道的前缘相连。末端护栏沿同一前缘连续收口，路面不再多伸出一个舌形块。4F 路面标高仍为 197 mm；停车区出口净宽仍为 70 mm。其余圈、各层标高不改。

## B · 坡道立柱与可拆托臂

三根坡道立柱改为 Ø14，每根与 Ø28 × 3 mm 底法兰、三个定位肩一体。每根装三只托臂，共九只。B1/B2/B3 柱肩高度不同，必须按位置装柱。

| 柱编号 | 平面角度 | 三个承托肩顶面 Z（mm） |
|---|---|---|
| B1 | 35° | 30.375 / 93.375 / 156.375 |
| B2 | 95° | 43.188 / 106.188 / 169.188 |
| B3 | 275° | 4.747 / 67.747 / 130.747 |

托臂的梁和内半箍为一体件，外半箍从柱外侧合上。抱箍孔名义 Ø14.4，两个接缝各留 0.6 mm 开口，由两颗 M3×16 配垫片、螺母夹紧。托臂底面坐在 Ø18 定位肩上，竖向荷载由定位肩承托，不依赖抱箍摩擦悬挂。

托臂上表面跟随该处轨道斜面，梁厚约 5 mm、宽 16 mm。两颗 M3×10 从梁下方穿过，拧入轨道底侧的短热熔嵌件；不让螺钉头突出路面。每个托臂单元配两个嵌件。

嵌件示意选用 RX-M3Sx4.0（或同尺寸件）：长 4 mm，建议预孔 Ø4 mm、盲孔至少 5 mm，依据厂商的 [Ruthex RX 系列数据表](https://www.igo3d.com/mediafiles/Sonstiges/Ruthex/ruthex_Datenblatt_RX-Serie.pdf)。在 6.6 mm 路板内保留约 1.6 mm 顶部余厚。预孔需以实际嵌件、材料和打印收缩做试样，不以图示干涉量代替热熔工艺验证。

安装顺序：

1. 在轨道下侧安装热熔嵌件；安装底座、车库和 B1/B2/B3 立柱。
2. 将轨道放到临时支撑上，先比最终位置垫高约 2 mm。此时不要把所有托臂预装在柱上再硬降整圈轨道。
3. 从侧面逐个送入托臂内半箍，放到定位肩；外半箍从外侧合上，用 M3×16 锁住。
4. 抽去临时垫片，让轨道落到九只托臂上；由下方拧入 M3×10 和垫片。

临时抬高留出插入余量。支柱在坡道净宽以外，抱箍可侧向安装，不需要将整条螺旋轨道穿过柱子。

## B/C · 底法兰固定

底法兰名义 Ø28、厚 3 mm，两个 Ø3.4 通孔位于柱中心两侧。底座在柱脚处局部加厚为 3.3 mm，并保留相同的穿孔。

每根用两颗 M3×10、上下垫片及底面六角螺母固定。底部脚垫留出 6 mm 空间，使螺母和螺钉尾端离桌面仍有余量；示意栈叠下螺钉末端离地约 0.8 mm。C 侧牌立杆采用同一种底法兰连接。

## A · 车库四根分段柱

继承 garage-bookshelf v5 的柱、销、孔、托环关系：

| 部位 | 名义尺寸 |
|---|---|
| 柱身 | Ø14 |
| 托环 | Ø20 × 4 mm，下面 3 mm 高锥肩 |
| 定位销 | Ø6，长度 9.6 mm |
| 层板孔／柱底孔 | Ø6.5 |
| 层板厚度 | 6.6 mm |
| 销穿过层板后的伸出 | 3 mm |
| 上段柱底盲孔深 | 3.3 mm |

顺序为底板定位销 → 承托柱段 → 层板 → 上段柱。层板落在下段的托环上，销穿过层板并插入上段柱底孔。销负责定位，托环承重。16 图将销标蓝仅为看清位置；实际它与下段黑柱是一体，不是额外蓝色零件。

四根柱共十二个常规柱段和四个封顶段。当前模型的柱中心随新停车板深度布置，继承的是原接口尺寸与装配方式，不表示原零件都能直接替换。

## 本轮检查与文件

- 安装样模各零件均为有效 BRep 实体，孔、盲孔、螺母槽为真实切除。
- 内半箍／外半箍与立柱无体积穿插，两半箍彼此无体积穿插；托臂及外盖到定位肩的距离为 0。
- 车库下段柱、层板、上段柱无体积穿插，销孔有配合余量。
- 增加托臂和螺钉头后，主坡道下方的最小局部净空更新为约 47.9 mm。
- 这不包含承载试验、热熔工艺试验、实际车模转向和整圈轨道的打印分片接头设计。

[mounting-checks.json](mounting-checks.json) 是局部安装检查记录；[../geometry-checks.json](../geometry-checks.json) 是整机道路和净空记录。

[mounting-study.FCStd](mounting-study.FCStd) / [mounting-study.step](mounting-study.step) 只包含一组局部托臂安装样模，用于检查孔、配合面及装配关系，不能视为整机生产 CAD。连续主道路网格还未分片，也没有完整制造孔系。

生成源文件：[mount_parts.py](mount_parts.py)（共享安装零件）和 [draw_installation.py](draw_installation.py)（分解／剖视图）。在仓库根目录运行：

```sh
PYTHONDONTWRITEBYTECODE=1 /Applications/FreeCAD.app/Contents/Resources/bin/python parking-lot/concepts/01-side-helix/geometry-rebuild/build_geometry.py
PYTHONDONTWRITEBYTECODE=1 /Applications/FreeCAD.app/Contents/Resources/bin/python parking-lot/concepts/01-side-helix/geometry-rebuild/installation/draw_installation.py
```
