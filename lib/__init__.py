from Rhino import ApplicationSettings
import rhinoscriptsyntax as rs
from scriptcontext import doc

import events
import utility
import calabi_yau as CalabiYau
from export import Export

reload(CalabiYau)

rs.EnableRedraw(True)

# Configure measurement unit and tolerances
# [Accuracy](https://www.rhino3d.com/accuracy)
rs.UnitAbsoluteTolerance(0.1, True)  # 0.0000000001
rs.UnitAngleTolerance(0.1, True)
rs.UnitRelativeTolerance(0.1, True)
rs.UnitSystem(13, False, True)  # 13 == 'nanometres'

# Allow rotation when in Parallel
ApplicationSettings.ViewSettings.AlwaysPanParallelViews = False

log = file('./log.txt')

if __name__ == '__main__':
    if rs.GetInteger('Export', 0) != 0:
        dir = rs.GetString('Destination', '/Users/daniel/Documents/Design/export')
        Export(CalabiYau.Batch(dir), CalabiYau.Layers, dir)
    else:
        CalabiYau.Run()

log.close()
