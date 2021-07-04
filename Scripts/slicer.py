# making proxy/ sliced/ cut-out rig script made by Truong Cg Artist
# gumroad.com/TruongCgArtist
# thank you Trong Hoan for supporting me during the process of making this script
# facebook.com/dauphairigging

import maya.cmds as cmds
from math import pow, sqrt
import maya.OpenMaya as OpenMaya
import pymel.core as pm
import re

bodyMesh = None
reducePercent = 50
bodyMeshTF = "body_mesh_text_field"
trsUI_ID = "Proxy_Making_script_by_Truong"
mainControl = None
mainControl_tf = "Main_control_text_field"

def autoRenamingDuplicateObjects():
    # find and auto fix the all items that have same name

    # this function is from Erwan Leroy erwanleroy.com/maya-python-renaming-duplicate-objects
    # Find all objects that have the same shortname as another
    # We can indentify them because they have | in the name
    duplicates = [f for f in cmds.ls() if '|' in f]
    # Sort them by hierarchy so that we don't rename a parent before a child.
    duplicates.sort(key=lambda obj: obj.count('|'), reverse=True)

    # if we have duplicates, rename them

    if duplicates:
        for name in duplicates:
            # extract the base name
            m = re.compile("[^|]*$").search(name)
            shortname = m.group(0)

            # extract the numeric suffix
            m2 = re.compile(".*[^0-9]").match(shortname)
            if m2:
                stripSuffix = m2.group(0)
            else:
                stripSuffix = shortname

            # rename, adding '#' as the suffix, which tells maya to find the next available number
            newname = cmds.rename(name, (stripSuffix + "#"))
            print("renamed %s to %s" % (name, newname))

        return "Renamed %s objects with duplicated name." % len(duplicates)
    else:
        return "No Duplicates"

# function to calculate distance between to objects
def getDistance(objA, objB):
    gObjA = cmds.xform(objA, q=True, t=True, ws=True)
    gObjB = cmds.xform(objB, q=True, t=True, ws=True)

    return sqrt(pow(gObjA[0] - gObjB[0], 2) + pow(gObjA[1] - gObjB[1], 2) + pow(gObjA[2] - gObjB[2], 2))

# get direction vector, then normalize. This code is from Paul from Techart
def placeNodeAtOffset(objA, objB, percent, node):
    pt1 = cmds.xform(objA, q=True, rp=True, ws=True)
    pt2 = cmds.xform(objB, q=True, rp=True, ws=True)
    distance = getDistance(objA, objB)
    offset = percent*distance
    V1 = OpenMaya.MVector(*pt1)
    V2 = OpenMaya.MVector(*pt2)
    V3 = (V1 - V2).normal()
    V4 = V2 + V3*offset

    cmds.move(V4.x, V4.y, V4.z, node)

def getClosestVert(bodyMesh, currentJoint):
    geo = pm.PyNode(bodyMesh) # user input (from UI) needed!
    fPG = pm.PyNode(currentJoint) # convert to PyNode
    pos = fPG.getRotatePivot(space='world')

    nodeDagPath = OpenMaya.MObject()
    try:
        selectionList = OpenMaya.MSelectionList()
        selectionList.add(geo.name())
        nodeDagPath = OpenMaya.MDagPath()
        selectionList.getDagPath(0, nodeDagPath)
    except:
        raise RuntimeError('OpenMaya.MDagPath() failed on %s' % geo.name())

    mfnMesh = OpenMaya.MFnMesh(nodeDagPath)

    pointA = OpenMaya.MPoint(pos.x, pos.y, pos.z)
    pointB = OpenMaya.MPoint()
    space = OpenMaya.MSpace.kWorld

    util = OpenMaya.MScriptUtil()
    util.createFromInt(0)
    idPointer = util.asIntPtr()

    mfnMesh.getClosestPoint(pointA, pointB, space, idPointer)
    idx = OpenMaya.MScriptUtil(idPointer).asInt()

    faceVerts = [geo.vtx[i] for i in geo.f[idx].getVertices()]
    closestVert = None
    minLength = None
    for v in faceVerts:
        thisLength = (pos - v.getPosition(space='world')).length()
        if minLength is None or thisLength < minLength:
            minLength = thisLength
            closestVert = v
    return str(closestVert)

