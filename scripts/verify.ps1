$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$desktop = 'src/sing-box/clients/desktop'
$bin = Join-Path $desktop 'release/win-unpacked'
$asar = Join-Path $bin 'resources/app.asar'
node -e 'if (!require("node:fs").readFileSync(process.argv[1]).includes(Buffer.from("+ts-udp-rebind"))) throw new Error("Missing sidebar version label");' $asar
$installer = @(Get-ChildItem "$desktop/release/SFW-*-x64.exe" -File)
if ($installer.Count -ne 1) {
    throw "Expected one x64 installer, found $($installer.Count)."
}
$certPath = (Resolve-Path dist/SFW-Patched-Code-Signing.cer).Path
$cert = [Security.Cryptography.X509Certificates.X509Certificate2]::new($certPath)
if ((Get-FileHash $certPath).Hash -ne (Get-FileHash SFW-Patched-Code-Signing.cer).Hash) {
    throw 'The configured signing certificate differs from the public certificate pinned in the repository.'
}
$daemon = Join-Path $bin 'resources/daemon/sing-box-daemon.exe'
foreach ($file in @($installer[0].FullName, (Join-Path $bin 'sing-box.exe'), $daemon)) {
    $signature = Get-AuthenticodeSignature -LiteralPath $file
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Thumbprint -ne $cert.Thumbprint) {
        throw "Wrong or invalid Authenticode signature on ${file}: $($signature.Status)."
    }
}
$metadata = (go version -m $daemon) -join "`n"
if ($metadata -notmatch 'github\.com/sagernet/tailscale\s+v' -or
    $metadata -notmatch '=>\s+\.\.[/\\]tailscale\s') {
    throw 'The packaged daemon does not reference the local patched Tailscale module.'
}
$name = "SFW-$($env:UPSTREAM_TAG.Substring(1))-x64-pr12.exe"
Copy-Item -LiteralPath $installer[0].FullName -Destination (Join-Path dist $name)
$manifest = Get-Content dist/build-info.json -Raw | ConvertFrom-Json -AsHashtable
$manifest['signing_thumbprint_sha1'] = $cert.Thumbprint
$manifest['signing_fingerprint_sha256'] = (Get-FileHash $certPath -Algorithm SHA256).Hash
$manifest['build_run'] = "$env:GITHUB_SERVER_URL/$env:GITHUB_REPOSITORY/actions/runs/$env:GITHUB_RUN_ID"
$manifest['daemon_sha256'] = (Get-FileHash $daemon -Algorithm SHA256).Hash
$manifest['installer_sha256'] = (Get-FileHash (Join-Path dist $name) -Algorithm SHA256).Hash
$manifest | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8NoBOM dist/build-info.json
@($name, 'SFW-Patched-Code-Signing.cer', 'build-info.json') | ForEach-Object {
    "$((Get-FileHash (Join-Path dist $_) -Algorithm SHA256).Hash.ToLowerInvariant())  $_"
} | Set-Content -Encoding ascii dist/SHA256SUMS.txt
