import time
import logging
from multiprocessing import Process
from diana.apis import Orthanc, DcmDir
from diana.apis.observables import ObservableOrthanc
from diana.utils.dicom import DicomEventType
from diana.utils.endpoint import Watcher, Trigger
from diana.dixel import DixelView

from test_utils import find_resource
from interruptingcow import timeout


def say(self, data):
    print(data)

ObservableOrthanc.say = say


def orth_test_runner():
    O = Orthanc()
    dicom_dir = find_resource("resources/dcm")
    D = DcmDir(path=dicom_dir)

    print("Starting script")
    time.sleep(1)
    d = D.get("IM2263", view=DixelView.FILE)
    O.put(d)
    O.check()
    print("Ending script")


def test_orthanc_watcher(setup_orthanc0, capfd):

    print("Starting")

    obs = ObservableOrthanc()
    watcher = Watcher()

    trigger0 = Trigger(
        evtype=DicomEventType.INSTANCE_ADDED,
        source=obs,
        action=obs.say
    )

    watcher.add_trigger(trigger0)

    p = Process(target=orth_test_runner)
    p.start()

    try:
        with timeout(5):
            print("Starting watcher")
            watcher.run()
    except:
        print("Stopping watcher")
        watcher.stop()

    if capfd:
        captured = capfd.readouterr()
        assert "8ea24299-e051fc03-3ae9ed25-adc22b32-971a056a" in captured.out


if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    from conftest import mk_orthanc

    O = mk_orthanc()
    logging.debug(O.dkr_container.status)
    test_orthanc_watcher(None, None)
