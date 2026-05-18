# Todo #6: Count total number of files in the project

Status: completed
Owner: @researcher
Tags: #simple #test
Branch: main

Run `find /root/t1d -not -path "./venv/*" -not -path "./node_modules/*" -not -path "./.git/*" -not -path "./.pi/*" -type f | wc -l` and report the total file count.