# function to get the farthest child joint distance >> use this for the length of cylinder (if have child joint)
def getCylinderHeight(currentJoint):
    childJoint = findCorrectChildJnt(currentJoint)
    cylinderHeight = getDistance(childJoint, currentJoint)
    print cylinderHeight
    return cylinderHeight

# function to get farthest point to joint (in any direction) >> use this for cylinder radios later
def getCylinderRadios(currentJoint):
    global bodyMesh
    # find child jnt
    childJoint = findCorrectChildJnt(currentJoint)
    locList = []
    if childJoint:
        percentList = [0.0, 0.25, 0.5, 0.75, 1.0]
        maxDistance = 0.0
        for p in percentList:
            loc = cmds.spaceLocator()
            print loc
            locList.append(loc[0])
            placeNodeAtOffset(currentJoint, childJoint, p, loc[0])
            closestVer = getClosestVert(bodyMesh, loc[0])
            distance = getDistance(loc[0], closestVer)
            if distance >= maxDistance:
                maxDistance = distance
        radius = maxDistance*165/100
        cmds.delete(locList)
    else:
        radius = 0.0
    return radius

# having problem with 11 and 1 in numbering joints
def searchSimilarJoints(currentJoint):
    allJoint = cmds.ls(type="joint")
    currentJointNameLength = len(currentJoint)
    for lastIndex in range(currentJointNameLength):
        print lastIndex
        if lastIndex != 0:
            tripOffName = currentJoint[0:-lastIndex]
            # what if it finds up to "horse"? 3 is a safe number ... for now
            if lastIndex > 3:
                return None
                break
            print tripOffName
            similarObjList = cmds.ls(tripOffName + "*", type="joint")
            print similarObjList
            if similarObjList:
                maxRange = len(similarObjList)
                currentJntIndex = similarObjList.index(currentJoint)
                print currentJntIndex
                if currentJntIndex < maxRange:
                    nextJoint = similarObjList[currentJntIndex + 1]
                    if nextJoint:
                        print nextJoint
                        return nextJoint
                    else:
                        print "no more child joint"
                        return None
                break

# Need a better way to find correct child joint
def pathLength(joint):
    fullPath = cmds.ls(joint, long=1)[0]
    fullPathList = fullPath.split("|")
    pathLength = len(fullPathList)-1
    return pathLength

def minLength(joint_list):
    min = 999999
    for jnt in joint_list:
        length = pathLength(jnt)
        if length <= min:
            min = length
    return min

def findCorrectChildJnt(currentJnt):
    childrenJointList = cmds.listRelatives(currentJnt, children=1, allDescendents=1, type="joint")
    print childrenJointList
    if childrenJointList:
        firstLevelChildJointLength = minLength(childrenJointList)
        firstLevelChildJntList=[]
        for child in childrenJointList:
            if pathLength(child) == firstLevelChildJointLength:
                firstLevelChildJntList.append(child)
        print firstLevelChildJntList
        return firstLevelChildJntList[0] # assume the first one is the right child, will fail if this is not the case
    else:
        return None
        # print "Looking for similar joints"
        # searchSimilarJoints(currentJnt)

# Create cylinders + get orientation (aim constraint to joint child) + get radius and length above
# >> move cylinder up 1/2 length >> freeze transform
# then parent constraint the cylinder to joint. Stop there for further adjustments from user
def createCylinders(mesh):
    if not (cmds.objExists("CutMesh_Grp")):
        cmds.group(em=True, name="CutMesh_Grp")

    autoRenamingDuplicateObjects()

    # get joint list from selected model
    jointList = cmds.skinCluster(mesh, q=True, inf=True)

    # still cannot get tail joint with ribbon setup

    for jnt in jointList:
        print jnt
        # need check if there is child joint
        checkHavingChildJntList = cmds.listRelatives(jnt, children=True, allDescendents=1, type="joint")
        if checkHavingChildJntList:
            cylinderRadius = getCylinderRadios(jnt)
            cylinderHeight = getCylinderHeight(jnt)
            polyCyl = cmds.polyCylinder(height=cylinderHeight, radius=cylinderRadius, name=jnt+"_cut")
            # move up 1/2 height
            cmds.xform(polyCyl, t=[0, cylinderHeight/2, 0], r=True)
            # move pivot to 0 0 0
            cmds.xform(polyCyl, pivots=[0, 0, 0], ws=True)
            # freeze transform
            cmds.makeIdentity(polyCyl, apply=True)
            # parent constraint to the current joint
            parentCon = cmds.parentConstraint(jnt, polyCyl, mo=0)
            cmds.delete(parentCon)
            # aim constraint to orient, then delete this constraint >>> This one will fail
            childJoints = findCorrectChildJnt(jnt)
            # usually the correct orient is the fist child joint. This is a temporary solution
            aimCon = cmds.aimConstraint(childJoints, polyCyl, mo=0, aim=[0, 1, 0])
            cmds.delete(aimCon)
            cmds.parent(polyCyl[0], "CutMesh_Grp")

