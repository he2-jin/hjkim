# 카카오톡 클론 백엔드 설계서

## Context
카카오톡 클론 프로젝트의 백엔드 서비스를 설계한다. 프론트엔드는 별도 작업자가 진행 중이므로 백엔드 책임만 다룬다. 기존 서버(`C:\Users\future\_ITU\git_ee_web\app\source\management\server`)의 3-tier 패턴(Router → Service → Model)과 네이밍 규칙을 따르되, 기술 스택은 SQLAlchemy 2.0 + Pydantic v2 + Redis + WebSocket으로 업그레이드한다.

---

## 1. 백엔드 관점의 기능 요구사항 정리

### 1.1 인증 (Auth)
**확정:**
- ID/PW 로그인 → JWT Access Token + Refresh Token 발급
- QR 코드 생성 → 스캔 인증 (로그인된 기기에서 새 기기 인증)
- 잠금모드: PIN/생체인증 설정값 서버 저장, 검증
- 로그아웃 (토큰 무효화, Redis blacklist)
- Refresh Token 갱신

**스토리보드상 추정:**
- 자동 로그인 (remember me)
- 다중 디바이스 관리 (새 기기 로그인 시 기존 기기 알림)
- QR 세션 TTL (Redis, 3분 만료)
- 비밀번호 변경/찾기

### 1.2 친구 (Friend)
**확정:**
- 친구 목록 조회 (즐겨찾기, 생일 친구 상단)
- ID 검색 친구 추가
- 연락처(전화번호) 기반 친구 추가
- 친구 차단/숨김/삭제

**스토리보드상 추정:**
- 친구 추천 (연락처 동기화)
- 즐겨찾기 on/off
- 별명 설정
- 친구 수 카운트

### 1.3 프로필 (Profile)
**확정:**
- 기본 프로필 (이름, 상태메시지, 프로필/배경 이미지)
- 멀티프로필: 특정 친구에게 보여줄 별도 프로필
- 이미지 업로드/삭제

**스토리보드상 추정:**
- 프로필 뮤직
- 멀티프로필 대상 친구 지정
- 공개 범위 설정
- 이미지 리사이징/썸네일

### 1.4 채팅 (Chat)
**확정:**
- 채팅 목록 (최근 메시지, 안읽은 수)
- 1:1 / 그룹 채팅방 생성
- 실시간 메시지 송수신 (WebSocket)
- 텍스트/이미지/파일/이모티콘 메시지 타입
- 읽음 처리 (읽은 사람 수)
- 채팅방 나가기

**스토리보드상 추정:**
- 메시지 검색, 삭제 (나만/전체)
- 멤버 초대, 채팅방 설정
- 커서 기반 페이지네이션
- 타이핑 인디케이터, 온라인 상태

### 1.5 공지사항 (Announcement)
**확정:** 채팅방 내 공지 등록/조회, 고정 표시
**스토리보드상 추정:** 권한(방장만), 히스토리, 알림 발송

### 1.6 일정/할 일 (Schedule/Todo)
**확정:** 채팅방 내 일정·할 일 CRUD
**스토리보드상 추정:** 캘린더 뷰 월별 API, 반복 일정, 담당자 지정, 시스템 메시지

### 1.7 알림 제어 (Notification)
**확정:** 채팅방별·전체 알림 on/off
**스토리보드상 추정:** 음소거 시간, 키워드 알림, 알림 목록, 디바이스별 푸시

### 1.8 이모티콘 (Emoticon)
**확정:** 팩 목록, 이모티콘 전송
**스토리보드상 추정:** 보유 목록, 구매, 최근 사용

### 1.9 톡서랍 (Talk Drawer)
**확정:** 미디어/파일/링크 모아보기
**스토리보드상 추정:** 타입별 필터, 날짜 정렬, 다운로드

### 1.10 설정/더보기 (Settings)
**확정:** 계정·알림·개인정보 설정
**스토리보드상 추정:** 테마, 글꼴, 언어, 백업, 차단 목록, 탈퇴

---

## 2. 핵심 도메인 모델 정의

