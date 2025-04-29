import importlib
import MayaUtils
importlib.reload(MayaUtils) 
import os
from MayaUtils import *
from PySide2.QtCore import Signal
from PySide2.QtGui import QIntValidator, QRegExpValidator
from PySide2.QtWidgets import QCheckBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton, QVBoxLayout, QWidget
import maya.cmds as mc
import MayaTools


def TryAction(action):
    def wrapper(*args, **kwargs):
        try:
            action(*args, **kwargs)
        except Exception as e:
            QMessageBox().critical(None, "Error", f"{e}")

    return wrapper

# Data oriented class
class AnimClip:
    def __init__(self):
        self.subfix = ""
        self.frameMin = mc.playbackOptions(q=True, min=True)
        self.frameMax = mc.playbackOptions(q=True, max=True)
        self.shouldExport = True

class MayaToUE:
    def __init__(self):
        self.rootJnt = ""
        self.meshes = []
        self.animationClips : list[AnimClip] = []
        self.fileName = ""
        self.saveDir = ""

    def GetAllJoints(self):
        jnts = []
        jnts.append(self.rootJnt)
        children = mc.listRelatives(self.rootJnt, c=True, ad=True, type="joint")
        if children:
            jnts.extend(children)

        return jnts

    def SaveFiles(self):
        allJnts = self.GetAllJoints()
        allMeshes = self.meshes

        allObjectsToExport = allJnts + allMeshes
        mc.select(allObjectsToExport, r=True)

        skeletalMeshExportPath = self.GetSkeletalMeshSavePath()
        
        mc.FBXResetExport()
        mc.FBXExportSmoothingGroups('-v', True)
        mc.FBXExportInputConnections('-v', False)

        self.SendToUnreal()

    def SendToUnreal(self):
        ueUtilPath = os.path.join(MayaTools.srcDir, "UnrealUtils.py")
        ueUtilPath = os.path.normpath(ueUtilPath)

        meshPath = self.GetSkeletalMeshSavePath().replace("\\", "/")
        aimDir = self.GetAnimDirPath().replace("\\", "/")

        commands = []
        with open(ueUtilPath, 'r') as ueUitlityFile:
            commands = ueUitlityFile.readlines()

        commands.append(f"\nImportMeshAndAnimation(\'{meshPath}\', \'{aimDir}\')")

        command = "".join(commands)
        print(command)

    def GetAnimDirPath(self):
        path = os.path.join(self.saveDir, "animations")
        return os.path.normpath(path)

    def GetSavePathForAnimClip(self, animClip):
        path = os.path.join(self.saveDir, self.GetAnimDirPath(), self.fileName + animClip.subfix + ".fbx")
        return os.path.normpath(path)

    def GetSkeletalMeshSavePath(self):
        path = os.path.join(self.saveDir, self.fileName + ".fbx")
        return os.path.normpath(path)

    def RemoveAnimClip(self, cliptoRemove: AnimClip):
        self.animationClips.remove(cliptoRemove)

    def AddNewAnimClipEntry(self):
        self.animationClips.append(AnimClip())
        return self.animationClips[-1]

    def SetSelectedAsRootJnt(self):
        selection = mc.ls(sl=True)
        if not selection:
            raise Exception("Nothing Selected, PLease Select the Root Joint of the Rig")
        
        selectedJnt = selection[0]
        if not IsJoint(selectedJnt):
            raise Exception(f"{selectedJnt} is not a joint, Please select the Root Joint of the Rig")

        self.rootJnt = selectedJnt

    def AddRootJoint(self):
        if (not self.rootJnt) or (not mc.objExists(self.rootJnt)):
            raise Exception("No Root Joint Assigned, please set the current root joint of the rig first by selecting the pelivs")

        currentRootJntPosX, currentRootJntPosY, currentRootJntPosZ = mc.xform(self.rootJnt, q=True, t=True, ws=True)
        if currentRootJntPosX == 0 and currentRootJntPosY ==0 and currentRootJntPosZ == 0:
            raise Exception("Current Root Joint is already at origin")

        mc.select(cl=True)
        rootJntName = self.rootJnt + "_root"
        mc.joint(n=rootJntName)
        mc.parent(self.rootJnt, rootJntName)
        self.rootJnt = rootJntName

    def AddMeshs(self):
        selection = mc.ls(sl=True)
        if not selection:
            raise Exception("No Mesh Selected")

        meshes = set()

        for sel in selection:
            if IsMesh(sel):
                meshes.add(sel)

        if len(meshes) == 0:
            raise Exception("No Mesh Selected")

        self.meshes = list(meshes)

