# Todo #3: Count lines of code in the project

Status: completed
Owner: @researcher
Tags: #simple #test
Branch: main

Run `find . -name "*.py" -not -path "./venv/*" -not -path "./node_modules/*" | xargs wc -l` and report the total line count.
