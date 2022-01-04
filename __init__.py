## Add-on for Blender to provide simple control of an SVN repo within the GUI
#
#    Target: 
#     Blender 2.8+, 3.0
#
#    Requirements:
#     subversion 1.14
#     svnadmin 1.14
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
#     - Blender 'installs' (copies) addons to the following locations:
#       MacOS: /Users/{user}/Library/Application Support/Blender/{versions}/
#       Win:   TBC
#
#    Acknowledgements:
#     - Subversion is owned and maintained by the Apache Foundation.
#     - Blender is maintained by the Blender Foundation.
#     - This add-on developed partly via 'Blender Development' extension for VS Code 
#       by Jacques Lucke
#  

import bpy
from bpy.types import Attribute, Operator, AddonPreferences
from bpy.props import StringProperty, IntProperty, BoolProperty

import sys, inspect, logging
import os, subprocess, re, gettext

from pathlib import Path
from datetime import datetime


#######################
###  INIT, LOGGING  ###
#######################

logFile = logging.FileHandler(filename=str(Path(__file__).parent/'svnconnector.log'),
                                mode='w',
                                encoding='utf-8')
logFile.setFormatter(logging.Formatter('%(name)s: %(levelname)s %(message)s'))

myLogger = logging.getLogger('com.codetestdummy.blender.svnconnector')
logging.basicConfig(level=logging.DEBUG, handlers=[logFile])

# console = logging.StreamHandler(stream=sys.stdout)
# console.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s [%(thread)d]:  %(message)s'))
# myLogger.addHandler(console)

myLogger.info(f'Started session at {datetime.utcnow()}.')



##############################
### Application Attributes ###
##############################

## Define properties for svn interface
server_modes = ["local","remote"]
server_mode_in_use = server_modes[0]

## Application capabilities
svn_version      = ""
svn_ra_local     = False
svn_ra_svn       = False

svnadmin_avail   = False
svnadmin_version = ""

## Define default preferences
## TODO: Move this to prefs file
prefs = dict(
    bln_SVNUseDefaultLocalHome = True,
    str_prefSVNRepoHome = None
)



# svn command parameter dictionary correct as v1.14.1
#  Ref: https://janakiev.com/blog/python-shell-commands/
#  If below alternatives are not used, we might need a command factory.
#   Alternatively SWIG: https://svnbook.red-bean.com/en/1.0/ch08s02.html#svn-ch-8-sect-2.3
svn_commands = {"svn_version_quiet": ["svn","--version","--quiet"],
                "svn_version": ["svn","--version"],
                "svn_info": ["svn","info"],
                "svn_status": ["svn","status"],
                "svn_admin_version": ["svn","--version","--quiet"] }
                        

#####################
### Instantiation ###
#####################

# Confirm OS type
#  https://stackoverflow.com/questions/1854/python-what-os-am-i-running-on/58071295#58071295
if not os.name == "posix":
    myLogger.critical("Aborting after instantiation on OS type: " + os.name)
    report({'ERROR'}, "This add-on has not been implemented for your OS.")
else:
    prefs["str_prefSVNRepoHome"] = "file://$HOME/.svnrepos/" 
    # return {'FINISHED'}


# Check blender version
# TODO! Necessary? see bl_info

## Check python version
#    v3.5+ Required for subprocess
if sys.version_info < (3, 5):
    myLogger.critical("Python version is below the required 3.5")
    raise SystemError("Python version is below the required 3.5")
myLogger.info("Using Python version " + '.'.join(map(str, sys.version_info)))


