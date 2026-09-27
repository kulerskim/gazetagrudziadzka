# -*- coding: utf-8 -*-
"""
Uchwyt worka na smieci z klapka - wspolna definicja geometrii.

Czysty Python (bez zaleznosci). Ten sam plik jest uzywany przez:
  * skrypt Fusion 360 (UchwytWorka.py) - buduje model z historia (timeline),
  * build_cadquery.py - generuje STL/STEP i podglady.

Wszystkie wymiary w mm. Uklad wspolrzednych (stan zamontowany):
  X+ -> w strone blatu (tam jest plyta montazowa),
  Y+ -> w strone sciany (tam jest zawias), Y- -> w strone pokoju (przycisk),
  Z+ -> do gory, Z=0 -> spod ramki, Z=H -> gorna krawedz ramki = spod blatu.

Zmien wartosci w P i uruchom skrypt ponownie.
"""
import math

P = dict(
    # --- ramka ---
    H=50.0,          # wysokosc ramki (4-6 cm)
    Wi=170.0,        # wewnetrzny wymiar otworu w X (wzdluz krawedzi blatu)
    Di=180.0,        # wewnetrzny wymiar otworu w Y (sciana -> pokoj)
    rc=15.0,         # promien naroznikow otworu
    t=3.0,           # grubosc scianek
    lip_w=3.0,       # wewnetrzny kolnierz 45 st. na dole (oparcie pierscienia)
    # --- plyta montazowa pod blat ---
    Lp=80.0,         # wysiegniecie plyty pod blat (od sciany ramki)
    Dp=120.0,        # szerokosc plyty (w Y)
    tp=6.0,          # grubosc plyty
    hole_d=4.5,      # otwor na wkret (4 mm, leb stozkowy)
    csk_d=9.0,       # srednica poglebienia stozkowego 90 st.
    hole_x=50.0,     # odleglosc otworow od sciany ramki
    hole_dy=70.0,    # rozstaw otworow w Y
    rib_t=4.0,       # grubosc zeber pod plyta
    # --- zatrzask z przyciskiem (strona pokoju) ---
    g=3.0,           # szczelina miedzy ramieniem sprezystym a sciana
    ta=2.5,          # grubosc ramienia sprezystego
    ha=20.0,         # wysokosc ramienia
    La=50.0,         # dlugosc ramienia (od zamocowania do konca)
    Ll=16.0,         # szerokosc zaczepu
    lp=2.0,          # wysuniecie zaczepu (glebokosc zazebienia)
    lh=3.0,          # wysokosc zaczepu
    root_w=8.0,      # szerokosc nasady ramienia
    # --- zawias-sprezyna (tasma PETG) ---
    R=12.0,          # promien giecia tasmy przy zamknietej klapce
    ts=0.6,          # grubosc tasmy (0.5-0.8; grubsza = mocniej otwiera)
    hb=3.0,          # kwadratowa listwa na koncach tasmy
    Ws=80.0,         # szerokosc tasmy
    neck_f=4.5,      # dlugosc szyjki w ramce
    neck_l=2.0,      # dlugosc szyjki w klapce
    c=0.3,           # luz w kanalach tasmy
    skin=2.0,        # scianka za kanalem
    back_rest=4.0,   # ile klapka zachodzi na tylny rant ramki
    # --- klapka ---
    Tl=6.0,          # calkowita grubosc klapki
    top_t=2.0,       # grubosc gornej plyty klapki (reszta to kieszen od spodu)
    sk=2.5,          # grubosc fartuchow klapki
    sk_h=4.0,        # wysokosc fartuchow
    cl=0.5,          # luz fartucha bocznego
    c_h=0.3,         # luz haczyka
    # --- pierscien na worek ---
    cb=1.0,          # luz na worek miedzy pierscieniem a ramka (na strone)
    tr=2.5,          # grubosc scianki pierscienia
    grip_w=30.0,     # szerokosc uchwytow pierscienia
    grip_d=8.0,      # glebokosc uchwytow
)


def derived(p):
    d = dict(p)
    d['Xo'] = p['Wi'] / 2 + p['t']                 # polowa zewn. szerokosci ramki
    d['Yf'] = -(p['Di'] / 2 + p['t'])              # zewn. lico sciany przedniej
    d['Ht'] = p['H'] + p['Tl']                     # gora klapki
    d['Zs'] = p['H'] + 1.2 + p['ts'] / 2 + p['c'] / 2   # os tasmy w klapce
    d['z_m'] = d['Zs'] - p['R']                    # wylot tasmy z ramki
    d['yr'] = p['Di'] / 2 + p['back_rest']         # tylna krawedz klapki
    d['ys'] = d['yr'] + p['R']                     # os pionowej czesci tasmy
    d['Yb'] = d['ys'] - p['ts'] / 2 - p['c'] / 2 + p['hb'] + p['c'] + p['skin']
    d['Lsp'] = p['neck_l'] + p['hb'] + p['c'] + 2.0   # glebokosc grzbietu klapki
    d['Ls'] = 2 * p['hb'] + p['neck_f'] + p['neck_l'] + math.pi * p['R'] / 2
    d['ledge_front'] = d['Yf'] - p['g'] - p['ta'] - p['lp']
    d['yl'] = d['ledge_front'] - p['c_h'] - p['sk']      # przednia krawedz klapki
    d['xl0'] = -d['Xo'] - p['cl'] - p['sk']
    d['xl1'] = d['Xo']
    return d


