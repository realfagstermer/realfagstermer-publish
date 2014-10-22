# encoding=utf8
import datetime
import logging
import logging.handlers
import os.path
import logging
import ConfigParser
import shutil
import subprocess

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s %(levelname)s] %(message)s')

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

warn_handler = logging.FileHandler('warnings.log')
warn_handler.setLevel(logging.WARNING)
warn_handler.setFormatter(formatter)
logger.addHandler(warn_handler)


def run():

    config = ConfigParser.ConfigParser()
    config.read('config.ini')
    args = [config.get('isql', x) for x in ['path', 'port', 'user', 'pass']]
    args.append('src/update_triple_store.isql')

    with open('/tmp/realfagstermer.ttl', 'w') as outfile:
        with open('realfagstermer.ttl', 'r') as infile:
            for line in infile:
                outfile.write(line.replace('data.ub.uio.no', 'data.ub.uio.nu'))

    proc = subprocess.Popen(args)
    if proc.wait() != 0:
        logger.error('%s exited with error!', path)


if __name__ == '__main__':
    run()
