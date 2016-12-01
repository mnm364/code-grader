#!/usr/bin/env bash

DATA=simple.input
OUT=simple.out
STUDENT_OUT="student.${OUT}"
STUDENT=.

if [ -n "$1" ]; then
  STUDENT="$1"
fi

MAPPER="${STUDENT}/fof.mapper"
REDUCER="${STUDENT}/fof.reducer"

fail() {
  echo "[FAIL]: ${1}"
  exit 0
}

_match_with_effort() {
  pushd .
  cd "${STUDENT}"
  for file in `find . -name '*map*'`; do
    MAPPER="${STUDENT}/${file}"
    break 
  done
  for file in `find . -name '*reduce*'`; do
    REDUCER="${STUDENT}/${file}"
	break
  done
  popd

  MAPPER=${MAPPER##*/}

  echo "bad name: ${MAPPER##*/}"
  echo "bad name: ${REDUCER##*/}"
}


match_with_effort() {
  pushd .
  cd "${STUDENT}"
  for file in `find . -name '*map*'`; do
    MAPPER="${STUDENT}/${file}"
    break 
  done
  for file in `find . -name '*reduce*'`; do
    REDUCER="${STUDENT}/${file}"
	break
  done
  popd

  MAPPER=${MAPPER##*/}

  echo "bad name: ${MAPPER##*/}"
  echo "bad name: ${REDUCER##*/}"
}

if [ ! -d "${DATA}" ]; then
  fail "Input data directory does not exist"
fi

rm -f "${STUDENT_OUT}"

supported=(
# <command>,<extension>
  "python","py"
  "perl","pl"
  "dummy", "dum" #sentinel
)

IFS=','
for i in "${supported[@]}"; do set -- $i;

  if [ -f "${MAPPER}.$2" ]; then
	if head -n 1 "${MAPPER}.$2" | grep -q '#!'; then
		echo 'shebang'
		chmod 755 ${MAPPER}.$2
		chmod 755 ${REDUCER}.$2
		echo "cat ${DATA}/* | ${MAPPER}.$2 | sort | ${REDUCER}.$2 | sort  > ${STUDENT_OUT}"
		cat ${DATA}/* | ${MAPPER}.$2 | sort | ${REDUCER}.$2 | sort  > ${STUDENT_OUT}
	else
		echo 'no shebang!'
		echo "cat ${DATA}/* | $1 ${MAPPER}.$2 | sort | $1 ${REDUCER}.$2 | sort  > ${STUDENT_OUT}"
		cat ${DATA}/* | $1 ${MAPPER}.$2 | sort | $1 ${REDUCER}.$2 | sort  > ${STUDENT_OUT}
	fi
	break
  fi

  if [ $1 == "dummy" ]; then
    match_with_effort
    fail "Missing or unknown streaming script"
  fi
done

# remove extra spaces (a gift for the students)
python -c "f=open('${STUDENT_OUT}','rw');d=f.read().replace('\t', ' ');f.close();\
  f=open('${STUDENT_OUT}','wb');f.write(d);f.close()"
python -c "f=open('${STUDENT_OUT}','rw');d=map(lambda x:x.strip()+'\n', f.readlines());f.close();\
  f=open('${STUDENT_OUT}','wb');f.writelines(d);f.close()"

echo "Number of triangles found by student: $(cat ${STUDENT_OUT} | wc -l)"

idiff=$(diff ${STUDENT_OUT} ${OUT})
if [ "$idiff" = "" ]; then
  echo "[SUCCESS]: Student solution correct!"
else
  echo "${idiff}"
  fail "Student failed diffs!"
fi
