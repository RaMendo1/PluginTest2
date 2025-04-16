from PySide2.QtGui import QColor
import maya.cmds as mc 
import maya.OpenMayaUI as omui 
import shiboken2 
import maya.mel as mel
from maya.OpenMaya import MVector

from PySide2.QtWidgets import (QColorDialog, 
                               QLineEdit, 
                               QMainWindow, 
                               QMessageBox, 
                               QWidget, 
                               QVBoxLayout, 
                               QHBoxLayout, 
                               QLabel, 
                               QSlider, 
                               QPushButton)
from PySide2.QtCore import Qt

from MayaUtils import QMayaWindow
    
class LimbRigger: 
    def __init__(self):
        self.root = " " 
        self.mid = " " 
        self.end = " " 
        self.controllerSize = 5 
        self.controllerColorRGB = (0.0, 0.0, 0.0)

    def AutoFindJnts(self): 
        self.root = mc.ls(sl=True, type="joint")[0]
        self.mid = mc.listRelatives(self.root, c=True, type="joint")[0]
        self.end = mc.listRelatives(self.mid, c=True, type="joint")[0]

    def ApplyColorToCurve(self, curveName):
        shapes = mc.listRelatives(curveName, shapes=True, type="nurbsCurve", fullPath=True)
        if not shapes:
            return

        r, g, b = self.controllerColorRGB

        for shape in shapes:
            mc.setAttr(f"{shape}.overrideEnabled", 1)
            mc.setAttr(f"{shape}.overrideRGBColors", 1)
            mc.setAttr(f"{shape}.overrideColorRGB", r, g, b, type="double3")

    def CreateFKControlForJnt(self, jntName): 
        ctrlName = "ac_fk_" + jntName
        ctrlGrpName = ctrlName + "_grp"
        mc.circle(n=ctrlName, r=self.controllerSize, nr = (1,0,0))
        self.ApplyColorToCurve(ctrlName)

        mc.group(ctrlName, n=ctrlGrpName)
        mc.matchTransform(ctrlGrpName, jntName)
        mc.orientConstraint(ctrlName, jntName)
        return ctrlName, ctrlGrpName
    
    def CreateBoxController(self, name):
        mel.eval(f"curve -n {name} -d 1 -p 0.5 0.5 0.5 -p -0.5 0.5 0.5 -p -0.5 -0.5 0.5 -p 0.5 -0.5 0.5 -p 0.5 0.5 0.5 -p 0.5 0.5 -0.5 -p 0.5 -0.5 -0.5 -p 0.5 -0.5 0.5 -p -0.5 -0.5 0.5 -p -0.5 -0.5 -0.5 -p -0.5 0.5 -0.5 -p -0.5 0.5 0.5 -p -0.5 0.5 -0.5 -p 0.5 0.5 -0.5 -p 0.5 -0.5 -0.5 -p -0.5 -0.5 -0.5 -k 0 -k 1 -k 2 -k 3 -k 4 -k 5 -k 6 -k 7 -k 8 -k 9 -k 10 -k 11 -k 12 -k 13 -k 14 -k 15 ;")
        mc.scale(self.controllerSize, self.controllerSize, self.controllerSize, name)
        mc.makeIdentity(name, apply = True) # this is freeze transformation

        grpName = name + "_grp"
        mc.group(name, n=grpName)
        self.ApplyColorToCurve(name)
        return name, grpName

    def CreatePlusController(self, name):
        mel.eval(f"curve -n {name} -d 1 -p -3 -1 0 -p -3 1 0 -p -1 1 0 -p -1 3 0 -p 1 3 0 -p 1 1 0 -p 3 1 0 -p 3 -1 0 -p 1 -1 0 -p 1 -3 0 -p -1 -3 0 -p -1 -1 0 -p -3 -1 0 -k 0 -k 1 -k 2 -k 3 -k 4 -k 5 -k 6 -k 7 -k 8 -k 9 -k 10 -k 11 -k 12 ;")
        #mc.scale(self.controllerSize/3, self.controllerSize/3, self.controllerSize/3)
        #mc.makeIdentity(name, apply = True)

        grpName = name + "_grp"
        mc.group(name, n=grpName)
        self.ApplyColorToCurve(name)
        return name, grpName

    def GetObjectLoc(self, objectName)->MVector:
        x, y, z = mc.xform(objectName, q=True, t=True, ws=True) #get the world space translation of the objectname
        return MVector(x, y, z)
    
    
    def PrintMVector(self, vectorToPrint):
        print(f"<{vectorToPrint.x}, {vectorToPrint.y}, {vectorToPrint.z}>")

    def RigLimb(self): 
        rootFKCtrl,  rootFKCtrlGrp = self.CreateFKControlForJnt(self.root)
        midFKCtrl,  midFKCtrlGrp = self.CreateFKControlForJnt(self.mid)
        endFKCtrl,  endFKCtrlGrp = self.CreateFKControlForJnt(self.end)

        mc.parent(midFKCtrlGrp, rootFKCtrl)
        mc.parent(endFKCtrlGrp, midFKCtrl)

        ikEndCtrl = "ac_ik_" + self.end
        ikEndCtrl, ikEndCtrlGrp = self.CreateBoxController(ikEndCtrl)
        mc.matchTransform(ikEndCtrlGrp, self.end)
        endOrientconstraint = mc.orientConstraint(ikEndCtrl, self.end)[0]

        rootJntLoc = self.GetObjectLoc(self.root)
        endJntLoc = self.GetObjectLoc(self.end)

        rootToEndVec = endJntLoc - rootJntLoc

        ikHandleName = "ikHandle_" + self.end
        mc.ikHandle(n=ikHandleName, sj=self.root, ee = self.end, sol="ikRPsolver")
        ikPoleVectorVals = mc.getAttr(ikHandleName + ".poleVector")[0]
        ikPoleVector = MVector(ikPoleVectorVals[0], ikPoleVectorVals[1], ikPoleVectorVals[2])

        ikPoleVector.normalize()
        ikPoleVectorCtrlLoc = rootJntLoc + rootToEndVec / 2 + ikPoleVector * rootToEndVec.length()

        ikPoleVectorCtrlName = "ac_ik_" + self.mid
        mc.spaceLocator(n=ikPoleVectorCtrlName)
        ikPoleVectorCtrlGrp = ikPoleVectorCtrlName + "_grp"
        mc.group(ikPoleVectorCtrlName, n=ikPoleVectorCtrlGrp)
        mc.setAttr(ikPoleVectorCtrlGrp+".t", ikPoleVectorCtrlLoc.x, ikPoleVectorCtrlLoc.y, ikPoleVectorCtrlLoc.z, typ = "double3")
        mc.poleVectorConstraint(ikPoleVectorCtrlName, ikHandleName)

        ikfkBlendCtrlName = "ac_ikfk_blend_" + self.root
        ikfkBlendCtrlName, ikfkBlendCtrlGrp = self.CreatePlusController(ikfkBlendCtrlName)
        ikfkBlendCtrlLoc = rootJntLoc + MVector(rootJntLoc.x, 0, rootJntLoc.z)
        mc.setAttr(ikfkBlendCtrlGrp+".t", ikfkBlendCtrlLoc.x, ikfkBlendCtrlLoc.y, ikfkBlendCtrlLoc.z, typ="double3")

        ikfkBlendAttrName = "ikfkBlend"
        mc.addAttr(ikfkBlendCtrlName, ln=ikfkBlendAttrName, min=0, max=1, k=True)
        ikfkBlendAttr = ikfkBlendCtrlName + "." + ikfkBlendAttrName

        mc.expression(s=f"{ikHandleName}.ikBlend = {ikfkBlendAttr}")
        mc.expression(s=f"{ikEndCtrlGrp}.v = {ikPoleVectorCtrlGrp}.v = {ikfkBlendAttr}")
        mc.expression(s=f"{rootFKCtrl}.v = 1 - {ikfkBlendAttr}")
        mc.expression(s=f"{endOrientconstraint}.{endFKCtrl}w0 = 1-{ikfkBlendAttr}")
        mc.expression(s=f"{endOrientconstraint}.{ikEndCtrl}w1 = {ikfkBlendAttr}")

        mc.parent(ikHandleName, ikEndCtrl)
        mc.setAttr(ikHandleName+".v", 0)

        topGrpName = self.root + "_rig_grp"
        mc.group([rootFKCtrlGrp, ikEndCtrlGrp, ikPoleVectorCtrlGrp, ikfkBlendCtrlGrp], n= topGrpName)


