@echo off
echo Starting Mental Health Diagnosis System Frontend...

REM npm install if it node_modules doesn't exist
if not exist node_modules (
    echo Installing dependencies...
    npm install
)

echo node_modules installed...
echo Starting the frontend...
npm start

echo Frontend started successfully!
