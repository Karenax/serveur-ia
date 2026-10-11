"""Prepare/verify the local Android signing directory, without opening any key."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'lanceur'))


def main():
    if os.name != 'nt' or len(sys.argv) != 2:
        return 1
    try:
        from wg_crypto import private_directory
        directory = Path(sys.argv[1]).resolve()
        private_directory(directory)
        command = (
            '$acl = [System.IO.Directory]::GetAccessControl($env:FRED_SIGNING_ACL_DIRECTORY); '
            '$current = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value; '
            '$entries = @($acl.Access | ForEach-Object { '
            '$_.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value }); '
            "$unexpected = @($entries | Where-Object { $_ -notin @($current, 'S-1-5-18', 'S-1-5-32-544') }); "
            'if ($acl.AreAccessRulesProtected -and $unexpected.Count -eq 0) { exit 0 } else { exit 1 }'
        )
        checked = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
                                 env={**os.environ, 'FRED_SIGNING_ACL_DIRECTORY': str(directory)},
                                 capture_output=True, timeout=15,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if checked.returncode:
            raise ValueError()
    except Exception:
        print('Windows refuse de protéger le dossier de signature Android.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
