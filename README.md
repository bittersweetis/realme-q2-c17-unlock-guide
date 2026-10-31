# 真我 Q2：解锁 BL、恢复 Fastboot（公开参考版）

这份教程记录了一台 **realme Q2 / RMX2117CN / Android 11 / C.17** 的成功经验，附上可审查的源码和校验工具，方便其他人理解、复核和补充。

第一次了解，可以先读 [一页简明版](教程简明版.md)，再看下面的完整说明和命令。

**实测结果：BL 解锁后正常开机，Bootloader Fastboot 可以连接并响应查询。没有做 Root。**

> 适用范围：本项目配置只接受实测 C.17 的分区布局和原厂启动文件。其他版本、容量或机型不匹配时会停止，没有强行跳过选项。BL 解锁会清除手机数据；修改 BOOT_1 有启动失败风险。备份不能保证任意故障都可恢复。

## 用一句话理解

**解锁 BL 和打开 Fastboot 是两件事：前者改 seccfg；后者在这台 Q2 上通过 preloader 的布局及标志补丁实现。**

```text
F.12（Android 12）→ 回退 C.17（Android 11）
  → 备份自己的手机
  → 硬件校验 seccfg，先清数据再写解锁配置
  → 正常开机，确认 BL unlocked
  → 从自己的 BOOT_1 原件生成补丁，写回并读回核对
  → 安装匹配的 Fastboot 驱动，验证通信
```

本次没有降到 UI 1.0，没有修改 LK，没有把其他手机的 NV 或底层字库刷进来。

## 先知道本项目验证到哪里

| 内容 | 验证情况 |
|---|---|
| 下面介绍的底层方法 | 私有原型在一台 Q2 C.17 上完成实际解锁、恢复 Fastboot、正常开机 |
| 本公开版的离线辅助工具 | 有自动测试，并用实测原件在本地复核；原件不随包发布 |
| 本公开版 `check_seccfg.py` | 从实测原型整理的只读硬件预检；未在手机上运行公开整理版 |
| 文中的 MTKClient 手动命令 | 已核对 v2.1.4.1 源码中的参数和读写范围；这套逐条命令没有作为完整流程重新刷机实测 |
| 其他手机、固件和容量 | 未验证，不能称为万能教程 |

**公开版是参考实现，不是一键刷机工具。** 项目不会因为解压、运行离线校验或导入源码而自动擦除手机。

## 从 GitHub 开始

本仓库提供教程、源码、测试和校验信息。Windows 运行依赖、驱动及厂商固件没有放入 Git 历史；安装脚本从所列官方来源取得工具，手机固件需自行取得并核对。

先安装 Python 3.10～3.13 x64，再在 PowerShell 执行：

```powershell
git clone https://github.com/bittersweetis/realme-q2-c17-unlock-guide.git
cd realme-q2-c17-unlock-guide
.\setup-source.ps1
.\python.cmd q2_tools.py --help
```

安装脚本仅准备电脑端文件，不连接手机、不安装驱动、不安装固件。完成后先读 [降级教程](docs/rollback.md)（已经是 C.17 可跳过），再逐节执行 [命令清单](docs/commands.md)。

## 文件夹怎么用

- **源码目录**：适合放到 GitHub，含教程、脚本、测试、公开机型配置和许可证。
- **本地完整配套文件夹**：另带 Python x64、现有依赖、干净的 MTKClient v2.1.4.1、ADB/Fastboot、驱动资料和 C.17 回退原包。上传源码时依赖和固件由 `.gitignore` 排除。

本地完整配套文件夹的 `firmware/` 保存实测 C.17 外层回退原包，使用前必须校验；仅有源码时可按固件说明自行取得可信原包。厂商固件不适用本项目的 AGPL，默认排除在 Git 提交之外。文件夹不含个人手机镜像、NV、校准备份、设备唯一标识或账户信息。

## 六步走

### 1. 确认型号和版本，必要时先降级

手机正常开机，打开 OEM 解锁和 USB 调试，并允许电脑授权。检查：

```powershell
.\platform-tools\adb.exe shell getprop ro.product.device
.\platform-tools\adb.exe shell getprop ro.build.display.id
.\platform-tools\adb.exe shell getprop ro.boot.slot_suffix
```

实测为 `RMX2117CN`、`RMX2117_11_C.17`，槽位属性为空。还应结合分区表确认没有 boot_a/boot_b；不能仅因某个属性为空就套用非 A/B 写入方式。

如果还是 F.12 / Android 12，先完成 [详细降级教程：F.12 → C.17](docs/rollback.md)：

1. 备份个人文件，手机充足电；回退按会清除数据准备。
2. 用 `prepare_rollback.py` 核对完整外层原包的大小和 SHA-256。
3. 将原包以 **`oplus_ota_downgrade.zip`** 放到内部存储根目录。
4. 在系统本地安装页面选择它，核对目标 **C.17 / Android 11**，再安装。
5. 安装后正常开机，确认版本 C.17、Android 11、`sys.boot_completed=1`。此时 BL 仍锁定属于预期状态。

完整的电脑校验、ADB 传输、手机页面选择和安装后验收命令均在降级教程中。已经是 C.17 就跳过降级。

### 2. 备份自己的手机

