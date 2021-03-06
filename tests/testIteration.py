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
from lsst.ts.ofc.ZTAAC import ZTAAC
from lsst.ts.ofc.CamRot import CamRot
from lsst.ts.ofc.IterDataReader import IterDataReader


class TestIteration(unittest.TestCase):
    """Test the iteration."""

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

        self.ztaac.setState0FromFile(state0InDofFileName="state0inDof.txt")
        self.ztaac.setStateToState0()

        self.camRot = CamRot()
        self.camRot.setRotAng(0)

        iterDataDir = os.path.join(getModulePath(), "tests", "testData",
                                   "iteration")
        self.iterDataReader = IterDataReader(iterDataDir)

    def testIteration(self):

        sensorIdList = self.iterDataReader.getWfsSensorIdList()
        sensorNameList = self.ztaac.mapSensorIdToName(sensorIdList)[0]

        pssnIdList = self.iterDataReader.getPssnSensorIdList()
        pssnSensorNameList = self.ztaac.mapSensorIdToName(pssnIdList)[0]

        maxIterNum = 5
        for iterNum in range(0, maxIterNum):

            pssn = self.iterDataReader.getPssn(iterNum)
            self.ztaac.setGainByPSSN(pssn, pssnSensorNameList)

            wfErr = self.iterDataReader.getWfsErr(iterNum)
            uk = self.ztaac.estiUkWithGain(wfErr, sensorNameList)

            rotUk = self.ztaac.rotUk(self.camRot, uk)
            self.ztaac.aggState(rotUk)

            # Collect the DOF for the comparison
            dof = []
            for dofGroup in DofGroup:
                # Get the DOF for each group
                dofOfGroup = self.ztaac.getGroupDof(dofGroup)
                dof = np.append(dof, dofOfGroup)
            dof += self.ztaac.getState0()

            # Read the answer of DOF in the test file. The calculated DOF
            # is applied to the next iteration/ visit. This is why we read
            # the data in "iterNum + 1" instead of "iterNum".
            dofAns = self.iterDataReader.getDof(iterNum + 1)

            delta = np.sum(np.abs(dof - dofAns))
            self.assertLess(delta, 0.002)


if __name__ == "__main__":

    # Run the unit test
    unittest.main()
