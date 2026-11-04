# 上方横牌 · HANK'S PARKING LOT

[双色3MF打印项目](hanks-parking-lot.3mf) · [可编辑CAD](../../../../cad/sign-carriers/upper/hanks-parking-lot/hanks-parking-lot.FCStd) · [验证记录与哈希](validation.json)

DIN Condensed Bold，全大写`HANK'S`、`PARKING LOT`两行居中。黑底`#16181B`、白字`#F4F5F6`，字形高18mm、凸起1mm；整体190×58×2.4mm。接口`sign-upper-v1`，一件替换上方原文字载板，沿用M3紧固件。

耗材序号1黑色、2白色，请按实际装料映射到打印机料槽。一盘一个对象；X2D、0.4mm喷嘴、纹理PEI、PLA、0.20mm层高、4圈墙、25%填充、无支撑，双色配色及擦料塔已保存。独立重开切片估算约36分钟、21.0g，以实际切片为准。

## 验证与实物反馈

原生保存后重开重算、字高往返、全约束草图、单实体、背面接口差体积为0、M3孔位与R3圆角继承、装配净空、封闭单连通网格、源CAD与3MF尺寸及颜色保留、保存后独立重开3MF切片检查均通过。切片结果的模型警告字段为空；实物打印与试装尚缺完成反馈，不含G-code。

工具运行消息另见[原始切片日志](evidence/logs/slice.log)：其中包含系统预设未找到及`Invalid T command`消息。它们与模型警告分开记录，仍需在实际打印环境核对。

原始CLI日志、冻结打印配置、无色检查STL和生成器快照保存于`evidence/`；文件哈希见[组件清单](../../../catalog.json)，源CAD、字形、3MF及检查网格的实际路径见`validation.json`中的`artifact_locations`，生成工具快照见`generator_snapshot`。验证执行日期保留原记录，整理文件位置不代表重新验证。

![正面预览](front-preview.png)

![实际3MF排盘](plate-preview.png)

搭配[On the Road. Between the Pages.竖牌](../../side/on-the-road-between-the-pages/README.md)的安装预览；按正式总装位置渲染两块定制载板，来源与哈希见[evidence/paired-assembly-preview.json](evidence/paired-assembly-preview.json)。

![两块新牌安装预览](assembly-preview.png)

[组装与更换](../../../../docs/assembly.md) · [文字载板规范](../../../../docs/interfaces/sign-carriers.md)
