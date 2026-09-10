# v2：五模块一体车库书架

v2 将主体改为五个一体打印模块。每个模块把底板、背板，以及其范围内的竖板和根部加强肋融合为一个连续实体；不再使用 v1 的底板/背板/竖板拼片与连接片。

## 主尺寸与范围

- 主体：920 × 220 × 238 mm（长 × 深 × 高），底板 8 mm，背板/竖板自底板上表面起高 230 mm。
- 模块边界：0 / 180 / 410 / 590 / 770 / 920 mm；模块宽度依次为 180 / 230 / 180 / 180 / 150 mm。
- 中隔板 X=360–366 mm 和两块根部肋完整融合于模块 2；右侧板 X=914–920 mm 和两块根部肋完整融合于模块 5。
- 保留三层车模层板与四根承托柱；柱由 Z=8 延伸至 Z=230，取消 v1 超出主体的顶梁、广告牌、广告牌柱和广告文字。右侧蓝色 `BOOK DEPOT` 牌保留。

## 四联燕尾榫与装配路径

每个模块界面有四组沿 X 方向滑入的燕尾榫：底板 Y=52、168 mm 两组，背板 Z=66、180 mm 两组，共 16 组。

- 底板榫：14 mm 公榫、15 mm 母槽；公榫在底面宽 30 mm、顶面宽 24 mm。它约束模块的相对 Y 位移和竖向拔出，底面仍为 Z=0 的平面。
- 背板榫：14 mm 公榫、15 mm 母槽；背板前侧高度 26 mm、后侧高度 34 mm。它约束模块的前后错位。
- 侧壁名义总间隙为 0.40 mm（每侧 0.20 mm），轴向端隙为 1 mm；这些参数集中定义在 `generate_v2.py` 的 `CLEARANCE`、`TONGUE` 与 `SOCKET_DEPTH`。
- 四种榫均为**恒定截面、沿 X 方向的滑入式燕尾**，而非末端渐宽的盲槽。装配顺序是固定模块 1，再依次将模块 2、3、4、5 沿 **-X** 方向滑入。验证脚本在每个界面的 60/30/15/5/1/0 mm 行程采样，确认没有实体碰撞。
- 燕尾榫限制侧向错位和拔出，但模块仍可沿插入方向退出；每个界面的四组榫与底板、背板接触面均应涂胶。不要将它描述为无需胶水的完全自锁连接。

## 生成、查看与打印

```sh
cd garage-bookshelf/v2
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd generate_v2.py
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd generate_v2_freecad.py
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd audit/validate_v2.py
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd audit/validate_freecad_assembly.py
python3 build_x2d_projects.py
python3 audit/validate_print_projects.py
```

- [garage-bookshelf-v2-assembly.FCStd](garage-bookshelf-v2-assembly.FCStd)：装配检查文件。
- `stl/`：五个主体模块、车库层板、承托柱、侧牌和测试件。
- `print/projects/`：22 个单件 X2D PLA 项目；每件实际排版到 256 × 256 × 260 mm 空间，保存为 4 圈墙、25% 填充、4 mm brim。模块 2 最大包络为 243.8 × 220 × 238 mm，预留 4 mm brim 后仍在 X2D 范围内。
- `test_base_*`、`test_back_*`：分别验证底板和背板燕尾榫；`test_corner_*_four_*`：保留同一界面的四组榫关系，用于先做共同滑入测试。
- [组装说明.md](组装说明.md)：从试件、施胶到五模块和车库部件的实际装配顺序。
- [audit/验证报告.md](audit/验证报告.md)：已完成的几何／网格／3MF 检查及仍需实物试验的事项。

## 尚需实物验证

几何、网格和装配路径已通过脚本验证；3MF 的对象与 X2D 边界已验证。仍应先打印两类榫试件和四联转角试件，确认 PLA 的实际间隙、brim 清理、底板朝下时背板公榫的外部支撑需求，以及胶水固化后的抗侧推表现。约 5 kg 书籍与 8 辆车模的承重尚未经过实物认证。
