# v4 书架背板接头试配小样

一盘6组、12件，比较原版接头、修正锥度、侧隙与槽底余量。正式v4榫槽未修改。

- [打开3MF](artifacts/back-joint-six-fit-tests.3mf)
- [参数、打印方法及试配记录表](artifacts/试配说明.md)
- [CAD](artifacts/back-joint-fit-samples.FCStd)
- [验证记录](artifacts/validation.json)

已完成实体、装配路径、封闭网格及3MF重开离线切片验证。预计2.41小时、81.6 g PLA；尚未实物试配。

## 重建

在安装FreeCAD与Bambu Studio的macOS上，按顺序执行：

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python generate.py
/Applications/FreeCAD.app/Contents/Resources/bin/python package.py
```

`generate.py`生成12件STL、组装CAD和参数；`package.py`使用v4已有打印预设生成一盘3MF并重开切片。临时切片结果及G-code只写入忽略的`work/`。不会连接打印机，也不会修改正式主体或榫槽。

`artifacts/back-joint-fit-test-kit.zip`为本次已验证产物的交付快照；脚本重建后需另行更新该ZIP和说明中的估算值。
