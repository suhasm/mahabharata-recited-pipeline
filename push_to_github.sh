#!/bin/bash
# push_to_github.sh — create a GitHub repo and push this pipeline.
# The bundle was assembled without a live .git (sandbox restriction). Run these
# commands locally after unpacking mahabharata-recited-pipeline.tgz.
set -e

REPO_NAME="mahabharata-recited-pipeline"
# --- Option A: GitHub CLI (easiest; https://cli.github.com) ---
#   gh auth login
#   cd mahabharata-recited-pipeline
#   git init
#   git add -A
#   git commit -m "Mahabharata CE recitation pipeline: scripts, naming data, docs"
#   gh repo create "$REPO_NAME" --private --source=. --remote=origin --push

# --- Option B: plain git + an existing empty GitHub repo ---
#   # first create an empty repo at https://github.com/new  (no README)
#   cd mahabharata-recited-pipeline
#   git init
#   git add -A
#   git commit -m "Mahabharata CE recitation pipeline: scripts, naming data, docs"
#   git branch -M main
#   git remote add origin git@github.com:<YOUR_USER>/$REPO_NAME.git
#   git push -u origin main

echo "See the commented commands in this file. Pick Option A (gh) or Option B (git)."
