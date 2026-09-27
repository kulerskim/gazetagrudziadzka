# -*- coding: utf-8 -*-
"""
Fusion 360: Utilities -> ADD-INS -> Scripts and Add-Ins -> (+) -> wskaz folder
UchwytWorka -> Run.

Skrypt tworzy NOWY dokument z 4 komponentami (Ramka, Klapka, Pierscien, Tasma),
kazdy z pelna historia (szkic -> wyciagniecie / wyciecie / loft).
Wymiary zmieniasz w tbh_design.py (slownik P) i uruchamiasz skrypt ponownie.
"""
import os
import sys
import importlib
import traceback

import adsk.core
import adsk.fusion

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import tbh_design  # noqa: E402

CM = 0.1  # API Fusion pracuje w cm

AXIS = {'XY': (0, 0, 1), 'XZ': (0, 1, 0), 'YZ': (1, 0, 0)}


def to3d(plane, u, v, a):
    if plane == 'XY':
        return (u, v, a)
    if plane == 'XZ':
        return (u, a, v)
    return (a, u, v)  # YZ


class Builder:
    def __init__(self, comp):
        self.comp = comp
        self.has_body = False

    def base_plane(self, plane):
        c = self.comp
        return {'XY': c.xYConstructionPlane, 'XZ': c.xZConstructionPlane,
                'YZ': c.yZConstructionPlane}[plane]

    def offset_plane(self, plane, a):
        """Plaszczyzna rownolegla do bazowej, w polozeniu a [mm] wzdluz osi."""
        base = self.base_plane(plane)
        n = base.geometry.normal
        ax = AXIS[plane]
        s = n.x * ax[0] + n.y * ax[1] + n.z * ax[2]
        s = 1.0 if s >= 0 else -1.0
        if abs(a) < 1e-9:
            return base
        pin = self.comp.constructionPlanes.createInput()
        pin.setByOffset(base, adsk.core.ValueInput.createByReal(a * CM * s))
        cp = self.comp.constructionPlanes.add(pin)
        cp.isLightBulbOn = False
        return cp

    def sketch(self, plane, a, shape, name):
        sk = self.comp.sketches.add(self.offset_plane(plane, a))
        sk.name = name
        sk.isComputeDeferred = True

        def P(u, v):
            x, y, z = to3d(plane, u, v, a)
            return sk.modelToSketchSpace(adsk.core.Point3D.create(x * CM, y * CM, z * CM))

        lines = sk.sketchCurves.sketchLines
        arcs = sk.sketchCurves.sketchArcs
        kind = shape[0]
        if kind == 'poly':
            pts = shape[1]
            first = None
            prev = None
            for i in range(len(pts)):
                p1 = prev if prev is not None else P(*pts[i])
                if i == len(pts) - 1:
                    p2 = first
                else:
                    p2 = P(*pts[i + 1])
                ln = lines.addByTwoPoints(p1, p2)
                if first is None:
                    first = ln.startSketchPoint
                prev = ln.endSketchPoint
        elif kind == 'circle':
            _, cu, cv, r = shape
            sk.sketchCurves.sketchCircles.addByCenterRadius(P(cu, cv), r * CM)
        elif kind == 'rrect':
            _, cu, cv, w, h, r = shape
            x0, x1, y0, y1 = cu - w / 2, cu + w / 2, cv - h / 2, cv + h / 2
            k = r * (1 - 2 ** -0.5)
            lines.addByTwoPoints(P(x0 + r, y0), P(x1 - r, y0))
            arcs.addByThreePoints(P(x1 - r, y0), P(x1 - k, y0 + k), P(x1, y0 + r))
            lines.addByTwoPoints(P(x1, y0 + r), P(x1, y1 - r))
            arcs.addByThreePoints(P(x1, y1 - r), P(x1 - k, y1 - k), P(x1 - r, y1))
            lines.addByTwoPoints(P(x1 - r, y1), P(x0 + r, y1))
            arcs.addByThreePoints(P(x0 + r, y1), P(x0 + k, y1 - k), P(x0, y1 - r))
            lines.addByTwoPoints(P(x0, y1 - r), P(x0, y0 + r))
            arcs.addByThreePoints(P(x0, y0 + r), P(x0 + k, y0 + k), P(x0 + r, y0))
        else:
            raise ValueError(kind)
        sk.isComputeDeferred = False
        if sk.profiles.count < 1:
            raise RuntimeError('Brak zamknietego profilu w szkicu ' + name)
        # najwiekszy profil (dla pojedynczej petli jest tylko jeden)
        best = None
        best_area = -1.0
        for i in range(sk.profiles.count):
            pr = sk.profiles.item(i)
            ar = pr.areaProperties().area
            if ar > best_area:
                best, best_area = pr, ar
        return best

    def operation(self, op_kind):
        FO = adsk.fusion.FeatureOperations
        if not self.has_body:
            self.has_body = True
            return FO.NewBodyFeatureOperation
        return FO.JoinFeatureOperation if op_kind == 'add' else FO.CutFeatureOperation

    def run(self, op):
        name = op.get('name') or op['kind']
        if op['kind'] == 'prism':
            a0, a1 = op['a0'], op['a1']
            mid = (a0 + a1) / 2.0
            prof = self.sketch(op['plane'], mid, op['shape'], name)
            ext = self.comp.features.extrudeFeatures
            inp = ext.createInput(prof, self.operation(op['op']))
            inp.setSymmetricExtent(adsk.core.ValueInput.createByReal((a1 - a0) * CM), True)
            f = ext.add(inp)
        else:  # loft
            (a0, s0), (a1, s1) = op['sections']
            p0 = self.sketch(op['plane'], a0, s0, name + ' A')
            p1 = self.sketch(op['plane'], a1, s1, name + ' B')
            lofts = self.comp.features.loftFeatures
            li = lofts.createInput(self.operation(op['op']))
            li.loftSections.add(p0)
            li.loftSections.add(p1)
            li.isSolid = True
            f = lofts.add(li)
        try:
            f.name = name
        except Exception:
            pass
        return f


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        importlib.reload(tbh_design)
        p = tbh_design.P

        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        design.fusionUnitsManager.distanceDisplayUnits = adsk.fusion.DistanceUnits.MillimeterDistanceUnits
        root = design.rootComponent
        root.name = 'Uchwyt worka'

        for comp_name, fn in tbh_design.PARTS:
            occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            comp = occ.component
            comp.name = comp_name
            b = Builder(comp)
            for op in fn(p):
                b.run(op)
            if comp.bRepBodies.count:
                comp.bRepBodies.item(0).name = comp_name
        app.activeViewport.fit()
        ui.messageBox('Gotowe: Ramka, Klapka, Pierscien, Tasma.\n'
                      'Tasma jest pokazana na plasko obok ramki (tak sie ja drukuje).')
    except Exception:
        if ui:
            ui.messageBox('Blad:\n{}'.format(traceback.format_exc()))