### User (사용자)
| 필드 | 타입 | 설명 |
|------|------|------|
| id | BIGINT PK | 내부 식별자 |
| uuid | CHAR(36) UNIQUE | 외부 노출용 |
| kakao_id | VARCHAR(30) UNIQUE | 카카오톡 ID |
| phone | VARCHAR(20) UNIQUE | 전화번호 |
| phone_hash | VARCHAR(64) | 연락처 매칭용 SHA-256 |
| password_hash | VARCHAR(255) | bcrypt 해시 |
| name | VARCHAR(30) | 실명 |
| status | ENUM(active, inactive, suspended, withdrawn) | |
| created_at, updated_at, deleted_at | DATETIME | |

### Device (기기)
| 필드 | 타입 | 설명 |
|------|------|------|
| id | BIGINT PK | |
| user_id | FK → User | |
| device_token | VARCHAR(255) | 푸시 토큰 |
| device_type | ENUM(ios, android, pc, web) | |
| is_active | BOOLEAN | |

### Profile (프로필)
| 필드 | 타입 | 설명 |
|------|------|------|
| id | BIGINT PK | |
| user_id | FK → User (UNIQUE) | 1:1 |
| nickname | VARCHAR(20) | |
| status_message | VARCHAR(60) | |
| profile_image_url | VARCHAR(500) | |
| background_image_url | VARCHAR(500) | |

### MultiProfile + MultiProfileTarget
- MultiProfile: user_id FK, nickname, status_message, profile_image_url, background_image_url
- MultiProfileTarget: multi_profile_id FK, target_user_id FK (어떤 친구에게 보여줄지)

### LockSetting
- user_id FK (UNIQUE), is_enabled, lock_type ENUM(pin, biometric, pattern), pin_hash

### Friend (친구)
| 필드 | 타입 | 설명 |
|------|------|------|
| id | BIGINT PK | |
| user_id | FK → User | 나 |
| friend_user_id | FK → User | 친구 |
| custom_name | VARCHAR(20) | 별명 |
| status | ENUM(normal, blocked, hidden) | |
| is_favorite | BOOLEAN | |
| UNIQUE(user_id, friend_user_id) | | |

### ChatRoom (채팅방)
| 필드 | 타입 | 설명 |
|------|------|------|
| id | BIGINT PK | |
| uuid | CHAR(36) UNIQUE | 외부 노출용 |
| room_type | ENUM(direct, group) | |
| name | VARCHAR(100) | 그룹방 이름 |
| owner_id | FK → User | 방장 |
| last_message_id | FK → ChatMessage | |
| last_message_at | DATETIME | 정렬용 |

### ChatMember (채팅방 멤버)
- room_id FK, user_id FK, last_read_message_id FK, notification_enabled, is_active, left_at
- UNIQUE(room_id, user_id)

### ChatMessage (메시지)
| 필드 | 타입 | 설명 |
|------|------|------|
| id | BIGINT PK | |
| room_id | FK → ChatRoom | INDEX |
| sender_id | FK → User | |
| message_type | ENUM(text, image, file, emoticon, system, schedule, announcement) | |
| content | TEXT | |
| file_url, file_name, file_size | | 파일 첨부 |
| emoticon_id | FK → EmoticonItem | |
| parent_message_id | BIGINT | 답장 |
| is_deleted | BOOLEAN | |
| INDEX(room_id, created_at DESC) | | 핵심 인덱스 |

### Announcement, Schedule, Todo
- 모두 room_id FK 기반, 채팅방 컨텍스트
- Schedule: start_at, end_at, repeat_type, alarm_minutes_before
- Todo: assignee_id, status ENUM(pending, in_progress, done), due_date

### Notification + NotificationSetting
- Notification: user_id, type, title, body, reference_type/id, is_read
- NotificationSetting: user_id, room_id(nullable), is_enabled, mute_until

### EmoticonPack + EmoticonItem + UserEmoticon
- Pack: name, author, thumbnail_url, price
- Item: pack_id FK, image_url, sort_order
- UserEmoticon: user_id FK, pack_id FK (보유 팩)

### UserSetting
- user_id (UNIQUE), theme, font_size, language, settings_json (JSON 확장용)

---

## 3. MariaDB ERD 초안

