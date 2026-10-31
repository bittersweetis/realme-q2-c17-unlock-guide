# 命令清单：逐步执行，每步检查结果

所有命令都在项目根目录运行。以下范围只对应本项目严格检查的 RMX2117CN C.17 布局。**先阅读 README 的验证范围；公开整理版没有在手机上重新执行整套流程。**

同一项目目录只连接同一台手机。更换手机必须使用全新解压目录和自己的新备份，不能复用会话或候选文件。手机写入中不要拔线。任何校验失败都停止，不修改哈希白名单、不跳过检查。

## 1. 环境

完整配套文件夹包含 `runtime/`，用 `python.cmd` 运行 Python，用 `mtk.cmd` 运行 MTKClient。仅有源码目录时，需要先安装 Python 3.10～3.13 x64，并运行 `setup-source.ps1` 取得依赖；该脚本不安装驱动、不访问手机。

```powershell
.\python.cmd q2_tools.py --help
.\mtk.cmd --help
New-Item -ItemType Directory -Force private,private\backup,private\fastboot | Out-Null
```

UsbDk 及 Fastboot 驱动的安装与核对见 [drivers.md](drivers.md)。仅在需要时手动安装；不关闭驱动签名校验。

**手机仍是 F.12 / Android 12 时，先完成 [降级步骤](rollback.md)，确认 C.17 正常开机后再执行下面的 BROM 备份。** 安装降级包使用手机系统本地更新，不使用下面的擦除和写入命令。

## 2. 只读备份

程序先等待，手机关机、拔线，按住音量上和音量下接 USB，不按电源。工具确认 DA 连接后松键。需要重新接入时，仍连接同一台手机。

```powershell
.\mtk.cmd printgpt
.\mtk.cmd rl private/backup --skip special_preload,super,cache,userdata
.\mtk.cmd ro 0 0x400000 private/boot1.bin --parttype boot1
.\mtk.cmd ro 0 0x400000 private/boot1-second.bin --parttype boot1
.\mtk.cmd ro 0 0x400000 private/boot2.bin --parttype boot2
.\mtk.cmd ro 0 0x400000 private/boot2-second.bin --parttype boot2
.\mtk.cmd r seccfg private/seccfg-second.bin
.\python.cmd q2_tools.py backup-check private
.\python.cmd q2_tools.py verify private
```

`rl` 保存 GPT 用户区分区；BOOT_1/2 是另外读取的区域。跳过了几个大分区和个人数据，不能称为全盘备份。上游 `rl` 保存的 `gpt_backup.bin` 与 `gpt.bin` 来自同一次主表数据，不能把它当成已独立读取的末尾备用 GPT。

确认所有命令完成，`backup-check` 和 `verify` 均 PASS。备份目录单独复制到另一个可靠存储，再核对哈希。工具验证的是文件内容，不保证任何损坏状态下都能恢复。

如果已正常处于 BL unlocked，可跳过第 3 节，但仍要做自己的备份。

## 3. BL 解锁（会清空数据）

先确保个人文件另有备份。运行只读硬件预检：

```powershell
.\python.cmd check_seccfg.py --directory private
```

它会重新检查当前手机的芯片、存储身份、GPT、原厂启动文件及 seccfg，使用硬件 SEJ 验证原件并生成候选，再用独立对象验证。只写电脑文件，不擦除或写入手机闪存。

**只有预检明确 PASS 后，保持同一台手机，才继续下面的破坏性步骤。** 任何脚本报错都不继续。公开版只提供可审查的手动流程，不具备实测私有原型那样的整段事务日志和写后失败自动回退。

```powershell
# 破坏性步骤：清除手机应用、设置和个人文件
.\mtk.cmd e metadata,userdata,md_udc

# 检查上一步三个分区都成功完成后，写入本机硬件验证过的 4 KiB 候选
# 此偏移仅对应本项目已检查的 C.17 GPT
.\mtk.cmd wo 0x25000000 0x1000 private/seccfg-candidate-block.bin

# 完整读回 8 MiB，比对首块和不应变化的其余内容
.\mtk.cmd r seccfg private/seccfg-readback.bin
.\python.cmd q2_tools.py check-seccfg-readback private private/seccfg-readback.bin
```

预检通过不代替确认擦除结果；上游命令必须逐项显示擦除完成。本手动清单没有自动对三个分区做首、中、尾空白抽样，实测私有原型做过该抽样，两者的验证深度不同。

读回 PASS 后退出 DA：

```powershell
.\mtk.cmd reset
```

必要时松开所有音量键，单独长按电源开机。首次设置完成后重开 USB 调试并允许授权，检查：

