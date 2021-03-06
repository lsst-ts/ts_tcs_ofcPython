import os
import re
import numpy as np

from lsst.ts.ofc.Utility import InstName, DofGroup, getMatchFilePath, \
                                getDirFiles
from lsst.ts.ofc.ParamReader import ParamReader


class DataShare(object):

    def __init__(self):
        """Initialization of data share class."""

        self.configDir = ""
        self.instName = InstName.LSST

        self.zn3Idx = np.array([], dtype=int)
        self.dofIdx = np.array([], dtype=int)

        self._zkAndDofIdxArraySetFile = ParamReader()
        self._senMfile = ParamReader()
        self._mappingFile = ParamReader()
        self._idxDofFile = ParamReader()
        self._sensorIdToNameFile = ParamReader()

    def config(self, configDir, instName=InstName.LSST,
               zkAndDofIdxArraySetFileName="zkAndDofIdxArraySet.txt",
               mappingFileName="sensorNameToFieldIdx.txt",
               idxDofFileName="idxDOF.txt",
               sensorIdToNameFileName="sensorIdToName.txt"):
        """Do the configuration of DataShare class.

        zk: Annular Zernike polynomial.
        DOF: Degree of Freedom.

        Parameters
        ----------
        configDir : str
            Configuration directory.
        instName : enum 'InstName', optional
            Instrument name. (the default is InstName.LSST.)
        zkAndDofIdxArraySetFileName : str, optional
            File name of zk and DOF index array set. (the default is
            "zkAndDofIdxArraySet.txt".)
        mappingFileName : str, optional
            File name of mapping abbreviated sensor name to index of optical
            field.  (the default is "sensorNameToFieldIdx.txt".)
        idxDofFileName : str, optional
            Index of DOF file name. (the default is "idxDOF.txt".)
        sensorIdToNameFileName : str, optional
            Configuration file name to map sensor Id to name. (the default
            is "sensorIdToName.txt".)
        """

        self.configDir = configDir
        self.instName = instName

        zkAndDofIdxArraySetFilePath = os.path.join(configDir,
                                                   zkAndDofIdxArraySetFileName)
        self._zkAndDofIdxArraySetFile = ParamReader(
                                        filePath=zkAndDofIdxArraySetFilePath)

        mappingFilePath = os.path.join(self.getInstDir(), mappingFileName)
        self._mappingFile = ParamReader(filePath=mappingFilePath)

        idxDofFilePath = os.path.join(configDir, idxDofFileName)
        self._idxDofFile = ParamReader(filePath=idxDofFilePath)

        sensorIdToNameFilePath = os.path.join(configDir,
                                              sensorIdToNameFileName)
        self._sensorIdToNameFile = ParamReader(
                                        filePath=sensorIdToNameFilePath)

        senMfilePath = self._getSenMfilePath(reMatchStr=r"\AsenM\S+")
        self._senMfile = ParamReader(filePath=senMfilePath)

        self._readZn3AndDofIdxArray()

    def _readZn3AndDofIdxArray(self):
        """Read the Z3-Zn and DOF index arrays.

        DOF: degree of freedom.
        """

        arrayParamList = ["izn3", "icomp"]

        self.zn3Idx = self._zkAndDofIdxArraySetFile.getSetting("izn3",
                                                               arrayParamList)
        self.zn3Idx = self._getNonZeroIdxFronStrArray(self.zn3Idx)

        self.dofIdx = self._zkAndDofIdxArraySetFile.getSetting("icomp",
                                                               arrayParamList)
        self.dofIdx = self._getNonZeroIdxFronStrArray(self.dofIdx)

    def _getNonZeroIdxFronStrArray(self, strArray):
        """Get the non-zero index array from the string array.

        Parameters
        ----------
        strArray : str
            String array.

        Returns
        -------
        numpy.ndarray
            Non-zero index array.
        """

        array = np.array(strArray.split(), dtype=int)

        return self._getNonZeroIdx(array)

    def _getNonZeroIdx(self, array):
        """Get the non-zero index array.

        Parameters
        ----------
        array : numpy.ndarray or list
            Array to look for the non-zero index.

        Returns
        -------
        numpy.ndarray
            Non-zero index array.
        """

        return np.where(np.array(array) != 0)[0]

    def _getSenMfilePath(self, reMatchStr):
        """Get the sensitivity matrix M file path.

        Parameters
        ----------
        reMatchStr : str
            Matching string for the regular expression.

        Returns
        -------
        str
            Sensitivity matrix M file path.
        """

        filePaths = getDirFiles(self.getInstDir())
        senMFilePath = getMatchFilePath(reMatchStr, filePaths)

        return senMFilePath

    def getInstDir(self):
        """Get the instrument directory.

        Returns
        -------
        str
            Instrument directory.
        """

        return os.path.join(self.configDir, self.instName.name.lower())

    def getConfigDir(self):
        """Get the configuration directory.

        Returns
        -------
        str
            configuration directory.
        """

        return self.configDir

    def getSenM(self):
        """Get the sensitivity matrix M.

        The arrangement of M is (field #, zn #, dof #).

        Returns
        -------
        numpy.ndarray
            Sensitivity matrix M.
        """

        # Get the shape of sensitivity matrix M
        filePath = self._senMfile.getFilePath()
        fileName = os.path.basename(filePath)
        shape = self._getSenMshape(fileName)

        # Set the sensitivity matrix M
        senM = self._senMfile.getMatContent()
        senM = senM.reshape(shape)
        senM = senM[np.ix_(np.arange(shape[0]), self.zn3Idx, self.dofIdx)]

        return senM

    def _getSenMshape(self, senMFileName):
        """Get the shape of sensitivity matrix M.

        Parameters
        ----------
        senMFileName : str
            Sensitivity matrix M file name.

        Returns
        -------
        tuple
            Shape of sensitivity matrix M.

        Raises
        ------
        ValueError
            Cannot match the shape of M.
        """

        shape = None

        m = re.match(r"\S+_(\d+)_(\d+)_(\d+)\S+", senMFileName)
        if (m is not None):
            shape = m.groups()
            shape = tuple(map(int, shape))

        if shape is None:
            raise ValueError("Cannot match the shape of M.")

        return shape

    def getDofIdx(self):
        """Get the index array of degree of freedom (DOF).

        Returns
        -------
        numpy.ndarray
            Index array of DOF.
        """

        return self.dofIdx

    def getZn3Idx(self):
        """Get the index array of z3 to zn.

        Returns
        -------
        numpy.ndarray
            Index array of z3 to zn.
        """

        return self.zn3Idx

    def getFieldIdx(self, sensorNameList):
        """Get the list of field index based on the abbreviated sensor
        name (e.g. R22_S11) and mapping file.

        Parameters
        ----------
        sensorNameList : list
            List of abbreviated sensor name.

        Returns
        -------
        list
            Field index array.

        Raises
        ------
        TypeError
            The input type is not list.
        """

        fieldIdx = []
        if (self._inputIsList(sensorNameList)):
            for sensorName in sensorNameList:
                field = self._mappingFile.getSetting(sensorName)
                fieldIdx.append(int(field))

        return fieldIdx

    def _inputIsList(self, input):
        """Check the type of input is list or not.

        Parameters
        ----------
        input : obj
            Input.

        Returns
        -------
        bool
            True if the input's type is list.

        Raises
        ------
        TypeError
            The input type is not list.
        """

        inputIsList = True
        if (not isinstance(input, list)):
            inputIsList = False
            raise TypeError("The input type is '%s' instead of list."
                            % type(input))

        return inputIsList

    def getGroupIdxAndLeng(self, dofGroup):
        """Get the start index and length of specific group of degree of
        freedom (DOF).

        Parameters
        ----------
        dofGroup : enum 'DofGroup'
            DOF group.

        Returns
        -------
        int
            Start index of group.
        int
            Index length of group.

        Raises
        ------
        ValueError
            The input is not found in the idxDof file.
        """

        # Assign the parameter name
        if (dofGroup == DofGroup.M2HexPos):
            param = "M2_Hex_Pos"
        elif (dofGroup == DofGroup.CamHexPos):
            param = "Cam_Hex_Pos"
        elif (dofGroup == DofGroup.M1M3Bend):
            param = "M1M3_Bend"
        elif (dofGroup == DofGroup.M2Bend):
            param = "M2_Bend"
        else:
            raise ValueError("'%s' is not found in the '%s'."
                             % (dofGroup, self._idxDofFile.getFilePath()))

        # Get the values from the file
        startIdx, groupLeng = self._idxDofFile.getSetting(param)

        # Change the data type
        startIdx = int(startIdx)
        groupLeng = int(groupLeng)

        return startIdx, groupLeng

    def setZkAndDofIdxArrays(self, zn3Idx, dofIdx):
        """Set the index array of zn and degree of freedom (DOF).

        Parameters
        ----------
        zn3Idx : numpy.ndarray[int] or list[int]
            Index array of z3 to zn.
        dofIdx : numpy.ndarray[int] or list[int]
            Index array of DOF.
        """

        self.zn3Idx = np.array(zn3Idx, dtype=int)
        self.dofIdx = np.array(dofIdx, dtype=int)

    def setZkAndDofInGroups(self, zkToUse=np.ones(19, dtype=int),
                            m2HexPos=np.ones(5, dtype=int),
                            camHexPos=np.ones(5, dtype=int),
                            m1m3Bend=np.ones(20, dtype=int),
                            m2Bend=np.ones(20, dtype=int)):
        """Set the index array of Zk and DOF in groups (M2 hexapod,
        camera hexapod, M1M3 bending mode, and M2 bending mode).

        For the element in input index array, use 1 for True and 0 for
        False. For example, if the m2HexPos is [1, 1, 1, 0, 0], only the
        first three positions will be used.

        Parameters
        ----------
        zkToUse : numpy.ndarray[int] or list[int], optional
            z3 to zn. (the default is np.ones(19, dtype=int))
        m2HexPos : numpy.ndarray[int] or list[int], optional
            M2 hexapod position. (the default is np.ones(5, dtype=int))
        camHexPos : numpy.ndarray[int] or list[int], optional
            Camera hexapod position. (the default is np.ones(5, dtype=int))
        m1m3Bend : numpy.ndarray[int] or list[int], optional
            M1M3 bending mode. (the default is np.ones(20, dtype=int))
        m2Bend : numpy.ndarray[int] or list[int], optional
            M2 bending mode. (the default is np.ones(20, dtype=int))

        Raises
        ------
        ValueError
            The length of 'zkToUse' is incorrect.
        ValueError
            "The length of DOF is incorrect."
        """

        zn3Max = self._getZn3Max()
        if (len(zkToUse) != zn3Max):
            raise ValueError("The length of 'zkToUse' should be %d."
                             % zn3Max)

        # Get the index of zk to use
        zn3Idx = self._getNonZeroIdx(zkToUse)

        # Assign the order for the following iteration with zip
        dofInputs = [m2HexPos, camHexPos, m1m3Bend, m2Bend]

        dofIdx = np.array([], dtype=int)
        for dofInput, dofGroup in zip(dofInputs, DofGroup):
            startIdx, groupLeng = self.getGroupIdxAndLeng(dofGroup)

            if (len(dofInput) != groupLeng):
                raise ValueError("The length of DOF is incorrect.")

            idx = self._getNonZeroIdx(dofInput)
            dofIdx = np.append(dofIdx, idx+startIdx)

        self.setZkAndDofIdxArrays(zn3Idx, dofIdx)

    def _getZn3Max(self):
        """Get the number of terms of Z3 to Zn.

        Zn: Annular Zernike polynomial.

        Returns
        -------
        int
            Number of terms of Z3 to Zn.
        """

        zn3Max = self._zkAndDofIdxArraySetFile.getSetting("znmax")
        zn3Max = int(zn3Max)-3

        return zn3Max

    def getWfAndFieldIdFromFile(self, wfFilePath, sensorNameList):
        """Get the wavefront error and field Id from the file.

        Parameters
        ----------
        wfFilePath : str
            Wavefront error file path.
        sensorNameList : list[str]
            List of abbreviated sensor name.

        Returns
        -------
        numpy.ndarray
            Wavefront error.
        list
            Field index list.

        Raises
        ------
        ValueError
            Number of sensors does not match the file.
        """

        wfErr = np.loadtxt(wfFilePath)
        fieldIdx = self.getFieldIdx(sensorNameList)

        if (len(fieldIdx) != wfErr.shape[0]):
            raise ValueError("Number of sensors does not match the file.")

        return wfErr, fieldIdx

    def getWfAndFieldIdFromShwfsFile(self, wfFilePath, sensorName="R22_S11"):
        """Get the wavefront error and field Id from the SHWFS file.

        SHWFS: Shack-Hartmann wavefront sensor.

        Parameters
        ----------
        wfFilePath : str
            Wavefront error file path.
        sensorName : str, optional
            Sensor name. (the default is "R22_S11", which uses the central
            position of main camera. This is to get the sensitivity matrix.)

        Returns
        -------
        numpy.ndarray
            Wavefront error.
        list
            Field index array.
        """

        # Only z3 to zn is considered
        wfErr = np.loadtxt(wfFilePath, usecols=1)[3:]
        fieldIdx = self.getFieldIdx([sensorName])

        return wfErr, fieldIdx

    def mapSensorIdToName(self, sensorIdList):
        """Map the list of sensor Id to sensor name.

        If no sensor name is found for a specific Id, there will be no returned
        value.

        Parameters
        ----------
        sensorIdList : list[int]
            List of sensor Id.

        Returns
        -------
        list
            List of abbreviated sensor names.
        int
            Number of sensors.
        """

        sensorNameList = []
        for sensorId in sensorIdList:
            try:
                sensorName = self._sensorIdToNameFile.getSetting(str(sensorId))
                sensorNameList.append(sensorName)
            except ValueError:
                pass

        return sensorNameList, len(sensorNameList)

    def mapSensorNameToId(self, sensorNameList):
        """Map the array of sensor name to sensor Id.

        Parameters
        ----------
        sensorNameList : list[str]
            List of abbreviated sensor names.

        Returns
        -------
        list[int]
            List of sensor Id.
        """

        sensorIdList = []
        if self._inputIsList(sensorNameList):

            content = self._sensorIdToNameFile.getTxtContent()

            for sensorName in sensorNameList:
                sensorIdList.append(self._mapSensorNameToIdFromContent(
                                                     content, sensorName))

        return sensorIdList

    def _mapSensorNameToIdFromContent(self, content, sensorName):
        """Map the sensor name to Id based on the mapping content.

        Parameters
        ----------
        content : str
            File content.
        sensorName : str
            Abbreviated sensor name.

        Returns
        -------
        int
            Sensor Id.

        Raises
        ------
        ValueError
            Can not find the sensor Id of input sensor name.
        """

        sensorId = None
        for line in content.splitlines():
            line = line.strip()

            # Skip the comment or empty line
            if line.startswith("#") or (len(line) == 0):
                continue

            sensorIdInFile, sensorNameInFile = line.split()

            if (sensorNameInFile == sensorName):
                sensorId = int(sensorIdInFile)
                break

        if (sensorId is None):
            raise ValueError("Can not find the sensor Id of '%s'."
                             % sensorName)

        return sensorId


if __name__ == "__main__":
    pass