### 테이블 관계 요약
```
User(1) ─── (1)Profile
User(1) ─── (N)MultiProfile ─── (N)MultiProfileTarget
User(1) ─── (N)Friend
User(1) ─── (N)Device
User(1) ─── (1)LockSetting
User(1) ─── (1)UserSetting
User(1) ─── (N)ChatMember ─── (1)ChatRoom
ChatRoom(1) ─── (N)ChatMessage
ChatRoom(1) ─── (N)Announcement
ChatRoom(1) ─── (N)Schedule
ChatRoom(1) ─── (N)Todo
EmoticonPack(1) ─── (N)EmoticonItem
User(1) ─── (N)UserEmoticon ─── (1)EmoticonPack
User(1) ─── (N)Notification
```

### 핵심 인덱스
- `users`: uuid, kakao_id, phone, phone_hash, status
- `friends`: (user_id, friend_user_id) UNIQUE, (user_id, status)
- `chat_messages`: (room_id, created_at DESC), (room_id, id DESC) ← **가장 중요**
- `chat_members`: (room_id, user_id) UNIQUE, (user_id, is_active)
- `chat_rooms`: (last_message_at DESC)
- `notifications`: (user_id, is_read, created_at DESC)

### 전체 DDL
- 20개 테이블, 모두 `ENGINE=InnoDB`, `CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci`
- Soft delete: users, announcements, schedules, todos에 `deleted_at` 컬럼
- 타임스탬프: 모든 테이블에 `created_at`, 대부분 `updated_at`

---

## 4. API 목록 초안

### Auth (`/api/auth`)
| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/auth/register` | 회원가입 |
| POST | `/api/auth/login` | 로그인 (Access+Refresh Token) |
| POST | `/api/auth/logout` | 로그아웃 |
| POST | `/api/auth/token/refresh` | 토큰 갱신 |
| POST | `/api/auth/qr/generate` | QR 세션 생성 |
| GET | `/api/auth/qr/status/{session_id}` | QR 상태 폴링 |
| POST | `/api/auth/qr/confirm` | QR 스캔 확인 |
| POST | `/api/auth/password/change` | 비밀번호 변경 |
| GET | `/api/auth/devices` | 디바이스 목록 |
| DELETE | `/api/auth/devices/{device_id}` | 디바이스 로그아웃 |

### User (`/api/user`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/user/profile` | 내 프로필 |
| PUT | `/api/user/profile` | 프로필 수정 |
| POST | `/api/user/profile/image` | 프로필 이미지 업로드 |
| DELETE | `/api/user/profile/image` | 프로필 이미지 삭제 |
| POST | `/api/user/profile/background` | 배경 이미지 업로드 |
| GET | `/api/user/profile/{user_uuid}` | 타인 프로필 (멀티프로필 적용) |
| GET/POST/PUT/DELETE | `/api/user/multi-profiles[/{id}]` | 멀티프로필 CRUD |
| POST | `/api/user/multi-profiles/{id}/targets` | 대상 친구 설정 |
| GET/PUT | `/api/user/lock` | 잠금 설정 |
| POST | `/api/user/lock/verify` | 잠금 해제 검증 |
| GET/PUT | `/api/user/settings` | 설정 |
| DELETE | `/api/user/account` | 탈퇴 |

### Friend (`/api/friend`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/friend/list` | 친구 목록 |
| GET | `/api/friend/favorites` | 즐겨찾기 |
| POST | `/api/friend/search/id` | ID 검색 |
| POST | `/api/friend/search/phone` | 전화번호 검색 |
| POST | `/api/friend/add` | 친구 추가 |
| POST | `/api/friend/sync-contacts` | 연락처 동기화 |
| PUT | `/api/friend/{id}/name` | 별명 변경 |
| PUT | `/api/friend/{id}/favorite` | 즐겨찾기 토글 |
| PUT | `/api/friend/{id}/block` | 차단 |
| PUT | `/api/friend/{id}/hide` | 숨김 |
| DELETE | `/api/friend/{id}` | 삭제 |
| GET | `/api/friend/blocked` | 차단 목록 |

