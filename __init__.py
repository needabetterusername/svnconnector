## Add-on for Blender to provide simple control of an SVN repo within the GUI
#
#    Target: 
#     Blender 2.8+, 3.0
#
#    Requirements:
#     subversion 1.14
#     (optional) svnadmin 1.14
#
#    Repo:
#     https://
#
#    Notes:
#     - This add-on is currently implemented using command line pipes via Python.
#     - Implementation is also limited to file access initially.
#     - The use of subversions SWIG hooks should be investigated since it should lead
#       to better compatibility accross svn versions.
#     - This add-on is not yet localized.
#     - Diff will be implemented in text first. If practical, a binary diff would be 
#       useful, 
#
#    Acknowledgements:
#     - Subversion is owned and maintained by the Apache Foundation.
#     - Blender is maintained by the Blender Foundation.
#     - This add-on developed partly with 'Blender Development' extension for VS Code 
#       by Jacques Lucke
#  

import bpy
from bpy.types import Attribute, Operator, AddonPreferences
from bpy.props import StringProperty, IntProperty, BoolProperty

import sys, inspect, logging
import os, subprocess, re, gettext


# Preferences Object
class ExampleAddonPreferences(AddonPreferences):
    # This must match the add-on name. Use '__package__'
    # if defining this in a SUBMODULE of a python package.
    bl_idname = __name__

    filepath: StringProperty(
        name="Local SVN Repository Root",
        subtype='FILE_PATH',
    )
    number: IntProperty(
        name="Example Number",
        default=4,
    )
    boolean: BoolProperty(
        name="Example Boolean",
        default=False,
    )

    def draw(self, context):
        layout = self.layout
        layout.label(text="Add-on preferences")

        print(f'Drawing preference properties for class {__class__}.')
        # NB: THis method specific for Python 3.9. 3.10 has inspect.get_annotations
        for name in __class__.__dict__.get('__annotations__', None):
                print(f'Adding prop {name} from class {__class__}.')
                layout.prop(self, name)
    


# Preferences Panel
# class OBJECT_OT_addon_prefs_example(Operator):
#     """Display example preferences"""
#     bl_idname = "object.addon_prefs_example"
#     bl_label = "Add-on Preferences Example"
#     bl_options = {'REGISTER', 'UNDO'}

#     def execute(self, context):
#         preferences = context.preferences
#         addon_prefs = preferences.addons[__name__].preferences

#         info = ("Path: %s, Number: %d, Boolean %r" %
#                 (addon_prefs.filepath, addon_prefs.number, addon_prefs.boolean))

#         self.report({'INFO'}, info)
#         print(info)

#         return {'FINISHED'}


# View panel display
class TESTADDON_PT_TestPanel(bpy.types.Panel):
    bl_idname = "TESTADDON_PT_TestPanel"
    bl_label = "Test Addon"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Test Addon"
    bl_context = "objectmode"

    def draw(self, context):

        layout = self.layout

        row = layout.row()
        row.label(text="How cool is this!")

        row = layout.row()
        row.label(text="Mighty cool!")

        row = layout.row()
        row.label(text="All the better for working on Mac!")


#########################
### BLENDER INTERFACE ###
#########################

bl_info = {
 "name": "Shabby's SVN Connector",
 "description": "Provides basic interface with a Subversion repository.",
 "author": "Tester",
 "blender": (2, 80, 0),
 "version": (0, 0, 1),
 "category": "Test",
 "location": "File -> SVN Connector",
 "warning": "",
 "doc_url": "",
 "tracker_url": ""
}

def register():    
    myLogger.info(f'Registering classes defined in module {__name__}')
    for name, cls in inspect.getmembers(sys.modules[__name__], lambda x: inspect.isclass(x) and (x.__module__ == __name__)):
        myLogger.debug(f'Registering class {cls} with name {name}')
        bpy.utils.register_class(cls)


def unregister():
    myLogger.info(f'Unregistering classes defined in module {__name__}')
    for name, cls in inspect.getmembers(sys.modules[__name__], lambda x: inspect.isclass(x) and (x.__module__ == __name__)):
        myLogger.debug(f'Unregistering class {cls} with name {name}')
        bpy.utils.unregister_class(cls)



##########################
###  TESTING, LOGGING  ###
##########################

myLogger = logging.getLogger()

if __name__ == "__main__":
    # logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
    # myLogger = logging.getLogger('com.codetestdummy.blender.svnconnector')

    # is this really required?
    register()
    #unregister()

#else:
    #myLogger = logging.getLogger(__name__)