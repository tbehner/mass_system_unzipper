import logging
import tempfile
import mass_api_client
import zipfile
import os
from mass_api_client import resources as mass
from mass_api_client.utils import process_analyses, get_or_create_analysis_system_instance

logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)
# TODO nicer logging format


def read_password_list():
    password_list_path = './password_list.txt'
    with open(password_list_path) as f:
        return f.read().splitlines()

class UnzipperAnalysis():
    def __init__(self):
        self._passwords = read_password_list() 
        logger.info('Read {} passwords from password file.'.format(len(self._passwords)))

    def unzip(self, scheduled_analysis):
        sample = scheduled_analysis.get_sample()
        logger.info('Analysing {}'.format(sample))
        with sample.temporary_file() as sample_file:
            zp = zipfile.ZipFile(sample_file)
            files = zp.namelist() 
            logger.info('Contains files: {}'.format(files))
            password = None
            for pw in self._passwords:
                try:
                    zo = zp.open(files[0], "r", pwd=pw.encode('utf-8'))
                except RuntimeError:
                    continue
                password = pw
                break
            if password:
                logger.info('Found password {}'.format(password))
            else:
                logger.info('No password found!')
                scheduled_analysis.create_report(
                        additional_metadata={'status': 'No password found'}
                    )


            for fn in files:
                logger.info('Submitting {}'.format(fn))
                with zp.open(fn, "r", pwd=pw.encode('utf-8')) as zo:
                    mass.FileSample.create(fn, zo)
                logger.info('Submission finished!')
            scheduled_analysis.create_report(
                    additional_metadata={'status': 'unpacked'},
                    json_report_objects={
                        'json_report': ('json_report', {'unpacked files': files, 'password': password})
                        }
                    )

if __name__ == "__main__"   :
    api_key = os.getenv('MASS_API_KEY', '')
    logger.info('Got API KEY {}'.format(api_key))
    server_addr = os.getenv('MASS_SERVER', 'http://localhost:8000/api/')
    logger.info('Connecting to {}'.format(server_addr))
    timeout = int(os.getenv('MASS_TIMEOUT', '60'))
    mass_api_client.ConnectionManager().register_connection('default', api_key, server_addr, timeout=timeout)

    analysis_system_instance = get_or_create_analysis_system_instance(identifier='unzip',
                                                                      verbose_name= 'Unzipper',
                                                                      tag_filter_exp='sample-type:filesample and mime-type:zip',
                                                                      )
    unzipper = UnzipperAnalysis()
    process_analyses(analysis_system_instance, unzipper.unzip, sleep_time=7)
