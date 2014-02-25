# -*- coding: utf-8 -*-
# Copyright (c) 2014, Vispy Development Team.
# Distributed under the (new) BSD License. See LICENSE.txt for more info.

from __future__ import division

import numpy as np

from .. import gloo
from ..gloo import gl
from . import Visual, VisualComponent
from ..shaders.composite import (Function, ModularProgram, 
                                 FragmentFunction, FunctionChain)
from .transforms import NullTransform, STTransform



vertex_shader = """
// local_position function must return the current vertex position
// in the Visual's local coordinate system.
//vec4 local_position();

attribute vec2 local_pos;

// mapping function that transforms from the Visual's local coordinate
// system to normalized device coordinates.
vec4 map_local_to_nd(vec4);

// generic hook for executing code after the vertex position has been set
void vert_post_hook();

varying vec2 image_pos;

void main(void) {
    vec4 nd_pos = map_local_to_nd(vec4(local_pos, 0, 1));
    gl_Position = nd_pos;
    image_pos = local_pos;
    vert_post_hook();
}
"""

fragment_shader = """
// maps from local coordinates of the Visual to texture coordinates.
vec4 map_local_to_tex(vec4);

// Generic hook for executing code after the fragment color has been set
// Functions in this hook may modify glFragColor or discard.
void frag_post_hook();

uniform sampler2D tex;
varying vec2 image_pos;

void main(void) {
    vec4 tex_coord = map_local_to_tex(vec4(image_pos,0,1));
    gl_FragColor = texture2D(tex, tex_coord.xy);
    
    frag_post_hook();
}
"""



    
class ImageVisual(Visual):
    def __init__(self, data):
        super(ImageVisual, self).__init__()
        self.set_gl_options('opaque')
        
        self._data = None
        
        # maps from quad vertexes to ND coordinates
        self._transform = NullTransform()
        
        # maps from quad coordinates to texture coordinates
        self._tex_transform = STTransform() 
        
        self._program = None
        self._texture = None
        #self.pos_input_component = LinePosInputComponent(self)
        #self.color_input_component = LineColorInputComponent(self)
        self._vbo = None
        self._fragment_callbacks = []
        self.set_data(data)
        self.set_gl_options(glCullFace=('GL_FRONT_AND_BACK',))

    @property
    def transform(self):
        return self._transform
    
    @transform.setter
    def transform(self, tr):
        self._transform = tr
        self._program = None

    def add_fragment_callback(self, func):
        self._fragment_callbacks.append(func)
        self._program = None

    def set_data(self, data):
        self._data = data
        
        # might need to rebuild vbo or program.. 
        # this could be made more clever.
        self._vbo = None
        self._texture = None
        self._program = None

    def _build_data(self):
        # Construct complete data array with position and optionally color
        
        subdiv = 4
        w = self._data.shape[0] / subdiv
        h = self._data.shape[1] / subdiv
        
        quad = np.array([[0,0], [w,h], [w,0], [0,0], [0,h], [w,h]], 
                        dtype=np.float32)
        quads = np.empty((subdiv, subdiv, 6, 2), dtype=np.float32)
        quads[:] = quad
        
        grid = np.mgrid[0:subdiv, 0:subdiv].transpose(1,2,0)[:, :, np.newaxis, :]
        grid[...,0] *= w
        grid[...,1] *= h
        
        quads += grid
        self._vbo = gloo.VertexBuffer(quads.reshape(subdiv*subdiv*6,2))
        
        
        self._texture = gloo.Texture2D(self._data)
        self._texture.set_filter('NEAREST', 'NEAREST')
        
        
    def _build_program(self):
        if self._vbo is None:
            self._build_data()
        
        # Create composite program
        program = ModularProgram(vertex_shader, fragment_shader)
        program['local_pos'] = self._vbo
        program['tex'] = self._texture
        #program['image_size'] = self._data.shape[:2]
        
        program.add_chain('vert_post_hook')
        program.add_chain('frag_post_hook')
        
        # Activate position input component
        #self.pos_input_component._activate(program)
        
        # Attach transformation functions
        program['map_local_to_nd'] = self.transform.shader_map()

        self._tex_transform.scale = (1./self._data.shape[0], 1./self._data.shape[1])
        program['map_local_to_tex'] = self._tex_transform.shader_map()
        
        # Activate color input function
        #self.color_input_component._activate(program)
        
        # Attach fragment shader post-hook chain
        for func in self._fragment_callbacks:
            program.add_callback('frag_post_hook', func)
        
        self._program = program
        
        
    def paint(self):
        super(ImageVisual, self).paint()
        
        if self._data is None:
            return
        
        if self._program is None:
            self._build_program()
            
        self._program.draw('TRIANGLES')
