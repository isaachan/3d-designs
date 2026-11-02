"""Rear installation preview using the actual native solids; orange is annotation only."""
import argparse

import _bootstrap
import FreeCAD as App
from PIL import Image, ImageDraw, ImageFont
from garage_bookshelf.paths import CAD, output_directory, sha
from garage_bookshelf.reinforcement import PLATES
from garage_bookshelf.rendering.software import triangles, render, saved_colors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output')
    args = parser.parse_args()
    output = output_directory(args.output, 'reinforcement-preview')
    before = sha(CAD)
    doc = App.openDocument(str(CAD))
    try:
        colors = saved_colors(CAD)
        names = ['module_1', 'module_2', 'module_3', 'billboard']+[row[0] for row in PLATES]
        for name, *_ in PLATES:
            body = doc.getObject(name+'_Body')
            colors[body.Tip.Name] = [(1., .45, .08)]*len(body.Shape.Faces)
        points, paint = triangles(doc, colors, names)
        file = output/'rear-installation.png'
        render(points, paint, file, [0, 1, .08], 1800, 1000)
    finally:
        App.closeDocument(doc.Name)
    model = Image.open(file)
    image = Image.new('RGB', (1800, 1200), 'white')
    image.paste(model, (0, 70))
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('/System/Library/Fonts/Hiragino Sans GB.ttc', 32)
    draw.text((45, 20), '背面安装：每条拼缝上、下各一片，共四片', font=font, fill='#17191b')
    draw.text((45, 1120), '每片 60 × 30 × 3 mm · 两侧各搭接 30 mm · 胶粘固定', font=font, fill='#17191b')
    draw.text((45, 1160), '橙色仅为位置标示；CAD 与打印件均为黑色。原主体无需修改或重印。', font=font, fill='#555555')
    image.save(file)
    assert sha(CAD) == before
    print('PASS', file, flush=True)


if __name__ == '__main__':
    main()
