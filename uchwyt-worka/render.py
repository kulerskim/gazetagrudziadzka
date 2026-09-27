# Podglady PNG (wymaga: cadquery, trimesh, matplotlib)
import os, sys, math
import numpy as np
import trimesh, cadquery as cq
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_cadquery as B
D = B.D

def mesh(s):
    vs, tris = s.tessellate(0.1, 0.2)
    return np.array([(v.x, v.y, v.z) for v in vs]), np.array(tris)

def bent_strip(d):
    """Tasma w pozycji zamknietej (do podgladu)."""
    ys, zm, R, ts, Ws = d['ys'], d['z_m'], d['R'], d['ts'], d['Ws']
    cy, cz = ys - R, zm
    pts = [(ys, zm - d['neck_f'] - d['hb'])]
    for i in range(0, 31):
        a = math.radians(90 * i / 30)
        pts.append((cy + R * math.cos(a), cz + R * math.sin(a)))
    pts.append((d['yr'] - d['neck_l'] - d['hb'], d['Zs']))
    pts = np.array(pts)
    tang = np.gradient(pts, axis=0); tang /= np.linalg.norm(tang, axis=1)[:, None]
    nrm = np.stack([-tang[:, 1], tang[:, 0]], 1)
    poly = [tuple(q) for q in pts + nrm * ts / 2] + [tuple(q) for q in (pts - nrm * ts / 2)[::-1]]
    return cq.Workplane('YZ', origin=(-Ws / 2, 0, 0)).polyline(poly).close().extrude(Ws).val()

COL = {'Ramka': '#d9d6cc', 'Klapka': '#4c8c66', 'Pierscien': '#e69933', 'Tasma': '#3366cc'}

def render(solids, fname, views, title):
    fig = plt.figure(figsize=(6 * len(views), 6))
    for k, (el, az) in enumerate(views):
        ax = fig.add_subplot(1, len(views), k + 1, projection='3d')
        allv = []
        for name, s in solids:
            v, t = mesh(s)
            allv.append(v)
            pc = Poly3DCollection(v[t], facecolor=COL[name], edgecolor='none', alpha=1.0)
            # proste cieniowanie
            n = np.cross(v[t][:, 1] - v[t][:, 0], v[t][:, 2] - v[t][:, 0])
            n /= (np.linalg.norm(n, axis=1)[:, None] + 1e-9)
            L = np.array([0.4, -0.6, 0.7]); L /= np.linalg.norm(L)
            sh = 0.45 + 0.55 * np.abs(n @ L)
            base = np.array(matplotlib.colors.to_rgb(COL[name]))
            pc.set_facecolor(np.clip(base[None, :] * sh[:, None], 0, 1))
            ax.add_collection3d(pc)
        allv = np.vstack(allv)
        mn, mx = allv.min(0), allv.max(0); c = (mn + mx) / 2; r = (mx - mn).max() / 2
        ax.set_xlim(c[0]-r, c[0]+r); ax.set_ylim(c[1]-r, c[1]+r); ax.set_zlim(c[2]-r, c[2]+r)
        ax.set_box_aspect((1, 1, 1)); ax.view_init(el, az); ax.set_axis_off()
    fig.suptitle(title); fig.tight_layout()
    fig.savefig(os.path.join(HERE, 'img', fname), dpi=110); plt.close(fig)

if __name__ == '__main__':
    p = D.P; d = D.derived(p)
    S = {n: B.build(fn(p)) for n, fn in D.PARTS}
    strip = bent_strip(d)
    closed = [('Ramka', S['Ramka']), ('Pierscien', S['Pierscien']), ('Klapka', S['Klapka']), ('Tasma', strip)]
    render(closed, 'zlozenie.png', [(25, -60), (25, 150)], 'Zlozenie (klapka zamknieta)')
    render([('Ramka', S['Ramka']), ('Pierscien', S['Pierscien'])], 'ramka_pierscien.png', [(40, -60), (-30, -120)], 'Ramka + pierscien')
    # przekroj srodkiem (x = 0..) - pokazuje zawias i zatrzask
    cutter = cq.Workplane('XY').box(400, 400, 400).translate((200 + 0.0, 0, 0)).val()
    sec = [(n, s.cut(cutter)) for n, s in closed]
    render(sec, 'przekroj.png', [(0, 0)], 'Przekroj X=0 (widok z boku)')
    render([('Klapka', S['Klapka'])], 'klapka_spod.png', [(-50, -60)], 'Klapka od spodu')
    print('ok')
