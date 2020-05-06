# Rehive rootfs + Mender
This is a step-by-step example of building a Mender-compatible image from the Rehive distro.

## Requirements

* The `mender-demo.py` script
* A functional OpenEmbedded toolchain with headers required for building U-Boot
* ARM SPL

All of the above can be obtained by downloading and extracting `mender-demo.tar.gz`

Additionally, you will need the archives containing the rootfs and bootfs of the Rehive distro:

* `rootfs.tar.gz`
* `bootfs.tar.gz`

## Preparing the rootfs

### Preparing the rootfs partition image
Prepare a local empty image of the rootfs partition:

```
dd if=/dev/zero of=rehive_rootfs.img bs=1G count=2
```

Create an `ext4` filesystem on the image:

```
mkfs.ext4 rehive_rootfs.img
```

Mount the filesystem:

```
mkdir fs
mount -o loop rehive_rootfs.img fs/
```

### Preparing the data partition image
Additionally, create an empty image of the data partition:

```
dd if=/dev/zero of=rehive_data.img bs=1M count=128
```

And create an `ext4` filesystem:

```
mkfs.ext4 rehive_data.img
```

### Extracting the rootfs
Extract `rootfs.tar.gz` to the rootfs mountpoint:

```
cd fs/
tar -xvzpf ../rootfs.tar.gz --strip-components=1
```

This step and the following steps will likely need to be done as root (for `mknod` and preserving permissions).

### Extracting the bootfs
Extract `bootfs.tar.gz` to the rootfs mountpoint:

```
cd boot/
tar -xvzpf ../../bootfs.tar.gz --strip-components=1
```

### Creating the data partition mountpoint
Create the mountpoint for the data partition:

```
cd ../
mkdir data
```

### Modifying fstab
Modify `etc/fstab`:

```
vim etc/fstab
```

```
/dev/root       /       ext4    defaults,noatime 0 0
/dev/mmcblk1p3  /data   ext4    defaults,noatime 0 0
tmpfs           /tmp    tmpfs   defaults,noatime 0 0
```

### Finishing up
These modifications will suffice to create an SD card image that will successfully boot. Unmount the rootfs:

```
umount fs/
```

## Creating a bootable SD image
The following steps demonstrate building U-Boot and creating a bootable SD image with the `mender-demo.py` script.

### Extracting mender-demo.tar.gz
Extract `mender-demo.tar.gz`:

```
tar -xvzf mender-demo.tar.gz
```

### Running mender-demo.py
Run `mender-demo.py`:

```
cd mender-demo/
./mender-demo.py
```

Install the toolchain:

```
Do you wish to install the toolchain? [N/y]: y
```

Clone U-Boot:

```
Do you wish to clone U-Boot? [N/y]: y
```

Build U-Boot:

```
Do you wish to build U-Boot? [N/y]: y
```

Set up U-Boot compile-time parameters. Due to the DTB configuration of this image, the kernel mmc device id is different
from the U-Boot mmc device id. As a result, the kernel boot device prefix must be modified. Otherwise, default
configuration values can be used:

```
U-Boot id of MMC device with UBoot and rootfs (0=sdcard, 2=eMMC) [0]: 
Kernel prefix of boot device [/dev/mmcblk0]: /dev/mmcblk1
Rootfs A partition [1]: 
Rootfs B partition [2]: 
UBoot environment size [0x4000]: 
Primary UBoot environment offset [0x400000]: 
Secondary UBoot environment offset [0x800000]: 
Rootfs offset (must be divisible by 0x100000) [0xa00000]: 
Kernel type (booti, bootm, ...) [booti]: 
Kernel image path (in /boot) [Image]: 
Device tree path (in /boot) [sun50i-h5-nanopi-neo-plus2.dtb]: 
Boot counter limit [3]:
```

Assemble the SD image:

```
Do you wish to assemble an MMC image? [N/y]: y
```

Set paths to the prepared rootfs and data images:

```
Path to rootfs partition image to use in final image [rootfs.img]: ../rehive_rootfs.img
Path to data partition image to use in final image [data.img]: ../rehive_data.img
Path to output image file [out_sdimage]:
```

The script will automatically create a partition table and assemble an image based on the offsets specified when
building U-Boot. Note that you can use the flashable U-Boot binary and assemble the image yourself, but you must honor
the offsets supplied when building U-Boot, otherwise the image will not boot.

### Flashing the SD image
Flash the image on an SD card:

```
dd if=out_sdimage bs=1M of=/dev/sdx && sync
```

## Setting up the Mender client
The following steps describe the final modifications necessary for a fully functional Mender environment.

### Booting the device
Boot the board up from the SD card. The system should successfully boot on the first rootfs partition.

### Setting up `fw_utils`
Install the `u-boot-tools` package for the `fw_printenv` and `fw_setenv` utilities:

```
apt install u-boot-tools
```

Create `/etc/fw_env.config` and configure the environment offsets:

```
# Device to access      offset           env size
/dev/mmcblk1            0x400000         0x4000
/dev/mmcblk1            0x800000         0x4000
```

Test the configuration by running `fw_printenv`. This should print the entire U-Boot environment.

### Installing the Mender client
The `mender-client` package is not available in stretch and requires `libc >= 2.28`. As a result, it is necessary to
upgrade to buster or bullseye.

Update repositories to bullseye:

```
vim /etc/apt/sources.list
```

```
deb http://deb.debian.org/debian bullseye main
deb https://repos.iqrf.org/debian bullseye stable
deb https://repos.iqrf.org/testing/debian bullseye testing
```

Perform a system upgrade:

```
apt update
apt upgrade
apt full-upgrade
```

Install the Mender client:

```
apt install mender-client
```

If upgrading to buster instead of bullseye, install the `mender-client` package from bullseye repositories, as the
buster version is ancient.

### Configuring the mender client

#### Creating the configuration file
Create the `/etc/mender/mender.conf` configuration file:

```
vim /etc/mender/mender.conf
```

```
{
    "ClientProtocol": "https",
    "ArtifactVerifyKey": "",
    "HttpsClient": {
        "Certificate": "",
        "Key": "",
        "SkipVerify": false
    },
    "RootfsPartA": "/dev/mmcblk1p1",
    "RootfsPartB": "/dev/mmcblk1p2",
    "DeviceTypeFile": "/var/lib/mender/device_type",
    "UpdatePollIntervalSeconds": 1800,
    "InventoryPollIntervalSeconds": 28800,
    "RetryPollIntervalSeconds": 300,
    "StateScriptTimeoutSeconds": 0,
    "StateScriptRetryTimeoutSeconds": 0,
    "StateScriptRetryIntervalSeconds": 0,
    "ModuleTimeoutSeconds": 0,
    "ServerCertificate": "",
    "ServerURL": "",
    "UpdateLogPath": "",
    "TenantToken": "",
    "Servers": []
}
```

For a reference of Mender configuration options, see:

https://docs.mender.io/2.3/client-configuration/configuration-file/configuration-options

#### Symlinking /var/lib/mender to the data partition
Symlink `/var/lib/mender` to `/data/mender`:

```
mkdir /data/mender
ln -s /data/mender /var/lib/mender
```

#### Creating the device type file
Create the `device_type` file `/var/lib/mender/device_type`:

```
vim /var/lib/mender/device_type
```

```
device_type=rehive_nanopineoplus2
```

`device_type` can be a string of your choice. It is used for determining the compatibility of a rootfs update with
the system.

## Using the Mender client
This section briefly describes how the Mender client works. For further information, see official Mender docs:

https://docs.mender.io/2.3

### Creating a rootfs snapshot
Mount a remote filesystem over `sshfs`:

```
apt install sshfs
mkdir sshfs
sshfs user@host:/mount/path sshfs/
```

Create a snapshot of the currently running system:

```
mender snapshot dump > sshfs/rootfs_dump.img
```

### Using the mender-artifact tool
Obtain the standalone `mender-artifact` tool on your work machine:

https://docs.mender.io/2.3/downloads

Create an artifact from the snapshot:

```
./mender-artifact write rootfs-image -t rehive_nanopineoplus2 -n release-v2.0 -u rootfs_dump.img -o release-v2.0-upgrade.mender 
```

Validate the artifact:

```
./mender-artifact validate release-v2.0-upgrade.mender
```

### Deploying the Mender artifact
Deploy the created artifact:

```
mender install sshfs/release-v2.0-upgrade.mender
```

The upgrade will be deployed on the second rootfs partition.

### Committing the changes
After deploying the upgrade, reboot the system:

```
reboot
``` 

The system will boot on the upgraded rootfs partition. It is necessary
to run `mender commit`, otherwise, Mender will revert to the old rootfs after the bootcount limit is reached:

```
mender commit
```

Alternatively, issue `mender rollback` to revert to the previous rootfs:

```
mender rollback
```
