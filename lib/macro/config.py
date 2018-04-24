from Rhino import ApplicationSettings
import rhinoscriptsyntax as rs

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

rs.UnitAbsoluteTolerance(0.0000000001, True)
rs.UnitRelativeTolerance(0.0, True)
rs.UnitAngleTolerance(0.0, True)
# 2  | millimeters
# 4  | meters
# 13 | nanometers
rs.UnitSystem(4, True, True)

# Allow rotation when in Parallel
ApplicationSettings.ViewSettings.AlwaysPanParallelViews = False
