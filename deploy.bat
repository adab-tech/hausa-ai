@echo off
echo ============================================================
echo               HAUSA AI — CLOUD RUN DEPLOYER                  
echo ============================================================
echo.
echo Project ID: gen-lang-client-0675423068
echo Region:     europe-west1
echo Service:    adabtech
echo.
echo Building container image in the cloud via Google Cloud Build...
cmd /c gcloud builds submit --tag europe-west1-docker.pkg.dev/gen-lang-client-0675423068/adabtech/adabtech:latest --project gen-lang-client-0675423068
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Cloud build failed. Please verify gcloud credentials.
    pause
    exit /b %errorlevel%
)

echo.
echo Deploying to Google Cloud Run...
cmd /c gcloud run deploy adabtech --image europe-west1-docker.pkg.dev/gen-lang-client-0675423068/adabtech/adabtech:latest --region europe-west1 --project gen-lang-client-0675423068 --allow-unauthenticated
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Cloud Run deployment failed.
    pause
    exit /b %errorlevel%
)

echo.
echo ============================================================
echo [SUCCESS] Hausa AI is now live!
echo Service URL: https://adabtech-1015422054034.europe-west1.run.app
echo ============================================================
pause
