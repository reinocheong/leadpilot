$wc = New-Object System.Net.WebClient
try {
    $r = $wc.DownloadString('http://localhost:9222/json/version')
    Write-Output "OPEN|$r"
} catch {
    Write-Output "CLOSED|$($_.Exception.Message)"
}
