# VHS tape for demonstrating complete workflow from setup to results
# This demo shows the end-to-end workflow

Output demos/07-complete-workflow.gif

Set Shell bash
Set FontSize 16
Set Width 1000
Set Height 720
Set Theme "TokyoNight"
Set TypingSpeed 80ms
Set WindowBar ColorfulRight

Hide
Type "cd /home/runner/work/SpecRecon/SpecRecon"
Enter 1
Show

Type "python3 refresh_database.py --path specification/logic"
Enter 1
Sleep 30s

Type "python3 analyze.py --source azure-rest-api-specs/specification/logic"
Enter 1
Sleep 8s

Type "./run-queries.sh"
Enter 1
Sleep 30s

Type "./scripts/sarif-analysis/prioritize-threats.sh --threshold high results/SasUriInResponse-results.sarif"
Enter 1
Sleep 4s
