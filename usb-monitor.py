#!/usr/bin/env python3

import pyudev
import subprocess
import sh
import json
from time import sleep
import re

uuid_pattern = re.compile('UUID="[^"]+"')
mount_config = [
    {
        "UUID": '67E3-17ED', "mount_point": "/data2"
    }
]

def mount(device, mount_point):
  sh.sudo.mount(device, mount_point)

def umount(device, mount_point):
  for mount in sh.mount().stdout.decode('utf-8').splitlines():
    if re.match(r'')
  sh.sudo.umount(mount_point)

def main():
  context = pyudev.Context()
  monitor = pyudev.Monitor.from_netlink(context)
  monitor.filter_by(subsystem='usb')
  monitor.start()
  cfg = dict((x['UUID'], x['mount_point']) for x in mount_config)
  for device in iter(monitor.poll, None):
    partitions = []
    sleep(1.0)  # use queue to minimize sleep
    devices = json.loads(sh.lsblk('-J').stdout)
    for device in devices['blockdevices']:
      for child in device.get('children', []):
        if not child['mountpoint']:
          partitions.append(child['name'])
    block_info = sh.blkid().stdout.decode('utf-8')
    for block in block_info.splitlines():
      for p in partitions:
        device = '/dev/{device}'.format(device=p)
        if block.strip().startswith('{}:'.format(device)):
          m = uuid_pattern.search(block)
          if m:
            uuid = (block[m.start(): m.end()].split('"')[1])
            if uuid in cfg:
              mount(device, cfg.get(uuid))
    

if __name__ == '__main__':
  main()