def createLoftMeshes(mesh):
    if not (cmds.objExists("CutMesh_Grp")):
        cmds.group(em=True, name="CutMesh_Grp")

    autoRenamingDuplicateObjects()

    # get joint list from selected model
    jointList = cmds.skinCluster(mesh, q=True, inf=True)
    if not (cmds.objExists("Curves_Grp")):
        cmds.group(em=True, name="Curves_Grp")

    for jnt in jointList:
        print jnt
        # need check if there is child joint
        checkHavingChildJntList = cmds.listRelatives(jnt, children=True, allDescendents=1, type="joint")
        if checkHavingChildJntList:
            # find child jnt
            childJoint = findCorrectChildJnt(jnt)

            curveList = []
            percentList = [0.0, 0.25, 0.5, 0.75, 1.0]
            # create 5 curves and move them along 0, 25%, 50%, 75%, 100% in the vector between 2 joints above
            for p in percentList:
                c = cmds.circle()
                curveList.append(c[0])
                placeNodeAtOffset(jnt, childJoint, p, c[0])
                # get distance of each curve to mesh surface for this curve's radius (update after create)
                closestVer = getClosestVert(mesh, c[0])
                radius = getDistance(c[0], closestVer)*165/100
                cmds.setAttr(c[1]+".radius", radius)
                if p == percentList[0]:
                    # for the last curve, aim to the parent joint
                    aimCon = cmds.aimConstraint(jnt, c[0], mo=0, aim=[0, 0, 1])
                    cmds.delete(aimCon)
                else:
                    # aim constraint the curve to the next joint, then delete the constraint
                    aimCon = cmds.aimConstraint(childJoint, c[0], mo=0, aim=[0, 0, -1])
                    cmds.delete(aimCon)
                cmds.parent(c[0], "Curves_Grp")

            # store first curve pivot
            firstCurvePivot = cmds.xform(curveList[-1], q=True, rp=True, ws=True)
            # store original Rotation
            oldRotation = cmds.xform(curveList[-1], q=True, rotation=True, ws=True)
            # this is for matching orientation of the pivot of proxy mesh & first curve/ jnt
            pivotGrp = cmds.group(em=True, world=True)
            # constraint to snap the pivotGrp to the first Curve
            firstCurveConstraint = cmds.parentConstraint(curveList[-1], pivotGrp, mo=0)
            cmds.delete(firstCurveConstraint)
            # parent all 5 curves under pivotGrp
            cmds.parent(curveList, pivotGrp)
            # zero out rotation, so the loft mesh will be straight up
            cmds.xform(pivotGrp, ws=True, rotation=[90, 0, 0])
            # loft 5 curves to make a loft mesh
            cmds.select(curveList, r=True)
            loftAction=cmds.loft(polygon=1, name=jnt+"_cut")
            # flip normal
            cmds.polyNormal(loftAction[0], normalMode=0)
            # close hole
            cmds.polyCloseBorder(loftAction[0])
            # match the pivot of loft mesh to the first curve
            cmds.xform(loftAction[0], rp=firstCurvePivot, ws=1)
            # parent loftMesh under pivotGrp
            cmds.parent(loftAction[0], pivotGrp)
            # delete history the loft mesh
            cmds.delete(loftAction[0], ch=True)
            # get back the rotation for pivotGrp
            cmds.xform(pivotGrp, rotation=oldRotation, ws=True)
            # parent loft meshes to Loft_Meshes_Grp
            cmds.parent(loftAction[0], "CutMesh_Grp")
            # delete pivot grp
            cmds.delete(pivotGrp)
    # delete Curves Grp
    cmds.delete("Curves_Grp")

