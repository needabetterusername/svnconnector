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
#     https://github.com/needabetterusername/svnconnector/
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
from bpy.types import Attribute, Operator, AddonPreferences, STATUSBAR_HT_header
from bpy.props import StringProperty, IntProperty, BoolProperty
from bpy.app.handlers import persistent

import sys, inspect, logging
import platform, subprocess, re, gettext

from pathlib import Path
from datetime import datetime



######################
###  INIT/LOGGING  ###
######################

logFile = logging.FileHandler(filename=str(Path(__file__).parent/'svnconnector.log'),
                                mode='w',
                                encoding='utf-8')
logFile.setFormatter(logging.Formatter('%(name)s: %(levelname)s %(message)s'))
logging.basicConfig(level=logging.DEBUG, handlers=[logFile])

myLogger = logging.getLogger('com.codetestdummy.blender.svnconnector')

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

# TODO: Need to handle file changes. E.g. file is re-saved with new name.
## File SVN Status
svn_file_status  = ''

## Define default preferences
## TODO: Move this to prefs file
prefs = dict(
    bln_SVNUseDefaultLocalHome = True,
    str_prefSVNRepoHome = None,
    bln_SVNUseDefaultRepoName = True
)

# svn command parameter dictionary correct as v1.14.1
#  Ref: https://janakiev.com/blog/python-shell-commands/
#  If below alternatives are not used, we might need a command factory.
#   Alternatively SWIG: https://svnbook.red-bean.com/en/1.0/ch08s02.html#svn-ch-8-sect-2.3
svn_commands = {"svn_version_quiet": ["svn","--version","--quiet"],
                "svn_version": ["svn","--version"],
                "svn_info": ["svn","info"], # E155007 'not a working copy'
                "svn_status": ["svn","status","-v"], # W155007 'not a working copy'
                "svn_admin_version": ["svnadmin","--version","--quiet"],
                "svn_admin_create": ["svnadmin", "create"],
                "svn_commit_single": ["svn","commit","-m \'Commit from svnconnector.\'"],
                "svn_add_single": ["svn","add"],
                "svn_update": ["svn", "update"],
                "svn_revert_previous": ["svn","revert"],
                "svn_mkdir_repo": ["svn", "mkdir", "-m \'Create directory structure.\'"],
                "svn_checkout": ["svn", "checkout"]}



########################
###  INIT/PRE-CHECK  ###
########################

# Confirm OS type
#  https://stackoverflow.com/questions/1854/python-what-os-am-i-running-on/58071295#58071295
myLogger.info(f'Got operating system: {platform.system()}')
if platform.system() == "Darwin": # | "Linux" | "Windows"
    prefs["str_prefSVNRepoHome"] = "~/.svnrepos/"
    #prefs["str_prefSVNRepoHome"] = "file://$HOME/.svnrepos/" 
# elif platform.system() == "Linux":
#     prefs["str_prefSVNRepoHome"] = "file://$HOME/.svnrepos/"
# elif platform.system() == "Windows":
#     prefs["str_prefSVNRepoHome"] = "file:///C:/SVNRepository/"
else:
    myLogger.critical(f'Aborting init due to unsupported operating system type {platform.system()}')
    raise SystemError('This add-on has not been implemented for your OS.')
    #TODO: This is probably no the graceful way to quit.


## Check python version
#    v3.5+ Required for subprocess
if sys.version_info < (3, 5):
    myLogger.critical("Python version is below the required 3.5")
    raise SystemError("Python version is below the required 3.5")
myLogger.info("Using Python version " + '.'.join(map(str, sys.version_info)))


# Record Blender version
myLogger.info(f'Got blender version {bpy.app.version}.')


