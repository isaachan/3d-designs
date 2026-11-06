# cassette-r1 装饰

兼容主体 r1、胶粘接口 r1；当前排盘修订为 `decoration-layout-r2`。

| 颜色 | 文件 | 该文件内的数量 |
|---|---|---|
| 浅蓝 | [02-lightblue.3mf](02-lightblue.3mf) | 面板 × 1 |
| 白色 | [03-white.3mf](03-white.3mf) | 卷带轮 × 2、磁头饰片 × 1 |
| 黄色 | [04-yellow.3mf](04-yellow.3mf) | 双音符 × 1 |

[原生源文件](../../../cad/music-card-box-r1.FCStd) · [验证记录](validation.json) · [粘贴接口](../../../docs/interfaces/mounting.md)

三份 3MF 均为 X2D / 0.4 mm / PLA 的独立 Bambu Studio 项目。浅蓝和黄色保留 5 mm 外侧 brim；白色保留后续保存的自动 brim（宽度 5 mm）、2 道墙和 3 层底部设置，排盘未变，2026-11-06 已重新切片通过，见[当前保存设置](../../saved-projects-20261106.json)。请以新项目打开所选文件。白色项目仅含两只卷带轮和一片磁头饰片，**不含 MusicNote**；音符在黄色项目中。

修复了原先不同颜色文件复用 XY 区域的问题：layout-r2 的三个装饰文件统一错开，每个零件保留 6 mm 扩边检查包络。初始项目已分别重开、切片，并在主体的原位置完成六件同盘的单耗材几何与 brim 回归。主体后续在独立项目中平移，因此当前跨项目合盘需重新排盘。原合盘检查不等同于 AMS 换色验证。

[排盘验证](evidence/layout-r2/repack-validation.json) · [切片结果](slice-result.json) · [原白色项目归档](../../../archive/printing/20261104-before-decoration-repack/README.md)

STL 分件保留在 `evidence/`，是原始几何导出，单件使用时可自行排盘；当前推荐打印入口为上面的新版 3MF。所有饰片实际胶面位于 Z=0。无需 AMS，可分色打印后粘贴；实际间隙、粘接和实机效果尚未实测。CLI 的预设路径和特殊 T 指令时间分析警告随[白色原始切片日志](evidence/layout-r2/03-white-slice.log)保存。
