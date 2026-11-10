# 도트 알람 공휴일 피드

도트 알람(iPhone)이 하루 한 번 내려받는 한국 공휴일 자료다. 앱은 이 파일로 대체공휴일·임시공휴일·다음 해 공휴일을 앱 업데이트 없이 받는다.

- 주소: `https://kongrae.github.io/dot-alarm-feed/holidays-kr.json` (앱 `Info.plist`의 `HolidayFeedURL`)
- 형식: 앱에 들어 있는 `holidays-kr.json`과 같다(`schemaVersion` 1, `datasetVersion`, `years`, `holidays[{date, name}]`).
- 공개 자료(공휴일 날짜와 이름)만 담는다. 키나 개인 정보는 없다.

## 이 저장소의 원본

`도트 알람` 저장소(`holiday-alarm`)의 `feed/` 폴더가 원본이다. `collect.py`는 그 저장소의 `tools/holidays/collect.py`와 같은 파일이어야 한다(그쪽 시험이 확인한다). 고칠 때는 원본을 고친 뒤 이 저장소로 복사한다.

## 처음 한 번 설정

1. 공공데이터포털에서 [한국천문연구원 특일 정보](https://www.data.go.kr/data/15012690/openapi.do)를 활용 신청하고 일반 인증키(Decoding)를 받는다.
2. 이 저장소 Settings → Secrets and variables → Actions에 `KASI_SERVICE_KEY`로 넣는다. 키는 파일이나 로그에 남기지 않는다.
3. Settings → Pages에서 Source를 `Deploy from a branch`, Branch를 `main` / `/(root)`로 둔다.
4. Actions → Publish Korean holidays → Run workflow로 한 번 돌리고, 위 주소가 열리는지 본다.

## 움직이는 방식

- 매일 한국 시각 06:15에 올해와 내년을 API에서 받고, 이전 해는 지우지 않는다.
- API가 아직 모르는 발표(새 공휴일, 임시공휴일)는 `supplement.json`에 넣는다. 날짜가 API에 이미 있으면 API 이름을 쓴다. 이 파일을 고쳐 main에 올리면 바로 다시 게시한다.
- 검증(고정 공휴일, 연도별 개수, 버전 역행, 해 누락, 20% 넘는 삭제)을 통과하고 공휴일 내용이 바뀐 때만 새로 게시한다. 실패하면 게시된 파일은 그대로다.
- 앱은 열릴 때 하루 한 번 이 파일을 확인한다. 받은 자료도 앱 안에서 같은 검증을 거친다. 통과하면 알람을 다시 맞추고, 실패하면 마지막 정상 자료를 계속 쓴다.
