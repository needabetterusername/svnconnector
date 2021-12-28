import bpy
from bpy.types import Operator, AddonPreferences
from bpy.props import StringProperty, IntProperty, BoolProperty


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


def register():
    bpy.utils.register_class(TESTADDON_PT_TestPanel)


def unregister():
    bpy.utils.unregister_class(TESTADDON_PT_TestPanel)



################
###  TESTING  ##
################

# Normally used for script execution
#  Replace with testing.
#if __name__ == "__main__":
#    register()