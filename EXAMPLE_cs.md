# RehiveTech distro + Mender
Tento dokument obsahuje konkrétní příklad sestavení Mender-kompatibilního image pro bezpečnou vzdálenou aktualizaci v systému PIXLA. Je postaven na distribuci, kterou používá RehiveTech (AuroraHub IoT Gateway v jakékoli variantě).

## Požadavky

* Skript `mender-demo.py`
* OpenEmbedded toolchain
* ARM SPL
* Root filesystem distribuce RehiveTech `rootfs.tar.gz`
* Boot filesystem distribuce RehiveTech `bootfs.tar.gz`

Vše je obsaženo v archivu na adrese https://bit.ly/mender-demo_tar_gz.

## Příprava systémového image

### Vytvoření prázdného image pro kořenovou partition
Vytvořte prázdný soubor, ze kterého bude vytvořen image kořenové partition:

```
dd if=/dev/zero of=rehive_rootfs.img bs=1G count=2
```

Zformátujte image:

```
mkfs.ext4 rehive_rootfs.img
```

Připojte image:

```
mkdir fs
mount -o loop rehive_rootfs.img fs/
```

### Vytvoření prázdného image pro data partition
Vytvořte prázdný soubor, ze kterého bude vytvořen image data partition:

```
dd if=/dev/zero of=rehive_data.img bs=1M count=128
```

Zformátujte image:

```
mkfs.ext4 rehive_data.img
```

### Rozbalení archivu `rootfs.tar.gz`
Archiv `rootfs.tar.gz` rozbalte do připojeného image kořenové partition:

```
cd fs/
tar -xvzpf ../rootfs.tar.gz --strip-components=1
```

Pro tento krok budou pravděpodobně nutná práva uživatele root (pro příkaz `mknod` and a zachování původních práv).

### Rozbalení archivu `bootfs.tar.gz`
Archiv `bootfs.tar.gz` rozbalte do adresáře `boot` v připojeném image kořenové partition:

```
cd boot/
tar -xvzpf ../../bootfs.tar.gz --strip-components=1
```

### Vytvoření mountpoint pro `/data` partition
V image kořenové partition vytvořte mountpoint pro `/data` partition:

```
cd ../
mkdir data
```

### Úprava fstab
V image kořenové partition upravte soubor `etc/fstab`:

```
vim etc/fstab
```

```
/dev/root       /       ext4    defaults,noatime 0 0
/dev/mmcblk1p3  /data   ext4    defaults,noatime 0 0
tmpfs           /tmp    tmpfs   defaults,noatime 0 0
```

### Konec
S těmito úpravami bude možné sestavit výsledný image, který úspěšně nabootuje. Zbytek úprav bude možné provést již na
živém systému.

Odpojte image kořenové partition:

```
umount fs/
```

## Vytvoření výsledného image
Následující kroky popisují překlad U-Bootu a vytvoření výsledného image pomocí skriptu `mender-demo.py`.

### Rozbalení archivu `mender-demo.tar.gz`
Rozbalte archiv `mender-demo.tar.gz`:

```
tar -xvzf mender-demo.tar.gz
```

### Spuštění skriptu `mender-demo.py`
Spusťte skript `mender-demo.py`:

```
cd mender-demo/
./mender-demo.py
```

Nainstalujte toolchain:

```
Do you wish to install the toolchain? [N/y]: y
```

Zklonujte repozitář U-Bootu:

```
Do you wish to clone U-Boot? [N/y]: y
```

Spusťte překlad U-Bootu:

```
Do you wish to build U-Boot? [N/y]: y
```

Skript se interaktivně dotáže na parametry pro překlad. Kvůli odlišnostem v device tree Rehive image a device tree
U-Bootu má SD karta v U-Bootu id 0 a v kernelu id 1. Pokud bude výsledný image flashován na SD kartu, je třeba upravit
parametr `Kernel prefix of boot device`. U ostatních parametrů lze použít default hodnoty:

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

Sestavte výsledný image:

```
Do you wish to assemble an MMC image? [N/y]: y
```

Bude potřeba zadat cesty k image kořenové a data partition:

```
Path to rootfs partition image to use in final image [rootfs.img]: ../rehive_rootfs.img
Path to data partition image to use in final image [data.img]: ../rehive_data.img
Path to output image file [out_sdimage]:
```

Skript sestaví výsledný image, který bude obsahovat SPL, U-Boot, dvě kořenové partitions a data partition.

### Flashování image
Naflashujte image na SD kartu:

