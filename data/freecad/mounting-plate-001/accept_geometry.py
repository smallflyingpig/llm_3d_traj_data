"""Independently inspect final FCStd and STEP geometry; do not read cutter parameters."""
import json
from pathlib import Path
import sys
import FreeCAD as App
import Part

root = Path(sys.argv[1]).resolve()
tolerance = 1e-6
expected_centers = [(10.0, 10.0), (10.0, 40.0), (70.0, 10.0), (70.0, 40.0)]


def inspect(shape):
    assert not shape.isNull() and shape.isValid(), 'Invalid shape'
    assert len(shape.Solids) == 1, 'Expected one solid'
    b = shape.BoundBox
    dimensions = [b.XLength, b.YLength, b.ZLength]
    assert all(abs(a - e) < tolerance for a, e in zip(dimensions, [80, 50, 5])), dimensions
    assert all(abs(v) < tolerance for v in [b.XMin, b.YMin, b.ZMin]), 'Unexpected origin'
    holes = []
    for face in shape.Faces:
        surface = face.Surface
        if not isinstance(surface, Part.Cylinder):
            continue
        axis = surface.Axis
        assert abs(axis.x) < tolerance and abs(axis.y) < tolerance
        assert abs(abs(axis.z) - 1) < tolerance, 'Hole axis is not perpendicular to plate'
        center = (float(surface.Center.x), float(surface.Center.y))
        radius = float(surface.Radius)
        assert abs(radius - 3) < tolerance, ('Unexpected radius', radius)
        # Each through-hole side wall must span the full plate thickness.
        fb = face.BoundBox
        assert abs(fb.ZMin) < tolerance and abs(fb.ZMax - 5) < tolerance
        # Final solid must be empty at the axis through the entire thickness,
        # with plate material present just outside the cylindrical wall.
        for z in [0.001, 2.5, 4.999]:
            assert not shape.isInside(App.Vector(center[0], center[1], z), tolerance, True)
            for dx, dy in [(3.1, 0), (-3.1, 0), (0, 3.1), (0, -3.1)]:
                assert shape.isInside(App.Vector(center[0] + dx, center[1] + dy, z), tolerance, True)
        edge_distance = min(center[0], 80-center[0], center[1], 50-center[1])
        assert abs(edge_distance - 10) < tolerance
        holes.append({'center_xy_mm': list(center), 'radius_mm': radius,
                      'diameter_mm': 2*radius, 'z_span_mm': [fb.ZMin, fb.ZMax],
                      'center_to_nearest_edge_mm': edge_distance,
                      'wall_to_nearest_edge_mm': edge_distance-radius})
    assert len(holes) == 4, ('Expected four cylindrical hole walls', len(holes))
    holes.sort(key=lambda h: tuple(h['center_xy_mm']))
    for hole, expected in zip(holes, expected_centers):
        assert all(abs(v-e) < tolerance for v, e in zip(hole['center_xy_mm'], expected)), hole
    return {'passed': True, 'dimensions_mm': dimensions,
            'solid_count': len(shape.Solids), 'hole_count': len(holes), 'holes': holes,
            'through_hole_check': 'Full-height cylindrical walls plus empty-axis/material-neighborhood probes',
            'tolerance_mm': tolerance}


doc = App.openDocument(str(root / 'mounting-plate.FCStd'))
doc.recompute()
fcstd = inspect(doc.getObject('Hole4').Shape)
step = Part.Shape()
step.read(str(root / 'mounting-plate.step'))
report = {'method': 'Inspect final B-rep geometry independently of construction parameters',
          'FCStd': fcstd, 'STEP': inspect(step), 'passed': True}
(root / 'geometry-acceptance.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report, indent=2))
App.closeDocument(doc.Name)