### Chat (`/api/chat`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/chat/rooms` | 채팅방 목록 |
| POST | `/api/chat/rooms` | 채팅방 생성 |
| GET | `/api/chat/rooms/{uuid}` | 방 상세 |
| PUT | `/api/chat/rooms/{uuid}` | 방 설정 변경 |
| POST | `/api/chat/rooms/{uuid}/leave` | 나가기 |
| POST | `/api/chat/rooms/{uuid}/invite` | 초대 |
| GET | `/api/chat/rooms/{uuid}/members` | 멤버 목록 |
| GET | `/api/chat/rooms/{uuid}/messages` | 메시지 히스토리 (커서) |
| POST | `/api/chat/rooms/{uuid}/messages` | HTTP 메시지 전송 (fallback) |
| DELETE | `/api/chat/messages/{id}` | 메시지 삭제 |
| POST | `/api/chat/rooms/{uuid}/read` | 읽음 처리 |
| GET | `/api/chat/rooms/{uuid}/search` | 메시지 검색 |
| POST | `/api/chat/upload` | 파일 업로드 |

### Chat 하위 도메인
| Path Prefix | Endpoints | 설명 |
|-------------|-----------|------|
| `/api/chat/rooms/{uuid}/announcements` | GET, POST, PUT/{id}, DELETE/{id} | 공지 |
| `/api/chat/rooms/{uuid}/schedules` | GET, POST, PUT/{id}, DELETE/{id} | 일정 |
| `/api/chat/rooms/{uuid}/todos` | GET, POST, PUT/{id}, DELETE/{id} | 할 일 |
| `/api/chat/rooms/{uuid}/drawer/media` | GET | 미디어 |
| `/api/chat/rooms/{uuid}/drawer/files` | GET | 파일 |
| `/api/chat/rooms/{uuid}/drawer/links` | GET | 링크 |

### Notification (`/api/notification`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/notification/list` | 알림 목록 |
| PUT | `/api/notification/{id}/read` | 읽음 |
| PUT | `/api/notification/read-all` | 전체 읽음 |
| GET/PUT | `/api/notification/settings` | 전체 알림 설정 |
| PUT | `/api/notification/settings/room/{uuid}` | 채팅방별 설정 |

### Emoticon (`/api/emoticon`)
| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/emoticon/packs` | 스토어 목록 |
| GET | `/api/emoticon/packs/{id}` | 팩 상세 |
| GET | `/api/emoticon/my` | 내 이모티콘 |
| POST | `/api/emoticon/purchase/{id}` | 구매 |

### WebSocket
| Path | 설명 |
|------|------|
| `ws://host/ws/chat/{room_uuid}` | 채팅방 (메시지, 타이핑, 읽음) |
| `ws://host/ws/notification` | 전역 알림 |

---

## 5. 서비스 계층 책임 분리안

### 공통 패턴 (기존 서버 준수)
- **Router**: Request 파라미터 수신, Pydantic 검증, `Depends(get_db/get_current_user)` 주입, `api_res()` 응답
- **Service**: 비즈니스 로직, `@staticmethod/@classmethod`, DB 세션 받아서 처리
- **Model**: SQLAlchemy ORM (models.py), Pydantic v2 스키마 (schemas.py), Enum (enums.py)

### 도메인별 서비스

**AuthService** (`services/auth/auth.py`)
- `login(db, credentials)` → 인증, 토큰 생성
- `register(db, user_data)` → 중복검사, 비밀번호 해싱, Profile 자동 생성
- `refresh_token(db, redis, token)` → Refresh Token 검증/갱신
- `create_qr_session(redis)` / `confirm_qr()` / `check_qr_status()`

**ProfileService** (`services/user/profile.py`)
- `get_profile(db, user_id)` / `update_profile(db, user_id, data)`
- `get_profile_for_viewer(db, owner_id, viewer_id)` → 멀티프로필 매칭
- `upload_image(file, type)` → 이미지 저장, URL 반환

**FriendService** (`services/friend/friend.py`)
- `get_friends(db, user_id, status, sort)` → 즐겨찾기 우선 정렬
- `add_friend(db, user_id, friend_user_id)` → 중복/자기자신 검증
- `search_by_kakao_id(db, kakao_id)` / `sync_contacts(db, user_id, phone_hashes)`
- `update_status()` / `toggle_favorite()`

**ChatRoomService** (`services/chat/room.py`)
- `create_room(db, creator_id, member_ids, type, name)` → 1:1은 기존 방 재활용
- `get_rooms_for_user(db, user_id)` → 안읽은 수 포함
- `leave_room()` / `invite_members()`

