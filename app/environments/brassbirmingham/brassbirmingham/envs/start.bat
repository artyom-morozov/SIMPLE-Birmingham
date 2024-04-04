@echo off
REM Start VS Code in the current directory
start code .

REM Navigate to the Python virtual environment and activate it
call "D:\Projects\Brass Player\SIMPLE-Birmingham\app\environments\brassbirmingham\brassbirmingham\envs\local\Scripts\activate.bat"

REM Keep the window open and give control back to the user
cmd /k