@echo off
echo =========================================
echo BayesElo Analysis for Chess Engines
echo =========================================
echo.

cd /d "S:\Maker Stuff\Programming\Chess Engines\Chess Engine Playground\engine-metrics"

echo Running BayesElo analysis...
python bayeselo_analyzer.py

echo.
echo Analysis complete! Check the generated files:
echo - bayeselo_analysis_report.md (detailed report)
echo - bayeselo_ratings.csv (for Excel)
echo - bayeselo_analysis_results.json (raw data)
echo.

pause
