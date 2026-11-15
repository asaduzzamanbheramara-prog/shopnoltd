# Archived namespace exports

The legacy all-namespace dump was intentionally removed because it contained inline credential material.

Do not restore or recreate plaintext credentials in Git. Use the encrypted disaster-recovery snapshots on the `database-backups` branch and the documented, reviewed restore process. Any credentials present in historical commits must be rotated; removing this file from the current tree does not purge Git history.
