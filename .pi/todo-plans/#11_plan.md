# Todo #11: List all .json files in the project

Status: completed
Owner: @scout
Tags: #simple #test
Branch: main

Run `find /root/t1d -name "*.json" -not -path "./venv/*" -not -path "./node_modules/*" -not -path "./.git/*" | sort` and report the full list.
