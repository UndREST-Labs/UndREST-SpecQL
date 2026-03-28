# VHS tape for demonstrating the SpeQL setup process
# This demo shows how to set up SpeQL including installing dependencies

Output demos/01-setup.gif

Set Shell bash
Set FontSize 16
Set Width 1000
Set Height 720
Set Theme "TokyoNight"
Set TypingSpeed 80ms
Set WindowBar ColorfulRight

Hide
Type "rm -rf /tmp/SpecRecon"
Enter 1
Type "cd /tmp"
Enter 1
Show

Type "git clone https://github.com/SpecRecon/SpecRecon.git"
Enter 1
Sleep 3s

Type "cd SpecRecon"
Enter 1
Sleep 500ms

Type "pip3 install -r requirements.txt"
Enter 1
Sleep 5s

Type "./setup.sh"
Enter 1
Sleep 8s