在完整配套文件夹根目录打开 PowerShell。执行 [命令清单第 2 节](docs/commands.md#2-只读备份)，先让电脑等待，再关机、按住两个音量键接 USB，不按电源。

关键要求：保存 seccfg、BOOT_1/2、boot、LK、vbmeta、Recovery、NV/校准及 GPT；BOOT_1、BOOT_2、seccfg 各独立读取两次。工具会核对大小、分区布局、已审查原厂文件和重复读取结果。

这是关键恢复资料，**不是个人文件或全盘备份**。保存到 `private/`，不要上传 GitHub。

### 3. 解锁 BL：先校验，再清数据，再写配置

运行只读预检，验证原始 seccfg 的硬件 SEJ 校验并在电脑生成候选。预检通过后，按 [命令清单第 3 节](docs/commands.md#3-bl-解锁会清空数据) 执行清除 metadata、userdata、md_udc，再写候选首块，随后完整读回验证。

本机第一次只改 seccfg、没有配套清数据，卡在开机标志；恢复原件后正常。第二次配套清除上述三个分区后进入设置向导。没有做逐分区对照实验，不能据此断言三个分区各自都必须擦除。

开机后重新开启并授权 USB 调试，看到以下结果才算解锁验收通过：

```text
ro.boot.flash.locked = 0
ro.boot.vbmeta.device_state = unlocked
sys.boot_completed = 1
```

### 4. 恢复 Fastboot：重新读 BOOT_1，再生成补丁

仅解锁后，本机 `adb reboot bootloader` 仍返回系统。下一步是 [命令清单第 4 节](docs/commands.md#4-恢复-fastboot仅写-boot_1)：

1. 再次备份 BOOT_1、BOOT_2 和当前 seccfg。
2. 用 `q2_tools.py patch-preloader` 在电脑生成补丁。
3. 工具严格检查原件哈希、布局、空白尾部和代码搬移结果；再与固定版本上游脚本输出逐字节对照。
4. 只写 **UFS BOOT_1 的 4 MiB**，完整读回，检查 BOOT_2、seccfg 未变。

**BOOT_1 不是 Android 的 boot 分区。** 这里不修改 boot.img，也不代表已安装 Root。

### 5. 进入 Fastboot，处理 Windows 驱动

先正常开机，再执行：

```powershell
.\platform-tools\adb.exe reboot bootloader
```

本机屏幕显示：

```text
secure boot is not enable
skip fastboot verify when secureboot is off
fastboot_unlock_verify ok
```

这些文字与本次补丁效果相符。它们本身不能证明电脑已能通信，也不意味着写过熔丝或关闭了所有安全机制。

本机当时 USB 反复响、屏幕不变，实际是 Windows 对 `VID_0E8D&PID_201C` 报错误码 28，缺驱动。用 [微软更新目录的匹配驱动](https://www.catalog.update.microsoft.com/ScopedViewInline.aspx?updateid=67446b50-e7f8-454a-9155-f48ddf362d01) 后恢复通信。具体核对方法见 [驱动说明](docs/drivers.md)。

### 6. 验证能通信，也能回系统

```powershell
.\platform-tools\fastboot.exe devices
.\platform-tools\fastboot.exe getvar unlocked
.\platform-tools\fastboot.exe getvar is-userspace
```

本机为 `unlocked: yes`、`is-userspace: no`，连续 6 次版本查询成功。这里只验证了查询，没有测试所有刷写命令。

`fastboot reboot` 这次返回 OKAY 后进入关机充电，单独长按电源约 3～5 秒才正常开机。回系统后再次检查 BL 状态和 `sys.boot_completed=1`。

## 遇到问题先看这里

| 现象 | 这次的经验 |
|---|---|
| 黑屏、有提示音 | 先看实际 BROM/DA 握手，不等于已经连接成功 |
| 几分钟停在 realme | 记录总时长及 ADB 状态；本机成功启动也曾等待数分钟，不要立刻反复刷写 |
| 解锁后进不了 Recovery | 本次成功路线直接在 DA 重置数据，不依赖解锁后的 Recovery |
| ADB unauthorized | 手机上允许调试，才能读取系统状态 |
| Fastboot 有字但没设备 | 检查 Windows 硬件 ID 和驱动问题码 |
| 程序退出码非 0 | 同时查看读回结果、断线原因和手机状态，不能单靠退出码判断 |

## 开发和开源

```powershell
python -m unittest discover -s tests -v
```

- 自编代码及本文档按 **AGPL-3.0-only** 发布，见 [LICENSE](LICENSE)。
- preloader 算法源自 Shocked-Cat / Max_Goblin，上游固定脚本及许可证位于 `third_party/`。
- MTKClient、Python、依赖和 Windows 工具按各自许可证提供，见 [第三方说明](THIRD_PARTY_NOTICES.md)。驱动和厂商固件不因本项目而变成开源软件。
- 提交问题时提供型号、系统版本、错误信息和脱敏截图；不要提交 `private/`、hwparam、`.state`、NV 或完整设备日志。
- 发布流程见 [发布检查](docs/publishing.md)。GitHub 中仅提交公开源码目录，不包含本地配套二进制和厂商固件。

原理和边界见 [实现说明](docs/implementation.md)。
