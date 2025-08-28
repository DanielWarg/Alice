# 🔧 GitHub Repository Settings Update Guide

## 📋 Required GitHub Settings Changes

To complete the branch consolidation and fix repository confusion, the following GitHub settings need to be updated through the GitHub web interface.

### 🌟 **1. Default Branch Settings**

**Navigate to:** `Settings` → `General` → `Default branch`

**Action:** Change default branch from `master` to `main`

**Steps:**
1. Click the pencil icon next to "Default branch"
2. Select `main` from the dropdown
3. Click "Update" and confirm the change

### 🛡️ **2. Branch Protection Rules**

**Navigate to:** `Settings` → `Branches` → `Branch protection rules`

**Action:** Set up protection for `main` branch

**Recommended Rules:**
- ✅ **Require pull request reviews before merging**
- ✅ **Require status checks to pass before merging**
  - Required status checks:
    - `CI Pipeline / python-ci (3.10)`
    - `CI Pipeline / web-ci (20)`
    - `Tests / unit`
- ✅ **Require branches to be up to date before merging**
- ✅ **Require linear history**
- ✅ **Include administrators**

### 📊 **3. Repository Topics & Description**

**Navigate to:** `Repository main page` → Click gear icon next to "About"

**Update Description:**
```
Production-ready Swedish AI assistant with FastAPI backend, Next.js HUD, and autonomous agent workflows. 89% Swedish NLU accuracy with local privacy-first architecture.
```

**Topics to add:**
```
ai-assistant, swedish, fastapi, nextjs, voice-recognition, privacy-first, 
ollama, agent-workflows, hud-interface, webhooks, real-time, tts, stt
```

**Website URL:**
```
https://github.com/DanielWarg/Alice/tree/main
```

### 🚀 **4. GitHub Pages (Optional)**

**Navigate to:** `Settings` → `Pages`

**Action:** Set up documentation hosting

**Configuration:**
- **Source:** Deploy from a branch
- **Branch:** `main`
- **Folder:** `/ (root)` or `/docs` if you prefer

### 🏷️ **5. Repository Labels**

**Navigate to:** `Issues` → `Labels`

**Recommended Labels to Add:**
- `swedish-language` (color: `#FFD700`) - Swedish language related issues
- `voice-pipeline` (color: `#9F7AEA`) - Voice and audio processing
- `agent-core` (color: `#38B2AC`) - Agent workflow system
- `hud-interface` (color: `#4299E1`) - Frontend HUD components
- `ci-cd` (color: `#48BB78`) - Continuous integration/deployment

### 📧 **6. Notifications & Integrations**

**Navigate to:** `Settings` → `Notifications`

**Webhooks/Integrations:**
- Consider adding Discord webhook for CI notifications
- Set up Codecov integration for test coverage reporting

### 🔒 **7. Security Settings**

**Navigate to:** `Settings` → `Security & analysis`

**Enable:**
- ✅ **Dependency graph**
- ✅ **Dependabot alerts**
- ✅ **Dependabot security updates**
- ✅ **Secret scanning**

### 📝 **8. Issue & PR Templates**

**Status:** ✅ **Already configured** (templates exist in `.github/` folder)

Templates include:
- Bug report template
- Feature request template
- Pull request template

### 🏃‍♂️ **9. Actions Settings**

**Navigate to:** `Settings` → `Actions` → `General`

**Workflow permissions:**
- ✅ **Read and write permissions**
- ✅ **Allow GitHub Actions to create and approve pull requests**

## 🎯 **Priority Order**

Execute these changes in order:

1. **🔥 HIGH PRIORITY:** Change default branch to `main`
2. **🔥 HIGH PRIORITY:** Set up branch protection rules for `main`
3. **📋 MEDIUM:** Update repository description and topics
4. **🛡️ MEDIUM:** Enable security features
5. **🎨 LOW:** Configure labels and optional integrations

## ✅ **Verification Steps**

After making changes:

1. **Test branch protection:** Create a test PR to ensure rules are working
2. **Verify CI badges:** Check that README badges show correct status
3. **Confirm default branch:** Ensure new clones default to `main`
4. **Test workflows:** Push a commit to trigger all CI workflows

## 🚨 **Master Branch Handling**

**Recommendation:** Keep `master` branch for now but add deprecation notice

**Future Action:** After 30 days, consider:
- Renaming `master` to `master-deprecated`
- Adding the `BRANCH_NOTICE.md` file to `master` branch
- Eventually deleting the deprecated branch

---

## 📞 **Need Help?**

If you encounter issues with any of these settings:

1. Check GitHub's documentation on branch management
2. Contact repository maintainers
3. Create an issue with the `ci-cd` label

---

**This guide ensures Alice repository follows modern GitHub best practices and eliminates branch confusion.**