import rhinoscriptsyntax as rs
from scriptcontext import doc

import events
from export import Export
import utility
import calabi_yau as CalabiYau


reload(CalabiYau)

rs.EnableRedraw(True)


if __name__ == '__main__':
    dir = rs.GetString('Destination')
    Export(CalabiYau.Batch(dir), dir)
    # CalabiYau.Run()
    # CalabiYau.Make2D()
