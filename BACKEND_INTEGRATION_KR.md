# Backend 비교 및 통합 순서

> 과거 `origin/feature/backend` 비교 기록입니다. 이후 제공된 ZIP의 수정 통합본은
> `backend/`와 `frontend/`에 있으며 현재 실행 방법은 [README](README.md)를 따릅니다.
> 아래의 미완료 항목은 당시 브랜치 기준이며 현재 통합본의 상태를 뜻하지 않습니다.

비교 기준: 로컬에 저장된 `origin/feature/backend`의 `41f0d9e`.
원격을 새로 fetch하지 않았으므로 이후 커밋은 포함하지 않는다.
`main.py`, `database.py`, `ai_service.py`, `requirements.txt`, `start.sh`를
확인했다. 해당 브랜치를 병합하거나 수정하지 않았다.

## 현재 바로 연결되지 않는 부분

| 항목 | Backend | Data + Realtime |
| --- | --- | --- |
| 서버 | `main:app` | `app:app` |
| DB | 고정 경로 `app.db` | 환경변수 `LIFEROOM_DB_PATH` |
| 사용자 | 방별 이름, 정수 ID, 인증 없음 | UUID, bearer session, 멤버십 검사 |
| 방 | `rooms`, 공개 `room_code`, 조회 시 자동 생성 | `households`, UUID, 비밀 초대 코드로 가입 |
| 가입 | `POST /api/join` | `POST /sessions`, `/households`, `/households/join` |
| 상태 | `/api/rooms/{room_code}/state` | `/households/{id}/state` |
| 메시지 작성자 | 요청의 `sender` 문자열을 신뢰 | 토큰으로 `sender_id` 결정 |
| chore 담당자 | 이름 `assignee` | 멤버 ID `assignee_id` |
| chore 완료 | `/api/chores/{id}/complete?room_code=...` | `/households/{id}/chores/{id}`, `completed` 명시 |
| WebSocket | `/ws/{room_code}`, 인증 없음 | `/households/{id}/events`, 첫 프레임 인증 |
| 이벤트 | `new_message`, `new_chore`, `chore_completed` + 객체 | `message.created`, `chore.created`, `chore.updated` + ID |
| 추가 상태 | `rent_due_date`, `rent_amount`, chore `source` | `members`, `bills`, `balances_cents` |

테이블 이름 `users`, `messages`, `chores`가 겹치지만 열과 ID 타입이 다르다.
**두 앱에 같은 DB 파일을 지정해도 통합되지 않는다.** 기존 데이터가 필요하면
ID 매핑과 이름→멤버 매핑을 포함한 명시적 마이그레이션이 필요하다.

## 우선순위

1. **하나의 서버·DB·사용자 계약으로 통일.** 데모에서 이미 검증한 멤버십,
   UUID, 정수 cents를 유지한다. Backend의 AI 기능을 이 데이터 경로에 연결하고,
   프론트 요청 경로 및 토큰 전달을 함께 맞춘다. 두 독립 앱을 같은 포트로
   실행하거나 API 경로만 바꾸는 방식으로 해결할 수 없다.
2. **Backend의 방 경계 보완.** `database.complete_chore(chore_id)`는 방 조건 없이
   수정하고 `main.complete_chore`는 요청의 `room_code`로 이벤트를 보낸다.
   인증된 멤버를 확인하고 `WHERE id=? AND room_id=?`로 갱신한 다음 같은 방에
   알림을 보내야 한다. 메시지 작성자도 요청 이름 대신 인증된 사용자로 정한다.
   현재 Data + Realtime 경로는 이 검사를 수행한다.
3. **프론트 이벤트 소비 방식을 하나로 선택.** 현재 계약대로 `ready`와 변경 이벤트에
   `/state`를 재조회하면 된다. 기존 `new_message` 객체 삽입 코드와 섞으면 누락이나
   중복이 발생한다. 재연결 후에도 스냅샷을 다시 읽는다.
4. **AI를 같은 저장·알림 경로로 연결.** Backend는 AI 결과를 `db.add_chore`로 직접
   저장하므로 다른 앱의 소켓에는 알림이 가지 않는다. 통합 서버에서 검증한 chore
   생성 경로를 재사용한다. 동기 Gemini 호출은 async 메시지 처리에서 직접 실행하지
   말고 스레드로 넘겨 소켓 처리를 막지 않게 한다. 이름만 반환된 담당자는 멤버 ID로
   확정할 수 없으면 미배정으로 둔다.
5. **Backend 실행 문제 정리.** `main.py`가 기대하는 `../frontend` 디렉터리는 비교한
   브랜치에 없어 정적 파일 mount가 실패한다. 또 `ai_service`를 import한 다음
   `load_dotenv()`를 호출하므로 `.env`에만 있는 키는 AI 초기화에 반영되지 않는다.
   환경 로딩을 AI import보다 앞에 두어야 한다.

## 이번에 적용한 최소 변경

- `/state`가 bill마다 shares를 따로 조회하던 SQL을 JOIN 한 번으로 변경했다.
  청구서 N개일 때 shares 조회가 N회에서 1회로 줄고 응답 계약은 그대로다.
- 여러 bill의 shares/잔액과 단일 조회를 검사하는 회귀 테스트를 추가했다.
- Backend에서 추적 중인 `venv/`, `.env`, `app.db`와 같은 로컬 산출물의 재유입을
  막도록 현재 브랜치의 `.gitignore`를 보완했다. 이미 다른 브랜치에서 추적 중인
  파일은 ignore만으로 제거되지 않는다. `.env` 내용은 열지 않았으며, 실제 키가
  커밋되었다면 담당자가 키를 교체하고 추적 파일도 별도로 정리해야 한다.

Backend의 `get_messages`는 오래된 100개만 반환하므로 최근 메시지가 누락된다.
그 경로를 유지한다면 `ORDER BY id DESC LIMIT ?`로 최근 목록을 얻고 표시 순서를
뒤집는다. 현재 `/state`의 전체 메시지 조회는 데모 규모에 유지하고, 페이지네이션과
별도 메시지 조회 API는 실제 데이터량이 요구할 때 추가한다.

아직 Backend와 실행 통합된 상태는 아니다. 위 계약 통합과 Backend 수정은 남아 있다.
