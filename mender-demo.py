#!/usr/bin/env python3
import subprocess
import os


class ImageCfg:
    BOOT_PART = 0
    ENV_PART = 0
    STORAGE_INTERFACE = 'mmc'
    KERNEL_DEVICE_PREFIX = '/dev/mmcblk'

    DEFAULT_MMC_DEVICE = 0
    DEFAULT_ROOTFS_PART_A = 1
    DEFAULT_ROOTFS_PART_B = 2
    DEFAULT_ENV_SIZE = 0x4000
    DEFAULT_ENV_PRIMARY_OFFSET = 0x400000
    DEFAULT_ENV_SECONDARY_OFFSET = 0x800000
    DEFAULT_ROOTFS_OFFSET = 0xa00000
    DEFAULT_KERNEL_TYPE = 'booti'
    DEFAULT_KERNEL_PATH = 'Image'
    DEFAULT_DTB_PATH = 'sun50i-h5-nanopi-neo-plus2.dtb'
    DEFAULT_BOOT_LIMIT = 3

    DEFAULT_ROOTFS_IMG = 'rootfs.img'
    DEFAULT_DATA_IMG = 'data.img'
    DEFAULT_OUTPUT_IMG = 'out_sdimage'

    DD_PART_BS = 1048576

    def __init__(self):
        self._mmc_dev = self.DEFAULT_MMC_DEVICE
        self._kernel_dev_prefix = None
        self._rootfs_a = self.DEFAULT_ROOTFS_PART_A
        self._rootfs_b = self.DEFAULT_ROOTFS_PART_B
        self._env_size = self.DEFAULT_ENV_SIZE
        self._env_primary_offset = self.DEFAULT_ENV_PRIMARY_OFFSET
        self._env_secondary_offset = self.DEFAULT_ENV_SECONDARY_OFFSET
        self._rootfs_offset = self.DEFAULT_ROOTFS_OFFSET
        self._kernel_type = self.DEFAULT_KERNEL_TYPE
        self._kernel_path = self.DEFAULT_KERNEL_PATH
        self._dtb_path = self.DEFAULT_DTB_PATH
        self._boot_limit = self.DEFAULT_BOOT_LIMIT
        self._rootfs_img = self.DEFAULT_ROOTFS_IMG
        self._data_img = self.DEFAULT_DATA_IMG
        self._out_img = self.DEFAULT_OUTPUT_IMG

    def uboot_opts(self):
        print('\nU-Boot setup:')

        mmc_dev = input(f'Number of MMC device with UBoot and rootfs (0=sdcard, 1=eMMC) [{self._mmc_dev}]: ')
        if mmc_dev:
            self._mmc_dev = int(mmc_dev, 0)

        self._kernel_dev_prefix = f'{self.KERNEL_DEVICE_PREFIX}{self._mmc_dev}'
        self._kernel_dev_prefix = input(
            f'Kernel prefix of boot device [{self._kernel_dev_prefix}]: ') or self._kernel_dev_prefix

        rootfs_a = input(f'Rootfs A partition [{self._rootfs_a}]: ')
        if rootfs_a:
            self._rootfs_a = int(rootfs_a, 0)

        rootfs_b = input(f'Rootfs B partition [{self._rootfs_b}]: ')
        if rootfs_b:
            self._rootfs_b = int(rootfs_b, 0)

        env_size = input(f'UBoot environment size [{hex(self._env_size)}]: ')
        if env_size:
            self._env_size = int(env_size, 0)

        primary_offset = input(f'Primary UBoot environment offset [{hex(self._env_primary_offset)}]: ')
        if primary_offset:
            self._env_primary_offset = int(primary_offset, 0)

        secondary_offset = input(f'Secondary UBoot environment offset [{hex(self._env_secondary_offset)}]: ')
        if primary_offset:
            self._env_secondary_offset = int(secondary_offset, 0)

        rootfs_offset = input(
            f'Rootfs offset (must be divisible by {hex(self.DD_PART_BS)}) [{hex(self._rootfs_offset)}]: ')
        if rootfs_offset:
            self._rootfs_offset = int(rootfs_offset, 0)

        if self._rootfs_offset % self.DD_PART_BS:
            raise ValueError(f'Rootfs offset not divisible by block size ({self.DD_PART_BS})')

        self._kernel_type = input(f'Kernel type (booti, bootm, ...) [{self._kernel_type}]: ') or self._kernel_type
        self._kernel_path = input(f'Kernel image path (in /boot) [{self._kernel_path}]: ') or self._kernel_path
        self._dtb_path = input(f'Device tree path (in /boot) [{self._dtb_path}]: ') or self._dtb_path

        boot_limit = input(f'Boot counter limit [{self._boot_limit}]: ')
        if boot_limit:
            self._boot_limit = int(boot_limit, 0)

    def img_opts(self):
        print('\nSD image parameters:')

        self._rootfs_img = input(
            f'Path to rootfs partition image to use in final image [{self._rootfs_img}]: ') or self._rootfs_img
        self._data_img = input(
            f'Path to data partition image to use in final image [{self._data_img}]: ') or self._data_img
        self._out_img = input(f'Path to output image file [{self._out_img}]: ') or self._out_img

    def dump_mender_defines(self, uboot_path):
        with open(f'{uboot_path}/include/config_mender_defines.h', 'w') as f:
            f.write(
                '#ifndef HEADER_CONFIG_MENDER_DEFINES_H\n'
                '#define HEADER_CONFIG_MENDER_DEFINES_H\n\n'
                f'#define MENDER_BOOT_PART_NUMBER {self.BOOT_PART}\n'
                f'#define MENDER_BOOT_PART_NUMBER_HEX {hex(self.BOOT_PART)}\n'
                f'#define MENDER_ROOTFS_PART_A_NUMBER {self._rootfs_a}\n'
                f'#define MENDER_ROOTFS_PART_A_NUMBER_HEX {hex(self._rootfs_a)}\n'
                f'#define MENDER_ROOTFS_PART_B_NUMBER {self._rootfs_b}\n'
                f'#define MENDER_ROOTFS_PART_B_NUMBER_HEX {hex(self._rootfs_b)}\n'
                f'#define MENDER_UBOOT_STORAGE_INTERFACE "{self.STORAGE_INTERFACE}"\n'
                f'#define MENDER_UBOOT_STORAGE_DEVICE {self._mmc_dev}\n'
                f'#define MENDER_UBOOT_CONFIG_SYS_MMC_ENV_PART {self.ENV_PART}\n\n'
                f'#define MENDER_STORAGE_DEVICE_BASE "{self._kernel_dev_prefix}p"\n'
                f'#define MENDER_UBOOT_ENV_STORAGE_DEVICE_OFFSET_1 {hex(self._env_primary_offset)}\n'
                f'#define MENDER_UBOOT_ENV_STORAGE_DEVICE_OFFSET_2 {hex(self._env_secondary_offset)}\n'
                f'#define MENDER_ROOTFS_PART_A_NAME "{self._kernel_dev_prefix}p{self._rootfs_a}"\n'
                f'#define MENDER_ROOTFS_PART_B_NAME "{self._kernel_dev_prefix}p{self._rootfs_b}"\n\n'
                f'#define MENDER_BOOTENV_SIZE {hex(self._env_size)}\n\n'
                f'#define MENDER_BOOT_KERNEL_TYPE "{self._kernel_type}"\n'
                f'#define MENDER_KERNEL_NAME "{self._kernel_path}"\n'
                f'#define MENDER_DTB_NAME "{self._dtb_path}"\n'
                f'#define MENDER_UBOOT_PRE_SETUP_COMMANDS ""\n'
                f'#define MENDER_UBOOT_POST_SETUP_COMMANDS ""\n\n'
                '#endif\n'
            )

    def dump_kconfig_fragment(self, uboot_path, fragment):
        with open(f'{uboot_path}/{fragment}', 'w') as f:
            f.write(
                f'CONFIG_ENV_SIZE={hex(self._env_size)}\n'
                f'CONFIG_ENV_OFFSET={hex(self._env_primary_offset)}\n'
                f'CONFIG_BOOTCOUNT_BOOTLIMIT={self._boot_limit}\n'
                f'CONFIG_ENV_OFFSET_REDUND={hex(self._env_secondary_offset)}\n'
                f'# CONFIG_ENV_IS_IN_FAT is not set\n'
                'CONFIG_ENV_IS_IN_MMC=y\n'
                'CONFIG_SYS_REDUNDAND_ENVIRONMENT=y\n'
                'CONFIG_BOOTCOUNT_LIMIT=y\n'
                'CONFIG_BOOTCOUNT_ENV=y\n'
            )

    @staticmethod
    def get_block_count(bytes, blocksize):
        blocks = bytes // blocksize
        if bytes % blocksize:
            blocks += 1

        return blocks

    def img_build(self):
        a = input('Do you wish to assemble an MMC image? [N/y]: ')
        if a != 'y':
            return

        self.img_opts()

        subprocess.run(['dd', 'if=/dev/zero', f'of={self._out_img}', f'bs={self._rootfs_offset}', 'count=1'])

        subprocess.run(['parted', '--script', self._out_img, 'mklabel', 'msdos'])

        subprocess.run(
            ['dd', f'if={UBootBuilder.RESULT_BINARY}', f'of={self._out_img}', 'bs=1024', 'seek=8', 'conv=notrunc'])

        rfs_size = os.stat(self._rootfs_img).st_size
        rfs_blocks = self.get_block_count(rfs_size, self.DD_PART_BS)

        data_size = os.stat(self._data_img).st_size

        offset_blocks = self.get_block_count(self._rootfs_offset, self.DD_PART_BS)
        subprocess.run(
            ['dd', f'if={self._rootfs_img}', f'of={self._out_img}', f'bs={self.DD_PART_BS}', f'seek={offset_blocks}'])
        subprocess.run(['dd', f'if={self._rootfs_img}', f'of={self._out_img}', f'bs={self.DD_PART_BS}',
                        f'seek={offset_blocks + rfs_blocks}'])
        subprocess.run(['dd', f'if={self._data_img}', f'of={self._out_img}', f'bs={self.DD_PART_BS}',
                        f'seek={offset_blocks + 2 * rfs_blocks}'])

        subprocess.run(['parted', '--script', self._out_img, 'mkpart', 'primary', 'ext2', f'{self._rootfs_offset}B',
                        f'{self._rootfs_offset + rfs_size - 1}B'])
        subprocess.run(['parted', '--script', self._out_img, 'mkpart', 'primary', 'ext2',
                        f'{self._rootfs_offset + rfs_blocks * self.DD_PART_BS}B',
                        f'{self._rootfs_offset + rfs_blocks * self.DD_PART_BS + rfs_size - 1}B'])
        subprocess.run(['parted', '--script', self._out_img, 'mkpart', 'primary', 'ext2',
                        f'{self._rootfs_offset + 2 * rfs_blocks * self.DD_PART_BS}B',
                        f'{self._rootfs_offset + 2 * rfs_blocks * self.DD_PART_BS + data_size - 1}B'])


