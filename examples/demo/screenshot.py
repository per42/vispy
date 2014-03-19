# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2014, Vispy Development Team. All Rights Reserved.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.
# -----------------------------------------------------------------------------
# Author: Per Rosengren
# Date:   19/03/2014
# -----------------------------------------------------------------------------
"""
Take a screenshot and save it.
"""

import logging

import vispy.gloo.util
import vispy.util.dataio

logger = logging.getLogger(__name__)


class Screenshot(object):
    def __init__(self, canvas, image_path="screenshot.png"):
        self.canvas = canvas
        self.canvas.events.paint.connect(self.save)
        self.image_path = image_path
        self.done = False
    
    def save(self, event):
        self.canvas.on_paint(event)
        image = vispy.gloo.util._screenshot(
            (0, 0, self.canvas.size[0], self.canvas.size[1]))
        vispy.util.dataio.imsave(self.image_path, image)
        self.canvas.events.paint.disconnect(self.save)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    import graph
    c = graph.Canvas()
    Screenshot(c, image_path="screenshot.png")
    c.show()
    c.app.run()