## Check that svn is installed
#   TODO: Confirm minimum version
try:
    process = subprocess.Popen(svn_commands["svn_version_quiet"],
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    svn_version = stdout.decode('utf-8')
    myLogger.info("\'svn\' command found successfully. Using version" + svn_version )
    
except FileNotFoundError:
    myLogger.critical(error)
    myLogger.critical("\'svn\' command could not be found")
    raise SystemError("\'svn\' command could not be found. Please ensure that subversion is installed and available on your environment's PATH variable.")


## Check svn capabilities
try:
    process = subprocess.Popen(svn_commands["svn_version"],
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    stdout = stdout.decode('utf-8')
    
    svn_ra_svn   = len(re.findall("ra_svn", stdout))>0
    svn_ra_local = len(re.findall("ra_local", stdout))>0
    
    myLogger.info("Subversion RA modules confirmed. ra_svn: {0} ra_local: {1}".format(svn_ra_svn, svn_ra_local))
    
except FileNotFoundError:
    myLogger.warning(error)
    myLogger.warning("\'svnadmin\' command could not be found.")


## Check that svnadmin is installed
try:
    process = subprocess.Popen(svn_commands["svn_admin_version"],
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    
    svnadmin_version = stdout.decode('utf-8')
    svnadmin_avail = True 
    
    myLogger.info("\'svnadmin\' command found successfully. Using version" + svnadmin_version)
    myLogger.info("\'svnadmin\' command found successfully. Using version" + svnadmin_version)
    
except FileNotFoundError:
    myLogger.warning(error)
    myLogger.warning("\'svnadmin\' command could not be found.")



########################
### Operators        ###
########################

# create repo
# (svn_import - ??) <- bundle initial add?
# ADD
# REVERT VERSION
# branch (copy)
# changelist
# DIFF

## Create Repo Operator
#   Create a new repo of the current working directory.
#   https://subversion.apache.org/quick-start#setting-up-a-local-repo
class CreateAndImportOperator(bpy.types.Operator):
    bl_idname = "scop.create_import"
    bl_label  = "Create Repo & Import"

    def execute(self, context):
        # Confirm that that the file is saved
        if not bpy.data.is_saved:
            self.report({'ERROR'}, "File has not been saved. Please save before committing.")
            return {'FINISHED'}
        
        # Check we are not already in a working set
        # Confirm whether there is a working set available.
        process = subprocess.Popen(svn_commands["svn_info"],
                     stdout=subprocess.PIPE, 
                     stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if (len(stderr)<1) & (len(re.findall("Working Copy Root Path:", stdout.decode('utf-8')))>0):
            self.report({'ERROR'}, "A working copy already exists for this directory.")
            return {'FINISHED'}
        
        if os.name == "posix":
        #On Unix:
            myLogger.info("Starting repo creation via filesystem.")
            # Create a parent directory .svnrepos where you will place your SVN repositories:
            # !! This might already exist.
            #  mkdir -p $HOME/.svnrepos/
            myLogger.info("Created repository at: ")
            
            # Create a new repository MyRepo under .svnrepos:
            #  svnadmin create ~/.svnrepos/MyRepo
            # Create a recommended project layout in the new repository:
            #  svn mkdir -m "Create directory structure." \
            #  file://$HOME/.svnrepos/MyRepo/trunk \
            #  file://$HOME/.svnrepos/MyRepo/branches \
            #  file://$HOME/.svnrepos/MyRepo/tags
            myLogger.info("Successfully created repository at: ")
            
            # Change directory to ./MyProject where your unversioned project is located:
            #  cd $HOME/MyProject
            # Convert the current directory into a working copy of the trunk/ in the repository:
            #  svn checkout file://$HOME/.svnrepos/MyRepo/trunk ./
            # Schedule your project's files to be added to the repository:
            #  svn add --force ./
            # Commit the project's files:
            #  svn commit -m "Initial import."
            # Update your working copy:
            #  svn update
            myLogger.info("Completed importing.")

        #if os.name == "nt":
        #On Windows:
            # Create a parent directory C:\Repositories where you will place your SVN repositories:
            #  mkdir C:\Repositories
            # Create a new repository MyRepo under C:\Repositories:
            #  svnadmin create C:\Repositories\MyRepo
            # Create a recommended project layout in the new repository:
            #  svn mkdir -m "Create directory structure." ^
            #  file:///C:/Repositories/MyRepo/trunk ^
            #  file:///C:/Repositories/MyRepo/branches ^
            #  file:///C:/Repositories/MyRepo/tags 
            # Change directory to C:\MyProject where your unversioned project is located:
            #  cd C:\MyProject
            # Convert the current directory into a working copy of the trunk/ in the repository:
            #  svn checkout file:///C:/Repositories/MyRepo/trunk .
            # Schedule your project's files to be added to the repository:
            #  svn add --force ./
            # Commit the project's files:
            #  svn commit -m "Initial import."
            # Update your working copy:
            #  svn update
        
        return {'FINISHED'}
        

## ADD Operator
## ADD current file to working set
class AddOperator(bpy.types.Operator):
    bl_idname = "scop.add"
    bl_label  = "Add"

    def execute(self, context):
        
        # Confirm that there is a working set available.
        process = subprocess.Popen(svn_commands["svn_info"],
                     stdout=subprocess.PIPE, 
                     stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if (len(stdout)<1) & (len(re.findall("E155007", stderr.decode('utf-8')))>0):
            self.report({'ERROR'}, stderr.decode('utf-8') + " Please import to a new repository or check out from an existing repository(!)")
            return {'FINISHED'}
        
        # Confirm that that the file is saved
        if not bpy.data.is_saved:
            self.report({'ERROR'}, "File has not been saved. Please save before committing.")
            return {'FINISHED'}


## Commit Operator
## Commit current file
class CommitOperator(bpy.types.Operator):
    bl_idname = "scop.commit"
    bl_label  = "Commit"

    def execute(self, context):
        # Confirm that there is a working set available.
        process = subprocess.Popen(svn_commands["svn_info"],
                     stdout=subprocess.PIPE, 
                     stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if (len(stdout)<1) & (len(re.findall("E155007", stderr.decode('utf-8')))>0):
            self.report({'ERROR'}, stderr.decode('utf-8') + " Please import to a new repository or check out from an existing repository(!)")
            return {'FINISHED'}
        
        # Confirm that this file is added to the working set.
        #TODO!
        
        # Confirm file state
        if not bpy.data.is_saved:
            self.report({'ERROR'}, "File has not been saved. Please save before committing.")
            return {'FINISHED'}
        if bpy.data.is_dirty:
            self.report({'ERROR'}, "File has unsaved changes. Please save before committing.")
            return {'FINISHED'}



###########################
### Blender GUI Objects ###
###########################

# Preferences Object
class ExampleAddonPreferences(AddonPreferences):
    # This must match the add-on name. Use '__package__'
    # if defining this in a SUBMODULE of a python package.
    bl_idname = __name__

    boolean: BoolProperty(
        name="Use Default local SVN Repository Home",
        default=prefs["bln_SVNUseDefaultLocalHome"]
    )

    filepath: StringProperty(
        name="Local SVN Repository Root",
        subtype='FILE_PATH',
        default=prefs["str_prefSVNRepoHome"]
    )

    # number: IntProperty(
    #     name="Example Number",
    #     default=4
    # )


    def draw(self, context):
        layout = self.layout
        layout.label(text="Add-on preferences")

        # print(f'Drawing preference properties for class {__class__}.')
        # NB: THis method specific for Python 3.9. 3.10 has inspect.get_annotations
        for name in __class__.__dict__.get('__annotations__', None):
                # print(f'Adding prop {name} from class {__class__}.')
                layout.prop(self, name)

## SVN Connector main menu
#   https://docs.blender.org/api/current/bpy.types.Menu.html#bpy.types.Menu.draw
class SvnSubMenu(bpy.types.Menu):
    bl_idname = "OBJECT_MT_svn_submenu"
    bl_label = "SVN Connector"

    def draw(self, context):
        layout = self.layout

        layout.operator("scop.create_import", text="Create Repo & Import")
        layout.operator("scop.add", text="Add")
        layout.operator("scop.commit", text="Commit")
        #layout.operator(scop.CommitOperator.bd_idname, text="Commit")
        #layout.operator("object.select_all", text="Inverse").action = 'INVERT'
        #layout.operator("object.select_random", text="Random")


# Function to draw the menu item.
def menu_draw_svn(self, context):
    #self.layout.operator("wm.save_homefile")
    self.layout.menu("OBJECT_MT_svn_submenu")



#############################
### BLENDER API INTERFACE ###
#############################

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


##############
### LAUNCH ###
##############
if __name__ == "__main__":

    register()
    #unregister()
else:
    bpy.types.TOPBAR_MT_file.append(menu_draw_svn)