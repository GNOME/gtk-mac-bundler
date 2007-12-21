#!/bin/sh

if [ $# -lt 2 ]; then
    echo "Usage: $0 library prefix"
    exit 1
fi

LIBRARY=$1
WRONG_PREFIX=$2
RIGHT_PREFIX="@executable_path/../Resources"

libs="`otool -L $LIBRARY 2>/dev/null | fgrep compatibility | cut -d\( -f1 | grep $WRONG_PREFIX | sort | uniq`"

for lib in $libs; do
    fixed=`echo $lib | sed -e s,\$WRONG_PREFIX,\$RIGHT_PREFIX,`
    install_name_tool -change $lib $fixed $LIBRARY
done
