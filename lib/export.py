import os
import errno
import sys
import System
from System.IO import Path, File, FileInfo, FileAttributes
import System.Collections.Generic as SCG

import rhinoscriptsyntax as rs
from scriptcontext import doc
import Rhino
from Rhino.FileIO import FileWriteOptions, FileReadOptions


def Export(queue, cb=None, dir='~/Documents/CY'):
    '''
    [See](https://bitbucket.org/kunst_dev/snippets/issues/11/export-2d)
    Parameters:
        queue : dict
        cb: function
        dir : string
    Example:
        dir = rs.GetString('Destination')
        Export(CalabiYau.Batch(dir), CalabiYau.Make2D, dir)

    TODO you may want to CreateWireframePreviewImage to provide hint as to 3d file contents
        preview = fname('jpg', path, f)
        view = doc.Views.Find('Top', False)
        previewSize = System.Drawing.Size(100, 100)  # view.ClientRectangle.Size
        view.CreateWireframePreviewImage(preview, previewSize, True, False)
    '''
    for path in queue.iterkeys():
        obj = queue[path]
        obj.Build()
        doc.Views.Redraw()

        if callable(cb):
            cb()

        ExportFile(path)

        # Reset Document
        rs.CurrentLayer('Default')
        rs.Command('_SelAll')
        rs.Command('_Delete')

        for layer in rs.LayerNames():
            if layer != 'Default':
                rs.PurgeLayer(layer)


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def fname(format='3dm', path='', *fname):
    basename = '_'.join(map(lambda e: str(e), fname)) + '.' + format
    mkdir_p(path)
    return os.path.join(path, basename)


def ExportFile(filePath, version=5, geomOnly=False, selectedOnly=False):
    '''
    Export a file.
    [See](https://github.com/localcode/rhinopythonscripts/blob/34c5314/FileTools.py)
    '''
    opt = FileWriteOptions()
    opt.FileVersion = version
    opt.WriteGeometryOnly = geomOnly
    opt.WriteSelectedObjectsOnly = selectedOnly

    return doc.WriteFile(filePath, opt)


def ExportLayers(layerNames, filePath, version=4):
    '''
    Export only the items on designated layers to a file.
    [See](https://github.com/localcode/rhinopythonscripts/blob/34c5314/FileTools.py)
    '''
    # save selection
    oldSelection = rs.SelectedObjects()

    # clear selection
    rs.UnselectAllObjects()

    # add everything on the layers to selection
    for name in layerNames:
        objs = scriptcontext.doc.Objects.FindByLayer(name)
        guids = [obj.Id for obj in objs]
        doc.Objects.Select.Overloads[SCG.IEnumerable[System.Guid]](guids)

    # export selected items
    exportFile(filePath, version, selectedOnly=True)

    # clear selection
    rs.UnselectAllObjects()

    # restore selection
    if oldSelection:
        doc.Objects.Select.Overloads[SCG.IEnumerable[System.Guid]](oldSelection)

    # print 'exported %s' % filePath
