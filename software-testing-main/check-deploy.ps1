 = "https://software-testing-mu.vercel.app/"
 = "https://software-testing-teq9.onrender.com/"

while (True) {
     = False
     = False

    try {
         = Invoke-WebRequest -Uri  -Method Head -UseBasicParsing -TimeoutSec 10
        if (.StatusCode -eq 200) {  = True }
    } catch { }

    try {
         = Invoke-WebRequest -Uri  -Method Head -UseBasicParsing -TimeoutSec 10
        if (.StatusCode -eq 200) {  = True }
    } catch { }

    if ( -and ) {
        Write-Output "ALL SYSTEMS ONLINE!"
        break
    } else {
        Write-Output "Waiting... Vercel: , Render: "
        Start-Sleep -Seconds 15
    }
}
