from Rhino import ApplicationSettings
import rhinoscriptsyntax as rs
from scriptcontext import doc

import events
import util
import calabi_yau as CalabiYau
from export import Export

reload(util)
reload(CalabiYau)

# Disable Autosave to prevent filesharing conflicts
rs.EnableAutosave(False)

rs.EnableRedraw(True)

# Configure measurement unit and tolerances
# [Accuracy](https://www.rhino3d.com/accuracy)
#
#         | Absolute     | Relative | Angle
# --------|--------------|----------|---------
# Min     | 0.0000000001 | 0.0001   | 0.0001
# Default | 0.001        | 1.0      | 1.0
#
# System: 4
# AbsoluteTolerance: 0.0000001
# RelativeTolerance: 0.0
# AngleTolerance: 0.0
#
# When tolerance >= 0.1 silhouette edges are fragmented.
# Set extreme intolerance to ensure precision.

rs.UnitAbsoluteTolerance(0.000000001, True)
rs.UnitRelativeTolerance(0.1, True)
rs.UnitAngleTolerance(0.1, True)
rs.UnitSystem(2, False, True)  # 13 == 'nanometres'

# Allow rotation when in Parallel
ApplicationSettings.ViewSettings.AlwaysPanParallelViews = False

log = file('./log.txt')

if __name__ == '__main__':
    if rs.GetInteger('Export', 0) != 0:
        dir = rs.GetString('Destination', '/Users/daniel/Documents/Design/export')
        Export(CalabiYau.Batch(dir), cb=None, dir=dir)
    else:
        CalabiYau.Run()

log.close()
