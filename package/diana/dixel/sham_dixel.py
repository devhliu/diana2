import logging
import hashlib
from datetime import datetime
from dateutil import parser as DatetimeParser
import attr
from . import Dixel
from ..utils.gateways import orthanc_id
from ..utils.guid import GUIDMint
from ..utils.dicom import dicom_date, dicom_name, dicom_datetime, DicomLevel, DicomUIDMint
from ..utils.dicom.uid_mint import hash_str

def mktime(datestr, timestr=""):
    if not datestr and not timestr:
        return
    # Parser does not like fractional seconds
    timestr = timestr.split(".")[0]
    dt_str = datestr + timestr
    # logging.debug(dt_str)
    dt = DatetimeParser.parse(dt_str)
    return dt

# TODO: Minor reformat to handle pre-shammed Dixels, ie, don't assume sham_info must be created

@attr.s(cmp=False, hash=False)
class ShamDixel(Dixel):

    REFERENCE_DATE = None
    ShamUID = DicomUIDMint()

    @classmethod
    def from_dixel(cls, dixel: Dixel, salt: str=None):
        # Force the new instance to keep its own copy of any data
        _meta = dict(dixel.meta)
        _tags = dict(dixel.tags)
        sh = ShamDixel(
            meta=_meta,
            tags=_tags,
            salt=salt,
            level=dixel.level
        )
        if dixel.file:
            sh.file = dixel.file
        if dixel.pixels is not None:
            sh.pixels = dixel.pixels
        return sh


    salt = attr.ib(default=None, type=str)
    sham_info = attr.ib(init=False, repr=False)

    @sham_info.default
    def set_sham_info(self):

        logging.debug(self)

        name = self.tags.get("PatientName")
        if self.salt:
            name = "{}+{}".format(name, self.salt)

        sham_info = GUIDMint.get_sham_id(
            name=name,
            dob=self.tags.get("PatientBirthDate"),
            age=self.meta.get("Age"),
            gender=self.tags.get("PatientSex", "U"),
            reference_date=self.REFERENCE_DATE
        )

        return sham_info

    def __attrs_post_init__(self):
        self.simplify_tags()  # Create meta dts
        self.update_shams()

    def update_shams(self):

        self.meta["ShamID"] = self.sham_info["ID"]
        self.meta["ShamName"] = dicom_name(self.sham_info["Name"])
        self.meta["ShamBirthDate"] = dicom_date(self.sham_info["BirthDate"])

        # if self.tags.get("AccessionNumber"):
        anum = self.tags.get("AccessionNumber") or self.tags.get("StudyInstanceUID")
        if self.salt:
            anum = "{}+{}".format(anum, self.salt)
        self.meta["ShamAccessionNumber"] = \
            hashlib.md5(anum.encode("UTF-8")).hexdigest()

        if self.meta.get("StudyDateTime"):
           self.meta["ShamStudyDateTime"] = self.meta.get("StudyDateTime") + self.sham_info['TimeOffset']

        if self.level >= DicomLevel.SERIES and \
                self.meta.get("SeriesDatetime"):
            self.meta["ShamSeriesDateTime"] = self.meta.get("SeriesDateTime") + self.sham_info['TimeOffset']

        if self.level >= DicomLevel.INSTANCES and \
                self.tags.get("InstanceDateTime"):
            self.meta["ShamInstanceCreationDateTime"] = self.tags.get("InstanceDateTime") + \
                                                        self.sham_info['TimeOffset']
    def ShamStudyDate(self):
        if self.meta.get("ShamStudyDateTime"):
            ssdt = self.meta.get("ShamStudyDateTime")
            # print(ssdt)
            if not isinstance(ssdt, datetime):
                ssdt = mktime(ssdt)
            # print(ssdt)
            return dicom_datetime(ssdt)[0]

    def ShamStudyTime(self):
        if self.meta.get("ShamStudyDateTime"):
            ssdt = self.meta.get("ShamStudyDateTime")
            # print(ssdt)
            if not isinstance(ssdt, datetime):
                ssdt = mktime(ssdt)
            # print(ssdt)
            return dicom_datetime(ssdt)[1]

    def ShamSeriesDate(self):
        if self.meta.get("ShamSeriesDateTime"):
            return dicom_datetime(self.meta["ShamSeriesDateTime"])[0]

    def ShamSeriesTime(self):
        if self.meta.get("ShamStudyDateTime"):
            return dicom_datetime(self.meta["ShamSeriesDateTime"])[1]

    def ShamStudyUID(self):
        return ShamDixel.ShamUID.uid(PatientID=self.meta["ShamID"],
                         StudyInstanceUID=self.meta["ShamAccessionNumber"])

    def ShamSeriesUID(self):
        return ShamDixel.ShamUID.uid(PatientID=self.meta["ShamID"],
                         StudyInstanceUID=self.meta["ShamAccessionNumber"],
                         SeriesInstanceUID=self.meta["ShamSeriesNumber"])

    def ShamInstanceUID(self):
        return ShamDixel.ShamUID.uid(PatientID=self.meta["ShamID"],
                         StudyInstanceUID=self.meta["ShamAccessionNumber"],
                         SeriesInstanceUID=self.meta["ShamSeriesNumber"],
                         SOPInstanceUID=self.tags["InstanceNumber"])

    # orthanc id
    def sham_oid(self):
        if not self.meta.get('ID'):
            if self.level == DicomLevel.PATIENTS:
                self.meta['ShamOID'] = orthanc_id(self.meta.get('ShamID'))
            elif self.level == DicomLevel.STUDIES:
                self.meta['ShamOID'] = orthanc_id(self.meta.get('ShamID'),
                                             ShamDixel.ShamStudyUID(self))
            elif self.level == DicomLevel.SERIES:
                self.meta['ShamOID'] = orthanc_id(self.meta.get('ShamID'),
                                                  ShamDixel.ShamStudyUID(self),
                                                  ShamDixel.ShamSeriesUID(self))
            elif self.level == DicomLevel.INSTANCES:
                self.meta['ShamOID'] = orthanc_id(self.tags.get('ShamID'),
                                                  ShamDixel.ShamStudyUID(self),
                                                  ShamDixel.ShamSeriesUID(self),
                                                  ShamDixel.ShamInstanceUID(self))
            else:
                raise ValueError("Unknown DicomLevel for oid")
        return self.meta.get('ShamOID')

    def orthanc_sham_map(self):

        # Formatted calls to invoke ShamDixel methods even when called with a
        # base-class Dixel, as long as _Sham_ meta exists...

        if self.level == DicomLevel.INSTANCES:
            # TODO: Validate instance creation time maps
            raise NotImplementedError("Validate instance creation time mapping")

        replace = {
                "PatientName": self.meta["ShamName"],
                "PatientID": self.meta["ShamID"],
                "PatientBirthDate": self.meta["ShamBirthDate"],
                "AccessionNumber": self.meta["ShamAccessionNumber"],
                "StudyInstanceUID": ShamDixel.ShamStudyUID(self),
                "StudyDate": ShamDixel.ShamStudyDate(self),
                "StudyTime": ShamDixel.ShamStudyTime(self),
            }
        keep = ['PatientSex']

        if self.meta.get('ShamStudyDescription'):
            replace['StudyDescription'] = self.meta.get('ShamStudyDescription')
        else:
            keep.append('StudyDescription')

        # TODO: At study level - set keep series descriptions when?

        if self.level >= DicomLevel.SERIES:
            replace['SeriesInstanceUID'] = ShamDixel.ShamSeriesUID(self)
            replace['SeriesTime'] = ShamDixel.ShamSeriesTime(self)
            replace['SeriesDate'] = ShamDixel.ShamSeriesDate(self)
            if self.meta.get('ShamSeriesDescription'):
                replace['SeriesDescription'] = self.meta.get('ShamSeriesDescription')
            else:
                keep.append('SeriesDescription')
            if self.meta.get('ShamSeriesNumber'):
                replace['SeriesNumber'] = self.meta.get('ShamSeriesNumber')
            else:
                keep.append('SeriesNumber')

        if self.level >= DicomLevel.INSTANCES:
            replace['SOPInstanceUID'] = ShamDixel.ShamInstanceUID(self)
            replace['InstanceCreationTime'] = ShamDixel.ShamInstanceTime(self)
            replace['InstanceCreationDate'] = ShamDixel.ShamInstanceDate(self)

        return {
            "Replace": replace,
            "Keep": keep,
            "Force": True
        }

    @property
    def image_base_fn(self):
        """Filename for shammed image instance"""

        ser_num = self.tags.get("SeriesNumber",
                                hash_str(self.tags["SeriesInstanceUID"], 4))
        inst_num = self.tags.get("InstanceNumber",
                                 hash_str(self.tags["SOPInstanceUID"], 4))

        return "{acc}-{ser:04}-{ins:04}".format(acc=self.meta['ShamAccessionNumber'],
                                                ser=ser_num,
                                                ins=inst_num)
