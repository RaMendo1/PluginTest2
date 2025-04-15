import importlib
import MayaUtils
importlib.reload(MayaUtils)

from MayaUtils import *
from PySide2.QtWidgets import QPushButton, QVBoxLayout
import maya.cmds as mc

class ProxyRigger:
    def __init__(self):
        self.skin = ""
        self.model = ""
        self.jnts = []

    def CreateProxyRigFromSelectedMesh(self):
        mesh = mc.ls(sl=True)[0]
        if not IsMesh(mesh):
            raise TypeError(f"{mesh} is NOT a Mesh! Select a Mesh!")
        
        self.model = mesh
        modelShape = mc.listRelatives(self.model, s=True)[0]
        print(f"Found Mesh {mesh} and Shape {modelShape}")
        
        skin = GetAllConnectIn(modelShape, GetUpperStream, 10, IsSkin)
        if not skin:
            raise Exception(f"{mesh} has no Skin! Tool Only Works with a Rigged Model")
        self.skin = skin[0]

        jnts = GetAllConnectIn(modelShape, GetUpperStream, 10, IsJoint)
        if not jnts:
            raise Exception(f"{mesh} has no Joint Bound! Tool Only Works with a Rigged Model")
        self.jnts = jnts

        print(f"Start Build with Mesh: {self.model}, Skin: {self.skin}, and Joints: {self.jnts}")

        jntVertMap = self.GenerateJntVertDict()
        segments = []
        ctrls = []
        for jnt, verts, in jntVertMap.items():
            print (f"Joint {jnt} controls {verts} primarily")
            newSeg = self.CreateProxyModelForJntAndVerts
            if newSeg is None:
                continue

            newSkinCluster = mc.skinCluster(self.jnts, newSeg)[0]
            mc.copySkinWeights(ss=self.skin, ds=newSkinCluster, nm=True, sa="closestPoint", ia="closestJoint")
            segments.append(newSeg)

            ctrlLocator = "ac_" + jnt + "_proxy"
            mc.spaceLocator(n=ctrlLocator)
            ctrlLocatorGrp = ctrlLocator + "_grp"
            mc.group(ctrlLocator, n=ctrlLocatorGrp)
            mc.matchTransform(ctrlLocatorGrp, jnt)

            visibilityAttr = "vis"
            mc.addAttr(ctrlLocator, ln=visibilityAttr, min=0, max=1, dv=1, k=True)
            mc.connectAttr(ctrlLocator + "." + visibilityAttr, newSeg + ".v")
            ctrls.append(ctrlLocatorGrp)

        proxyTopGrp = self.model + "_proxy_grp"
        mc.group(segments, n=proxyTopGrp)

        ctrlTopGrp = "ac_" + self.model + "_proxy_grp"
        mc.group(ctrls, n=ctrlTopGrp)

        globalProxyCtrl = "ac_" + self.model + "_proxy_global"
        mc.circle(n=globalProxyCtrl, r=30)
        mc.parent(proxyTopGrp, globalProxyCtrl)
        mc.parent(ctrlTopGrp, globalProxyCtrl)
        mc.setAttr(proxyTopGrp + ".inheritsTransform", 0)

        visibilityAttr = "vis"
        mc.addAttr(globalProxyCtrl, ln=visibilityAttr, min=0, max=1, dv=1, k=True)
        mc.connectAttr(globalProxyCtrl + "." + visibilityAttr, proxyTopGrp + ".v")



    def CreateProxyModelForJntAndVerts(self, jnt, verts):
        if not verts:
            return None
        
        faces = mc.polyListComponentConversion(verts, fromvertex=True, toFace=True)
        faces = mc.ls(faces, fl=True)

        labels = set() # a set is like a list, but only holds unique elements and it is not ordered, fast than list when it coems to looking for stuff inside.
        for face in faces:
            labels.add(face.replace(self.model, ""))

        dup = mc.duplicate(self.model)[0]

        allDupFaces = mc.ls(f"{dup}.f[*]", fl=True)
        facesToDelete = []
        for dupFace in allDupFaces:
            label = dupFace.replace(dup, "")
            if label not in labels:
                facesToDelete.append(dupFace)

        mc.delete(facesToDelete)

        dupName = self.model + "_" + jnt + "_proxy"
        mc.rename(dup, dupName)
        return dupName


    def GenerateJntVertDict(self):
        dict = {}
        for jnt in self.jnts:
            dict[jnt] = []

        verts = mc.ls(f"{self.model}.vtx[*]", fl=True)
        for vert in verts:
            owningJnt = self.GetJntWithMaxInfluence(vert, self.skin)
            dict[owningJnt].append(vert)

        return dict

    def GetJntWithMaxInfluence(self, vert, skin):
        weights = mc.skinPercent(skin, vert, q=True, v=True)
        jnts = mc.skinPercent(skin, vert, q=True, t=None)

        maxWeightIndex = 0
        maxWeight = weights[0]

        for i in range(1, len(weights)):
            if weights[i] > maxWeight:
                maxWeight = weights[i]
                maxWeightIndex = i

        return jnts[maxWeightIndex]

class ProxyRiggerWidget(QMayaWindow):
    def __init__(self):
        super().__init__()
        self.proxyRigger = ProxyRigger()
        self.setWindowTitle("Proxy Rigger")
        self.masterLayout = QVBoxLayout()
        self.setLayout(self.masterLayout)
        generateProxyRigBtn = QPushButton("Generate Proxy Rig")
        self.masterLayout.addWidget(generateProxyRigBtn)
        generateProxyRigBtn.clicked.connect(self.GenerateProxyRigButtonClicked)

    def GenerateProxyRigButtonClicked(self):
        self.proxyRigger.CreateProxyRigFromSelectedMesh()

    def GetWindowHash(self):
        return "reydauuthdunanuudrajindahaad"

ProxyRiggerWidget = ProxyRiggerWidget()
ProxyRiggerWidget.show()