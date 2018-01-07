from scriptcontext import doc
import rhinoscriptsyntax as rs


def Halt():
    '''
    In lieu of MacOS debugger this will have to do.
    '''
    if rs.GetBoolean('Proceed',  ('Proceed?', 'No', 'Yes'), (True)) is None:
        return None