```
dd if=out_sdimage bs=1M of=/dev/sdx && sync
```

## Instalace a konfigurace Mender klienta
Následující kroky popisují úpravy potřebné pro zprovoznění Mender klienta na nově vytvořeném image.

### Boot z výsledného image
Vložte SD kartu s výsledným image. Systém by měl úspěšně nabootovat do první kořenové partition.

### Instalace a konfigurace `fw_utils`
Nainstalujte balíček `u-boot-tools`, který obsahuje utility `fw_printenv` a `fw_setenv`:

```
apt install u-boot-tools
```

Vytvořte soubor `/etc/fw_env.config` a nastavte offsety k hlavnímu a záložnímu prostředí U-Bootu:

```
# Device to access      offset           env size
/dev/mmcblk1            0x400000         0x4000
/dev/mmcblk1            0x800000         0x4000
```

Otestujte příkazem `fw_printenv`, který by měl vypsat kompletní prostředí U-Bootu.

### Instalace Mender klienta
Balíček `mender-client` není v Debian stretch dostupný a vyžaduje `libc >= 2.28`. Je tedy třeba provést aktualizaci
distribuce na Debian buster nebo bullseye.

Úprava repozitářů:

```
vim /etc/apt/sources.list
```

```
deb http://deb.debian.org/debian bullseye main
deb https://repos.iqrf.org/debian bullseye stable
deb https://repos.iqrf.org/testing/debian bullseye testing
```

Aktualizace systému:

```
apt update
apt upgrade
apt full-upgrade
```

Instalace balíčku `mender-client`:

```
apt install mender-client
```

Pokud budete aktualizovat pouze na buster, nainstaluje balíček `mender-client` z repozitářů pro bullseye, verze z
busteru je stará a chybí v ní některé uživatelské utility.

### Konfigurace Mender klienta

#### Vytvoření konfiguračního souboru
Vytvořte konfigurační soubor `/etc/mender/mender.conf`:

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

Přehled možností v konfiguračním souboru je zde:

https://docs.mender.io/2.3/client-configuration/configuration-file/configuration-options

#### Symlink adresáře /var/lib/mender do data partition
Vytvořte symlink adresáře `/data/mender` na `/var/lib/mender`:

```
mkdir /data/mender
ln -s /data/mender /var/lib/mender
```

#### Vytvoření souboru `device_type`
Vytvořte soubor `device_type`:

```
vim /var/lib/mender/device_type
```

```
device_type=rehive_nanopineoplus2
```

`device_type` může být libovolný řetězec. `device_type` systému se porovnává s `device_type` uvedeným v aktualizačním
artefaktu pro zjištění, zda je daná aktualizace určena pro aktuální systém.

## Používání Mender klienta
Tato kapitola popisuje základní práci s Mender klientem. Více informací je k dispozici v oficiální dokumentaci:

https://docs.mender.io/2.3

### Vytvoření snapshotu aktuálního systému
Připojte vzdálený filesystém přes `sshfs`:

```
apt install sshfs
mkdir sshfs
sshfs user@host:/mount/path sshfs/
```

Vytvořte snapshot aktuálně běžícího systému:

```
mender snapshot dump > sshfs/rootfs_dump.img
```

### Používání nástroje `mender-artifact`
Stáhněte si nástroj `mender-artifact`:

https://docs.mender.io/2.3/downloads

Ze získaného snapshotu vygenerujte artefakt:

```
./mender-artifact write rootfs-image -t rehive_nanopineoplus2 -n release-v2.0 -u rootfs_dump.img -o release-v2.0-upgrade.mender 
```

Ověřte artefakt:

```
./mender-artifact validate release-v2.0-upgrade.mender
```

### Provedení aktualizace
Proveďte aktualizaci systému vygenerovaným artefaktem:

```
mender install sshfs/release-v2.0-upgrade.mender
```

Filesystém obsažený v artefaktu bude umístěn na aktuálně nepoužívanou rootfs partition.

### Potvrzení aktualizace
Po dokončení aktualizace proveďte reboot:

```
reboot
``` 

Systém nabootuje do druhé partition. Pro potvrzení aktualizace je třeba provést `mender commit`, v opačném případě
bude aktualizace považována za neúspěšnou a Mender přepne na původní partition po dosažení maximálního počtu
neúspěšných nabootování (`Boot counter limit`):

```
mender commit
```

Zadání příkazu `mender rollback` způsobí okamžité přepnutí na předchozí partition:

```
mender rollback
```
