#!/usr/bin/env python3

import pyudev
import subprocess
import sh
import json
from time import sleep
import re
import click
import logging
import click_log
uuid_pattern = re.compile('UUID="[^"]+"')
mount_config = [
    {
        "UUID": '67E3-17ED', "mount_point": "/data2"
    }
]

log = logging.getLogger(__name__)
click_log.basic_config(log)


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
  """USB disk mounter"""
  if not ctx.invoked_subcommand:
    auto()


def mount(device, mount_point):
  sh.sudo.mount(device, mount_point)


def umount(device, mount_point):
  pattern = re.compile(f'^${device}\W+on\W+mount_point\W+.*$')
  matched = [
      mount
      for mount in sh.mount().stdout.decode('utf-8').splitlines()
      if re.match(pattern, mount)
  ]
  if matched:
    sh.sudo.umount(mount_point)


def collect_mounted():
  result = {}
  devices = json.loads(sh.lsblk('-J').stdout)
  for device in devices['blockdevices']:
    for child in device.get('children', []):
      if child['mountpoint']:
        result[child['name']] = child['mountpoint']
  return result


@cli.command('auto')
@click_log.simple_verbosity_option(log)
def auto():
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
              log.info("Mounting device %s, with UUID %s on path %s", device, uuid, cfg.get(uuid))
              mount(device, cfg.get(uuid))


if __name__ == '__main__':
  cli()