# ---------------------------------------------------------------------------
# Operacje. Kazda operacja to slownik:
#   kind='prism': plane in {'XY','XZ','YZ'}, a0,a1 (zakres wzdluz normalnej),
#                 shape, op in {'add','cut'}
#   kind='loft' : plane, sections=[(a, shape), (a, shape)], op
# shape: ('rrect', cu, cv, w, h, r) | ('poly', [(u,v),...]) | ('circle', cu, cv, r)
# Plaszczyzny: XY -> (u,v)=(x,y), normalna Z
#              XZ -> (u,v)=(x,z), normalna Y
#              YZ -> (u,v)=(y,z), normalna X
# ---------------------------------------------------------------------------

def box(x0, x1, y0, y1, z0, z1, op='add', name=''):
    return dict(kind='prism', plane='XY', a0=z0, a1=z1, op=op, name=name,
                shape=('poly', [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]))


def prism(plane, a0, a1, shape, op='add', name=''):
    return dict(kind='prism', plane=plane, a0=a0, a1=a1, shape=shape, op=op, name=name)


def frame_ops(p):
    d = derived(p)
    H, Wi, Di, rc, t = d['H'], d['Wi'], d['Di'], d['rc'], d['t']
    Xo, Yf, ys, z_m, Yb = d['Xo'], d['Yf'], d['ys'], d['z_m'], d['Yb']
    lw = d['lip_w']
    ops = []
    # korpus
    ops.append(prism('XY', 0, H, ('rrect', 0, 0, 2 * Xo, Di + 2 * t, rc + t), name='Korpus'))
    # belka zawiasu (tyl)
    zb0 = z_m - d['neck_f'] - d['hb'] - d['c'] - 3.0
    ops.append(box(-Xo, Xo, Di / 2 - 1, Yb, zb0, H, name='Belka zawiasu'))
    # otwor + kolnierz 45 st. na dole
    ops.append(prism('XY', lw - 0.1, H + 1, ('rrect', 0, 0, Wi, Di, rc), 'cut', 'Otwor'))
    ops.append(dict(kind='loft', plane='XY', op='cut', name='Kolnierz 45',
                    sections=[(-1.0, ('rrect', 0, 0, Wi - 2 * (lw + 1), Di - 2 * (lw + 1), rc - lw - 1)),
                              (lw, ('rrect', 0, 0, Wi, Di, rc))]))
    # fazowanie tylu belki (miejsce na luk tasmy)
    y1 = ys - (H - z_m)
    ops.append(prism('YZ', -Xo - 1, Xo + 1, ('poly', [
        (y1, H), (ys, z_m), (Yb + 1, z_m - (Yb + 1 - ys)), (Yb + 1, H + 1), (y1, H + 1)]),
        'cut', 'Faza tasmy'))
    # kanal tasmy (otwarty od strony +X, zamkniety przy -X)
    xa, xb = -d['Ws'] / 2 - d['c'], Xo + 1
    ya = ys - d['ts'] / 2 - d['c'] / 2
    ops.append(box(xa, xb, ya, ys + d['ts'] / 2 + d['c'] / 2, z_m - d['neck_f'], H + 1, 'cut', 'Szyjka tasmy'))
    ops.append(box(xa, xb, ya, ys - d['ts'] / 2 + d['hb'] + d['c'] / 2,
                   z_m - d['neck_f'] - d['hb'] - d['c'], z_m - d['neck_f'], 'cut', 'Kanal listwy'))
    # plyta montazowa + zebra
    X0 = Xo
    ops.append(box(X0 - 1, X0 + d['Lp'], -d['Dp'] / 2, d['Dp'] / 2, H - d['tp'], H, name='Plyta'))
    rt = d['rib_t']
    for yc in (-d['Dp'] / 2 + rt / 2, 0.0, d['Dp'] / 2 - rt / 2):
        ops.append(prism('XZ', yc - rt / 2, yc + rt / 2, ('poly', [
            (X0 - 1, H - d['tp'] + 0.5), (X0 + d['Lp'] - 8, H - d['tp'] + 0.5), (X0 - 1, 6.0)]),
            name='Zebro'))
    # otwory z poglebieniem stozkowym od spodu
    hx = X0 + d['hole_x']
    zb = H - d['tp']
    for hy in (-d['hole_dy'] / 2, d['hole_dy'] / 2):
        ops.append(prism('XY', zb - 1, H + 1, ('circle', hx, hy, d['hole_d'] / 2), 'cut', 'Otwor wkretu'))
        rr = d['csk_d'] / 2
        ops.append(dict(kind='loft', plane='XY', op='cut', name='Poglebienie',
                        sections=[(zb - 1, ('circle', hx, hy, rr + 1)),
                                  (zb + rr - d['hole_d'] / 2, ('circle', hx, hy, d['hole_d'] / 2))]))
    # zatrzask: ramie sprezyste = przycisk
    xe = d['Ll'] / 2
    xr = xe - d['La']
    ya0, ya1 = Yf - d['g'] - d['ta'], Yf - d['g']
    ops.append(box(xr - d['root_w'], xr, ya0, Yf + 1, H - d['ha'], H, name='Nasada ramienia'))
    ops.append(box(xr - 1, xe, ya0, ya1, H - d['ha'], H, name='Ramie przycisku'))
    ops.append(box(-d['Ll'] / 2, xe, d['ledge_front'], ya0 + 1.0, H - d['lh'], H, name='Zaczep'))
    ops.append(box(-d['Ll'] / 2, xe, ya0 - 1.0, ya0 + 1.0, H - d['ha'] + 2, H - d['lh'] - 4, name='Przycisk'))
    return ops


