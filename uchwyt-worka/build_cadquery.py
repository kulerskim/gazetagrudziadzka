# -*- coding: utf-8 -*-
"""Generuje STEP (zlozenie) i STL (orientacja do druku) z tbh_design.py.

    pip install cadquery
    python build_cadquery.py
"""
import os
import sys
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'fusion360', 'UchwytWorka'))
import tbh_design as D  # noqa: E402


def plane(pl, a):
    if pl == 'XY':
        return cq.Plane(origin=(0, 0, a), xDir=(1, 0, 0), normal=(0, 0, 1))
    if pl == 'XZ':   # (u,v)=(x,z); normalna -Y, wiec start od a1
        return cq.Plane(origin=(0, a, 0), xDir=(1, 0, 0), normal=(0, -1, 0))
    if pl == 'YZ':
        return cq.Plane(origin=(a, 0, 0), xDir=(0, 1, 0), normal=(1, 0, 0))
    raise ValueError(pl)


def draw(wp, shape):
    k = shape[0]
    if k == 'poly':
        return wp.polyline(shape[1]).close()
    if k == 'circle':
        _, cu, cv, r = shape
        return wp.moveTo(cu, cv).circle(r)
    if k == 'rrect':
        _, cu, cv, w, h, r = shape
        x0, x1, y0, y1 = cu - w / 2, cu + w / 2, cv - h / 2, cv + h / 2
        s = r * (1 - 2 ** -0.5)
        return (wp.moveTo(x0 + r, y0).lineTo(x1 - r, y0)
                .threePointArc((x1 - s, y0 + s), (x1, y0 + r)).lineTo(x1, y1 - r)
                .threePointArc((x1 - s, y1 - s), (x1 - r, y1)).lineTo(x0 + r, y1)
                .threePointArc((x0 + s, y1 - s), (x0, y1 - r)).lineTo(x0, y0 + r)
                .threePointArc((x0 + s, y0 + s), (x0 + r, y0)).close())
    raise ValueError(k)


def solid_of(op):
    pl = op['plane']
    if op['kind'] == 'prism':
        a0, a1 = op['a0'], op['a1']
        start = a1 if pl == 'XZ' else a0
        return draw(cq.Workplane(plane(pl, start)), op['shape']).extrude(a1 - a0).val()
    if op['kind'] == 'loft':
        (a0, s0), (a1, s1) = op['sections']
        wp = draw(cq.Workplane(plane(pl, a0)), s0)
        wp = draw(wp.workplane(offset=a1 - a0), s1)
        return wp.loft(combine=True).val()
    raise ValueError(op['kind'])


def build(ops):
    body = None
    for op in ops:
        s = solid_of(op)
        if body is None:
            body = s
        elif op['op'] == 'add':
            body = body.fuse(s)
        else:
            body = body.cut(s)
    return body.clean()


def main():
    p = D.P
    d = D.derived(p)
    out_stl = os.path.join(HERE, 'stl')
    out_step = os.path.join(HERE, 'step')
    os.makedirs(out_stl, exist_ok=True)
    os.makedirs(out_step, exist_ok=True)
    asm = cq.Assembly(name='UchwytWorka')
    colors = {'Ramka': (0.85, 0.85, 0.82), 'Klapka': (0.30, 0.55, 0.40),
              'Pierscien': (0.90, 0.60, 0.20), 'Tasma': (0.20, 0.40, 0.80)}
    solids = {}
    for name, fn in D.PARTS:
        s = build(fn(p))
        solids[name] = s
        print(f'{name}: volume {s.Volume() / 1000:.1f} cm3, valid={s.isValid()}')
        asm.add(s, name=name, color=cq.Color(*colors[name]))
        cq.exporters.export(cq.Workplane().add(s), os.path.join(out_step, f'{name}.step'))
        # orientacja do druku
        if name in ('Ramka', 'Klapka', 'Pierscien'):
            ps = s.rotate((0, 0, 0), (1, 0, 0), 180)   # gora na stole
        else:
            ps = s
        bb = ps.BoundingBox()
        ps = ps.translate((-bb.center.x, -bb.center.y, -bb.zmin))
        cq.exporters.export(cq.Workplane().add(ps), os.path.join(out_stl, f'{name}.stl'),
                            tolerance=0.02, angularTolerance=0.1)
        bb = ps.BoundingBox()
        print(f'   druk: {bb.xlen:.1f} x {bb.ylen:.1f} x {bb.zlen:.1f} mm')
    asm.save(os.path.join(out_step, 'UchwytWorka_zlozenie.step'))
    # kontrola kolizji klapka/ramka/pierscien w pozycji zamknietej
    for a, b in (('Ramka', 'Klapka'), ('Ramka', 'Pierscien'), ('Klapka', 'Pierscien')):
        v = solids[a].intersect(solids[b]).Volume()
        print(f'kolizja {a}-{b}: {v:.3f} mm3')
    return solids


if __name__ == '__main__':
    main()
