from pathlib import Path
import yaml, os, logging
from datetime import datetime, timedelta
from diana.apis import Montage, ProxiedDicom
from diana.daemons.collector2 import Collector
from diana.utils.gateways import MontageModality as Modality

# 17/11/01 - 17/11/12 done
# 18/07/01 - 18/12/18 done
# 19/01/01 - 19/01/17 done

# CONFIG
services_path = "/services.yml"
pacs_svc = "radarch"
dest_path = Path("/data/")
montage_svc = "montage"
query = {"q": "", "modality": Modality.CR}
start = datetime(year=2018, month=12, day=19)
stop = datetime(year=2018, month=12, day=31)
# Montage can only query by day
step = timedelta(days=1)
get_meta = True
pool_size = 2
delay = 0.01
logging_level = logging.DEBUG

# Should make num jobs and delay time dependent
# -- 16 jobs at night with 0.1 delay
# -- 2 during day with 1 sec delay


def collect_corpus(_worklist, _pacs, _dest_path):

    c = Collector(pool_size=pool_size)
    c.run(worklist=_worklist,
          source=_pacs,
          dest_path=_dest_path,
          inline_reports=False,
          save_as_im=True,
          anonymize=True,
          delay=delay)


if __name__ == "__main__":

    logging.basicConfig(level=logging_level)
    logging.getLogger("PMap").setLevel(logging.WARNING)
    from diana.utils.gateways import supress_urllib_debug
    supress_urllib_debug()

    with open(services_path) as f:
        services_exp = os.path.expandvars(f.read())
        services = yaml.safe_load(services_exp)

    montage = Montage(**services[montage_svc])
    montage.check()
    worklist = montage.iter_query_by_date(query, start, stop, step, get_meta)

    pacs = ProxiedDicom(**services[pacs_svc])
    pacs.check()

    collect_corpus(worklist, pacs, dest_path)
