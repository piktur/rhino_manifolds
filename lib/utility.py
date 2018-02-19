from System.Drawing import Color
from scriptcontext import doc
import rhinoscriptsyntax as rs


def Halt():
    '''
    In lieu of MacOS debugger...
    '''
    if rs.GetBoolean('Proceed',  ('Proceed?', 'No', 'Yes'), (True)) is None:
        return None


def Palette():
    '''
    Returns 2D list of colours 10 * 4
    '''
    arr = []
    for i in range(25, 255, 25):  # 255 / 25 == 10
        arr.append((
            Color.FromArgb(i, 0, i),  # Red-Blue
            Color.FromArgb(0, 0, i),  # Blue
            Color.FromArgb(0, i, i),  # Green-Blue
            Color.FromArgb(0, i, 0)   # Green
        ))

    return arr


def chunk(list, size):
    '''
    Yield successive chunks of `size` from `list`.
    '''
    for i in range(0, len(list), size):
        yield list[i:i + size]
