#!/usr/bin/env bash
# push-to-github.sh
# Run this script locally (on your machine) to create the GitHub repo and push
#
# Prerequisites:
#   - GitHub CLI (gh) installed: https://cli.github.com/
#   - Authenticated: gh auth login
#
# Usage:
#   chmod +x push-to-github.sh
#   ./push-to-github.sh

set -euo pipefail

REPO_NAME="repo-validation-system"
GITHUB_USER="juliopessan"
DESCRIPTION="Multi-agent system for automated repository validation and skill A/B benchmarking — built on Claude skills"

echo "🚀 Creating GitHub repository: ${GITHUB_USER}/${REPO_NAME}"

# Create the repo on GitHub (public)
gh repo create "${GITHUB_USER}/${REPO_NAME}" \
  --public \
  --description "${DESCRIPTION}" \
  --source . \
  --remote origin \
  --push

echo ""
echo "✅ Done! Repository available at:"
echo "   https://github.com/${GITHUB_USER}/${REPO_NAME}"
echo ""
echo "📌 Next steps:"
echo "   1. Add repo topics: gh repo edit --add-topic 'claude,ai-agents,repository-validation,benchmarking,avanade'"
echo "   2. Enable GitHub Actions: https://github.com/${GITHUB_USER}/${REPO_NAME}/actions"
echo "   3. Run first workflow_dispatch validation:"
echo "      gh workflow run validate-on-pr.yml -f repo=juliopessan/arch-review-assistant"
