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


def collect_mounted_blocks():
  result = {}
  devices = json.loads(sh.lsblk('-J').stdout)
  for device in devices['blockdevices']:
    for child in device.get('children', []):
      if child['mountpoint']:
        result[child['name']] = child['mountpoint']
  return result


def get_block_uuid():
  result = {}
  block_info = sh.blkid().stdout.decode('utf-8')
  for block in block_info.splitlines():
    tokens = block.split(':', 1)
    if len(tokens) < 2:
      continue
    if not tokens[0].startswith('/dev/'):
      continue
    device = tokens[0][5:]
    m = uuid_pattern.search(tokens[1])
    if m:
      uuid = (tokens[1][m.start(): m.end()].split('"')[1])
      result[device] = uuid
  return result


def collect_existing_mounts():
  """
  return a dictionary of currently registered info.
  Key: mount path.
  Value: the block device path
  Note when a block is removed from system, the mount path is still registered
  """
  result = {}
  for mount in sh.mount().stdout.decode('utf-8').splitlines():
    tokens = mount.split()
    if tokens[1] == 'on' and tokens[0].startswith('/dev/'):
      device = tokens[0][5:]
      result[tokens[2]] = device
  return result


@cli.command('auto')
@click_log.simple_verbosity_option(log)
def auto():
  context = pyudev.Context()
  monitor = pyudev.Monitor.from_netlink(context)
  monitor.filter_by(subsystem='usb')
  monitor.start()
  config_by_uuid = dict((x['UUID'], x['mount_point']) for x in mount_config)
  config_by_path = dict((x['mount_point'], x['UUID']) for x in mount_config)

  for device in iter(monitor.poll, None):
    sleep(1.0)  # use queue to minimize sleep
    mounted_blocks = collect_mounted_blocks()
    log.debug('Block info: %s', mounted_blocks)
    existing_mounts = collect_existing_mounts()
    log.debug("Mounts info:%s", existing_mounts)
    blk_uuids = get_block_uuid()
    log.debug("Block uuid:%s", blk_uuids)

    for mount_point in config_by_path.keys():
      if mount_point in existing_mounts:
        if existing_mounts[mount_point] not in mounted_blocks \
          or blk_uuids.get(existing_mounts[mount_point]) != config_by_path[mount_point]:
          # either the block is gone, or the mount point is mounted with a wrong block
          umount(existing_mounts[mount_point], mount_point)

    for block_device in blk_uuids:
      if block_device not in mounted_blocks:
        uuid = blk_uuids[block_device]
        if uuid in config_by_uuid:
          log.info("Mounting device %s, with UUID %s on path %s", block_device, uuid, config_by_uuid.get(uuid))
          mount(block_device, config_by_uuid.get(uuid))


if __name__ == '__main__':
  cli()
