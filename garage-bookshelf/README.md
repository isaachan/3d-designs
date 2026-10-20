# 车库书架

本目录保留四个彼此独立、可复现的版本。

| 版本 | 方案 | 入口 |
| --- | --- | --- |
| v1 | 原板件拼装方案：四段底板、八块背板、独立竖板与连接片 | [v1/ARCHIVE.md](v1/ARCHIVE.md) |
| v2 | 五个一体主体模块：总高 238 mm，模块间采用四联滑入式燕尾榫 | [v2/README.md](v2/README.md) |
| v3 | 基于 v2 最终设计重建的 FreeCAD 原生参数化工程，包含可编辑草图、Part Design 特征和集中参数表 | [v3/README.md](v3/README.md) |
| v4 | 540 × 170 mm 紧凑方案：200 mm 车库、340 mm 书架；整块车库层板、分段定位立柱，沿用 v3 高度 | [v4/README.md](v4/README.md) |

v1 是完整的冻结归档，包含当时的脚本、FreeCAD、STL、3MF、说明和审计资料。v2 保留原设计脚本与产物；v3 在独立目录中提供参数化装配工程、验证报告和 STL 导出文件，不覆盖前两个版本。v3 的具体文件入口、编辑与重建方式见其 [README](v3/README.md)。

v4 为独立重新设计，包含可编辑 FreeCAD 工程、STEP、打印 STL、X2D 3MF 与验证报告；详细尺寸和装配顺序见 [v4/README.md](v4/README.md)。
