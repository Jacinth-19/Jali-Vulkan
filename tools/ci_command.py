#!/usr/bin/env python3
"""Run bounded setup commands and expose failure tails in GitHub check annotations.

No environment dumps. Useful when hosted log-download redirects are unavailable.
Only use for public/synthetic setup commands; never for private recording input.
"""
import os
import subprocess
import sys


def main():
    try:
        result = subprocess.run(sys.argv[1:], capture_output=True, text=True, timeout=600)
        output = result.stdout + result.stderr
        print(output, end='', flush=True)
        code = result.returncode
    except subprocess.TimeoutExpired as error:
        output = f'CI setup command exceeded 600 seconds: {error.cmd}'
        print(output, flush=True)
        code = 1
    if code and os.environ.get('GITHUB_ACTIONS') == 'true':
        message = output[-2800:].replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
        print(f'::error title=Neural setup failure::{message}', flush=True)
    return code


if __name__ == '__main__':
    sys.exit(main())
