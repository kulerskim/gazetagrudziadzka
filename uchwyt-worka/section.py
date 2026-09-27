# Przekroje 2D (YZ przy x=0) - detal zawiasu i zatrzasku
import os, sys, numpy as np, trimesh
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import build_cadquery as B, render as Rn
D = B.D; p = D.P; d = D.derived(p)
S = {n: B.build(fn(p)) for n, fn in D.PARTS}
parts = [('Ramka', S['Ramka']), ('Pierscien', S['Pierscien']), ('Klapka', S['Klapka']), ('Tasma', Rn.bent_strip(d))]

def slice2d(s, x):
    v, t = Rn.mesh(s); m = trimesh.Trimesh(v, t, process=True)
    sec = m.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
    if sec is None: return []
    return [np.array(sec.vertices[e.points])[:, 1:] for e in sec.entities]

def draw(ax, x, lim, title):
    for n, s in parts:
        for poly in slice2d(s, x):
            ax.add_patch(Polygon(poly, closed=True, fc=Rn.COL[n], ec='k', lw=0.4))
    ax.set_xlim(*lim[0]); ax.set_ylim(*lim[1]); ax.set_aspect('equal'); ax.grid(alpha=.3)
    ax.set_title(title); ax.set_xlabel('Y [mm] (+ = sciana)'); ax.set_ylabel('Z [mm]')

fig, axs = plt.subplots(1, 3, figsize=(18, 6))
draw(axs[0], 0.0, ((-110, 120), (-5, 65)), 'Przekroj X=0 - calosc')
draw(axs[1], 0.0, ((80, 115), (25, 60)), 'Zawias-sprezyna (tasma PETG)')
draw(axs[2], 0.0, ((-106, -86), (28, 58)), 'Zatrzask + przycisk')
fig.tight_layout(); fig.savefig(os.path.join(HERE, 'img', 'przekroje.png'), dpi=110)
fig, ax = plt.subplots(figsize=(9, 5))
draw(ax, 60.0, ((-110, 120), (-5, 65)), 'Przekroj X=60 (plyta montazowa w tle)')
fig.savefig(os.path.join(HERE, 'img', 'przekroj_x60.png'), dpi=90)
