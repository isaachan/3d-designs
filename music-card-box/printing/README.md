# 当前打印入口

| 需要的文件 | 入口 |
|---|---|
| 深蓝主体 | [主体选型](main/README.md) |
| 浅蓝、白色、黄色磁带装饰 | [装饰选型](decorations/README.md) |
| 彩色整机装配预览（非打印姿态） | [装配 3MF](assembly/music-card-box-r1.3mf) |
| 全部交付哈希与路径 | [catalog.json](catalog.json) |

四个分色 3MF 均为 **X2D / 0.4 mm / PLA 的 Bambu Studio 项目**。主体与白色保留后续保存的自动 brim（宽度 5 mm）、2 道墙等设置，已按当前文件重新切片；其余两份保留 5 mm 外侧 brim。详见[当前保存设置](saved-projects-20261106.json)。装饰位置互相错开；主体后续在独立热床中平移，合盘时需要重新排盘。建议以新项目打开对应文件。交付文件均不含 G-code。STL 保留原始几何导出位置，单件使用时自行排盘；整机装配 3MF 用于预览。

使用[组装说明](../docs/assembly.md)确认主件直立方向、装饰平放和上墙步骤。组件说明中的 `validation.json` 记录实际数字检查，`evidence/` 保存日志和原始输入；未做实物验证。