class Toolchain:
    TOOLCHAIN_EXECUTABLE = './poky-glibc-x86_64-meta-toolchain-aarch64-nanopi-neo-plus2-toolchain-3.0.2.sh'
    ENV_FILE = 'environment-setup-aarch64-poky-linux'
    EXTRACT_PATH = 'sdk'

    def __init__(self):
        self._env = {}

    @staticmethod
    def extract():
        a = input('Do you wish to install the toolchain? [N/y]: ')
        if a != 'y':
            return

        print('\nClearing existing SDK')
        subprocess.run(['rm', '-rf', Toolchain.EXTRACT_PATH])

        print('\nExtracting toolchain')
        subprocess.run([Toolchain.TOOLCHAIN_EXECUTABLE, '-d', Toolchain.EXTRACT_PATH])

    def load_env(self):
        self._env.update(os.environ)
        self._env.update(self.source(f'{self.EXTRACT_PATH}/{self.ENV_FILE}'))

    @property
    def env(self):
        return self._env

    @staticmethod
    def source(path):
        proc = subprocess.Popen(['bash', '-c', f'set -a && source {path} && env -0'], stdout=subprocess.PIPE,
                                shell=False)
        output, err = proc.communicate()
        output = output.decode('utf8')
        env = dict((line.split("=", 1) for line in output.split('\x00') if line))

        return env


