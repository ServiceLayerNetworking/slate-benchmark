#!/bin/bash

if [ "$#" -ne 2 ]; then
  echo "Usage: $0 <original_word> <replacement_word>"
  exit 1
fi

original_word="$1"
replacement_word="$2"

grep -rl "$original_word" . | xargs sed -i "s/$original_word/$replacement_word/g"
