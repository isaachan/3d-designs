# cassette-r1 装饰

兼容主体 r1、胶粘接口 r1；当前排盘修订为 `decoration-layout-r2`。

| 颜色 | 文件 | 该文件内的数量 |
|---|---|---|
| 浅蓝 | [02-lightblue.3mf](02-lightblue.3mf) | 面板 × 1 |
| 白色 | [03-white.3mf](03-white.3mf) | 卷带轮 × 2、磁头饰片 × 1 |
| 黄色 | [04-yellow.3mf](04-yellow.3mf) | 双音符 × 1 |

[原生源文件](../../../cad/music-card-box-r1.FCStd) · [验证记录](validation.json) · [粘贴接口](../../../docs/interfaces/mounting.md)

三份 3MF 现均为 X2D / 0.4 mm / PLA 的独立 Bambu Studio 项目，已设置对应颜色和 5 mm 外侧 brim。请以新项目打开所选文件。白色项目仅含两只卷带轮和一片磁头饰片，**不含 MusicNote**；音符在黄色项目中。

修复了原先不同颜色文件复用 XY 区域的问题：新版三个装饰文件与主体的占位统一错开，每个零件保留 6 mm 扩边检查包络。三个装饰项目已分别重开、切片；另将全部六件放到同一盘做单耗材几何与 brim 冲突回归，切片成功、模型未报告警告。这项合盘检查不等同于 AMS 换色验证。

[排盘验证](evidence/layout-r2/repack-validation.json) · [切片结果](slice-result.json) · [原白色项目归档](../../../archive/printing/20261104-before-decoration-repack/README.md)

STL 分件保留在 `evidence/`，是原始几何导出，单件使用时可自行排盘；当前推荐打印入口为上面的新版 3MF。所有饰片实际胶面位于 Z=0。无需 AMS，可分色打印后粘贴；实际间隙、粘接和实机效果尚未实测。CLI 的预设路径和特殊 T 指令时间分析警告随[白色原始切片日志](evidence/layout-r2/03-white-slice.log)保存。