class UBootBuilder:
    REPO = 'https://github.com/u-boot/u-boot.git'
    TAG = 'v2020.04-rc3'
    UBOOT_PATH = 'u-boot'
    UBOOT_PATCH_PATH = 'u-boot-patches'
    UBOOT_PATCHES = [
        f'0001-Add-missing-header-which-fails-on-recent-GCC.patch',
        f'0002-Generic-boot-code-for-Mender.patch',
        f'0003-Integration-of-Mender-boot-code-into-U-Boot.patch',
        f'0004-Disable-CONFIG_BOOTCOMMAND-and-enable-CONFIG_MENDER_.patch',
        f'0005-sunxi-increase-image-size-limit-for-sunxi-boards.patch',
        f'0006-sunxi-remove-environment-mmc-option.patch'
    ]
    BL31_BIN = 'bl31.bin'
    KCONFIG_FRAGMENT = 'mender_kconfig_fragment'
    DEFCONFIG = 'nanopi_neo_plus2_defconfig'
    RESULT_BINARY = f'{UBOOT_PATH}/u-boot-sunxi-with-spl.bin'
    MAKE_PARALLEL = 8

    def __init__(self, image_cfg, toolchain):
        self._image_cfg: ImageCfg = image_cfg
        self._toolchain: Toolchain = toolchain

    @staticmethod
    def shallow_clone():
        a = input('Do you wish to clone U-Boot? [N/y]: ')
        if a != 'y':
            return

        print(f'\nClearing existing U-Boot repository')
        subprocess.run(['rm', '-rf', UBootBuilder.UBOOT_PATH])

        print(f'\nShallow-cloning U-Boot {UBootBuilder.TAG}')
        subprocess.run(['git', 'clone', '-b', UBootBuilder.TAG, '--single-branch', '--depth', '1', UBootBuilder.REPO])

        UBootBuilder.patch()

    @staticmethod
    def patch():
        print('\nPatching U-Boot')
        for p in UBootBuilder.UBOOT_PATCHES:
            with open(f'{UBootBuilder.UBOOT_PATCH_PATH}/{p}', 'r') as pf:
                subprocess.run(['git', 'am'], cwd=UBootBuilder.UBOOT_PATH, stdin=pf)

    def build(self):
        a = input('Do you wish to build U-Boot? [N/y]: ')
        if a != 'y':
            return

        self._image_cfg.uboot_opts()

        self._image_cfg.dump_mender_defines(self.UBOOT_PATH)
        self._image_cfg.dump_kconfig_fragment(self.UBOOT_PATH, self.KCONFIG_FRAGMENT)

        subprocess.run(['cp', self.BL31_BIN, self.UBOOT_PATH])

        subprocess.run(['make', self.DEFCONFIG], cwd=self.UBOOT_PATH, env=self._toolchain.env)
        subprocess.run(['scripts/kconfig/merge_config.sh', '-m', '.config', self.KCONFIG_FRAGMENT], cwd=self.UBOOT_PATH,
                       env=self._toolchain.env)
        subprocess.run(['make', 'olddefconfig'], cwd=self.UBOOT_PATH, env=self._toolchain.env)

        subprocess.run(['make', f'-j{self.MAKE_PARALLEL}'], cwd=self.UBOOT_PATH, env=self._toolchain.env)


print('This script will attempt to set up the toolchain, U-Boot, compile it and build a system image')

Toolchain.extract()
UBootBuilder.shallow_clone()

img = ImageCfg()

t = Toolchain()
t.load_env()

ub = UBootBuilder(img, t)
ub.build()

img.img_build()
