import rhinoscriptsyntax as rs
import events
import export
import utility
import calabi_yau as CalabiYau

from scriptcontext import doc

reload(CalabiYau)

rs.EnableRedraw(True)

if __name__ == '__main__':
    CalabiYau.Run()
