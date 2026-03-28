# VHS tape for demonstrating SARIF analysis tools
# This demo shows how to analyze SARIF output files

Output demos/06-sarif-analysis.gif

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

Type "./scripts/sarif-analysis/deduplicate-by-product-operation.sh results/SasUriInResponse-results.sarif"
Enter 1
Sleep 4s

Type "./scripts/sarif-analysis/parse-sarif-endpoints.sh -f csv results/SasUriInResponse-results.sarif"
Enter 1
Sleep 4s

Type "./scripts/sarif-analysis/prioritize-threats.sh --threshold high results/SasUriInResponse-results.sarif"
Enter 1
Sleep 4s