**MessageService** (`services/chat/message.py`)
- `send_message(db, room_id, sender_id, content, type)` → 저장 + last_message 갱신
- `get_messages(db, room_id, cursor, limit)` → 커서 페이지네이션
- `mark_as_read(db, room_id, user_id, message_id)`

**RealtimeService** (`services/chat/realtime.py`)
- `broadcast_to_room(room_id, message)` → WebSocket 브로드캐스트
- `notify_typing(room_id, user_id)`

**NotificationService**, **EmoticonService**, **TalkDrawerService**, **ScheduleService**, **TodoService**
- 각각 표준 CRUD 패턴

---

## 6. WebSocket vs HTTP 구분

### WebSocket 필수 (실시간성 필수)
| 기능 | 이벤트 |
|------|--------|
| 메시지 송수신 | `message.new` |
| 읽음 상태 | `message.read` |
| 타이핑 인디케이터 | `typing.start/stop` |
| 온라인 상태 | `presence.online/offline` |
| 전역 알림 | `notification.new` |

### HTTP 전용 (실시간성 불필요)
로그인/로그아웃, 회원가입, 프로필 CRUD, 친구 CRUD, 멀티프로필, 이모티콘 목록/구매, 설정, 파일 업로드, 톡서랍, 일정/할 일 CRUD, QR 상태 폴링, 메시지 히스토리

### 하이브리드 (HTTP 저장 + WebSocket 알림)
공지 등록, 일정 생성, 할 일 상태 변경, 친구 추가, 멤버 초대, 채팅방 나가기
→ POST/PUT으로 DB 저장 후, 시스템 메시지 또는 알림 이벤트를 WebSocket으로 전달

### WebSocket 메시지 프로토콜
```json
// Client → Server
{"type": "message.send", "data": {"content": "...", "message_type": "text"}, "request_id": "uuid"}

// Server → Client
{"type": "message.new", "data": {"id": 123, "sender": {...}, "content": "...", "created_at": "..."}, "request_id": "uuid"}

// 읽음
{"type": "message.read", "data": {"last_read_message_id": 123, "reader_uuid": "..."}}

// 타이핑
{"type": "typing.start", "data": {"user_uuid": "..."}}
```

### Redis 활용
1. `refresh_token:{user_id}:{device_id}` → token_hash (TTL: 14일)
2. `blacklist:{token_jti}` → 1 (TTL: access token 남은 시간)
3. `qr_session:{session_id}` → JSON (TTL: 180초)
4. Redis Pub/Sub: `channel:room:{room_id}`, `channel:user:{user_id}`
5. `online:{user_id}` → 1 (TTL: 60초, heartbeat)
6. `typing:{room_id}:{user_id}` → 1 (TTL: 3초)

---

## 7. MVP 범위와 후순위

### Phase 1 - MVP (4~6주)
- 회원가입/로그인/로그아웃 + JWT + Refresh Token
- 기본 프로필 (이름, 상태메시지, 이미지)
- 친구 추가 (ID 검색) + 친구 목록
- 1:1 채팅방 생성
- 실시간 메시지 송수신 (WebSocket)
- 메시지 히스토리 (커서 페이지네이션)
- 채팅 목록 (안읽은 수)
- 읽음 처리

### Phase 2 - 확장 (2~3주)
- 그룹 채팅 + 멤버 초대/나가기
- 이미지/파일 전송
- 친구 차단/숨김 + 연락처 동기화
- 채팅방 공지사항
- 알림 on/off
- 타이핑 인디케이터
- 잠금모드

### Phase 3 - 부가 (2~3주)
- QR 로그인
- 멀티프로필
- 일정/할 일
- 이모티콘
- 톡서랍
- 메시지 검색/삭제
- 설정 (테마, 글꼴 등)
- 다중 디바이스 관리, 온라인 상태

---

## 8. 가장 먼저 구현할 3개 유스케이스

### UC-1: 회원가입 + 로그인 + 토큰 관리 (최우선)
**이유:** 모든 API가 인증을 전제. `deps.py`(get_db, get_current_user)가 전체 프로젝트의 기반.

