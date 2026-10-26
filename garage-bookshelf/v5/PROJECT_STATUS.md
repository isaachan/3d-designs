# 当前状态

- 正式设计：`cad/garage-bookshelf-v5-assembly.FCStd`，原样继承v4在`c407d75`后的正式CAD。
- 初始CAD SHA256：`822d05f79b60b10a8a9958e427d9591d476a89f391914b90d9eaa1d83fde6958`。
- v5是目录、维护代码和工具整理，不是重新设计零件。
- 当前尺寸与角色合同：`cad/model-spec.json`；35个Body＝26个打印件＋8个外购M3硬件＋1个通用托座样件。
- 四层2/2/3/3、共10槽；三块悬空层板6.6mm，槽深1.6mm；广告牌顶面名义高度343.333mm。
- 右侧口号为HORSEPOWER LEFT, BRAINPOWER RIGHT；当前字牌以M3螺钉固定，旧燕尾锁销方案已归档。
- M Power外观含零厚度色面；打印导出排除这些面、外购件和样件。STEP保留外购硬件。
- 原生模型/草图/装配检查、当前STEP/STL导出和预览的验证结果见`docs/verification.json`。
- 整机3MF和多色映射未定稿，`printing/plate-plan.json`为12盘单材料草案；`releases/`暂无整机发行版。
- 今日层板＋托座3MF保存在`studies/parking-tray-fit-2026-10-26/`，属于独立试件。
- 旧5mm层板STL、旧11盘清单、旧STEP、旧分析和阶段验证均有历史标签，不代表本版整机打印已完成。
- 仍待处理：车型轮胎夹、配色制造方法、整套排盘/支撑确认、实物试配与载荷观察、完整生成器追平。
