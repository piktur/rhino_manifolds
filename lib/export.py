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
    for (path, obj) in queue.iteritems():
        obj.Build()
        obj.AddLayers(obj.Layers)
        obj.Render()
        obj.Finalize()

        doc.Views.Redraw()

        if callable(cb):
            cb()

        ExportFile(path)
        Purge()


def Purge():
    '''
    Delete all objects within current Rhino document.
    '''
    rs.CurrentLayer('Default')

    for layer in rs.LayerNames():
        if rs.IsLayer(layer) and layer != 'Default':
            rs.PurgeLayer(layer)

    objs = []
    objTable = doc.Objects
    for obj in objTable.GetObjectList(Rhino.DocObjects.ObjectType.AnyObject):
        objs.append(obj.Id)
    for guid in objs:
        objTable.Delete(guid, True)


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
