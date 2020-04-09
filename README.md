# mender-demo
This repository contains tools for building Mender-compatible system images for the NanoPi Neo Plus2 board.

## Building a Mender-compatible System Image from Scratch
This chapter describes the steps necessary for building a Mender-compatible system image from an arbitrary, functional
Linux rootfs.

### Preparing the rootfs
This section describes the process of modifying an existing, live system to be used as the base for a Mender-compatible
image. Steps in this section assume you have a functional, live system running on the board.

#### Migrating partitions
Mender requires the entire rootfs to reside on a single partition. It is necessary to migrate all mountpoints to `/` (
typical cases are `/boot` and `/home`). Once all partitions have been migrated, the corresponding entries must be
removed from `/etc/fstab`

#### Creating the `/data` partition
The only exception to the above requirement is a separate `/data` partition, which is used by Mender for storing
persistent data across updates. It can also be used for any other persistent data that must be preserved
between updates (for example device identifiers, private keys, etc.). A reasonable size (Mender default) is `128 MiB`.

Create the partition, mount it to `/data` and add an entry to `/etc/fstab`. Note that the `/data` partition
will be the third partition in the final image, so use `/dev/mmcblk0p3` in fstab if the system will run on `mmcblk0`.

For more information, see official Mender docs:

https://docs.mender.io/2.3/devices/yocto-project/partition-configuration

#### Modifying entry for root partition in `/etc/fstab`
`/etc/fstab` should now contain only 2 entries - `/` and the `/data` mountpoint created in the previous
step. Modify the entry for the root mountpoint to use `/dev/root`, which is symlinked to the root partition
according to the `root=` parameter passed to the kernel in initramfs.

#### Setting up `fw_utils`
The `fw_printenv` and `fw_setenv` utilities for modifying U-Boot environment variables must be present on the system.
In Debian, these can be obtained by installing the `u-boot-tools` package. Alternatively, you can use the binaries
obtained from building U-Boot (in a later step).

Once the utilities are installed, modify `/etc/fw_env.config` to correctly reference the U-Boot environment offsets:

```
# Device to access      offset           env size
/dev/mmcblk0            0x400000         0x4000
/dev/mmcblk0            0x800000         0x4000
```

You can use different offsets, but you must then specify the same offsets when building U-Boot.

#### Installing the Mender client
In Debian, just install the `mender-client` package. Run `mender bootstrap` or edit `/etc/mender.conf` to configure
partitions for rootfs A and rootfs B. The first two partitions on the target device (for example `/dev/mmcblk0p1` and
`/dev/mmcblk0p2`) should be configured as rootfs partitions and the third partition (`/dev/mmcblk0p3`) should be
configured as the data partition.

For a reference of Mender configuration options, see:

https://docs.mender.io/2.3/client-configuration/configuration-file/configuration-options

Once Mender is configured, symlink `/var/lib/mender` to `/data/mender`. Create the `device_type` file
`/var/lib/mender/device_type`:

```
device_type=nanopineoplus2
```

`device_type` can be a string of your choice. It is used for determining the compatibility of a rootfs update with
the system.

The Mender systemd service does not need to be enabled unless you are using a Mender Server that the client will
connect to.

#### Setting up `/boot`
The `/boot` directory must contain the kernel image and the flattened device tree blob. Feel free to use any path and
filename for these files, but make note of these as they will be required when building U-Boot.

#### Dumping reference rootfs and data partitions
Complete the above steps and adjust the reference system to your liking, then power down the system and dump
the reference rootfs and data partitions using `dd`

```
dd if=/dev/mmcblk0p1 bs=1M of=rootfs.img
dd if=/dev/mmcblk0p2 bs=1M of=data.img
```

### Building the image

#### Building U-Boot
This step requires you to have a toolchain and the ARM SPL. Feel free to use the ones in
`antdev:/srv/git/xposto02/mender-demo.tar.gz`

Once the toolchain and `bl31.bin` are placed in the working directory, run `./mender-demo.py`. The script will extract
the toolchain, download U-Boot sources and apply patches.

The script will interactively query for parameters and offer default values.

#### Building the image
Once U-Boot successfully builds, the script will combine U-Boot and the reference rootfs and data partition dumps into
a flashable image with the following layout:

```
|---------------------------------------------------------------------------------------|
|                                      |                |                |              |
|  SPL + U-Boot + U-Boot Environment   |   rootfs.img   |   rootfs.img   |   data.img   |
|                                      |                |                |              |
|---------------------------------------------------------------------------------------|
```

## Using the Mender client
This section briefly describes how the Mender client works. For further information, see official Mender docs:

https://docs.mender.io/2.3

### Creating a rootfs snapshot
A rootfs upgrade can be deployed by making changes to one device, snapshotting that device and deploying the snapshot
to other devices of the same `device_type`. To test this, make some changes to a live, functional mender-compatible
system and run:

```
mender snapshot dump > rootfs_dump.img
```

Mender will dump the snapshot to `stdout`. The output should be redirected to a mounted filesystem (for example
`sshfs`) as no compression is used at this stage and there will not be enough space on the device to store the snapshot.

### Creating a Mender artifact
Once a snapshot is obtained, it must be packed into a Mender artifact, which can then be deployed as an update package.
This should not be done directly on the board, as it will take a long time to compress the snapshot.

Obtain the standalone `mender-artifact` tool:

https://docs.mender.io/2.3/downloads

Create an artifact from the snapshot:

```
./mender-artifact --copmression lzma write rootfs-image -t nanopineoplus2 -n release-v2.0 -u rootfs_dump.img -o release-v2.0-upgrade.mender 
```

see:

https://docs.mender.io/development/artifacts/modifying-a-mender-artifact

After the artifact has been successfully created, validate the artifact:

```
./mender-artifact validate release-v2.0-upgrade.mender
```

If the Mender client is configured to verify artifact signatures, it is also necessary to sign the artifact:

```
./mender-artifact sign release-v2.0-upgrade.mender
```

### Deploying the Mender artifact
Once an artifact is created, it can be deployed on the board:

```
mender install release-v2.0-upgrade.mender
```

The client will validate the artifact, install and deploy it on the other partition and attempt to boot up. If the
upgrade succeeds, `mender commit` must be called from the new rootfs to make the upgrade permanent (otherwise, Mender
will revert to the previous rootfs after the bootcount limit is reached).