def renameCut(mesh, side):
    newSide = None
    meshName = list(mesh.split(side))[0]
    print meshName
    if side == "_R_":
        newSide = "_L_"
    if side == "_L_":
        newSide = "_R_"
    print newSide
    newName = meshName + newSide + "cut"
    print newName
    return newName

def mirrorScale(mesh, newMeshName):
    if cmds.objExists(newMeshName):
        cmds.delete(newMeshName)
    cmds.duplicate(mesh, name=newMeshName)
    cmds.select(clear=True)
    tempGrp = cmds.group(empty=1)
    cmds.parent(newMeshName, tempGrp)
    cmds.xform(tempGrp, scale=[-1, 1, 1])
    if cmds.objExists("CutMesh_Grp"):
        cmds.parent(newMeshName, "CutMesh_Grp")
    else:
        raise Exception("There is no CutMesh_Grp")
    cmds.delete(tempGrp)

def mirrorSelectedCut():
    cut_mesh_list = cmds.ls(sl=1)
    for mesh in cut_mesh_list:
        if "_R_" in mesh:
            newMeshName = renameCut(mesh, "_R_")
            mirrorScale(mesh, newMeshName)
        if "_L_" in mesh:
            newMeshName = renameCut(mesh, "_L_")
            mirrorScale(mesh, newMeshName)
        else:
            print ("This is a middle mesh")
        cmds.select(mesh, r=1)

def setReducePercent(percent):
    global reducePercent
    reducePercent = percent
    print reducePercent

def reduceMainMesh():
    global bodyMesh
    # get joint list from main model
    jointList = cmds.skinCluster(bodyMesh, q=True, inf=True)
    print jointList
    newOriginal = cmds.duplicate(bodyMesh, rr=1)[0]
    print newOriginal
    cmds.hide(bodyMesh)
    cmds.polyReduce(newOriginal, keepQuadsWeight=1, percentage=reducePercent, triangulate=0, ch=0)
    cmds.skinCluster(newOriginal, jointList, tsb=1, sm=0)
    bodyMesh = newOriginal
    print bodyMesh
    return bodyMesh

# loop through cylinder mesh in Cylinders_Grp >> duplicate mesh >> boolean the mesh
def makeBooleans():
    global bodyMesh
    if not (cmds.objExists("CutMesh_Grp")):
        raise Exception("Please create cylinder meshes first!")
    if not (cmds.objExists("Proxy_Grp")):
        cmds.group(em=True, name="Proxy_Grp")
    cutMesh_list = cmds.listRelatives("CutMesh_Grp", children=True)
    print cutMesh_list
    for cutMesh in cutMesh_list:
        print cutMesh
        dupMesh = cmds.duplicate(bodyMesh, rr=True, name=bodyMesh+'_for_'+cutMesh)[0]
        print dupMesh
        proxy = cmds.polyBoolOp(cutMesh, dupMesh, operation=3, name=cutMesh+"_proxy")
        cmds.delete(proxy[0], ch=True)
        cmds.parent(proxy[0], "Proxy_Grp")
        if cmds.objExists(dupMesh):
            cmds.delete(dupMesh)
        cmds.refresh()

def setMainControl():
    global mainControl
    mainControl = cmds.ls(sl=True)[-1]
    load_selected_as(mainControl, mainControl_tf)

# constraint to joint by names
def constraintProxy():
    if not (cmds.objExists("Proxy_Grp")):
        raise Exception("Please create proxy meshes first!")
    proxy_list = cmds.listRelatives("Proxy_Grp", children=True)
    for proxy in proxy_list:
        jntName = proxy.split("_cut_proxy")[0]
        cmds.parentConstraint(jntName, proxy, mo=True)
        if mainControl:
            cmds.scaleConstraint(mainControl, proxy, mo=True)

def parentProxy():
    if not (cmds.objExists("Proxy_Grp")):
        raise Exception("Please create proxy meshes first!")
    proxy_list = cmds.listRelatives("Proxy_Grp", children=True)
    for proxy in proxy_list:
        jntName = proxy.split("_cut_proxy")[0]
        cmds.parent(proxy, jntName)

