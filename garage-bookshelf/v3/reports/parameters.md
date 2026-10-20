# Spreadsheet 参数说明

所有长度单位为mm；数量、墙圈数、填充百分数无量纲，说明列已标注。B列Alias供Expression引用。independent input可直接编辑，derived通过公式关联。模块数5、层数3及文字岛拓扑是生成配置，不伪装为可动态增减实体的表格参数。

| Alias | 初始值/表达式 | 类型 | 设计含义 |
|---|---|---|---|
| Zero | 0 mm | input | 局部坐标基准 |
| ModuleWidth1 | 180 mm | input | 模块1宽 |
| ModuleWidth2 | 230 mm | input | 模块2宽 |
| ModuleWidth3 | 180 mm | input | 模块3宽 |
| ModuleWidth4 | 180 mm | input | 模块4宽 |
| ModuleWidth5 | 150 mm | input | 模块5宽 |
| ModuleStart1 | =Zero | derived | 模块1位置 |
| ModuleStart2 | =ModuleWidth1 | derived | 模块2位置 |
| ModuleStart3 | =ModuleStart2+ModuleWidth2 | derived | 模块3位置 |
| ModuleStart4 | =ModuleStart3+ModuleWidth3 | derived | 模块4位置 |
| ModuleStart5 | =ModuleStart4+ModuleWidth4 | derived | 模块5位置 |
| OverallWidth | =ModuleStart5+ModuleWidth5 | derived | 主体宽（派生） |
| OverallDepth | 220 mm | input | 主体深 |
| OverallHeight | 238 mm | input | 主体高 |
| BaseThickness | 8 mm | input | 底板厚 |
| BackThickness | 5 mm | input | 背板厚 |
| WallThickness | 6 mm | input | 竖板厚 |
| Overlap | 0.2 mm | input | 源设计融合重叠/榫根偏移 |
| WallStart | =BaseThickness-Overlap | derived | 背/竖板起点 |
| WallPadLength | =OverallHeight-WallStart | derived | 背/竖板高 |
| BackFront | =OverallDepth-BackThickness | derived | 背板前沿 |
| DividerX | 360 mm | input | 中隔板全局X |
| RightWallX | =OverallWidth-WallThickness | derived | 右侧板X |
| PanelDepth | =BackFront | derived | 竖板深 |
| RibSize | 25 mm | input | 根肋直角边 |
| RibThickness | 5 mm | input | 肋厚 |
| RibFrontY | 12 mm | input | 前肋Y |
| RibRearY | 183 mm | input | 后肋Y |
| TongueLength | 14 mm | input | 主体公榫Loft长 |
| SocketDepth | 15 mm | input | 主体母槽Loft长 |
| FitClearance | 0.40 mm | input | 名义总侧隙 |
| HalfClearance | =FitClearance/2 | derived | 单侧扩张 |
| SocketOvercut | 0.2 mm | input | 母槽上下越界 |
| BaseJointY1 | 52 mm | input | 底榫1中心 |
| BaseJointY2 | 168 mm | input | 底榫2中心 |
| BackJointZ1 | 66 mm | input | 背榫1中心 |
| BackJointZ2 | 180 mm | input | 背榫2中心 |
| BaseRootBottom | 15 mm | input | 底榫根底半宽 |
| BaseRootTop | 12 mm | input | 底榫根顶半宽 |
| BaseTipBottom | 12 mm | input | 底榫末底半宽 |
| BaseTipTop | 9 mm | input | 底榫末顶半宽 |
| BackFrontOverlap | 0.2 mm | input | 背榫前沿融合 |
| BackRootFront | 13 mm | input | 背榫根前半高 |
| BackRootRear | 17 mm | input | 背榫根后半高 |
| BackTipFront | 10 mm | input | 背榫末前半高 |
| BackTipRear | 14 mm | input | 背榫末后半高 |
| DeckHalfWidth | 180 mm | input | 层板半片宽 |
| DeckWidth | =2*DeckHalfWidth | derived | 整层宽 |
| DeckDepth | 215 mm | input | 层板深 |
| DeckThickness | 5 mm | input | 层板厚 |
| DeckFirstZ | 66 mm | input | 首层底高 |
| DeckPitch | 63 mm | input | 层距 |
| DeckZ1 | =DeckFirstZ | derived | 层1位置 |
| DeckZ2 | =DeckFirstZ+DeckPitch | derived | 层2位置 |
| DeckZ3 | =DeckFirstZ+2*DeckPitch | derived | 层3位置 |
| DeckNotchX | 153 mm | input | 每半片缺口起X |
| DeckNotchWidth | 14 mm | input | 缺口宽 |
| DeckFrontNotchDepth | 17 mm | input | 前缺口深 |
| DeckRearNotchStart | 188 mm | input | 后缺口起Y |
| DeckTongueLength | 10 mm | input | 层板公榫长 |
| DeckSocketDepth | 10.2 mm | input | 层板母槽长 |
| DeckJointY1 | 55 mm | input | 层板榫1 |
| DeckJointY2 | 160 mm | input | 层板榫2 |
| DeckRootBottom | 11 mm | input | 层板根底半宽 |
| DeckRootTop | 8 mm | input | 层板根顶半宽 |
| DeckTipBottom | 8 mm | input | 层板末底半宽 |
| DeckTipTop | 6 mm | input | 层板末顶半宽 |
| DeckBridgeWidth | 48 mm | input | 层板跨缝片宽 |
| DeckBridgeDepth | 110 mm | input | 层板跨缝片深 |
| DeckBridgeThickness | 3 mm | input | 层板跨缝片厚 |
| DeckBridgeX | =DeckHalfWidth-DeckBridgeWidth/2 | derived | 跨缝片位置 |
| DeckBridgeY | 55 mm | input | 跨缝片Y |
| ColumnRadius | 6 mm | input | 柱轴半径 |
| CollarRadius | 14 mm | input | 托环半径 |
| ColumnCentreOffset | 10 mm | input | 原柱局部轴心 |
| ColumnPitchX | 330 mm | input | 柱X定位距 |
| ColumnPitchY | 185 mm | input | 柱Y定位距 |
| ColumnTop | 230 mm | input | 柱顶Z |
| ColumnHeight | =ColumnTop-BaseThickness | derived | 柱轴高 |
| ConeHeight | 8 mm | input | 锥肩高 |
| CollarThickness | 4 mm | input | 托环厚 |
| SignWidth | 36 mm | input | 侧牌局部宽 |
| SignHeight | 180 mm | input | 侧牌局部长 |
| SignThickness | 6 mm | input | 侧牌厚 |
| SignBaseZ | 50 mm | input | 侧牌装配Z |
| BillboardHalfWidth | 180 mm | input | 广告牌半宽 |
| BillboardHeight | 64 mm | input | 广告牌高 |
| BillboardThickness | 6 mm | input | 广告牌厚 |
| BillboardBottom | 300 mm | input | 广告牌底Z |
| BillboardBridgeWidth | 50 mm | input | 广告牌跨缝片宽 |
| BillboardBridgeThickness | 3 mm | input | 广告牌跨缝片厚 |
| BillboardBridgeHeight | 36 mm | input | 广告牌跨缝片高 |
| BillboardBridgeLift | 14 mm | input | 跨缝片距底高 |
| PostWidth | 24 mm | input | 广告牌支架宽 |
| PostThickness | 6 mm | input | 支架厚 |
| PostHeight | 150 mm | input | 支架高 |
| PostCentreLeft | =BillboardHalfWidth/2 | derived | 左支架中心 |
| PostCentreRight | =BillboardHalfWidth*1.5 | derived | 右支架中心 |
| TextPixel | 1 mm | input | 原掩码像素尺寸 |
| TextOverlap | 0.1 mm | input | 像素行融合扩张 |
| TextThickness | 1 mm | input | 文字厚 |
| TextOriginX | 90 mm | input | 文字掩码原点X |
| TextLovelyZ | 332 mm | input | Lovely行原点Z |
| TextDrivenZ | 304 mm | input | Driven行原点Z |
| CouponWidth | 70 mm | input | 试件宽 |
| CouponDepth | 100 mm | input | 底榫试件深 |
| CouponBaseY | 50 mm | input | 底试榫中心 |
| CouponBackHeight | 80 mm | input | 背试件高 |
| CouponBackZ | 48 mm | input | 背试榫中心 |
| NarrowCutFrom2 | 35 mm | input | 模块2局部删除起点 |
| NarrowCutTo2 | 165 mm | input | 模块2局部删除终点 |
| NarrowRemoved2 | =NarrowCutTo2-NarrowCutFrom2 | derived | 模块2缩短移除量 |
| NarrowCutFrom5 | 30 mm | input | 模块5局部删除起点 |
| NarrowCutTo5 | 130 mm | input | 模块5局部删除终点 |
| NarrowRemoved5 | =NarrowCutTo5-NarrowCutFrom5 | derived | 模块5缩短移除量 |
| NarrowViewOffset5 | 135 mm | input | 原缩短查看工程模块5平移 |
| PrintBrim | 4 mm | input | 原PLA brim |
| PrintBedWidth | 256 mm | input | 原打印床X |
| PrintBedDepth | 256 mm | input | 原打印床Y |
| PrintHeight | 260 mm | input | 原打印高度 |
| ExportLinearDeflection | 0.02 mm | input | 新STL最大线性弦高（导出设置） |
| ModuleCount | =5 | derived | 主体模块数量（无量纲；固定拓扑，改数量需重建） |
| DeckLevelCount | =3 | derived | 车库层数（无量纲；固定拓扑） |
| ColumnCount | =4 | derived | 承托柱数量（无量纲；固定拓扑） |
| PrintWallLoops | 4 | input | 原PLA墙圈数（无量纲） |
| PrintInfillPercent | 25 | input | 原PLA填充百分数（无量纲，25表示25%） |
