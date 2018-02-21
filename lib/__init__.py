from Rhino import ApplicationSettings
import rhinoscriptsyntax as rs
from scriptcontext import doc

import events
import utility
import calabi_yau as CalabiYau
from export import Export

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
rs.UnitAbsoluteTolerance(0.001, True)
rs.UnitRelativeTolerance(1.0, True)
rs.UnitAngleTolerance(1.0, True)
rs.UnitSystem(13, False, True)  # 13 == 'nanometres'

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
