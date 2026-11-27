# SFW Windows x64 补丁构建

这是基于官方 sing-box 发布版的自用 Windows 客户端，包含 [SagerNet/tailscale PR #12](https://github.com/SagerNet/tailscale/pull/12) 的 UDP 绑定恢复修复。

[下载页面](https://github.com/stellar-gemini/sfw-patched-builds/releases)同时跟踪官方稳定版和预览版。GitHub Actions 每 6 小时分别检查两个频道中最新且带有官方 SFW x64 安装包的版本；两边独立构建，一边失败不会阻止另一边发布。预览版标为 Pre-release，不取代稳定版的 Latest。也可以在 [Actions](https://github.com/stellar-gemini/sfw-patched-builds/actions/workflows/windows.yml) 手动运行：版本标签留空时检查两个频道，填写标签（例如 `v1.15.0-alpha.14`）时只处理该版本。

从发行页下载 `SFW-<版本>-x64-pr12.exe`。**安装和使用 SFW 无需先导入证书。** SFW 接受有效的自签名代码签名证书，并检查 GUI、daemon 和应用内更新安装包的签名者是否一致。Windows 仍可能提示发布者不受信任，能否运行安装包取决于本机策略。[SFW 签名验证源码](https://github.com/SagerNet/sing-box/blob/v1.14.4/experimental/boxdd/authenticode_windows.go#L50)

安装前可用 `Get-FileHash -Algorithm SHA256 -LiteralPath <安装包>` 计算安装包的 SHA-256，并与同一发行页的 `SHA256SUMS.txt` 对照。随包提供的 `SFW-Patched-Code-Signing.cer` 是公开签名证书，可用下文指纹核对。

发行标签带 `-auto1` 的安装包内置本仓库的更新源。在客户端启用检查更新后，可以在应用内下载更新并确认安装。客户端的稳定更新频道只接收稳定版；预览更新频道也接收预览版。更新时 daemon 仍会校验安装包签名。此前的补丁版需要从 Releases 手动装一次新版，以接入这个更新源。

构建使用官方标签锁定的 GUI、dashboard 和 Go 依赖。流水线比对 `go.sum`，在该版本实际使用的 Tailscale 依赖上应用已固定的 PR 补丁，再运行 UDP 恢复回归测试。补丁冲突、测试失败、签名无效或 daemon 没有使用补丁后的依赖时，构建失败且不会发布。已有同版本、同官方提交、同补丁的成功产物时，定时任务跳过构建。

构建按 `go.mod` 中实际的 Tailscale 依赖选择补丁。

| Tailscale 依赖 | 补丁文件 | 最少回归测试 |
| --- | --- | --- |
| `v1.102.x-sing-box-…` | `patches/tailscale-pr12.patch` | 15 项 |
| `v1.106.x-sing-box-…` | `patches/tailscale-pr12-ts106.patch` | 16 项，包含 socket group 生命周期 |

106 补丁将同一恢复方案适配到新版的 socket group 和接收接口。两套补丁独立保存，构建使用的补丁、测试数和 SHA-256 写入 `build-info.json`。未知依赖版本会停止构建并提示适配。独立的兼容性工作流在 Linux 上同时验证两套补丁，开启 race 检测，每项测试重复三次。发布工作流在 Windows 上运行所选版本的回归测试。

每个发行版包含安装包、证书公钥、`SHA256SUMS.txt` 及 `build-info.json`。清单记录上游源码提交、补丁校验值和构建记录。私钥存放在该仓库的 Actions Secrets。

对应的源码和构建方式可从该发行标签获取。按 `build-info.json` 中记录的提交从 [sing-box](https://github.com/SagerNet/sing-box)、[桌面客户端](https://github.com/SagerNet/sing-box-for-desktop) 和 [dashboard](https://github.com/SagerNet/sing-box-dashboard) 获取源码，并按同一标签的 Actions 工作流下载 `go.sum` 锁定的依赖和应用 `patches/` 中的补丁。各组件保留上游许可证和版权声明。

专用证书 SHA-256：`4880F36AE06B4E32E8A7C563628EC532FF7923AF38F2DE6B462888F638047C54`
