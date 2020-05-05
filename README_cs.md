# mender-demo
Tento repozitář obsahuje nástroje potřebné pro sestavení image pro desku FriendlyARM NanoPI Neo Plus2, který je
kompatibilní se systémem Mender.

## Úvod

[Mender](https://mender.io "Mender") je open-source software updater, který umožňuje spolehlivým způsobem provádět
OTA firmware aktualizace (má podporu pro návrat k předchozí verzi firmware v případě, že se aktualizace nezdaří).
Zařízení, které využívá funkcionality OTA aktualizací Menderu, musí splňovat několik požadavků: musí být použita
verze bootloaderu (U-Bootu), která je upravena pro použití s Menderem, musí být použito vhodné rozložení diskových
oddílů a v systému musí být nainstalována klientská aplikace Menderu. Zároveň musí být v systému k dispozici nástroje,
které Mender klient pro provádění aktualizací potřebuje (například utilita pro konfiguraci bootloaderu).

Součástí Menderu je klientská i serverová aplikace. Klient běží přímo na zařízení a zajišťuje provádění systémových
aktualizací. Každý klient může být připojen k serveru, pomocí kterého lze řídit a plánovat aktualizace připojených
klientů. Součástí klienta je utilita, pomocí které lze lokálně provádět veškeré operace, včetně aktualizace systému.
Klienta je tedy možné používat i bez připojení k Mender serveru.

Tento dokument obsahuje přehled kroků, které je třeba provést pro zprovoznění Mender klienta na libovolné distribuci
běžící na desce NanoPI Neo Plus2. Jsou zde popsány potřebné úpravy systému a postup pro vygenerování bootovatelného
image, který bude s Mender klientem fungovat. Skripty obsažené v tomto repozitáři lze použít k automatizovanému
překladu bootloaderu a sestavení image.

Tento dokument se nezabývá konfigurací a použitím Mender serveru ani dalšími tématy, ktrá se bezprostředně netýkají
zprovoznění Mender klienta na konkrétním hardware. Tato témata jsou pokrytá oficiální 
[dokumentací](https://docs.mender.io/2.3 "Mender dokumentace") Menderu.

## Sestavení image kompatibilního s Menderem
V této kapitole jsou popsány kroky potřebné pro sestavení image, který podporuje Mender, s použitím libovolného
funkčního systému jako základu tohoto image.

### Příprava systému
Tato sekce popisuje úpravy existujícího, funkčního systému, aby ho bylo možné použít jako základ pro image.

#### Migrace diskových oddílů
Správné fungování Mender aktualizací vyžaduje, aby byl celý systém na jediném diskovém oddílu. Pokud sytém využívá
více oddílů (např. pro `/boot` nebo `/home`), je třeba přesunout obsah těchto oddílů na kořenový oddíl. Zároveň je
třeba odstranit odpovídající přípojné body z `/etc/fstab`.

#### Vytvoření `/data` partition
Jedinou výjímku z výše uvedeného požadavku tvoří diskový oddíl `/data`, na který se ukládají soubory, které musí
aktualizaci systému přežít. Oddíl `/data` je pro funkčnost Mender klienta nezbytný. Zároveň jej lze využít např. k
uložení jedinečných identifikátorů zařízení nebo privátních klíčů, které jsou pro každé zařízení unikátní a které je
třeba při aktualizaci systému zachovat. Mender pro tento oddíl doporučuje velikost `128 MiB`.

Vytvořte a naformátujte tento oddíl a připojte ho do `/data`. Zároveň přidejte odpovídající záznam do `/etc/fstab`.
Na finálním image bude tento oddíl vždy třetí, v `/etc/fstab` tedy jako oddíl uveďte například `/dev/mmcblk0p3`,
pokud bude finální image umístěn na zařízení `/dev/mmcblk0`.

Více informací o rozložení diskových oddílů lze nalézt v oficiální dokumentaci Menderu:

https://docs.mender.io/2.3/devices/yocto-project/partition-configuration

#### Modifikace záznamu pro kořenový adresář v `/etc/fstab`
Změňte oddíl v záznamu pro kořenový adresář (`/`) na `/dev/root`. `/dev/root` je v ramdisku symlink na oddíl, který je
kernelu předám v parametru `root=`. Tento parametr bude Mender měnit podle toho, který oddíl zrovna obsahuje aktuální
verzi systému.

#### Instalace a konfigurace `fw_utils`
Utility `fw_printenv` a `fw_setenv` slouží k modifikaci proměnných prostředí U-Bootu. Tyto utility je třeba
nainstalovat. V Debian repozitářích jsou obsaženy v balíčku `u-boot-tools`. Pokud tyto utility vaše distribuce v
repozitářích nemá, je možné použít binárky získané při [překladu U-Bootu](#building-u-boot "Překlad U-Bootu").

Po instalaci `fw_utils` vytvořte soubor `/etc/fw_env.config` a nastavte offsety k hlavnímu a záložnímu prostředí U-Bootu:

```
# Device to access      offset           env size
/dev/mmcblk0            0x400000         0x4000
/dev/mmcblk0            0x800000         0x4000
```

#### Instalace a konfigurace Mender klienta
V Debianu lze nainstalovat balíček `mender-client`. Klienta je možné nakonfigurovat příkazem `mender bootstrap`, nebo
ruční úravou soboru `/etc/mender.conf`. Je třeba správně nastavit oddíly rootfs A a rootfs B, což budou vždy první
dva oddíly na finálním image (tedy například `/dev/mmcblk0p1` a `/dev/mmcblk0p2`, pokud bude image umístěn na zařízení
`/dev/mmcblk0`). Jako data partition je pak třeba nastavit třetí oddíl (`/dev/mmcblk0p3`). 

Přehled možností v konfiguračním souboru je zde:

https://docs.mender.io/2.3/client-configuration/configuration-file/configuration-options

Poté je třeba vytvořit symlink z `/data/mender` na `/var/lib/mender` a vytvořit soubor `/var/lib/mender/device_type`:

```
device_type=nanopineoplus2
```

`device_type` může být libovolný řetězec. `device_type` systému se porovnává s `device_type` uvedeným v aktualizačním
artefaktu pro zjištění, zda je daná aktualizace určena pro aktuální systém.

`systemd` službu `mender` není třeba povolovat, pokud klient není připojen na Mender server.

#### Soubory v `/boot`
Adresář `/boot` musí obsahovat kernel a device tree zařízení. Na názvu těchto souborů nezáleží, ale při překladu
U-Bootu je třeba poskytnout skriptu správné názvy těchto souborů.

#### Uložení image kořenové partition a data partition
Po provedení všech úprav je třeba systém vypnout a získat image kořenového oddílu a data oddílu. Tyto image budou
použity pro vytvoření finálního image:

```
dd if=/dev/mmcblk0p1 bs=1M of=rootfs.img
dd if=/dev/mmcblk0p2 bs=1M of=data.img
```

### Vytvoření finálního image

#### Překlad U-Bootu
Pro tento krok je třeba skript `mender-demo.py`, funkční OpenEmbedded toolchain a již přeložený ARM SPL. Jak
toolchain, tak ARM SPL jsou k dispozici v archivu `mender-demo.tar.gz`

Po umístění toolchain instalátoru (`poky-glibc-x86_64-meta-toolchain-aarch64-nanopi-neo-plus2-toolchain-3.0.2.sh`) a
ARM SPL (`bl31.bin`) do stejného adresáře se skriptem `mender-demo.py` stačí skript spustit. Skript stáhne U-Boot a
aplikuje patche. Následně se interaktivně dotáže na parametry výsledného image a spustí překlad.

#### Sestavení image
Po úspěšném překladu U-Bootu skript sestaví výsledný bootovatený image:

```
|---------------------------------------------------------------------------------------|
|                                      |                |                |              |
|  SPL + U-Boot + U-Boot Environment   |   rootfs.img   |   rootfs.img   |   data.img   |
|                                      |                |                |              |
|---------------------------------------------------------------------------------------|
```

## Používání Mender klienta
Tato kapitola popisuje základní práci s Mender klientem. Více informací je k dispozici v oficiální dokumentaci:

https://docs.mender.io/2.3

### Vytvoření rootfs snapshot
Pro vytvoření aktualizačního balíčku lze provést snapshot referenčního systému, který bude použit k aktualizaci jiných
zařízení se stejným `device_type`. Snapshot lze na referenčním systému vytvořit takto:

```
mender snapshot dump > rootfs_dump.img
```

Výstup příkazu `mender snapshot dump` je třeba přesměrovat do nějakého mountpointu (například `sshfs`), protože velikost
snapshotu bude stejná, jako velikost systémové oddílu a na systémovém oddílu tedy nebude pro snapshot dost místa.

### Vytvoření aktualizačního artefaktu
Snapshot je třeba zabalit do Mender artefaktu, který lze použít pro aktualizaci jiných zařízení. Pro vygenerování
artefaktu je třeba použít nástroj `mender-artifact`, který lze stáhnout zde:

https://docs.mender.io/2.3/downloads

Následně je třeba vytvořit artefakt:

```
./mender-artifact write rootfs-image -t nanopineoplus2 -n release-v2.0 -u rootfs_dump.img -o release-v2.0-upgrade.mender
```

viz. také:

https://docs.mender.io/development/artifacts/modifying-a-mender-artifact

Po vytvoření artefaktu je možné provést validaci:

```
./mender-artifact validate release-v2.0-upgrade.mender
```

V případě, že mají klienti nakonfigurovaný veřejný klíč pro ověřování podpisů artefaktů, je třeba artefakt podepsat:

```
./mender-artifact sign release-v2.0-upgrade.mender
```

### Provedení aktualizace
Po vytvoření artefaktu lze na jiném zařízení provést aktualizaci:

```
mender install release-v2.0-upgrade.mender
```

Mender klient artefakt ověří a nainstaluje na diskový oddíl, který se aktuálně nepoužívá. Poté se z tohoto oddílu 
pokusí nabootovat. Pokud bude aktualizace úspěšná, je třeba provést `mender commit`, jinak dojde k opětovnému přepnutí
na původní oddíl.