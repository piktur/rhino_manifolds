# @todo Export Points to File. Useful in cases where we might wish to generate models from the points array with tools other than Rhino.
# @see ~/Library/Application Support/McNeel/Rhinoceros/Scripts/samples/ExportPoints.py

# @example Export
# for dimension in range(10):
#     step = 15 # ensure multiple of 15
#     for i in range((360 / step) - 1): # No need to export at both 0 and 360deg
#         rotation = i * step
#         print {'dim': dimension, 'x': rotation}