**구현 범위:**
1. `db/database.py` - SQLAlchemy 2.0 엔진/세션
2. User + Profile 모델 (ORM + Schema)
3. `api/deps.py` - get_db, get_current_user, create_access_token, create_refresh_token
4. POST `/api/auth/register` - 회원가입
5. POST `/api/auth/login` - 로그인
6. POST `/api/auth/token/refresh` - 토큰 갱신
7. POST `/api/auth/logout` - 로그아웃
8. Redis 연결 (Refresh Token, Blacklist)
9. `models/base.py` - ResponseBase, api_res()
10. `middlewares/exceptions.py` - 에러 핸들러

### UC-2: 친구 추가 + 친구 목록 (2번째)
**이유:** 채팅 대상 확보 필수. 단순 CRUD로 3-tier 구조 정립에 적합.

**구현 범위:**
1. Friend 모델 (ORM + Schema)
2. POST `/api/friend/search/id` - ID 검색
3. POST `/api/friend/add` - 친구 추가
4. GET `/api/friend/list` - 친구 목록
5. Profile 조회 연동

### UC-3: 1:1 채팅방 + 실시간 메시지 (3번째)
**이유:** 메신저 핵심 가치. MVP의 핵심 경험 시연 가능.

**구현 범위:**
1. ChatRoom, ChatMember, ChatMessage 모델
2. `core/websocket_manager.py` - ConnectionManager
3. POST `/api/chat/rooms` - 1:1 방 생성
4. GET `/api/chat/rooms` - 방 목록 (last_message, unread_count)
5. `ws://host/ws/chat/{room_uuid}` - WebSocket 핸들러
6. GET `/api/chat/rooms/{uuid}/messages` - 메시지 히스토리
7. 읽음 처리 로직

---

## 프로젝트 디렉토리 구조

```
src/
├── app.py                     # FastAPI 앱 초기화
├── routes.py                  # 라우터 등록
├── setting.py                 # 환경변수, DB URL 등
├── core/
│   ├── config.py              # ConfigDict 설정
│   ├── redis.py               # Redis 연결
│   └── websocket_manager.py   # WebSocket 연결 관리
├── db/
│   └── database.py            # SQLAlchemy 2.0 엔진/세션/Base
├── api/
│   ├── deps.py                # get_db, get_current_user
│   ├── auth/auth.py
│   ├── user/profile.py, settings.py
│   ├── friend/friend.py
│   ├── chat/room.py, message.py, ws.py
│   ├── announcement/announcement.py
│   ├── schedule/schedule.py
│   ├── notification/notification.py
│   ├── emoticon/emoticon.py
│   └── talk_drawer/talk_drawer.py
├── models/
│   ├── base.py                # ResponseBase, api_res
│   ├── auth/models.py, schemas.py, enums.py
│   ├── user/models.py, schemas.py, enums.py
│   ├── friend/models.py, schemas.py, enums.py
│   ├── chat/models.py, schemas.py, enums.py
│   ├── announcement/, schedule/, notification/, emoticon/, talk_drawer/
├── services/
│   ├── auth/auth.py
│   ├── user/profile.py
│   ├── friend/friend.py
│   ├── chat/room.py, message.py, realtime.py
│   ├── announcement/, schedule/, notification/, emoticon/, talk_drawer/
├── lib/
│   └── utils.py               # api_res, 유틸
├── middlewares/
│   └── exceptions.py
└── errors.py
```

## 참조할 기존 파일
- `server/src/F3/api/deps.py` → 인증/DI 패턴 원본
- `server/src/F3/models/base.py` → ResponseBase, PageParams 패턴
- `server/src/F3/lib/utils.py` → api_res() 응답 유틸
- `server/src/F3/routes.py` → 라우터 등록 구조
- `server/src/F3/db/database.py` → DB 설정 (2.0으로 업그레이드)

## 검증 방법
1. UC-1 완료 후: 회원가입 → 로그인 → 보호된 API 호출 → 토큰 갱신 → 로그아웃 흐름 테스트
2. UC-2 완료 후: 친구 검색 → 추가 → 목록 조회 테스트
3. UC-3 완료 후: 채팅방 생성 → WebSocket 연결 → 메시지 송수신 → 읽음 처리 E2E 테스트
