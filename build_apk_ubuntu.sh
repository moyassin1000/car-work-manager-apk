#!/usr/bin/env bash
set -e

python3 -m pip install --user --upgrade pip setuptools wheel
python3 -m pip install --user "buildozer==1.5.0" "cython==0.29.36"
export PATH="$HOME/.local/bin:$PATH"

buildozer android debug

echo ""
echo "APK created in: bin/"
ls -lh bin/*.apk
