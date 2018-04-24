import rhinoscriptsyntax as rs

import config
import util
import calabi_yau

if __name__ == '__main__':
    dir = rs.GetString('Destination', '~/Documents/Design/export[REBUILD]')

    util.Export(
        calabi_yau.Batch(dir),
        cb=None,
        dir=dir
    )