class AnimClipEntryWidget(QWidget):
    entryRemoved = Signal(AnimClip)
    entrySubFixChanged = Signal(str)
    def __init__(self, animClip: AnimClip):
        super().__init__()
        self.animClip = animClip
        self.masterLayout = QHBoxLayout()
        self.setLayout(self.masterLayout)

        shouldExportCheckbox = QCheckBox()
        shouldExportCheckbox.setChecked(self.animClip.shouldExport)
        self.masterLayout.addWidget(shouldExportCheckbox)
        shouldExportCheckbox.toggled.connect(self.ShouldExportCheckBoxToggled)

        self.masterLayout.addWidget(QLabel("Subfix: "))

        subfixLineEdit = QLineEdit()
        subfixLineEdit.setValidator(QRegExpValidator("[a-zA-z0-9_]+"))
        subfixLineEdit.setText(self.animClip.subfix)
        subfixLineEdit.textChanged.connect(self.SubfixTextChanged)
        self.masterLayout.addWidget(subfixLineEdit)

        self.masterLayout.addWidget(QLabel("Min: "))
        minFrameLineEdit = QLineEdit()
        minFrameLineEdit.setValidator(QIntValidator())
        minFrameLineEdit.setText(str(int(self.animClip.frameMin)))
        minFrameLineEdit.textChanged.connect(self.MinFrameChanged)
        self.masterLayout.addWidget(minFrameLineEdit)

        self.masterLayout.addWidget(QLabel("Max: "))
        maxFrameLineEdit = QLineEdit()
        maxFrameLineEdit.setValidator(QIntValidator())
        maxFrameLineEdit.setText(str(int(self.animClip.frameMax)))
        maxFrameLineEdit.textChanged.connect(self.MaxFrameChanged)
        self.masterLayout.addWidget(maxFrameLineEdit)

        setRangeBtn = QPushButton("[-]")
        setRangeBtn.clicked.connect(self.setRangeBtnClicked)
        self.masterLayout.addWidget(setRangeBtn)

        deleteBtn = QPushButton("X")
        deleteBtn.clicked.connect(self.DeleteButtonClicked)
        self.masterLayout.addWidget(deleteBtn)

    def DeleteButtonClicked(self):
        self.entryRemoved.emit(self.animClip)
        self.deleteLater()

    def setRangeBtnClicked(self):
        mc.playbackOptions(e=True, min=self.animClip.frameMin, max=self.animClip.frameMax)
        mc.playbackOptions(e=True, ast=self.animClip.frameMin, aet=self.animClip.frameMax)

    def MinFrameChanged(self, newVal):
        self.animClip.frameMin = int(newVal)

    def MaxFrameChanged(self, newVal):
        self.animClip.frameMax = int(newVal)

    def SubfixTextChanged(self, newText):
        self.animClip.subfix = newText
        self.entrySubFixChanged.emit(newText)

    def ShouldExportCheckBoxToggled(self):
        self.animClip.shouldExport = not self.animClip.shouldExport

