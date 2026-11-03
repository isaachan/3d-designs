# garage-bookshelf v5

车库书架由三类组件组成：主体、广告牌文字可换载板、车位卡槽。当前采用黑色主体与齐平内嵌三色饰片。

| 组件 | 范围 | 文件入口 |
|---|---|---|
| 主体 | 车库、书架、层板、柱段、饰片、连接片及两块广告牌的固定结构；不含可换文字载板 | [主体打印](printing/main/README.md) · [主体CAD](cad/main/README.md) |
| 广告牌文字可换载板 | 上方、右侧两种安装接口的可换文字件，可持续增加定制款 | [载板打印](printing/sign-carriers/README.md) · [载板CAD](cad/sign-carriers/README.md) |
| 车位卡槽 | 带通用底脚和取放耳的可取放托座，按车型增加上部固定结构 | [卡槽选型](printing/parking-inserts/README.md) · [卡槽CAD](cad/parking-inserts/README.md) |

## 组装者从这里开始

1. 阅读[打印件选型清单](printing/README.md)，确认主体、两块文字载板和所需车型卡槽。
2. 按[组装说明](docs/assembly.md)准备外购件并拼装。
3. 需要个性化文字或新增车型时，按[定制需求说明](docs/customization.md)向维护者提供信息和试配反馈。

## 项目维护者从这里开始

1. 阅读[当前状态](PROJECT_STATUS.md)和[维护指南](docs/maintenance.md)，确认正式源文件、运行环境与修改流程。
2. 通过[当前设计](docs/design.md)、[CAD说明](cad/README.md)及[配色说明](docs/colors.md)了解主体。
3. 按[打印生成指南](docs/printing.md)验证、导出、排盘和打包。
4. 新增定制款时遵守[文字载板规范](docs/interfaces/sign-carriers.md)或[车型卡槽规范](docs/interfaces/parking-inserts.md)，再交给组装者试配。

正式总装源文件为[cad/garage-bookshelf-v5-assembly.FCStd](cad/garage-bookshelf-v5-assembly.FCStd)。总装同时保存主体、默认文字载板及通用托座样件，便于验证接口；具体零件的源文件归属见各组件CAD入口。

[设计沿革](CHANGELOG.md) · [版本目录规约](../README.md#版本目录规约从v5开始)
