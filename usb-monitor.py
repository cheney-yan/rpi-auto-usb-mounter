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


def collect_blks():
  result = {}
  devices = json.loads(sh.lsblk('-J').stdout)
  for device in devices['blockdevices']:
    for child in device.get('children', []):
      if child['mountpoint']:
        result[child['name']] = child['mountpoint']
  return result


def collect_existing_mounts():
  """
  return a dictionary of currently registered info.
  Key: mount path.
  Value: the block path
  Note when a block is removed from system, the mount path is still registered
  """
  result = {}
  for mount in sh.mount().stdout.decode('utf-8').splitlines():
    tokens = mount.split()
    if tokens[1] == 'on':
      result[tokens[2]] = tokens[0]
  return result


@cli.command('auto')
@click_log.simple_verbosity_option(log)
def auto():
  context = pyudev.Context()
  monitor = pyudev.Monitor.from_netlink(context)
  monitor.filter_by(subsystem='usb')
  monitor.start()
  config_by_uuid = dict((x['UUID'], x['mount_point']) for x in mount_config)
  config_by_path = dict((x['UUID'], x['mount_point']) for x in mount_config)

  for device in iter(monitor.poll, None):
    sleep(1.0)  # use queue to minimize sleep
    existing_blocks = collect_blks().keys()
    existing_mounts = collect_existing_mounts()
    for path in config_by_path.keys():
      if path in existing_mounts:
        log.debug("Checking device: %s, path: %s", existing_mounts[path], path)
        if path in existing_mounts and existing_mounts[path] not in existing_blocks:  # currently registered as mounted, but device is gone
          log.info("Umounting device %s from path %s, seems the device is gone.", existing_mounts[path], path)
          umount(existing_mounts[path], path)

    block_info = sh.blkid().stdout.decode('utf-8')
    for block in block_info.splitlines():
      for p in existing_blocks:
        device = '/dev/{device}'.format(device=p)
        if block.strip().startswith('{}:'.format(device)):
          m = uuid_pattern.search(block)
          if m:
            uuid = (block[m.start(): m.end()].split('"')[1])
            if uuid in config_by_uuid:
              log.info("Mounting device %s, with UUID %s on path %s", device, uuid, config_by_uuid.get(uuid))
              mount(device, config_by_uuid.get(uuid))


if __name__ == '__main__':
  cli()
