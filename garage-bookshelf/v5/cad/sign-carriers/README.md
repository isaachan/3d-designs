# 广告牌文字载板CAD

默认款的唯一源文件是[正式总装](../garage-bookshelf-v5-assembly.FCStd)：上方`top_carrier_Body`、右侧`side_cartridge_Body`。固定广告牌和牌座属于主体。对象名中的历史“燕尾”标签不代表当前紧固方式，当前按M3螺钉接口装配。

新增款分别放`upper/<款式>/`、`side/<款式>/`，保存独立、原生可编辑的CAD与必要的冻结文字轮廓，说明所继承的接口和总装版本。总装负责整体配合验证；新款以其单独源文件为准，不另存一个可被误认为正式总装的副本。

[文字载板规范](../../docs/interfaces/sign-carriers.md) · [打印款式](../../printing/sign-carriers/README.md)

## 当前定制源文件

| 位置 | 文字 | 唯一源文件 |
|---|---|---|
| 上方横牌 | Life's too short to drive boring cars | [原生CAD](upper/lifes-too-short/lifes-too-short.FCStd) · [维护说明](upper/lifes-too-short/README.md) |
| 右侧竖牌 | Engines Roar. Pages Whisper | [原生CAD](side/engines-roar-pages-whisper/engines-roar-pages-whisper.FCStd) · [维护说明](side/engines-roar-pages-whisper/README.md) |
