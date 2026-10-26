# 工具流程检查

在v5中运行`python3 -m unittest discover -s tests -v`。
覆盖生成输出不能写入人工目录、不能覆盖既有结果、拒绝过期/改动/越界文件，以及保存试件3MF真实边界和计划完整性。
检查临时文件只进入build/tmp，不写正式CAD和人工3MF。
