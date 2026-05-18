# Todo #9: List all .md files in the project

Status: in_progress
Owner: @worker
Tags: #simple #test
Branch: main

Run `find /root/t1d -name "*.md" -not -path "./venv/*" -not -path "./node_modules/*" | sort` and report the full list of markdown files.