def lid_ops(p):
    d = derived(p)
    H, Ht, yr, yl, xl0, xl1 = d['H'], d['Ht'], d['yr'], d['yl'], d['xl0'], d['xl1']
    sk, Zs = d['sk'], d['Zs']
    ops = []
    ops.append(box(xl0, xl1, yl, yr, H, Ht, name='Klapka'))
    # kieszen od spodu (odchudzenie)
    ops.append(box(-d['Wi'] / 2 + 2, d['Wi'] / 2 - 2, -d['Di'] / 2 + 2, yr - d['Lsp'],
                   H - 1, Ht - d['top_t'], 'cut', 'Kieszen'))
    # fartuchy: przedni i lewy (-X)
    ops.append(box(xl0, xl1, yl, yl + sk, H - d['sk_h'], H + 0.5, name='Fartuch przedni'))
    ops.append(box(xl0, xl0 + sk, yl, yr - d['Lsp'], H - d['sk_h'], H + 0.5, name='Fartuch boczny'))
    # haczyk zatrzasku
    ztop = H - d['lh'] - 0.2
    tip = yl + sk + d['lp'] + d['c_h'] - 0.4
    zc = ztop - 1.0
    zd = zc - (tip - (yl + sk))
    hw = d['Ll'] / 2 - 1
    ops.append(box(-hw, hw, yl, yl + sk, zd, H + 0.5, name='Jezyk haczyka'))
    ops.append(prism('YZ', -hw, hw, ('poly', [
        (yl + sk - 0.5, ztop), (tip, ztop), (tip, zc), (yl + sk - 0.5, zd)]), name='Haczyk'))
    # kanal tasmy (otwarty od -X, zamkniety przy +X)
    xa, xb = xl0 - 1, d['Ws'] / 2 + d['c']
    za = Zs - d['ts'] / 2 - d['c'] / 2
    ops.append(box(xa, xb, yr - d['neck_l'], yr + 1, za, Zs + d['ts'] / 2 + d['c'] / 2, 'cut', 'Szyjka tasmy'))
    ops.append(box(xa, xb, yr - d['neck_l'] - d['hb'] - d['c'], yr - d['neck_l'],
                   za, za + d['hb'] + d['c'], 'cut', 'Kanal listwy'))
    return ops


def ring_ops(p):
    d = derived(p)
    cb, tr = d['cb'], d['tr']
    wo, do_, ro = d['Wi'] - 2 * cb, d['Di'] - 2 * cb, d['rc'] - cb
    z0, z1 = d['lip_w'] - cb, d['H'] - 1.0
    ops = [prism('XY', z0, z1, ('rrect', 0, 0, wo, do_, ro), name='Pierscien'),
           prism('XY', z0 - 1, z1 + 1, ('rrect', 0, 0, wo - 2 * tr, do_ - 2 * tr, max(ro - tr, 1.0)), 'cut', 'Wnetrze')]
    yin = do_ / 2 - tr
    gw = d['grip_w'] / 2
    ops.append(box(-gw, gw, -yin - 0.5, -yin + d['grip_d'], z1 - 3, z1, name='Uchwyt przedni'))
    ops.append(box(-gw, gw, yin - d['grip_d'], yin + 0.5, z1 - 3, z1, name='Uchwyt tylny'))
    return ops


def spring_ops(p, x_off=None, y_off=-60.0):
    """Tasma drukowana na plasko (listwy do gory). Ustawiona obok ramki."""
    d = derived(p)
    if x_off is None:
        x_off = d['Xo'] + d['Lp'] + 20 + d['Ws'] / 2
    ws, Ls, hb, ts = d['Ws'], d['Ls'], d['hb'], d['ts']
    x0, x1 = x_off - ws / 2, x_off + ws / 2
    return [box(x0, x1, y_off, y_off + Ls, 0, ts, name='Tasma'),
            box(x0, x1, y_off, y_off + hb, 0, hb, name='Listwa A'),
            box(x0, x1, y_off + Ls - hb, y_off + Ls, 0, hb, name='Listwa B')]


PARTS = [
    ('Ramka', frame_ops),
    ('Klapka', lid_ops),
    ('Pierscien', ring_ops),
    ('Tasma', spring_ops),
]
