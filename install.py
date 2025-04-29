import os
import shutil
import maya.cmds as mc

def Install():
    prjPath = os.path.dirname(os.path.abspath(__file__))
    pluginName = os.path.split(prjPath)[-1]
    mayaScriptPath = os.path.join(mc.internalVar(uad=True), "scripts")
    
    pluginDestPath = os.path.join(mayaScriptPath, pluginName)
    if os.path.exists(pluginDestPath):
        shutil.rmtree(pluginDestPath)

    os.makedirs(pluginDestPath, exist_ok=True)
    srcDirName = "src"
    assetDirName = "assets"
    shutil.copytree(os.path.join(prjPath, srcDirName), os.path.join(pluginDestPath, srcDirName))
    shutil.copytree(os.path.join(prjPath, assetDirName), os.path.join(pluginDestPath, assetDirName))
    shutil.copytree(os.path.join(prjPath, "vendor"), os.path.join(pluginDestPath, "vendor"))
    shutil.copy2(os.path.join(prjPath, "_init_.py"), os.path.join(pluginDestPath, "_init_.py"))

    def AddShelfBtn(scriptName):
        currentShelf = mc.tabLayout("ShelfLayout", q=True, selectTab = True);
        mc.setParent(currentShelf)
        icon = os.path.join(pluginDestPath, assetDirName, scriptName + " Icon.PNG")
        mc.shelfButton(c=f"from {pluginName}.src import {scriptName};{scriptName}.Run()", image=icon)

    AddShelfBtn("LimbRiggingTool")
    AddShelfBtn("ProxyRigger")
    AddShelfBtn("MayaToUE")