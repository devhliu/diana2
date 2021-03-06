import random, logging, time
from pprint import pprint
from datetime import datetime, timedelta
import attr
from diana.dixel import MockStudy
from diana.apis import Orthanc

sample_site_desc = """
---
- name: Example Hospital
  services:
  - name: Main CT
    modality: CT
    devices: 3
    studies_per_hour: 15
  - name: Main MR
    modality: MR
    devices: 2
    studies_per_hour: 4
"""

@attr.s
class MockDevice(object):
    """Generates studies on a schedule"""

    site_name = attr.ib(default="Mock Facility")
    station_name = attr.ib(default="Imaging Device")
    modality = attr.ib(default="CT")
    studies_per_hour = attr.ib(default=6)
    action_interval = attr.ib(default=5.0)

    _next_study = attr.ib(init=False, factory=datetime.now)

    def gen_study(self, study_datetime=None):
        # Can force a study datetime for testing
        s = MockStudy(study_datetime=study_datetime or datetime.now(),
                      site_name = self.site_name,
                      station_name = self.station_name,
                      modality=self.modality
                      )
        return s

    def poll(self, dest: Orthanc=None):
        if datetime.now() > self._next_study:
            print("{}: Study ready to push".format( self.station_name ) )
            study = self.gen_study()
            pprint(study.tags)
            for d in study.instances():
                d.gen_file()
                if dest:
                    dest.put(d)
            delay = 60*60/self.studies_per_hour
            R = random.Random()
            delay = R.randint(int(0.5*delay), int(1.5*delay))
            self._next_study = datetime.now() + timedelta(seconds=delay)
            print("{}: Next study at {}".format(self.station_name, self._next_study))
        else:
            logging.debug("No study, next at {}".format(self._next_study))
            time.sleep(self.action_interval)


@attr.s
class MockService(object):
    """Set of similar modality imaging devices"""
    site_name = attr.ib(default="Mock Facility")
    name = attr.ib(default="Imaging Service")
    modality = attr.ib(default="CT")
    num_devices = attr.ib(default=1)
    studies_per_hour = attr.ib(default=6)

    devices = attr.ib(init=False)
    @devices.default
    def setup_devices(self):
        devices = []
        for i in range(self.num_devices):
            device = MockDevice(
                    site_name = self.site_name,
                    station_name = "{}_{}".format(
                        self.name.upper().replace(" ","_"),
                        len(devices)+1),
                    modality=self.modality,
                    studies_per_hour = self.studies_per_hour/self.num_devices
                )
            devices.append(device)
        return devices

@attr.s
class MockSite(object):
    """Set of imaging services"""

    name = attr.ib(default="Mock Facility")
    services = attr.ib(init=False, factory=list)

    # seed = attr.ib( default=None )
    # @seed.validator
    # def set_seed(self, attribute, value):
    #     if value:
    #         random.seed(value)

    def add_service(self, name, modality, devices, studies_per_hour):
        self.services.append(
            MockService(
                name=name,
                modality=modality,
                num_devices=devices,
                studies_per_hour=studies_per_hour,
                site_name=self.name)
        )

    def devices(self):
        for service in self.services:
            for device in service.devices:
                yield device

    def run(self, pacs):
        while True:
            for device in self.devices():
                logging.debug("Checking device for studies")
                device.poll(dest=pacs)
                time.sleep(1)



    class Factory(object):

        @classmethod
        def create(cls, desc: dict):

            print("Creating mock site from spec")

            sites = []
            for site_desc in desc:
                site = MockSite(name=site_desc.get("name"))
                for service in site_desc.get("services"):
                    site.add_service(**service)
                sites.append(site)

            return sites
