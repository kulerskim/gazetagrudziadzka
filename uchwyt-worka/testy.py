# -*- coding: utf-8 -*-
"""Male wydruki testowe (kupony) + szablon 1:1 do przylozenia pod blat.

    python testy.py   ->  stl/testy/*.stl, szablon/szablon_1do1.pdf
"""
import os
import cadquery as cq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import build_cadquery as B

D = B.D
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'stl', 'testy')


def clip(solid, x0, x1, y0, y1, z0, z1):
    b = cq.Workplane('XY').box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0)).val()
    return solid.intersect(b)


def save(solid, name, flip):
    s = solid.rotate((0, 0, 0), (1, 0, 0), 180) if flip else solid
    bb = s.BoundingBox()
    s = s.translate((-bb.center.x, -bb.center.y, -bb.zmin))
    cq.exporters.export(cq.Workplane().add(s), os.path.join(OUT, name + '.stl'),
                        tolerance=0.02, angularTolerance=0.1)
    bb = s.BoundingBox()
    print(f'{name:28s} {bb.xlen:6.1f} x {bb.ylen:6.1f} x {bb.zlen:5.1f} mm, {s.Volume() / 1000:5.1f} cm3')


def main():
    os.makedirs(OUT, exist_ok=True)
    p = dict(D.P)
    d = D.derived(p)
    H, Xo, Yf, Yb, yr, yl = d['H'], d['Xo'], d['Yf'], d['Yb'], d['yr'], d['yl']
    frame = B.build(D.frame_ops(p))
    lid = B.build(D.lid_ops(p))
    ring = B.build(D.ring_ops(p))

    # T1: zawias-sprezyna. Wycinek belki + klapki szer. 50 mm, tasma 40 mm.
    save(clip(frame, -25, 25, 70, Yb + 1, 20, H + 1), 'T1_zawias_ramka', True)
    save(clip(lid, -25, 25, 30, yr + 1, 0, 100), 'T1_zawias_klapka', True)
    pt = dict(p, Ws=40.0)
    save(B.build(D.spring_ops(pt, x_off=0, y_off=0)), 'T1_tasma_40mm', False)

    # T2: zatrzask z przyciskiem + fragment przodu klapki
    save(clip(frame, -60, 20, Yf - 12, Yf + 12, 20, H + 1), 'T2_zatrzask_ramka', True)
    save(clip(lid, -20, 20, yl - 1, yl + 35, 0, 100), 'T2_zatrzask_klapka', True)

    # T3: pasowanie worka - niski pelny obwod ramki (z kolnierzem) + niski pierscien
    save(clip(frame, -Xo - 1, Xo - 0.01, -150, 150, -1, 12), 'T3_worek_ramka_12mm', False)
    save(clip(ring, -200, 200, -200, 200, 0, 14), 'T3_worek_pierscien_12mm', False)

    template(frame, d)


def template(frame, d):
    """Rzut z gory 1:1 na 2 kartkach A4 (drukowac w skali 100%)."""
    import numpy as np
    sec = frame.intersect(cq.Workplane('XY').box(600, 600, 0.5).translate((0, 0, d['H'] - 0.3)).val())
    os.makedirs(os.path.join(HERE, 'szablon'), exist_ok=True)
    vs, tris = sec.tessellate(0.05, 0.2)
    V = np.array([(v.x, v.y) for v in vs])
    bb = frame.BoundingBox()
    x0, x1, y0, y1 = bb.xmin - 5, bb.xmax + 5, bb.ymin - 5, bb.ymax + 5
    xm = (x0 + x1) / 2
    W, Hh = 297.0, 210.0  # A4 poziomo
    with PdfPages(os.path.join(HERE, 'szablon', 'szablon_1do1.pdf')) as pdf:
        for k, (a, b) in enumerate(((x0, xm + 10), (xm - 10, x1))):
            fig = plt.figure(figsize=(W / 25.4, Hh / 25.4))
            ax = fig.add_axes([0, 0, 1, 1])
            # strona pionowa: os Y modelu -> poziomo, os X modelu -> pionowo
            cx, cy = (y0 + y1) / 2, (a + b) / 2
            ax.set_xlim(cx - W / 2, cx + W / 2)
            ax.set_ylim(cy - Hh / 2, cy + Hh / 2)
            ax.set_aspect('equal')
            ax.axis('off')
            for t in tris:
                pts = V[list(t)]
                ax.fill(pts[:, 1], pts[:, 0], color='0.8', lw=0)
            ax.axhline(xm, color='r', lw=0.5, ls='--')
            ax.text(cx, xm + 1, 'linia sklejenia', color='r', ha='center', fontsize=7)
            hx = d['Xo'] + d['hole_x']
            for hy in (-d['hole_dy'] / 2, d['hole_dy'] / 2):
                ax.plot([hy - 3, hy + 3], [hx, hx], 'k', lw=0.5)
                ax.plot([hy, hy], [hx - 3, hx + 3], 'k', lw=0.5)
            ax.plot([cx - 50, cx + 50], [cy - 90, cy - 90], 'k', lw=1)
            ax.text(cx, cy - 88, 'kontrola skali: 100 mm', ha='center', fontsize=7)
            ax.text(cx, cy + 100, f'Szablon 1:1 - kartka {k + 1}/2, A4 poziomo (widok z gory, drukuj 100%)\n'
                    'szary = obrys ramki + plyty na wys. blatu; krzyzyki = otwory na wkrety\n'
                    'gora kartki = strona blatu (+X), lewo = pokoj, prawo = sciana',
                    ha='center', va='top', fontsize=7)
            pdf.savefig(fig)
            plt.close(fig)
    print('szablon/szablon_1do1.pdf')


if __name__ == '__main__':
    main()
