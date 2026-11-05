#!/usr/bin/env bash
# MY_HARNESS bootstrap
# 사용법 (작업 공간 루트에서):
#   git clone <저장소 URL> .kit && bash .kit/bootstrap.sh
#   작업 공간 안에 clone 하면 설치 후 .kit 를 지운다. 작업 공간 밖에 clone 해도 된다.
# 옵션:
#   --ws <경로>        작업 공간 루트 (기본: 현재 폴더)
#   --user-skills      스킬을 $HOME/.agents/skills 에도 연결 (작업 공간 밖, 사용자 범위)
#   --no-repo-skills   작업 공간 .agents/skills 연결을 만들지 않음
#   --no-install       pip 설치 생략
set -u

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="$PWD"
USER_SKILLS=0
REPO_SKILLS=1
DO_INSTALL=1
while [ $# -gt 0 ]; do
  case "$1" in
    --ws) WS="$2"; shift 2 ;;
    --user-skills) USER_SKILLS=1; shift ;;
    --no-repo-skills) REPO_SKILLS=0; shift ;;
    --no-install) DO_INSTALL=0; shift ;;
    *) echo "알 수 없는 옵션: $1"; exit 2 ;;
  esac
done
WS="$(cd "$WS" && pwd)"

say()  { printf '\n[kit] %s\n' "$*"; }
warn() { printf '\n[kit][주의] %s\n' "$*"; }

if [ "$KIT_DIR" = "$WS" ]; then
  warn "키트 폴더 자체에서 실행했습니다. 작업 공간 루트에서 'bash .kit/bootstrap.sh' 로 실행하세요."
  exit 1
fi
KIT_IN_WS=0
case "$KIT_DIR" in "$WS"/*) KIT_IN_WS=1; KIT_REL="${KIT_DIR#$WS/}" ;; esac

say "작업 공간: $WS"
say "키트 위치: $KIT_DIR"

# 1) 기존 상태 스냅샷 (원래 있던 파일 보호)
say "작업 공간 기존 파일 목록 (최상위)"
ls -la "$WS"

# 2) git 초기 상태 커밋 (원래 상태를 먼저 기록)
cd "$WS"
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git init -q && say "git init 완료"
fi
git config user.name  >/dev/null 2>&1 || git config user.name  "candidate"
git config user.email >/dev/null 2>&1 || git config user.email "candidate@local"
if [ "$KIT_IN_WS" = "1" ]; then
  git add -A -- . ":(exclude)$KIT_REL"
else
  git add -A
fi
git diff --cached --quiet || { git commit -q -m "[S0] 작업 공간 초기 상태" && say "작업 공간 초기 상태 커밋"; }

# 3) AGENTS.md: 이미 있으면 덮어쓰지 않음
if [ -e "$WS/AGENTS.md" ]; then
  cp "$KIT_DIR/AGENTS.md" "$WS/AGENTS.kit.md"
  warn "작업 공간에 AGENTS.md 가 이미 있습니다. 덮어쓰지 않고 AGENTS.kit.md 로 저장했습니다.
       → 기존 AGENTS.md 를 우선하고, 이 하네스 규칙을 함께 쓸지 사람이 판단하세요.
       → 쓰기로 했다면 Codex 첫 메시지에 'AGENTS.kit.md 도 읽고 따르라' 고 지시하세요."
else
  cp "$KIT_DIR/AGENTS.md" "$WS/AGENTS.md" && say "AGENTS.md 설치"
fi

# 4) harness 폴더
if [ -e "$WS/harness" ]; then
  warn "harness/ 가 이미 있습니다. 덮어쓰지 않습니다."
else
  cp -r "$KIT_DIR/harness" "$WS/harness" && say "harness/ 설치"
fi
touch "$WS/harness/__init__.py" "$WS/harness/scaffold/__init__.py"
[ -e "$WS/harness/README.md" ] || cp "$KIT_DIR/README.md" "$WS/harness/README.md"   # 프롬프팅 가이드를 에디터에서 열 수 있게

# 5) 작업 폴더 (기존 것은 건드리지 않음)
for d in data/raw data/clean work src tests outputs/tables outputs/figures; do
  mkdir -p "$WS/$d"
done
[ -e "$WS/src/__init__.py" ] || touch "$WS/src/__init__.py"
[ -e "$WS/work/STATE.md" ] || cp "$WS/harness/templates/STATE.md" "$WS/work/STATE.md"
for f in data/raw data/clean outputs/tables outputs/figures; do
  [ -e "$WS/$f/.gitkeep" ] || touch "$WS/$f/.gitkeep"
done

# 6) pytest 설정 (없을 때만)
if [ ! -e "$WS/pytest.ini" ] && [ ! -e "$WS/pyproject.toml" ] && [ ! -e "$WS/setup.cfg" ]; then
  printf '[pytest]\npythonpath = .\ntestpaths = tests\naddopts = -q\n' > "$WS/pytest.ini"
  say "pytest.ini 생성"
else
  warn "pytest 설정 파일이 이미 있습니다. pythonpath 에 . 이 포함되는지 확인하세요."
fi

# 7) .gitignore (없을 때만, 최소)
[ -e "$WS/.gitignore" ] || printf '__pycache__/\n*.pyc\n.pytest_cache/\n' > "$WS/.gitignore"

# 8) 패키지 설치
if [ "$DO_INSTALL" = "1" ]; then
  say "pip 설치 (requirements.txt)"
  PIP="python3 -m pip"
  $PIP install -q -r "$KIT_DIR/requirements.txt" \
    || $PIP install -q --user -r "$KIT_DIR/requirements.txt" \
    || $PIP install -q --break-system-packages -r "$KIT_DIR/requirements.txt" \
    || warn "pip 설치 실패. 'python3 -m pip install -r $KIT_DIR/requirements.txt' 를 직접 확인하세요."
fi

# 9) Codex 네이티브 스킬 등록
#    Codex 는 실행 폴더~저장소 루트의 .agents/skills 와 $HOME/.agents/skills 를 스캔한다 (심볼릭 링크 지원).
#    원본은 harness/skills 에 두고 링크만 건다.
link_skills() {  # $1 = 대상 skills 폴더, $2 = 링크 대상 기준 경로
  mkdir -p "$1"
  for d in "$WS/harness/skills/"*/; do
    name="$(basename "$d")"
    if [ -e "$1/$name" ] || [ -L "$1/$name" ]; then
      warn "$1/$name 이 이미 있어 건너뜁니다."
    else
      ln -s "$2/$name" "$1/$name"
    fi
  done
}
if [ "$REPO_SKILLS" = "1" ]; then
  link_skills "$WS/.agents/skills" "../../harness/skills" && say "스킬 6개를 .agents/skills 에 연결 (codex 에서 /skills 또는 \$이름 으로 확인)"