```powershell
.\platform-tools\adb.exe shell getprop ro.boot.flash.locked
.\platform-tools\adb.exe shell getprop ro.boot.vbmeta.device_state
.\platform-tools\adb.exe shell getprop sys.boot_completed
```

期望 `0`、`unlocked`、`1`。卡启动时先保留记录，不反复写入，不把“出现解锁提示”当成已完成。

## 4. 恢复 Fastboot：仅写 BOOT_1

先确认 C.17、BL unlocked 且系统正常启动。重新进入 BROM/DA 后，读取当前原件和配置：

```powershell
.\mtk.cmd ro 0 0x400000 private/fastboot/boot1-original.bin --parttype boot1
.\mtk.cmd ro 0 0x400000 private/fastboot/boot1-second.bin --parttype boot1
.\mtk.cmd ro 0 0x400000 private/fastboot/boot2-original.bin --parttype boot2
.\mtk.cmd ro 0 0x400000 private/fastboot/boot2-second.bin --parttype boot2
.\mtk.cmd r seccfg private/fastboot/seccfg-before.bin
.\python.cmd q2_tools.py compare private/boot1.bin private/fastboot/boot1-original.bin
.\python.cmd q2_tools.py compare private/fastboot/boot1-original.bin private/fastboot/boot1-second.bin
.\python.cmd q2_tools.py compare private/boot2.bin private/fastboot/boot2-original.bin
.\python.cmd q2_tools.py compare private/fastboot/boot2-original.bin private/fastboot/boot2-second.bin
.\python.cmd q2_tools.py verify private
.\python.cmd q2_tools.py patch-preloader private/fastboot/boot1-original.bin private/fastboot/boot1-patched.bin
```

全部 PASS 后，只写 BOOT_1，并检查完整读回和两个不应变化的对象：

```powershell
# 写入动作：UFS BOOT_1 偏移 0，长度恰好 4 MiB
.\mtk.cmd wo 0 0x400000 private/fastboot/boot1-patched.bin --parttype boot1
.\mtk.cmd ro 0 0x400000 private/fastboot/boot1-readback.bin --parttype boot1
.\python.cmd q2_tools.py compare private/fastboot/boot1-patched.bin private/fastboot/boot1-readback.bin
.\mtk.cmd ro 0 0x400000 private/fastboot/boot2-after.bin --parttype boot2
.\python.cmd q2_tools.py compare private/fastboot/boot2-original.bin private/fastboot/boot2-after.bin
.\mtk.cmd r seccfg private/fastboot/seccfg-after.bin
.\python.cmd q2_tools.py compare private/fastboot/seccfg-before.bin private/fastboot/seccfg-after.bin
.\mtk.cmd reset
```

正常开机，确认 C.17、解锁状态和 `sys.boot_completed=1`。再发送 `adb reboot bootloader`，按 README 第 5、6 步验证 Fastboot 和 Windows 驱动。

## 5. 需要回退时

### BOOT_1 原件

前提：能够进入本机 BROM/DA；已核对当前 BOOT_1 是刚写入的候选、BOOT_2 仍是原件，且备份内容有效。保留故障快照，不用其他手机的文件。

```powershell
.\python.cmd q2_tools.py verify private
.\mtk.cmd ro 0 0x400000 private/fastboot/boot1-before-restore.bin --parttype boot1
.\python.cmd q2_tools.py compare private/fastboot/boot1-patched.bin private/fastboot/boot1-before-restore.bin
# 只有以上检查都成功才恢复本机原件
.\mtk.cmd wo 0 0x400000 private/fastboot/boot1-original.bin --parttype boot1
.\mtk.cmd ro 0 0x400000 private/fastboot/boot1-restored.bin --parttype boot1
.\python.cmd q2_tools.py compare private/fastboot/boot1-original.bin private/fastboot/boot1-restored.bin
```

这只是受限的手动回退示例。未识别的新内容、读回不符或通道无法建立时应停止分析；没有实际测试过 BOOT_1 恢复写入，不能承诺照做即可救回。

### seccfg / 回锁

本机首次失败后确实恢复过 seccfg，但恢复前严格确认 boot、vbmeta、LK、LK2 都是原厂，并审查了启动后新增的 AVB 记录。本文不提供无条件回锁命令。已修改引导镜像或不能确认当前状态时，先分析完整恢复顺序。

### 连接需要 EMI / preloader

有些新会话可能需要匹配固件的原始 preloader 提供内存初始化数据。实测私有原型使用了经过核验的本机 C.17 原件。它不在公开包中，也不能把补丁 BOOT_1 当成 raw preloader 随便传入。缺少正确资料、无法再次建立通道时，应先解决连接和恢复条件再做写入。
