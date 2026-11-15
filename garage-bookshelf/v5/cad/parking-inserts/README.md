# 车位卡槽CAD

所有车型必须遵循[BMW Z4 E89实测四轮弧形槽方法](../../docs/interfaces/parking-inserts.md)：实测轮胎数据，参数化推导轮心位置，在通用底脚上建立四个原生弧形轮槽，并完成参数、轮胎净空、十车位和单件打印检查。

通用接口来自[正式总装](../garage-bookshelf-v5-assembly.FCStd)的`parking_tray_interface_Body`，该样件只有底脚和取放耳。BMW脚本按相同接口原生重建底脚，并以双向布尔差验证一致。

| 款式 | 当前唯一可编辑源 | 当前状态 |
|---|---|---|
| BMW Z4 E89 | [原生CAD](../../studies/measured-tray-s51-b23-d10-t5p1/parking-tray-s51-b23-d10-t5p1.FCStd) | 实际参数为B28；目录名b23是旧路径，无字B28版尺寸已确认，当前0.4mm凸字版未打印 |
| Mazda MX5 · r1 | [原生CAD](mazda-mx5/r1/mazda-mx5-r1.FCStd) · [输入与复现](mazda-mx5/r1/README.md) | 使用用户图片中的七项实测值；原生参数、轮胎净空、十车位及重开切片通过，[实物试配待完成](../../printing/parking-inserts/mazda-mx5/r1/README.md) |
| BMW M4 · r1 | [原生CAD](bmw-m4/r1/bmw-m4-r1.FCStd) · [输入与复现](bmw-m4/r1/README.md) | 使用用户图片中的七项实测值；原生参数、轮胎净空、十车位及重开切片通过，[实物试配待完成](../../printing/parking-inserts/bmw-m4/r1/README.md) |
| AMG C63 · r1 | [原生CAD](amg-c63/r1/amg-c63-r1.FCStd) · [输入与复现](amg-c63/r1/README.md) | 2026-11-06实测四轮槽；原生参数、文字支撑、轮胎净空、十车位及重开切片通过，[实物试配待完成](../../printing/parking-inserts/amg-c63/r1/README.md) |
| Citroen C2 · r1 | [原生CAD](citroen-c2/r1/citroen-c2-r1.FCStd) · [输入与复现](citroen-c2/r1/README.md) | 2026-11-06实测四轮槽；原生参数、文字支撑、轮胎净空、十车位及重开切片通过，[实物试配待完成](../../printing/parking-inserts/citroen-c2/r1/README.md) |
| Teramont Pro · r1 | [原生CAD](teramont-pro/r1/teramont-pro-r1.FCStd) · [输入与复现](teramont-pro/r1/README.md) | 2026-11-06实测四轮槽，字高3.2mm；原生参数、文字支撑、轮胎净空、十车位及重开切片通过，[实物试配待完成](../../printing/parking-inserts/teramont-pro/r1/README.md) |
| Benz E Cabriolet · r1 | [原生CAD](benz-e-cabriolet/r1/benz-e-cabriolet-r1.FCStd) · [输入与复现](benz-e-cabriolet/r1/README.md) | 2026-11-06实测四轮槽，字高2.6mm；原生参数、文字支撑、轮胎净空、十车位及重开切片通过，[实物试配待完成](../../printing/parking-inserts/benz-e-cabriolet/r1/README.md) |
| MINI Cooper · r1 | [原生CAD](mini-cooper/r1/mini-cooper-r1.FCStd) · [输入与复现](mini-cooper/r1/README.md) | 前胎直径暂按 10.2 mm，CAD 重算和十车位干涉检查通过。[试配状态](../../printing/parking-inserts/mini-cooper/r1/README.md) |

BMW的[生成脚本和验证](../../studies/measured-tray-s51-b23-d10-t5p1/README.md)是新增车型的设计参考；源文件保持原位置，不复制第二份可编辑CAD。新增款放本目录`<车型>/<修订>/`，使用该车型实测值和标记，保留相同的原生建模及验证方法。

[单件打印文件](../../printing/parking-inserts/README.md) · [组装者提供的定制信息](../../docs/customization.md)
