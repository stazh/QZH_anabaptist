New-Item -Path 'C:\QZH_anabaptist\outputs' -ItemType Directory -Force
Copy-Item -Path 'C:\Users\rloet\Downloads\Ausgabeordner\QZH_*.xml' -Destination 'C:\QZH_anabaptist\outputs\' -Force
Get-ChildItem 'C:\QZH_anabaptist\outputs' -Filter 'QZH_*.xml' | Select-Object -First 20 | ForEach-Object { $_.Name }
