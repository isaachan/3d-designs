"""One-command pipeline: step_3 PNGs -> step_4 SVGs -> step_5 FCStd -> step_6 STL + 3MF.

Run inside FreeCAD's console interpreter:

    /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd \
        handwriting-handachuan/pipeline/run.py [--project DIR] [--config FILE] [--force-svg]
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, HERE)
import trace_svg
import detect
import cadbuild
import export3mf


def load_config(path, fallback):
    if path and os.path.isfile(path):
        with open(path) as fh:
            return json.load(fh)
    if os.path.isfile(fallback):
        with open(fallback) as fh:
            return json.load(fh)
    with open(os.path.join(HERE, 'default_config.json')) as fh:
        return json.load(fh)


def ensure_svgs(project, cfg, force):
    svg_dir = os.path.join(project, 'step_4_layered_svgs')
    os.makedirs(svg_dir, exist_ok=True)
    layers = os.path.join(project, 'step_3_layered_pictures')
    status = []

    hw_path = os.path.join(svg_dir, 'handwriting.svg')
    if force or not os.path.isfile(hw_path):
        svg, loops = trace_svg.trace_handwriting_png(
            os.path.join(layers, 'handwriting.png'),
            cfg['handwriting']['alpha_threshold'],
            cfg['handwriting']['min_component_px'],
            cfg['handwriting']['simplify_epsilon'])
        with open(hw_path, 'w') as fh:
            fh.write(svg)
        status.append('handwriting.svg: traced %d loops' % loops)
    else:
        status.append('handwriting.svg: reused existing file')

    lines_path = os.path.join(svg_dir, 'ruled_lines.svg')
    if force or not os.path.isfile(lines_path):
        rows = detect.ruled_line_rows(
            os.path.join(layers, 'ruled_lines.png'),
            cfg['ruled_lines'].get('row_min_coverage', 0.5),
            cfg['ruled_lines'].get('alpha_threshold', 128))
        w, h = cfg['canvas']['width_px'], cfg['canvas']['height_px']
        paths = ''.join('    <path d="M 0 %d H %d"/>\n' % (round(y), w) for y in rows)
        with open(lines_path, 'w') as fh:
            fh.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                     '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">\n'
                     '  <g fill="none" stroke="#666a6d" stroke-width="3" stroke-linecap="round">\n%s  </g>\n</svg>\n'
                     % (w, h, w, h, paths))
        status.append('ruled_lines.svg: detected %d rows' % len(rows))
    else:
        status.append('ruled_lines.svg: reused existing file')

    paper_path = os.path.join(svg_dir, 'paper_outline.svg')
    if force or not os.path.isfile(paper_path):
        x0, y0, x1, y1 = detect.paper_bbox(os.path.join(layers, 'paper_outline.png'))
        r = cfg['svg_cosmetics']['paper_corner_radius_px']
        w, h = cfg['canvas']['width_px'], cfg['canvas']['height_px']
        with open(paper_path, 'w') as fh:
            fh.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                     '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">\n'
                     '  <path d="%s" fill="none" stroke="#202020" stroke-width="3" stroke-linejoin="round"/>\n</svg>\n'
                     % (w, h, w, h, detect.rounded_rect_path_px(x0, y0, x1, y1, r)))
        status.append('paper_outline.svg: bbox %s' % ((x0, y0, x1, y1),))
    else:
        status.append('paper_outline.svg: reused existing file')

    date_path = os.path.join(svg_dir, 'date.svg')
    if force or not os.path.isfile(date_path):
        cos = cfg['svg_cosmetics']
        with open(date_path, 'w') as fh:
            fh.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                     '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">\n'
                     '  <text x="%s" y="%s" fill="#292929" font-family="Arial, Helvetica, sans-serif" '
                     'font-size="%s" font-weight="400" letter-spacing="2.2">%s</text>\n</svg>\n'
                     % (cfg['canvas']['width_px'], cfg['canvas']['height_px'],
                        cfg['canvas']['width_px'], cfg['canvas']['height_px'],
                        cos['date_text_x_px'], cos['date_text_y_px'], cos['date_font_size_px'],
                        cfg['date']['text']))
        status.append('date.svg: rebuilt clean text %r' % cfg['date']['text'])
    else:
        status.append('date.svg: reused existing file')
    return status


def default_project():
    """Newest dated project directory (YYYYMMDD) that has step_3 inputs."""
    root = os.path.dirname(HERE)
    dated = [d for d in os.listdir(root)
             if re.fullmatch(r'\d{8}', d)
             and os.path.isfile(os.path.join(root, d, 'step_3_layered_pictures', 'ruled_lines.png'))]
    if dated:
        return os.path.join(root, max(dated))
    return root  # legacy flat layout


def check_inputs(project, svg_dir, force_svg):
    layers = os.path.join(project, 'step_3_layered_pictures')
    missing = []
    if not os.path.isfile(os.path.join(layers, 'ruled_lines.png')):
        missing.append('ruled_lines.png')
    hw_svg = os.path.join(svg_dir, 'handwriting.svg')
    if (force_svg or not os.path.isfile(hw_svg)) and \
            not os.path.isfile(os.path.join(layers, 'handwriting.png')):
        missing.append('handwriting.png')
    if missing:
        sys.stdout.flush()
        print('missing step_3 inputs in %s: %s' % (layers, ', '.join(missing)), file=sys.stderr, flush=True)
        raise SystemExit(1)


def log(tag, msg):
    print('[%s] %s' % (tag, msg), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project', default=None)
    ap.add_argument('--config', default=None)
    ap.add_argument('--force-svg', action='store_true')
    args, _unknown = ap.parse_known_args([a for a in sys.argv[1:] if a != '--'])

    project = os.path.abspath(args.project or os.environ.get('NAMEPLATE_PROJECT') or default_project())
    log('project', project)
    cfg = load_config(args.config, os.path.join(project, 'nameplate_config.json'))

    svg_dir = os.path.join(project, 'step_4_layered_svgs')
    check_inputs(project, svg_dir, args.force_svg)
    status = ensure_svgs(project, cfg, args.force_svg)
    for line in status:
        log('svg', line)

    fcstd = os.path.join(project, 'step_5_freecad_model', 'nameplate.FCStd')
    os.makedirs(os.path.dirname(fcstd), exist_ok=True)
    doc, rows = cadbuild.build(project, cfg, svg_dir, fcstd)
    log('cad', '%s - ruled rows: %s' % (os.path.relpath(fcstd, project), [round(r, 1) for r in rows]))

    out_dir = os.path.join(project, 'step_6_printables')
    export3mf.export_stls(doc, out_dir)
    mf = export3mf.export_3mf(doc, cfg, os.path.join(out_dir, 'nameplate_multicolor.3mf'))
    log('stl', ', '.join(sorted(f for f in os.listdir(out_dir) if f.endswith('.stl'))))
    log('3mf', os.path.relpath(mf, project))


main()
