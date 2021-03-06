import os
import numpy as np
import unittest

from lsst.ts.wep.Utility import FilterType

from lsst.ts.ofc.Utility import InstName, DofGroup, getModulePath
from lsst.ts.ofc.DataShare import DataShare
from lsst.ts.ofc.OptStateEstiDataDecorator import OptStateEstiDataDecorator
from lsst.ts.ofc.OptCtrlDataDecorator import OptCtrlDataDecorator
from lsst.ts.ofc.OptStateEsti import OptStateEsti
from lsst.ts.ofc.OptCtrl import OptCtrl
from lsst.ts.ofc.CamRot import CamRot
from lsst.ts.ofc.ZTAAC import ZTAAC


class TestZTAAC(unittest.TestCase):
    """Test the ZTAAC class."""

    def setUp(self):

        dataShare = DataShare()
        configDir = os.path.join(getModulePath(), "configData")
        dataShare.config(configDir, instName=InstName.LSST)

        optStateEstiData = OptStateEstiDataDecorator(dataShare)
        optStateEstiData.configOptStateEstiData()

        mixedData = OptCtrlDataDecorator(optStateEstiData)
        mixedData.configOptCtrlData(configFileName="optiPSSN_x00.ctrl")

        optStateEsti = OptStateEsti()
        optCtrl = OptCtrl()

        self.ztaac = ZTAAC(optStateEsti, optCtrl, mixedData)
        self.ztaac.config(filterType=FilterType.REF, defaultGain=0.7,
                          fwhmThresholdInArcsec=0.2)

    def testConfig(self):

        self.assertEqual(self.ztaac.getFilter(), FilterType.REF)
        self.assertEqual(self.ztaac.defaultGain, 0.7)
        self.assertEqual(self.ztaac.fwhmThresholdInArcsec, 0.2)

    def testMapSensorIdToName(self):

        sensorIdList = [1, 2, 3, 4]
        sensorNameList, numOfsensor = self.ztaac.mapSensorIdToName(
                                                        sensorIdList)
        self.assertEqual(sensorNameList,
                         ["R00_S21", "R00_S22", "R01_S00", "R01_S01"])
        self.assertEqual(numOfsensor, 4)

    def testMapSensorNameToId(self):

        sensorNameList = ["R00_S21", "R00_S22", "R01_S00", "R01_S01"]
        sensorIdList = self.ztaac.mapSensorNameToId(sensorNameList)
        self.assertEqual(sensorIdList, [1, 2, 3, 4])

    def testSetAndGetFilter(self):

        filterType = FilterType.Y
        self.ztaac.setFilter(filterType)
        self.assertEqual(self.ztaac.getFilter(), filterType)

    def testSetAndGetState0(self):

        state0 = [1, 2, 3, 4]
        self.ztaac.setState0(state0)

        state0InOpCtrl = self.ztaac.getState0()

        delta = np.sum(np.abs(state0InOpCtrl - np.array(state0)))
        self.assertEqual(delta, 0)

    def testSetStateToState0(self):

        state0 = [1, 2, 3, 4]
        self.ztaac.setState0(state0)
        self.ztaac.setStateToState0()

        delta = np.sum(np.abs(self.ztaac.optCtrl.state0InDof -
                              self.ztaac.optCtrl.stateInDof))
        self.assertEqual(delta, 0)
        self.assertNotEqual(id(self.ztaac.optCtrl.state0InDof),
                            id(self.ztaac.optCtrl.stateInDof))

    def testSetState0FromFile(self):

        self.ztaac.setState0FromFile(state0InDofFileName="state0inDof.txt")

        state0 = self.ztaac.getState0()
        self.assertEqual(len(state0), 50)
        self.assertEqual(np.sum(np.abs(state0)), 0)

    def testSetAndGetGainInUse(self):

        self.assertEqual(self.ztaac.getGainInUse(), 0)

        gain = 0.3
        self.ztaac.setGain(gain)

        self.assertEqual(self.ztaac.getGainInUse(), gain)

    def testSetGainByPssnWithGoodImageQuality(self):

        pssn = np.ones(31)
        self._setGainByPSSN(pssn)
        self.assertEqual(self.ztaac.getGainInUse(), self.ztaac.defaultGain)

    def testSetGainByPssnWithBadImageQuality(self):

        pssn = np.ones(31) * 0.2
        self._setGainByPSSN(pssn)
        self.assertEqual(self.ztaac.getGainInUse(), 1)

    def _setGainByPSSN(self, pssn):

        sensorIdList = [100, 103, 104, 105, 97, 96, 95, 140, 150, 109,
                        44, 46, 93, 180, 120, 118, 18, 45, 82, 183,
                        122, 116, 24, 40, 81, 179, 161, 70, 5, 33,
                        123]
        sensorNameList = self.ztaac.dataShare.mapSensorIdToName(
                                                        sensorIdList)[0]

        self.ztaac.setGainByPSSN(pssn, sensorNameList)

    def testGetWfFromFile(self):

        wfErr = self._getWfErrAndSensorNameListFromLsstFile()[0]

        self.assertEqual(wfErr.shape, (4, 19))

    def _getWfErrAndSensorNameListFromLsstFile(self):

        wfFilePath = os.path.join(getModulePath(), "tests", "testData",
                                  "lsst_wfs_error_iter0.z4c")
        sensorNameList = ["R44_S00", "R04_S20", "R00_S22", "R40_S02"]
        wfErr = self.ztaac.getWfFromFile(wfFilePath, sensorNameList)

        return wfErr, sensorNameList

    def _getWfErrAndSensorNameListFromComCamFile(self):

        wfFilePath = os.path.join(getModulePath(), "tests", "testData",
                                  "comcam_wfs_error_iter0.z4c")
        sensorNameList = ["R22_S00", "R22_S01", "R22_S02", "R22_S10",
                          "R22_S11", "R22_S12", "R22_S20", "R22_S21",
                          "R22_S22"]
        wfErr = self.ztaac.getWfFromFile(wfFilePath, sensorNameList)

        return wfErr, sensorNameList

    def testGetWfFromShwfsFile(self):

        wfFilePath = os.path.join(getModulePath(), "tests", "testData",
                                  "shwfs_wfs_error.txt")
        wfErr, sensorName = self.ztaac.getWfFromShwfsFile(wfFilePath)

        self.assertEqual(len(wfErr), 19)
        self.assertEqual(sensorName, "R22_S11")

    def testEstiUkWithGainOfLsst(self):

        gainToUse = 0.9

        self._setStateAndState0FromFile()
        self.ztaac.setGain(gainToUse)

        wfErr, sensorNameList = self._getWfErrAndSensorNameListFromLsstFile()
        uk = self.ztaac.estiUkWithGain(wfErr, sensorNameList)

        ansFilePath = os.path.join(getModulePath(), "tests", "testData",
                                   "lsst_pert_iter1.txt")
        ukAns = gainToUse * np.loadtxt(ansFilePath, usecols=1)

        delta = np.sum(np.abs(uk - ukAns))
        self.assertLess(delta, 0.0012)

    def testEstiUkWithGainOfComCam(self):

        dataShare = DataShare()
        configDir = os.path.join(getModulePath(), "configData")
        dataShare.config(configDir, instName=InstName.COMCAM)

        optStateEstiData = OptStateEstiDataDecorator(dataShare)
        optStateEstiData.configOptStateEstiData()

        mixedData = OptCtrlDataDecorator(optStateEstiData)
        mixedData.configOptCtrlData(configFileName="optiPSSN_x00.ctrl")

        optStateEsti = OptStateEsti()
        optCtrl = OptCtrl()

        self.ztaac = ZTAAC(optStateEsti, optCtrl, mixedData)
        self.ztaac.config(filterType=FilterType.REF, defaultGain=0.7,
                          fwhmThresholdInArcsec=0.2)

        self._setStateAndState0FromFile()

        gainToUse = 1
        self.ztaac.setGain(gainToUse)

        wfErr, sensorNameList = self._getWfErrAndSensorNameListFromComCamFile()
        uk = self.ztaac.estiUkWithGain(wfErr, sensorNameList)

        ansFilePath = os.path.join(getModulePath(), "tests", "testData",
                                   "comcam_pert_iter1.txt")
        ukAns = gainToUse * np.loadtxt(ansFilePath, usecols=1)

        delta = np.sum(np.abs(uk - ukAns))
        self.assertLess(delta, 0.0012)

    def _setStateAndState0FromFile(self):

        self.ztaac.setState0FromFile(state0InDofFileName="state0inDof.txt")
        self.ztaac.setStateToState0()

    def testAggState(self):

        calcDof = dofIdx = np.arange(len(self.ztaac.dataShare.getDofIdx()))
        self._setStateAndState0FromFile()
        self.ztaac.aggState(calcDof)

        delta = np.sum(np.abs(self.ztaac.optCtrl.getState(dofIdx) - calcDof))
        self.assertEqual(delta, 0)

    def testAggStateWithUserDefinedIdx(self):

        self._setStateAndState0FromFile()

        m2HexPos = np.zeros(5, dtype=int)
        m2HexPos[[0, 2]] = 1

        camHexPos = np.zeros(5, dtype=int)
        camHexPos[[0, 3]] = 1

        m1m3Bend = np.zeros(20, dtype=int)
        m1m3Bend[[0, 2]] = 1

        m2Bend = np.zeros(20, dtype=int)
        m2Bend[[0, 3]] = 1

        self.ztaac.setZkAndDofInGroups(m2HexPos=m2HexPos, camHexPos=camHexPos,
                                       m1m3Bend=m1m3Bend, m2Bend=m2Bend)

        calcDof = np.arange(1, 9)
        self.ztaac.aggState(calcDof)

        m2HexPosInZTAAC = self.ztaac.getGroupDof(DofGroup.M2HexPos)
        camHexPosInZTAAC = self.ztaac.getGroupDof(DofGroup.CamHexPos)
        m1m3BendInZTAAC = self.ztaac.getGroupDof(DofGroup.M1M3Bend)
        m2BendInZTAAC = self.ztaac.getGroupDof(DofGroup.M2Bend)

        m2HexPosAns = np.zeros(m2HexPos.shape)
        m2HexPosAns[[0, 2]] = [1, 2]
        camHexPosAns = np.zeros(camHexPos.shape)
        camHexPosAns[[0, 3]] = [3, 4]
        m1m3BendAns = np.zeros(m1m3Bend.shape)
        m1m3BendAns[[0, 2]] = [5, 6]
        m2BendAns = np.zeros(m2Bend.shape)
        m2BendAns[[0, 3]] = [7, 8]

        self.assertEqual(np.sum(np.abs(m2HexPosAns - m2HexPosInZTAAC)), 0)
        self.assertEqual(np.sum(np.abs(camHexPosAns - camHexPosInZTAAC)), 0)
        self.assertEqual(np.sum(np.abs(m1m3BendAns - m1m3BendInZTAAC)), 0)
        self.assertEqual(np.sum(np.abs(m2BendAns - m2BendInZTAAC)), 0)

    def testGetGroupDofWithoutInputDof(self):

        state0 = np.ones(len(self.ztaac.dataShare.getDofIdx()))
        self.ztaac.setState0(state0)
        self.ztaac.setStateToState0()

        calcDof = np.arange(len(self.ztaac.dataShare.getDofIdx()))
        self.ztaac.aggState(calcDof)

        dof = self.ztaac.getGroupDof(DofGroup.CamHexPos, inputDof=None)
        ans = np.arange(5, 10)
        delta = np.sum(np.abs(dof - ans))
        self.assertEqual(delta, 0)

    def testGetGroupDofWithInputDof(self):

        calcDof = np.arange(3, len(self.ztaac.dataShare.getDofIdx())+3)

        dof = self.ztaac.getGroupDof(DofGroup.CamHexPos, inputDof=calcDof)
        ans = np.arange(8, 13)
        delta = np.sum(np.abs(dof - ans))
        self.assertEqual(delta, 0)

    def testSetZkAndDofInGroups(self):

        zkToUse = np.ones(19, dtype=int)
        zkToUse[2] = 0

        camHexPos = np.ones(5, dtype=int)
        camHexPos[3] = 0

        self.ztaac.setZkAndDofInGroups(zkToUse=zkToUse,
                                       camHexPos=camHexPos)

        self.assertNotIn(2, self.ztaac.dataShare.getZn3Idx())
        self.assertNotIn(8, self.ztaac.dataShare.getDofIdx())

    def testRotUk(self):

        camRot = CamRot()
        camRot.setRotAng(45)

        uk = np.ones(len(self.ztaac.dataShare.getDofIdx()))

        self._setStateAndState0FromFile()
        rotUk = self.ztaac.rotUk(camRot, uk)

        self.assertAlmostEqual(rotUk[2], 1.41421356)


if __name__ == "__main__":

    # Run the unit test
    unittest.main()