## Check that svn is installed
#   TODO: Confirm minimum version
try:
    process = subprocess.Popen(svn_commands["svn_version_quiet"],
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    svn_version = stdout.decode('utf-8')
    myLogger.info("\'svn\' command found successfully. Using version" + svn_version )
    
except FileNotFoundError as error:
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
    
except FileNotFoundError as error:
    myLogger.critical(error)
    myLogger.critical("\'svn\' command could not be found.")


## Check that svnadmin is installed
try:
    process = subprocess.Popen(svn_commands["svn_admin_version"],
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    
    svnadmin_version = stdout.decode('utf-8')
    svnadmin_avail = True 
    
    myLogger.info("\'svnadmin\' command found successfully. Using version" + svnadmin_version)
    
except FileNotFoundError as error:
    myLogger.error(error)
    myLogger.error("\'svnadmin\' command could not be found.")



########################
### Utility Funcs    ###
########################

## Get the SVN status of the file at filepath
# From svn help status
#  Confirm status of file in current local working set
#   The first seven columns in the output are each one character wide:
#     First column: Says if item was added, deleted, or otherwise changed
#     ' ' no modifications
#     'A' Added
#     'C' Conflicted
#     'D' Deleted
#     'I' Ignored
#     'M' Modified
#     'R' Replaced
#     'X' an unversioned directory created by an externals definition
#     '?' item is not under version control
#     '!' item is missing (removed by non-svn comman    d) or incomplete
#     '~' versioned item obstructed by some item of a different kind
def getSvnFileStatus(filepath):
    process = subprocess.Popen(svn_commands["svn_status"] + [filepath],
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    if len(stdout)>1:
        result = stdout.decode('utf-8')
        return None, result[0]
    elif len(stderr)>1:
        error = stderr.decode('utf-8')
        return error, None
    else:
        return f'Command returned code: {process.returncode}', None

## Generate a repo name based on the current folder
def generateRepoName(filepath):
    result = Path(filepath).parent.name
    return result

########################
### Operators        ###
########################

# o CREATE REPO
# √ ADD
# √ COMMIT
#   VERSION HISTORY -> Move to info panel w/dismiss - svn log [-q] filename
#   REVERT VERSION PREVIOUS
#   REVERT VERSION N
#   BRANCH (copy)
#   MERGE BRANCH
#   DELETE BRANCH
#   DIFF

## Create Repo Operator
#   Create a new repo of the current working directory.
#   If necessary, create the repo root folder too.
#   https://subversion.apache.org/quick-start#setting-up-a-local-repo
#   https://docs.blender.org/manual/en/2.93/advanced/blender_directory_layout.html
class CreateAndImportOperator(bpy.types.Operator):
    bl_idname = "scop.create_import"
    bl_label  = "Create Repo & Add"

    def execute(self, context):

        myLogger.info(f'Running CreateAndImportOperator()')

        # Confirm that the current file is saved
        if not bpy.data.is_saved:
            self.report({'ERROR'}, "File has not been saved to your drive. Please save it before continuing.")
            return {'FINISHED'}

        # Get paths for current file
        filepath = bpy.data.filepath
        filename = Path(filepath).name
        working_dir = Path(filepath).parent
        
        # Check we are not already in a working set
        # Confirm whether there is a working set available.
        process = subprocess.Popen(svn_commands["svn_info"] + [working_dir],
                     stdout=subprocess.PIPE, 
                     stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if (len(stderr)<1) & (len(re.findall("Working Copy Root Path:", stdout.decode('utf-8')))>0):
            self.report({'ERROR'}, "A working copy already exists for this directory. You can add or commit this file to the existing working copy.")
            return {'FINISHED'}
        

        # Above confirms that file & working set status are OK to continue
        preferences = context.preferences
        addon_prefs = preferences.addons[__name__].preferences

        # Get locations via prefs
        repoRoot = prefs['str_prefSVNRepoHome'] if addon_prefs.useDefaultRepoRoot else addon_prefs.repoRoot
        repoRoot = Path(repoRoot)
        if not repoRoot.is_absolute():
            repoRoot = repoRoot.expanduser()
            if not repoRoot.is_absolute():
                try:
                    repoRoot = working_dir.joinpath(repoRoot).resolve()
                except ValueError as error:
                    myLogger.error(f'Could not resolve repoRoot {repoRoot} against working_dir {working_dir}.')
                    self.report({'ERROR'},'Could not resolve repsitory root folder.')

                    return {'FINISHED'}

        repoName = generateRepoName(filepath) if addon_prefs.useDefaultRepoName else addon_prefs.repoName


        #Start to create necessary paths
        myLogger.info(f'Start creating repository at Root: \'{repoRoot}\', Name: \'{repoName}\'.')
        # On Unix:
        if platform.system() == "Darwin": # or "Linux"

            # Check whether the repo home exists. If not, create it.
            if not repoRoot.exists():
                myLogger.info(f'Repositories home {repoRoot.as_posix()} not found. Attempting to create it.')
                try:
                    Path.mkdir(repoRoot, parents=True)
                    myLogger.info(f'Successfully created repositories home.')
                except OSError as error:
                    myLogger.error(error)
                    self.report({'ERROR'}, f'Error creating repositories home: {error}')

                    return  {'FINISHED'}
            else:
                myLogger.info(f'Existing repo home was found.')


            ## Check whether the repo already exists
            #   If not create it
            #   If so, error.
            myLogger.info(f'Checking for repo \'{repoName}\'')

            repoPath = Path(repoRoot,repoName)
            if repoPath.exists():
                myLogger.error(f'Repository {repoPath.as_posix()} already exists. Aborting.')
                self.report({'ERROR'},f'Indicated repository {repoPath.as_posix()} already exists. Please choose another name or move this file to the related working set.')
            
                return {'FINISHED'}

            # Create a new repository withing the repoRoot
            myLogger.info(f'Attempting to create repository via SVNadmin.')
            try:
                process = subprocess.Popen(svn_commands['svn_admin_create'] + [repoPath.as_posix()],
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()

                if len(stderr)>1:
                    error = stderr.decode("utf-8")
                    myLogger.error(f'Error creating respository (svn_admin_create): {error}')
                    self.report({'ERROR'},f'Error creating repository (svn_admin_create): {error}')

                    return {'FINISHED'}   
                myLogger.info('Successfully created repository with svnadmin.')


                # Create a recommended project layout in the new repository:
                myLogger.info('Creating repository structure with svn...')
                process = subprocess.Popen(svn_commands['svn_mkdir_repo'] + [Path(repoPath,"trunk").as_uri()] + [Path(repoPath,"branches").as_uri()] + [Path(repoPath,"tags").as_uri()],
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()
                
                if len(stderr)>1:
                    error = stderr.decode("utf-8")
                    myLogger.error(f'Error creating respository (svn_mkdir_repo): {error}')
                    self.report({'ERROR'},f'Error creating repository (svn_mkdir_repo): {error}')

                    return {'FINISHED'} 
                myLogger.info('Successfully created repository structure')


                # Convert the current directory into a working copy of the trunk/ in the repository:
                #  svn checkout file://$HOME/.svnrepos/MyRepo/trunk ./
                process = subprocess.Popen(svn_commands['svn_checkout'] + [Path(repoPath,"trunk").as_uri()] + [working_dir.as_posix()],
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()

                if len(stderr)>1:
                    error = stderr.decode("utf-8")
                    myLogger.error(f'Error checking out new respository: {error}')
                    self.report({'ERROR'},f'Error checking out new respository: {error}')

                    return {'FINISHED'}
                myLogger.info('Successfully checked out new repository.')


                # Schedule your project's files to be added to the repository:
                #  svn add --force ./
                process = subprocess.Popen(svn_commands['svn_add_single'] + [filepath],
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()

                if len(stderr)>1:
                    error = stderr.decode("utf-8")
                    myLogger.error(f'Error adding file to repository: {error}')
                    self.report({'ERROR'},f'Error adding file to repository: {error}')

                    return {'FINISHED'}
                myLogger.info('Successfully added file to new repository.')


                # Commit the project's files:
                #  svn commit -m "Initial import."
                process = subprocess.Popen(svn_commands['svn_commit_single'] + [filepath],
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()

                if len(stderr)>1:
                    error = stderr.decode("utf-8")
                    myLogger.error(f'Error committing file to repository: {error}')
                    self.report({'ERROR'},f'Error committing file to repository: {error}')

                    return {'FINISHED'}
                myLogger.info('Successfully committed file to new repository.')
                
                # Update your working copy:
                #  svn update
                process = subprocess.Popen(svn_commands['svn_update'] + [working_dir.as_posix()],
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()

                if len(stderr)>1:
                    error = stderr.decode("utf-8")
                    myLogger.error(f'Error updating working copy: {error}')
                    self.report({'ERROR'},f'Error updating working copy: {error}')

                    return {'FINISHED'}
                myLogger.info('Successfully updated working copy.')


                myLogger.info('Completed importing {filename} to repository.')

            except OSError as error:
                myLogger.error(error)
                self.report({'ERROR'},f'Error creating repository (OSError): {error}')

                return {'FINISHED'}


        #if platform.system() == "Windows":
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
        
        self.report({'INFO'}, f'Created repository at {repoPath} and comitted {filename}.')
        return {'FINISHED'}
        

## ADD Operator
## ADD current file to working set
class AddOperator(bpy.types.Operator):
    bl_idname = "scop.add"
    bl_label  = "Add"

    def execute(self, context):
        
        filepath = bpy.data.filepath
        filename = Path(filepath).stem
        working_dir = Path(filepath).parent

        # Confirm that there is a working set available.
        process = subprocess.Popen(svn_commands["svn_info"] + [working_dir],
                     stdout=subprocess.PIPE, 
                     stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if (len(stdout)<1) & (len(re.findall("E155007", stderr.decode('utf-8')))>0):
            self.report({'ERROR'}, "There is not working set for this directory. Please create a new repository or move the file to an existing working set.")

            return {'FINISHED'}
        
        # Confirm that that the file is saved
        if not bpy.data.is_saved:
            self.report({'ERROR'}, "File has not been saved. Please save before committing.")
            return {'FINISHED'}

        myLogger.info(f'Attempting to add file \'{filepath}\'.')

        # Confirm file's SVN status
        # Acceptable for add '?' only
        err, status = getSvnFileStatus(filepath)

        if not err:
            if status in [' ','A','C','M']:
                self.report({'ERROR'},"File is already added to the working set.")
            elif status == 'I':
                self.report({'ERROR'},"File is currently ignored. Please remove it from the .svnignore file.")
            elif status in ['?']:
                process = subprocess.Popen(svn_commands["svn_add_single"] + [filepath],
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()
                if len(stdout)>0:
                    result = stdout.decode('utf-8')
                    myLogger.info(result.replace('\n',' '))
                    myLogger.debug(f'Successfully committed. Return code: \'{process.returncode}\'.')
                    self.report({'INFO'},result.replace('\n',' '))
                elif len(stderr)>0:
                    result = stderr.decode('utf-8')
                    myLogger.error(result)
                    self.report({'ERROR'},result)
                else:
                    myLogger.error(f'Error when committing file: {process.returncode}')
                    self.report({'ERROR'},f'Error when committing file: {process.returncode}')
            else:
                myLogger.error(f'File has unsupported status \'{status}\'.')
                self.report({'ERROR'},f'File has unsupported status \'{status}\'.')
        else:
            myLogger.error(err)
            self.report(err)

        return {'FINISHED'}

## Commit Operator
## Commit current file
class CommitOperator(bpy.types.Operator):
    bl_idname = "scop.commit"
    bl_label  = "Commit"

    def execute(self, context):

        filepath = bpy.data.filepath
        filename = Path(filepath).stem
        working_dir = Path(filepath).parent

        # Confirm file state
        if not bpy.data.is_saved:
            self.report({'ERROR'}, "This file has not been saved to your drive. Please save it before committing.")
            return {'FINISHED'}
        if bpy.data.is_dirty:
            self.report({'ERROR'}, "This file has unsaved changes. Please save before committing.")
            return {'FINISHED'}

        # Confirm that there is a working set available.
        process = subprocess.Popen(svn_commands["svn_info"] + [working_dir],
                     stdout=subprocess.PIPE, 
                     stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if (len(stdout)<1) & (len(re.findall("E155007", stderr.decode('utf-8')))>0):
            self.report({'ERROR'}, "There is no working set available for this folder. Please prepare one, or move this file into an existing one.")
            return {'FINISHED'}

        myLogger.info(f'Attempting to commit file \'{filepath}\'.')

        # Confirm file status
        # Acceptable for commit: 'A','M'
        err, status = getSvnFileStatus(filepath)

        if not err:
            if status == ' ':
                self.report({'ERROR'},"File has no oustanding changes to commit.")
            elif status == '?':
                self.report({'ERROR'},"File has not been added to the working set. Please add it before committing.")
            elif status == 'I':
                self.report({'ERROR'},"File is currently ignored. Please remove it from the .svnignore file.")
            elif status in ['M','A']:
                process = subprocess.Popen(svn_commands["svn_commit_single"] + [filepath],
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()
                if len(stdout)>0:
                    result = stdout.decode('utf-8')
                    myLogger.info(result.replace('\n',' '))
                    myLogger.debug(f'Successfully committed. Return code: \'{process.returncode}\'.')
                    self.report({'INFO'},result.replace('\n',' '))
                elif len(stderr)>0:
                    result = stderr.decode('utf-8')
                    myLogger.error(result)
                    self.report({'ERROR'},result)
                else:
                    myLogger.error(f'Error when committing file: {process.returncode}')
                    self.report({'ERROR'},f'Error when committing file: {process.returncode}')
            else:
                myLogger.error(f'File has unsupported status \'{status}\'.')
                self.report({'ERROR'},f'File has unsupported status \'{status}\'.')
        else:
            myLogger.error(err)
            self.report({'ERROR'},err)

        return {'FINISHED'}


## Revert Operator
## Revert to Previously Committed State
class RevertPreviousOperator(bpy.types.Operator):
    bl_idname = "scop.revert_previous"
    bl_label  = "Revert to Previous"

    def execute(self, context):

        filepath = bpy.data.filepath
        filename = Path(filepath).stem
        working_dir = Path(filepath).parent


        # Confirm that there is a working set available.
        process = subprocess.Popen(svn_commands["svn_info"] + [working_dir],
                     stdout=subprocess.PIPE, 
                     stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if (len(stdout)<1) & (len(re.findall("E155007", stderr.decode('utf-8')))>0):
            self.report("There is no working set available for this folder. No reversion possible.")

            return {'FINISHED'}

        myLogger.info(f'Attempting to commit file \'{filepath}\'.')

        # Confirm file status
        # Acceptable for commit: ' ','M'
        #  if 'M' -> svn revert filename 
        #  if ' ' -> svn export --force -r PREV filename filename 
        #         or svn merge -r HEAD:123 .
        #            svn commit -m "Reverted to revision 123"
        err, status = getSvnFileStatus(filepath)
        if not err:
            if status in ['M','A']:
                process = subprocess.Popen(svn_commands["svn_revert_previous"] + [filepath],
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()
                if len(stdout)>0:
                    result = stdout.decode('utf-8')
                    myLogger.info(result.replace('\n',' '))
                    myLogger.debug(f'Successfully committed. Return code: \'{process.returncode}\'.')
                    self.report({'INFO'},result.replace('\n',' '))
                elif len(stderr)>0:
                    result = stderr.decode('utf-8')
                    myLogger.error(result)
                    self.report({'ERROR'},result)
                else:
                    myLogger.error(f'Error when committing file: {process.returncode}')
                    self.report({'ERROR'},f'Error when committing file: {process.returncode}')
            else:
                myLogger.error(f'File has unsupported status \'{status}\'.')
                self.report({'ERROR'},f'File has unsupported status \'{status}\'.')
        else:
            myLogger.error(err)
            self.report(err)

        return {'FINISHED'}

#################################
### Blender GUI Class Objects ###
#################################

# Preferences Object
class SVNConnectorAddonPreferences(AddonPreferences):
    # This must match the add-on name. Use '__package__'
    # if defining this in a SUBMODULE of a python package.
    bl_idname = __name__

    # TODO: Add application state.

    useDefaultRepoRoot: BoolProperty(
        name="Use default local SVN Home Path",
        description="If you are unsure, use the default setting",
        default=prefs["bln_SVNUseDefaultLocalHome"]
    )

    repoRoot: StringProperty(
        name="Local SVN Home",
        subtype='DIR_PATH',
        default=prefs["str_prefSVNRepoHome"]
    )

    useDefaultRepoName: BoolProperty(
        name="Use the default (generated) repository name",
        description="By default, the addon will re-use the name of the folder where the file is saved. \n This can be any value which your system accepts as a foldername",
        default=prefs["bln_SVNUseDefaultRepoName"]
    )   

    repoName: StringProperty(
        name="Custom Repo Name",
        subtype='NONE'
    )


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
    bl_idname = "OBJECT_MT_SVN_submenu"
    bl_label = "SVN Connector"

    def draw(self, context):
        layout = self.layout

        # Append in order of expected frequency of use
        layout.operator("scop.commit", text="Commit")
        layout.operator("scop.revert_previous")
        layout.operator("scop.add", text="Add")
        layout.operator("scop.create_import", text="Commit to new repo")


# Function to draw the menu item.
# This function is passed to blender and called each time the parent menu is drawn.
def menu_draw_svn(self, context):
    #self.layout.operator("wm.save_homefile")
    self.layout.menu("OBJECT_MT_SVN_submenu")


## INFO Panel
class SvnInfoPanel(bpy.types.Panel):
    bl_idname = "SVN_PT_InfoPanel"
    bl_label = "SVN Info"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SVNConnector"
    #bl_context = "objectmode"

    def draw(self, context):

        layout = self.layout

        row = layout.row()
        row.label(text=f'svn_version: {svn_version}')
        row = layout.row()
        row.label(text=f'svn_ra_local: {svn_ra_local}')
        row = layout.row()
        row.label(text=f'svn_ra_svn: {svn_ra_svn}')

        row =layout.row()
        row.label(text=f'svnadmin_avail: {svnadmin_avail}') 
        row = layout.row()
        row.label(text=f'svnadmin_version: {svnadmin_version}') 

        row = layout.row()
        row.label(text=f'platform.system: {platform.system()}')


## INFO Panel
class SvnStatusPanel(bpy.types.Panel):
    bl_idname = "SVN_PT_StatusPanel"
    bl_label = "SVN Status"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SVNConnector"
    #bl_context = "objectmode"

    def draw(self, context):

        err, status = getSvnFileStatus(bpy.data.filepath)

        layout = self.layout
        row = layout.row()
        row.label(text=f'File status: \'{status}\'')

    @persistent
    def fileUpdateHandler(self,dummy, arg1, arg2):
        self.file_status = getSvnFileStatus(bpy.data.filepath)
    

    # def __init__(self) -> None:
    #     super().__init__()

    #     bpy.app.handlers.load_post.append(self.fileUpdateHandler)
    #     bpy.app.handlers.save_post.append(self.fileUpdateHandler)


###############################
### BLENDER ADDON INTERFACE ###
###############################

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

    # TODO: Check application state and register as appropriate.

    for name, cls in inspect.getmembers(sys.modules[__name__], lambda x: inspect.isclass(x) and (x.__module__ == __name__)):
        myLogger.debug(f'Registering class {cls} with name {name}')
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file.append(menu_draw_svn)

def unregister():
    myLogger.info(f'Unregistering classes defined in module {__name__}')

    for name, cls in inspect.getmembers(sys.modules[__name__], lambda x: inspect.isclass(x) and (x.__module__ == __name__)):
        myLogger.debug(f'Unregistering class {cls} with name {name}')
        bpy.utils.unregister_class(cls)
    bpy.types.TOPBAR_MT_file.remove(menu_draw_svn)



##############
### LAUNCH ###
##############
if __name__ == "__main__":

    register()
    #unregister()