def load_selected_as(sel, text_field):
    text_field = cmds.textField(text_field, e=True, tx=str(sel))

def chooseBodyMesh():
    global bodyMesh
    bodyMeshList= cmds.ls(sl=True)
    if not bodyMeshList:
        raise Exception("Please select something")
    if len(bodyMeshList)>1:
        raise Exception("Please choose 1 mesh only!")
    bodyMesh = bodyMeshList[0]
    bodyMeshShape = cmds.listRelatives(bodyMesh, s=True, ni=True, f=True)
    bodyMeshNodeType = cmds.nodeType(bodyMeshShape)
    if bodyMeshNodeType != "mesh":
        raise Exception("Please select mesh type object!")
    load_selected_as(bodyMesh, bodyMeshTF)
    cmds.select(clear=True)
    print bodyMesh
    return bodyMesh

def show_UI(winID):
    if cmds.window(winID, exists=True):
        cmds.deleteUI(winID)
    cmds.window(winID)
    create_UI(winID)
    cmds.showWindow(winID)

def create_UI(winID):
    cmds.window(winID, e=True, width=250, height=410)
    main_lo = cmds.columnLayout(p=winID)
    cmds.text("\n Select Character Mesh then hit the button: \n")
    cmds.button(label="Mesh*", width=250, command='chooseBodyMesh()')
    cmds.textField(bodyMeshTF, width=250, ed=False)

    cmds.separator(height=10, p=main_lo)

    cyl_loft_row_lo = cmds.rowLayout(p=main_lo, nc=3)
    cmds.button(label="Create Cylinders", width=114, command='createCylinders(bodyMesh)', p=cyl_loft_row_lo)
    cmds.text(" or ", p=cyl_loft_row_lo)
    cmds.button(label="Create Loft Meshes", width=114, command='createLoftMeshes(bodyMesh)', p=cyl_loft_row_lo)
    cmds.button(label="Mirror Selected Meshes", command='mirrorSelectedCut()', width=250, p=main_lo)

    cmds.text("\n Please adjust further to cover your character,", p=main_lo)
    cmds.text(" Delete unused cylinders/ loft meshes, then: \n", p=main_lo)

    cmds.separator(height=10, p=main_lo, width=250)

    reduce_lo = cmds.rowLayout(p=main_lo, nc=3)
    cmds.text(label=" Reduce Main Mesh** (%):")
    percent = cmds.intField()
    cmds.intField(percent, e=True, changeCommand=setReducePercent, w=50)
    reduce_btn = cmds.button(label="Reduce", c='reduceMainMesh()', w=50)

    cmds.text("** Optional/ Fix failed Boolean Operation", p=main_lo)

    cmds.separator(height=10, p=main_lo, width=250)
    cmds.separator(height=10, p=main_lo)

    cmds.button(label="Create Proxy Meshes", width=250, command='makeBooleans()', p=main_lo)

    cmds.separator(height=10, p=main_lo)

    set_main_row_lo = cmds.rowLayout(p=main_lo, nc=3)
    cmds.text(" Load Main Control:")
    cmds.textField(mainControl_tf, ed=False)
    set_main_btn = cmds.button(label=">>", c='setMainControl()', width=25)

    parent_options_row_lo = cmds.rowLayout(p=main_lo, nc=3)
    cmds.button(label="Constraint To Joints", width=114, command='constraintProxy()', p=parent_options_row_lo)
    cmds.text(" or ", p=parent_options_row_lo)
    cmds.button(label="Parent Under Joints", width=114, command='parentProxy()', p=parent_options_row_lo)

    cmds.separator(height=10, p=main_lo)

    hide_show_row_lo = cmds.rowLayout(p=main_lo, nc=2)
    cmds.button(label="Hide Original Mesh", width=123, command='cmds.hide(bodyMesh)', p=hide_show_row_lo)
    cmds.button(label="Show Original Mesh", width=123, command='cmds.showHidden(bodyMesh)', p=hide_show_row_lo)
    cmds.text("\n * Click again if you close the tool mid way \n", p=main_lo)
show_UI(trsUI_ID)

