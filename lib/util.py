from System.Drawing import Color
from scriptcontext import doc
import rhinoscriptsyntax as rs
import json


def Halt():
    '''
    In lieu of MacOS debugger...
    '''
    if rs.GetBoolean('Proceed',  ('Proceed?', 'No', 'Yes'), (True)) is None:
        return None


def ExportNamedViews():
    log = open('./views.json', 'a')
    fname = rs.DocumentPath() + rs.DocumentName()
    data = {}
    data[fname] = {}

    for view in rs.NamedViews():
        rs.RestoreNamedView(view)
        data[fname][view] = (
            list(rs.ViewCamera()),
            list(rs.ViewTarget())
        )

    log.write(json.dumps(data, indent=2) + '\n')
    log.close()

    return data


def ImportNamedViews():
    # TODO
    log = open('./views.json', 'a')
    data = json.loads(log)

    for fname in data.iterkeys():
        for view in data[fname].iterkeys():
            camera, target = data[fname][view]
            rs.AddNamedView(view)
            rs.ViewCameraTarget(view, camera, target)


def Palette():
    '''
    Returns 2D list of colours 10 * 4
    '''
    arr = []
    for i in range(25, 255, 51):  # 255 / 51 == 5
        arr.append((
            Color.FromArgb(i, 0, i),  # Red-Blue
            Color.FromArgb(0, 0, i),  # Blue
            Color.FromArgb(0, i, i),  # Green-Blue
            Color.FromArgb(0, i, 0),  # Green
            Color.FromArgb(i, i, 0),  # Green-Red
            Color.FromArgb(i, 0, 0)   # Red
        ))

    return arr


def layer(*args):
    return '::'.join([str(e) for e in args])


def chunk(list, size):
    '''
    Yield successive chunks of `size` from `list`.
    '''
    for i in range(0, len(list), size):
        yield list[i:i + size]
