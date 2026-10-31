# 降级教程：F.12 / Android 12 → C.17 / Android 11

**这是整条路线的第一阶段。** 本机先由系统本地更新成功回退，再进行 BL 解锁和 Fastboot 恢复。没有降到 UI 1.0，也没有直接从 F.12 安装 A.27。

实测范围为 **真我 Q2 / RMX2117CN / RMX2117_11_F.12 → RMX2117_11_C.17**。其他型号、地区或版本不能仅因名称相似就套用。

## 1. 开始前：保存个人文件，确认版本

回退按会清空手机数据准备。先把照片、聊天记录、验证器等重要资料保存到手机以外，并确认备份可用。后续 BL 解锁还会再次重置数据，不能把后面的关键分区备份当成这一步的个人文件备份。

本次回退通过原厂系统更新器完成，不需要先解锁 BL。手机先充电到至少 50%，留出存放约 4 GB 安装包及安装临时文件的空间。

在“设置 → 关于设备 / 关于手机”查看型号和版本。已开启 USB 调试并允许电脑授权时，也可在项目根目录执行以下只读命令：

```powershell
.\platform-tools\adb.exe shell getprop ro.product.device
.\platform-tools\adb.exe shell getprop ro.build.display.id
.\platform-tools\adb.exe shell getprop ro.build.version.release
.\platform-tools\adb.exe shell getprop ro.separate.soft
```

本机降级前分别为 `RMX2117CN`、`RMX2117_11_F.12`、`12`、`20613`。已经处于 C.17 / Android 11 时直接进入后面的备份阶段，不重复回退。

## 2. 选对回退包

本机使用的原始文件名：

```text
realme UI3.0 真我Q2降级2.0回退包.zip
```

目标是 **UI 3.0 → UI 2.0 / C.17**。它是一个完整外层 ZIP，里面还有 `ota_downgrade.zip`。手机这次接受的是外层原包，不需要提取内层或重新压缩。

原包大小 **3,997,003,120 字节**，SHA-256：

```text
1313770a2618a2b4037e8b1e297cbc07a07790a7fe838fa957f85a2294add646
```

本地完整配套文件夹中的 `firmware/oplus_ota_downgrade.zip` 就是这份外层原包，仅改了文件名。若使用不含固件的源码目录，请自行通过可信渠道取得匹配的原始回退包；本项目没有已验证的官方固件直链，不编造下载地址。

厂商固件与开源脚本分别处理：固件不适用本项目的 AGPL 许可，并已被 `.gitignore` 排除。上传 GitHub 时保留固件说明、文件名和哈希，源码安装脚本也不会自动下载或安装手机固件。

## 3. 在电脑校验原包

若文件夹里已有配套原包：

```powershell
.\python.cmd prepare_rollback.py ".\firmware\oplus_ota_downgrade.zip"
```

自行下载的原包可这样检查，并复制为正确文件名：

```powershell
# 将下面路径替换为自己下载的原包路径
.\python.cmd prepare_rollback.py "D:\下载\realme UI3.0 真我Q2降级2.0回退包.zip" --copy-to ".\firmware"
```

脚本检查精确大小和 SHA-256；只有匹配才复制成 `oplus_ota_downgrade.zip`，不会重新压缩、修改包内容、访问手机或触发安装。发现不一致立即停止，不把未知文件改名后继续试。

也可以用 PowerShell 独立核对：

```powershell
Get-FileHash -LiteralPath ".\firmware\oplus_ota_downgrade.zip" -Algorithm SHA256
```

哈希相同只证明与本次原包内容一致，仍须由手机系统检查签名和兼容性。

## 4. 传到手机：内置存储根目录、固定文件名

保持手机正常开机并允许 USB 调试，在电脑执行：

```powershell
.\platform-tools\adb.exe push ".\firmware\oplus_ota_downgrade.zip" /sdcard/oplus_ota_downgrade.zip
.\platform-tools\adb.exe shell sha256sum /sdcard/oplus_ota_downgrade.zip
```

等传输完成，再把手机端摘要与前面的 SHA-256 比较。这里 `/sdcard/` 指“内部存储 / 手机存储”的最外层，不是 Download 文件夹，也不是外置 SD 卡。

不用 ADB 时，也可以通过 USB 文件传输复制，在文件管理器中确认最终名称恰好是 `oplus_ota_downgrade.zip`，不要出现重复的 `.zip.zip` 后缀。

本机实际识别对照：

本机识别过程：

| 内容和位置 | 结果 |
|---|---|
| 外层 ZIP，放 Download，名为 Q2_UI3_to_UI2_C17.zip | 提示安装包不匹配 |
| 提取出的内层 ota_downgrade.zip，放根目录 | 验证失败 |
| 完整外层 ZIP，仅改名为根目录 `oplus_ota_downgrade.zip` | 验证通过，目标 C.17 |

最后只调整外层原包的文件名和位置，没有修改签名或绕过验证。这是本机的成功组合，不是所有更新器的通用规则。

## 5. 在手机上选择“本地安装”

1. 打开设置中的系统更新页面；通常从“关于设备 / 关于手机”的版本卡片进入，再查看右上角菜单是否有“本地安装”。不同更新器的菜单文字和入口可能不同，本机最终由系统本地更新页面安装。
2. 选择内部存储根目录的 `oplus_ota_downgrade.zip`，等待系统验证。
3. **核对页面显示目标 `RMX2117_11_C.17`、Android 11，大小约 4.00 GB。** 本次成功验证页面保留了“realme UI 3.0”的页面文字，因此以目标版本号和 Android 版本为核对重点。
4. 确认已备份个人文件并接受清除数据，再点“立即安装”。

若找不到本地安装入口，先确认更新器版本和页面；本教程没有为所有 F.12 更新器验证统一入口。若提示“不匹配 / 验证失败”，先检查外层原包、摘要、名称、根目录和本机版本，不强行安装、改包或把其他型号固件拿来代替。

## 6. 安装期间等待完成

手机断开 ADB、重启并显示安装进度是本次出现过的过程。保持供电，安装期间不要拔线、按组合键或强制重启。

本机首次开机曾在 realme 标志停约 4 分钟，随后正常进入系统。几分钟停留不能单独判定失败；若出现明确报错或持续无法启动，保留画面和时间记录，先排查，不立即叠加底层写入。

## 7. 开机后验收，再进入 BL 阶段

完成设置向导，重新开启 USB 调试并允许电脑授权，执行：

```powershell
.\platform-tools\adb.exe shell getprop ro.product.device
.\platform-tools\adb.exe shell getprop ro.build.display.id
.\platform-tools\adb.exe shell getprop ro.build.version.release
.\platform-tools\adb.exe shell getprop ro.boot.flash.locked
.\platform-tools\adb.exe shell getprop sys.boot_completed
```

本次实际回退后的结果：

```text
ro.product.device = RMX2117CN
ro.build.display.id = RMX2117_11_C.17
ro.build.version.release = 11
ro.boot.flash.locked = 1
sys.boot_completed = 1
```

这说明 **降级完成，但 BL 仍锁定**，属于预期状态。再检查开发者选项中的 OEM 解锁许可，然后回到 [命令清单第 2 节：备份](commands.md#2-只读备份)，开始后续解锁准备。