class ColorPicker(QWidget):
    def __init__(self):
        super().__init__()
        self.masterLayout = QVBoxLayout()
        self.setLayout(self.masterLayout)
        self.colorPickerBtn = QPushButton()
        self.colorPickerBtn.setStyleSheet(f"background-color:black")
        self.masterLayout.addWidget(self.colorPickerBtn)
        self.colorPickerBtn.clicked.connect(self.ColorPickerBtnClicked)
        self.color = QColor(0,0,0)

    def ColorPickerBtnClicked(self):
        self.color = QColorDialog.getColor()
        self.colorPickerBtn.setStyleSheet(f"background-color:{self.color.name()}")

class LimbRigToolWidget(QMayaWindow): 
    def __init__(self): 
        super().__init__()
        self.setWindowTitle("Limb Rigging Tool") 
        self.rigger = LimbRigger()

        self.masterLayout = QVBoxLayout()
        self.setLayout(self.masterLayout)

        self.tipLabel = QLabel("Select the First Joint of the Limb, and click on the Auto Find Button") 
        self.masterLayout.addWidget(self.tipLabel)

        self.jointSelectionText = QLineEdit()
        self.masterLayout.addWidget(self.jointSelectionText)
        self.jointSelectionText.setEnabled(False)

        self.autoFindBtn = QPushButton("Auto Find") 
        self.masterLayout.addWidget(self.autoFindBtn)
        self.autoFindBtn.clicked.connect(self.AutoFindBtnClicked)

        ctrlSliderLayout = QHBoxLayout()
        self.ctrlSizeSlider = QSlider()
        self.ctrlSizeSlider.setValue(self.rigger.controllerSize)
        self.ctrlSizeSlider.valueChanged.connect(self.CtrlSizeValueChanged)
        self.ctrlSizeSlider.setRange(1, 30)
        self.ctrlSizeSlider.setOrientation(Qt.Horizontal)
        ctrlSliderLayout.addWidget(self.ctrlSizeSlider)
        self.ctrlSizeLabel = QLabel(f"{self.rigger.controllerSize}")
        ctrlSliderLayout.addWidget(self.ctrlSizeLabel)

        self.masterLayout.addLayout(ctrlSliderLayout)

        self.colorPicker = ColorPicker()
        self.masterLayout.addWidget(self.colorPicker)

        self.rigLimbBtn = QPushButton("Rig Limb")
        self.masterLayout.addWidget(self.rigLimbBtn)
        self.rigLimbBtn.clicked.connect(self.RigLimbBtnClicked)

        self.recolorBtn = QPushButton("Recolor Selected Controllers")
        self.masterLayout.addWidget(self.recolorBtn)
        self.recolorBtn.clicked.connect(self.RecolorSelectedControllers)

        self.setWindowTitle("Limb Rigging Tool")

    def CtrlSizeValueChanged(self, newValue): 
        self.rigger.controllerSize = newValue
        self.ctrlSizeLabel.setText(f"{self.rigger.controllerSize}")

    def RigLimbBtnClicked(self): 
        qcolor = self.colorPicker.color
        r, g, b, _ = qcolor.getRgbF()
        self.rigger.controllerColorRGB = (r, g, b)
        self.rigger.RigLimb()

    def AutoFindBtnClicked(self): 
        try: 
            self.rigger.AutoFindJnts()
            self.jointSelectionText.setText(f"{self.rigger.root}, {self.rigger.mid}, {self.rigger.end}")
        except Exception as e: 
            QMessageBox.critical(self, "Error", "Wrong Selection! Please select the first joint of the limb")

    def RecolorSelectedControllers(self):
        qcolor = self.colorPicker.color
        r, g, b, _ = qcolor.getRgbF()
        
        selected = mc.ls(sl=True, type="transform")
        if not selected:
            QMessageBox.warning(self, "Warning", "Please select one or more controllers to recolor.")
            return
        
        for obj in selected:
            try:
                self.rigger.controllerColorRGB = (r, g, b)
                self.rigger.ApplyColorToCurve(obj)
            except Exception as e:
                print(f"Failed to apply color to {obj}: {e}")


LimbRigToolWidget = LimbRigToolWidget() 
LimbRigToolWidget.show() 

