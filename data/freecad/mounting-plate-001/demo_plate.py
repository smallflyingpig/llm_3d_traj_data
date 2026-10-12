"""FreeCAD job: editable 80x50x5 mm plate with four diameter-6 holes."""
import json
import math
from pathlib import Path
import sys
import FreeCAD as App
import Part
import Mesh

out = Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
paths = {ext: out / ('mounting-plate.' + ext) for ext in ('FCStd', 'step', 'stl')}
if any(p.exists() for p in paths.values()):
    raise FileExistsError('Demo outputs already exist; choose another output directory.')
doc = App.newDocument('MountingPlate')
plate = doc.addObject('Part::Box', 'Plate')
plate.Length, plate.Width, plate.Height = 80, 50, 5
last = plate
for i, (x, y) in enumerate([(10, 10), (70, 10), (70, 40), (10, 40)], 1):
    hole = doc.addObject('Part::Cylinder', 'HoleTool%d' % i)
    hole.Radius, hole.Height = 3, 7
    hole.Placement.Base = App.Vector(x, y, -1)
    cut = doc.addObject('Part::Cut', 'Hole%d' % i)
    cut.Base, cut.Tool = last, hole
    last = cut
doc.recompute()
shape = last.Shape
assert not shape.isNull() and shape.isValid() and len(shape.Solids) == 1
expected = 80 * 50 * 5 - 4 * math.pi * 3**2 * 5
assert abs(shape.Volume - expected) < 1e-6
if App.GuiUp:
    for obj in doc.Objects:
        obj.ViewObject.Visibility = obj == last
doc.saveAs(str(paths['FCStd']))
Part.export([last], str(paths['step']))
Mesh.export([last], str(paths['stl']))
App.closeDocument(doc.Name)
saved = App.openDocument(str(paths['FCStd']))
saved.recompute()
assert saved.getObject('Hole4').Shape.isValid()
assert abs(saved.getObject('Hole4').Shape.Volume - expected) < 1e-6
step_shape = Part.Shape()
step_shape.read(str(paths['step']))
assert step_shape.isValid() and len(step_shape.Solids) == 1
assert abs(step_shape.Volume - expected) < 1e-4
mesh = Mesh.Mesh(str(paths['stl']))
assert mesh.CountFacets > 0 and mesh.isSolid()
b = step_shape.BoundBox
report = {'freecad_version': App.Version(), 'units': 'mm',
          'dimensions': [b.XLength, b.YLength, b.ZLength],
          'hole_diameter': 6, 'hole_centers': [[10,10],[70,10],[70,40],[10,40]],
          'volume_mm3': step_shape.Volume, 'solid_count': len(step_shape.Solids),
          'valid': True, 'stl_facets': mesh.CountFacets,
          'files': {key: str(value) for key, value in paths.items()}}
(out / 'validation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
App.closeDocument(saved.Name)
