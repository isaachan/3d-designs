# BMW Garage

- `Garage_Honda.3mf`：未修改的原文件。
- `Garage_BMW.3mf`：BMW 改版工程，使用 Bambu Studio 打开。
- `BMW-panels-preview.png`：实际生成的装饰面二维预览（不是组装渲染）。
- `convert_to_bmw.py`：可重复生成脚本。
- `validation.json`：网格闭合、尺寸与体积检查记录。

## 改动

门头改为蓝底白字 BMW GARAGE 和简化 BMW 蓝白圆标；内侧招牌和两块隔板更换为 BMW 标识。原有 Honda 标识浅浮雕被填平，再制作 0.4 mm 深、与表面齐平的独立分色嵌件。保留装饰板外形尺寸与背部安装轮廓。

车库主体、道路、停车线、挡车器、办公室零件的网格文件完全不变。保留原六盘布局和打印朝向。耗材 5 从红色改为蓝色，也会使其他使用该耗材的装饰变蓝。

耗材顺序：1 黑、2 黄、3 灰、4 白、5 蓝（#0066CC）。隔板若改用透明耗材，会同时影响使用 4 号耗材的白色标志，建议另行分配耗材。

## 验证与打印注意

生成的各分色实体通过闭合/正体积检查，组合后的外包尺寸与原件一致。Bambu Studio 2.8.2 CLI 已成功读取工程并识别六盘。

**尚未完成切片或实物试打。** 原工程使用 Bambu Lab X2D / 0.4 mm 配置；本机 CLI 提示找不到对应系统打印机和工艺预设，打印前请在界面重新选择实际打印机、耗材及 AMS 映射，再切片。门头小圆标中的细字可能受 0.4 mm 喷嘴分辨率限制，务必检查切片预览，建议先试打门头。

删除了显示 Honda 的旧缩略图、照片和切片缓存，打开后由切片软件重新生成预览。原作者 Tomik s Cuprou 及 Standard Digital File License 元数据保留；本改版不改变原文件授权条件。

## 重建

```sh
cd bmw-garage
uv venv .venv --python 3.11
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python convert_to_bmw.py
```
