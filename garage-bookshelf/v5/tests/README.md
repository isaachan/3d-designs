# 工具流程检查

在v5中运行：

```sh
python3 -m unittest discover -s tests -v
python3 tools/verify_printing.py
```

工具测试覆盖：生成结果只能进入build、不能覆盖既有结果或人工目录；拒绝过期／改动／越界文件；整机排盘覆盖全部零件；打包把40个主体零件与两块文字载板分开，拒绝不完整交付且不改当前打印文件；保存的通用接口试件保持真实尺寸与两个对象。

`verify_printing.py`只读检查当前组件清单、3MF覆盖、文件哈希、历史来源及零件角色，不重新执行CAD、切片或实物验证。
