from __future__ import annotations

from litmus.discovery.diff import parse_changed_files


def test_parse_changed_files_from_git_diff_output() -> None:
    diff_output = """
diff --git a/app/api.py b/app/api.py
index 1234567..89abcde 100644
--- a/app/api.py
+++ b/app/api.py
@@ -1,3 +1,3 @@
-old
+new
diff --git a/app/services/payment.py b/app/services/payment.py
index 0123456..789abcd 100644
--- a/app/services/payment.py
+++ b/app/services/payment.py
@@ -1,3 +1,3 @@
-old
+new
""".strip()

    changed_files = parse_changed_files(diff_output)

    assert changed_files == ["app/api.py", "app/services/payment.py"]
