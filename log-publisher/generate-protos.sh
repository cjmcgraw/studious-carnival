#!/usr/bin/env bash
output_directory=""
proto_file=""

function usage() {
    echo "$0 args"
    echo ""
    echo "  required arguments:"
    echo "    --protos  <proto-file>            proto files to compile (on filesystem)"
    echo "    --output-directory <output-dir>   directory to output generated python code to"
    echo ""
}

while [[ $# -gt 0 ]];do case $1 in
    --proto-file) proto_file="$(realpath $2)"; shift;;
    --output-directory) output_directory="$2"; shift ;;
    --help) usage; exit 0 ;;
esac; shift; done

if [[ -z "$proto_file" ]] ; then
    echo "missing required arguments: --proto-file"
    echo ""
    usage
    exit 1
fi

import_directory=$(dirname "${proto_file}")
if [[ -z "${import_directory}" ]]; then
    echo "must provide protos file with path so that way we can determine the import path!"
    echo ""
    usage
    exit 1
fi

proto_name=$(basename "${proto_file}")
if [[ -z "${proto_name}" ]]; then
    echo "must provide proto file"
    echo ""
    usage
    exit 1
fi

if [[ -z "$output_directory" ]]; then
    echo "missing required arguments: --output-directory"
    echo ""
    usage
    exit 1
fi

set -eu
echo "python version: $(python --version)"
echo "python location: $(which python)"
echo ""

_=$(python -m grpc_tools.protoc --help 2 /dev/null)
if [[ "$?" -gt 0 ]]; then
    echo "failed to find python grpc executable! Please run this command:"
    echo""
    echo "  pip install grpc_tools betterproto"
    echo ""
    exit 1
fi

mkdir -p ${output_directory}
echo "running protobuf code generation..."
echo ""
python -m grpc_tools.protoc \
    -I "${import_directory}" \
    --python_betterproto_out=${output_directory} \
    ${proto_name}
echo ""
echo "successfully generated code in ${output_directory}"
