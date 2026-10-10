# arirang123 – 자동 YouTube Shorts 에이전트

주제 한 줄 → 대본 → 음성 → 영상 소스 → 단어별 하이라이트 자막 → 1080×1920 마스터링 → (선택) 업로드.

```
Claude(대본 JSON) → edge-tts(음성+단어 타이밍) → Pexels 세로 스톡영상(없으면 그라데이션)
   → ASS 카라오케 자막 → ffmpeg (x264 CRF18, AAC 192k, -14 LUFS, BGM 덕킹) → YouTube API
```

## 설치 / 실행
```bash
pip install -r requirements.txt        # ffmpeg 필요
export ANTHROPIC_API_KEY=...           # 대본 (없으면 placeholder 대본)
export PEXELS_API_KEY=...              # 무료 스톡영상 (없으면 그라데이션 배경)
export SHORTS_BGM=bgm.mp3              # 선택: 저작권 문제 없는 배경음악만 사용
python -m shorts_agent "월배당 ETF 입문"            # output/<시간>-<주제>/short.mp4
python -m shorts_agent "주제" --upload --privacy private
python -m shorts_agent "주제" --offline            # 네트워크 없이 파이프라인 테스트
pytest                                              # 단위 + 오프라인 E2E
```
한글 자막 폰트: `SHORTS_FONT="Noto Sans CJK KR"` (또는 `SHORTS_FONTS_DIR`로 폰트 폴더 지정).

## 품질 설계 포인트
- **훅 우선 대본**: 1장면=2초 안에 호기심, 5–7장면, 한 장면 한 아이디어, 마지막은 CTA.
- **음성 길이 기준 편집**: 장면 길이 = 실제 TTS 길이 → 싱크 어긋남 없음. 58초 초과 시 중단.
- **자막**: 단어 단위 하이라이트, 3단어씩, 하단 UI 영역(약 27%) 회피.
- **화질/음질**: 중간 산출물 CRF14, 최종 CRF18 + faststart, 음량 -14 LUFS 정규화.

## 확인된 사실과 한계 (실행 환경 검증 기준)
- 이 저장소 샌드박스에서 검증한 것: 오프라인 모드 전체 렌더(1080×1920, H.264+AAC) 및 테스트 4개 통과.
- **검증하지 못한 것**: Claude 대본 생성, edge-tts 실제 음성, Pexels 다운로드, YouTube 업로드 —
  샌드박스에서 해당 외부 호스트가 차단되어(edge-tts 호스트는 403 확인) 실제 호출 테스트를 못 했습니다.
  본인 PC에서 키를 넣고 한 번 돌려 확인하세요.
- edge-tts는 비공식(Microsoft Edge 읽기 기능) 서비스라 안정성·상업 이용 보장이 없습니다. 상업 채널이면 Google/Azure/ElevenLabs 등 공식 TTS로 `tts.py`만 교체하세요.
- 한국어에서 단어 경계가 문장 단위로 오면 자막 타이밍은 글자 수 비례 추정으로 대체됩니다.
- YouTube API: 검증 전(unverified) API 프로젝트로 올린 영상은 비공개로 잠길 수 있다고 알려져 있습니다(정책 변경 가능) — 최신 공식 문서 확인 필요. 일일 쿼터도 제한적입니다.
- 저작권/정책: 스톡 영상 라이선스·BGM 저작권 확인, AI 생성 콘텐츠 공개 설정(YouTube Studio), 대량 복제형 영상은 수익화 제한 대상이 될 수 있음.
- 금융·투자 주제는 대본이 사실을 지어내지 않도록 프롬프트로 제한했지만, **게시 전 사람이 수치·종목을 반드시 검수**하세요. 투자 권유가 아님을 영상에 명시하는 것을 권장합니다.