fi
if [ "$USER_SKILLS" = "1" ]; then
  link_skills "$HOME/.agents/skills" "$WS/harness/skills" && say "스킬 6개를 $HOME/.agents/skills 에도 연결"
fi

# 10) 스캐폴드 자체 테스트
say "스캐폴드 자체 테스트"
if python3 -m pytest -q --noconftest -p no:cacheprovider "$WS/harness/scaffold/tests"; then
  say "스캐폴드 테스트 통과"
else
  warn "스캐폴드 테스트 실패. 패키지 설치 상태를 확인하세요."
fi

# 11) 하네스 커밋
for p in AGENTS.md AGENTS.kit.md harness .agents work src tests data outputs pytest.ini .gitignore; do
  [ -e "$p" ] && git add "$p"
done
[ -e tests/.gitkeep ] || { touch tests/.gitkeep; git add tests/.gitkeep; }
git commit -q -m "[S0] 하네스 부트스트랩" && say "하네스 커밋 완료" || warn "하네스 커밋 실패. git status 를 확인하세요."

# 12) 작업 공간 안에 clone 한 키트 정리
if [ "$KIT_IN_WS" = "1" ]; then
  rm -rf "$KIT_DIR" && say "$KIT_REL 삭제 (설치 완료)"
fi

cat << 'MSG'

[kit] 완료. 다음 순서:
  1. 작업 공간 루트에서 codex 실행 → 첫 메시지 "시작" → 첫 줄에 [harness loaded] 확인
  2. /status 로 모델·권한 확인, /model 로 모델 선택, /skills 로 스킬 6개 확인
  3. README·요구사항 문서를 직접 읽고 필수 산출물·파일명·형태(보고서/서비스)를 work/STATE.md 에 적기
  4. harness/playbook/01_S0_setup.md 의 데이터 인벤토리 프롬프트 실행
MSG