class MayaToEUWidget(QMayaWindow):
    def GetWindowHash(self):
        return "MAYATOUEAWDOAWNONOLR"

    def __init__(self):
        super().__init__()
        self.mayaToUE = MayaToUE()
        self.setWindowTitle("Maya to UE")
        
        self.masterLayout = QVBoxLayout()
        self.setLayout(self.masterLayout)

        self.rootJntText = QLineEdit()
        self.rootJntText.setEnabled(False)
        self.masterLayout.addWidget(self.rootJntText)

        setSelectionAsRootJntBtn = QPushButton("Set Root Joint")
        setSelectionAsRootJntBtn.clicked.connect(self.SetSelectionAsRootJointBtnClicked)
        self.masterLayout.addWidget(setSelectionAsRootJntBtn)

        addRootJntBtn = QPushButton("Add Root Joint")
        addRootJntBtn.clicked.connect(self.AddRootJntButtonClicked)
        self.masterLayout.addWidget(addRootJntBtn)

        self.meshList = QListWidget()
        self.masterLayout.addWidget(self.meshList)
        self.meshList.setFixedHeight(80)
        addMeshBtn = QPushButton("Add Meshes")
        addMeshBtn.clicked.connect(self.AddMeshBtnClicked)
        self.masterLayout.addWidget(addMeshBtn)

        addNewAnimClipEntryBtn = QPushButton("Add Animation Clip")
        addNewAnimClipEntryBtn.clicked.connect(self.AddNewAnimClipEntryBtnClicked)
        self.masterLayout.addWidget(addNewAnimClipEntryBtn)

        self.animEntryLayout = QVBoxLayout()
        self.masterLayout.addLayout(self.animEntryLayout)

        self.saveFileLayout = QHBoxLayout()
        self.masterLayout.addLayout(self.saveFileLayout)
        fileNameLabel = QLabel("File Name: ")
        self.saveFileLayout.addWidget(fileNameLabel)

        self.fileNameLineEdit = QLineEdit()
        self.fileNameLineEdit.setFixedWidth(90)
        self.fileNameLineEdit.setValidator(QRegExpValidator("\w+"))
        self.fileNameLineEdit.textChanged.connect(self.FileNameLineEditChanged)
        self.saveFileLayout.addWidget(self.fileNameLineEdit)

        self.directoryLabel = QLabel("Save Directory: ")
        self.saveFileLayout.addWidget(self.directoryLabel)
        self.saveDirectoryLineEdit = QLineEdit()
        self.saveDirectoryLineEdit.setEnabled(False)
        self.saveFileLayout.addWidget(self.saveDirectoryLineEdit)
        self.pickDirBtn = QPushButton("...")
        self.pickDirBtn.clicked.connect(self.PickDirBtnClicked)
        self.saveFileLayout.addWidget(self.pickDirBtn)

        self.savePreviewLabel = QLabel("")
        self.masterLayout.addWidget(self.savePreviewLabel)

        saveFileBtn = QPushButton("Save Files")
        saveFileBtn.clicked.connect(self.SaveFilesBtnClicked)
        self.masterLayout.addWidget(saveFileBtn)

    def SaveFilesBtnClicked(self):
        self.mayaToUE.SaveFiles()

    def UpdateSavePreviewLabel(self):
        previewText = self.mayaToUE.GetSkeletalMeshSavePath()
        if not self.mayaToUE.animationClips:
            return
        
        for animClip in self.mayaToUE.animationClips:
            animSavePath = self.mayaToUE.GetSavePathForAnimClip(animClip)
            previewText += "\n" + animSavePath

        self.savePreviewLabel.setText(previewText)

    @TryAction
    def PickDirBtnClicked(self):
        path = QFileDialog().getExistingDirectory()
        self.saveDirectoryLineEdit.setText(path)
        self.mayaToUE.saveDir = path
        self.UpdateSavePreviewLabel()

    @TryAction
    def FileNameLineEditChanged(self, newText):
        self.mayaToUE.fileName = newText
        self.UpdateSavePreviewLabel()

    @TryAction
    def AddNewAnimClipEntryBtnClicked(self):
        newEntry = self.mayaToUE.AddNewAnimClipEntry()
        newEntryWidget = AnimClipEntryWidget(newEntry)
        newEntryWidget.entryRemoved.connect(self.AnimClipEntryRemoved)
        newEntryWidget.entrySubFixChanged.connect(lambda x : self.UpdateSavePreviewLabel())
        self.animEntryLayout.addWidget(newEntryWidget)
        self.UpdateSavePreviewLabel()

    @TryAction
    def AnimClipEntryRemoved(self, animClip: AnimClip):
        self.mayaToUE.RemoveAnimClip(animClip)
        self.UpdateSavePreviewLabel()

    @TryAction
    def AddMeshBtnClicked(self):
        self.mayaToUE.AddMeshs()
        self.meshList.clear()
        self.meshList.addItems(self.mayaToUE.meshes)

    @TryAction
    def AddRootJntButtonClicked(self):
        self.mayaToUE.AddRootJoint()
        self.rootJntText.setText(self.mayaToUE.rootJnt)

    @TryAction
    def SetSelectionAsRootJointBtnClicked(self):
        self.mayaToUE.SetSelectedAsRootJnt()
        self.rootJntText.setText(self.mayaToUE.rootJnt)

MayaToEUWidget().show()

#AnimClipEntryWidget(AnimClip()).show()