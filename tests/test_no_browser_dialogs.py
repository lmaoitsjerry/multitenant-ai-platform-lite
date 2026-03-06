"""Test 5: Browser Dialogs Removed"""
import os
import re


def test_no_window_confirm_in_frontend():
    """No window.confirm() or bare confirm() calls should exist in JSX files."""
    frontend_dir = os.path.join("frontend", "tenant-dashboard", "src")
    violations = []

    for root, dirs, files in os.walk(frontend_dir):
        if "node_modules" in root:
            continue
        for f in files:
            if f.endswith(".jsx") or f.endswith(".js"):
                filepath = os.path.join(root, f)
                with open(filepath, "r", encoding="utf-8") as fh:
                    for lineno, line in enumerate(fh, 1):
                        # Match window.confirm(
                        if re.search(r'window\.confirm\s*\(', line):
                            violations.append(f"{filepath}:{lineno}: {line.strip()}")
                        # Match bare confirm( but not ConfirmDialog references
                        elif re.search(r'(?<!\w)confirm\s*\(', line):
                            # Skip ConfirmDialog-related, state setters, imports, comments
                            if any(skip in line for skip in [
                                'ConfirmDialog', 'showConfirm', 'setConfirm',
                                'confirmDelete', 'confirmReset', 'confirmDiscard',
                                'confirmPublish', 'onConfirm', 'showDeleteConfirm',
                                'showResetConfirm', 'showDiscardConfirm',
                                'confirmAction', 'confirmPublishAction',
                            ]):
                                continue
                            # Skip comments
                            stripped = line.lstrip()
                            if stripped.startswith('//') or stripped.startswith('*') or stripped.startswith('/*'):
                                continue
                            # Skip imports
                            if 'import' in line:
                                continue
                            violations.append(f"{filepath}:{lineno}: {line.strip()}")

    assert len(violations) == 0, \
        f"Found {len(violations)} browser dialog(s):\n" + "\n".join(violations)


def test_confirm_dialog_imported_in_fixed_files():
    """All 5 fixed files should import ConfirmDialog."""
    fixed_files = [
        os.path.join("frontend", "tenant-dashboard", "src", "pages", "KnowledgeBase.jsx"),
        os.path.join("frontend", "tenant-dashboard", "src", "pages", "admin", "TenantOnboarding.jsx"),
        os.path.join("frontend", "tenant-dashboard", "src", "pages", "Settings.jsx"),
        os.path.join("frontend", "tenant-dashboard", "src", "pages", "website", "WebsiteMedia.jsx"),
        os.path.join("frontend", "tenant-dashboard", "src", "pages", "website", "WebsitePreview.jsx"),
    ]

    for filepath in fixed_files:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        assert "import ConfirmDialog" in content, \
            f"{filepath} should import ConfirmDialog"
        assert "<ConfirmDialog" in content, \
            f"{filepath} should render <ConfirmDialog>"
