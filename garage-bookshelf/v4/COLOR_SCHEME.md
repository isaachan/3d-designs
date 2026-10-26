# v4 M Power 黑色配色 · 2026-10-26

正式主模型：`garage-bookshelf-v4-assembly.FCStd`。以实际 CAD 为结构依据，将用户确认的黑色效果图方案应用为原生外观；白色方案不再使用。

| 位置 | 颜色 |
| --- | --- |
| 主体、书架、圆柱、横牌底板 | 黑 `#16181B` |
| 停车托座槽底 | 更深黑 `#0E1013` |
| 三块悬空层板外缘，自下而上 | 浅蓝 `#39A9DB`、深蓝 `#151B65`、红 `#ED242A` |
| 书架三色带，自左至右 | 浅蓝、深蓝、红，实际宽度 1∶1∶1 |
| 横牌左/右支架正面 | 浅蓝 / 红，支架窄边仍为黑色 |
| 横牌文字 | 白 `#F4F5F6`，保留原字形；横牌没有三色标 |
| 右侧可拆口号牌 | 深蓝底、白字，保留螺钉，不带三色标 |
| 停车白线、编号、箭头、斑马线 | 白；原安全斜线改为浅蓝，无障碍蓝区改为深蓝 |
| 原金属件 | 深色 `#24272B`，保留螺钉与螺母几何 |

这些 HEX 值是本方案的颜色目标，并非官方色卡或已选定的耗材色号。

2026-10-26 追加确认：右侧口号灯箱也去掉小三色标。入口 `update_plain_side_sign.py`，检查见 `reports/plain-side-sign-validation.json`；书架主体三色带、层板边和横牌支架颜色不变。

## 等宽与编辑

`MPowerAppearance` 组内的 `MColorParameters` 表保存共用参数：`StripeWidth = 36 mm`、`Slope = 0.6`。三个颜色均由同一个宽度参数驱动。面上横截距 `Pitch = StripeWidth*sqrt(1+Slope^2)`，因此沿板面垂直条带方向测量的实际宽度全部为36mm。边界平行；背板与底板在折线处镜像衔接；颜色延伸到背板顶边及底板前沿外边缘。实际F接头前表面的0.2mm高差也有对应外观色面，未覆盖或改掉接头。

可双击该表修改 `StripeWidth` 后重算。所有新草图完全约束，面由 FreeCAD 自带的 SubShapeBinder、MultiFuse 和 Common 计算，无外部纹理、网格或自定义Python特征代理依赖。

图案是零厚度外观面，不是新增打印件或材料层。`DisplayOffset = 0.01 mm` 只让色面略离开原面以避免深度缓冲闪烁，不改变任何Body的实体或承重厚度。单件制造仍以原Body为准；后续多色切片另行处理，不能把外观面作为实体STL导出。

## 维护与检查

在 FreeCAD Python 控制台恢复本方案的颜色、显示和视角：

```python
import sys
sys.path.insert(0, '/Users/kai.han/code/3d-designs/garage-bookshelf/v4')
import apply_mpower_colors
apply_mpower_colors.review(App.ActiveDocument)
```

`gui_review.run()` 检测到本配色组后也会使用该入口，不再重置为旧灰黄配色。`apply_mpower_colors.run()` 只用于将指定历史SHA的主模型首次升级，不能再次覆盖现模型。旧完整重建脚本仍未包含全部历史增量，不要用其覆盖正式主模型。

备份：`backups/2026-10-26-before-mpower-colors.FCStd`。

`reports/mpower-color-validation.json` 验证35个原Body的形状、体积、面数、Tip与全局定位保留，三色的实际宽度、边界平行和相邻色面的零面积重叠，以及保存后正常重开的颜色和可见性。`render_mpower_colors.py` 仅读取正式CAD的实际面和保存材质生成预览，不修改模型。

本轮未更新STEP、STL、3MF、打印ZIP或打印参数。
