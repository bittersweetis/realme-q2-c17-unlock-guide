# Windows 驱动说明

BROM/DA 通道与 Bootloader Fastboot 通道使用的驱动环节不同。先看设备管理器中当前设备的硬件 ID、问题码，再选择处理方式，不给所有 MTK 端口强行装同一驱动。

## UsbDk

本机使用 UsbDk 1.0.22 x64。Windows 配套包 `drivers/UsbDk_1.0.22_x64.msi` 从[官方项目发布页](https://github.com/daynix/UsbDk/releases/tag/v1.00-22)补存，签名检查为 Valid、签名人为 Red Hat, Inc.。仅归档和验签，没有在整理期间安装。

SHA-256：`91f6f695e1e13c656024e6d3b55620bf08d8835ef05ee0496935ba6bb62466a5`。

系统已具备可工作版本时无需因为解压包而重装。

## Fastboot 接口

本机进入 Fastboot 后枚举为 `USB\VID_0E8D&PID_201C`，错误码 28，表示缺驱动。使用[微软更新目录的 MediaTek 条目](https://www.catalog.update.microsoft.com/ScopedViewInline.aspx?updateid=67446b50-e7f8-454a-9155-f48ddf362d01)中的匹配驱动。

Windows 配套包保存了原 CAB 和解压文件，CAB SHA-256：

```text
bcebf41bfc2c081544cc3ce4ebdc0b8d890f6411c1d2b925dc2f6b6a0ccd6c5b
```

核对硬件 ID 匹配、x64 CAT 签名 Valid 后，管理员 PowerShell 中手动执行：

```powershell
pnputil.exe /add-driver ".\drivers\fastboot\android_winusb.inf" /install
```

没有修改 INF、关闭驱动签名或调整 Windows 安全启动设置。设备显示名可能仍为 Android ADB Interface，以实际 `fastboot devices/getvar` 响应为准。

本机安装后的 `oemXX.inf` 编号是 Windows 分配结果，不应套用到其他电脑。配套包只保存干净的安装文件，不包含原电脑安装日志或设备实例 ID。
