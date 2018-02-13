from Rhino import ApplicationSettings
import rhinoscriptsyntax as rs
from scriptcontext import doc

import events
from export import Export
import utility
import calabi_yau as CalabiYau

reload(CalabiYau)

rs.EnableRedraw(True)

# Configure measurement unit and tolerances
rs.UnitAbsoluteTolerance(0.0000000001, True)
rs.UnitAngleTolerance(0.1, True)
rs.UnitRelativeTolerance(1.0, True)
rs.UnitSystem(13, False, True)

# Allow rotation when in Parallel
ApplicationSettings.ViewSettings.AlwaysPanParallelViews = False

dir = '/Users/daniel/Documents/Design/export'

if __name__ == '__main__':
    dir = rs.GetString('Destination', dir)
    Export(CalabiYau.Batch(dir), CalabiYau.Layers, dir)

    # CalabiYau.Run()
