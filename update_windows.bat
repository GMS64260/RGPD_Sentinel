@echo off
echo Mise a jour de l'analyseur RGPD pour Windows Server

REM Creer le repertoire des taches s'il n'existe pas
if not exist "saved_analyses\tasks" (
    echo Creation du repertoire des taches...
    mkdir "saved_analyses\tasks"
) else (
    echo Le repertoire des taches existe deja.
)

REM Sauvegarder app.py s'il a ete modifie localement
if not exist app.py.backup (
    echo Sauvegarde de app.py...
    copy app.py app.py.backup
) else (
    echo La sauvegarde app.py.backup existe deja.
)

REM Mettre a jour depuis GitHub
echo Mise a jour depuis GitHub...
git checkout app.py analyzer/storage.py analyzer/background_task.py
git pull origin main

REM Creer un fichier de log pour le debugage
echo. > saved_analyses\tasks\debug.log
echo Fichier de log cree.

echo Redemarrage de l'application...
REM Ajoutez ici la commande pour redemarrer le service sur Windows Server
REM Par exemple:
REM net stop RGPDAnalyzer
REM net start RGPDAnalyzer
REM ou
REM powershell -Command "Restart-Service RGPDAnalyzer"

echo Mise a jour terminee!
pause
