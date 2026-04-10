# GrampsClean — Project Instructions

## Plugin Sync (REQUIRED after every file edit)

After modifying ANY file in `grampsclean/`, immediately sync to the GRAMPS plugins folder:

```bash
cp -r "/Users/lieuwejongsma/GRAMPS plugin/grampsclean/"* "/Users/lieuwejongsma/Library/Application Support/gramps/gramps60/plugins/grampsclean/"
```

**Never** use a symlink — GRAMPS's `os.walk` does not follow symlinks, so the plugin will be invisible.

The user must restart GRAMPS after a sync for changes to take effect.
