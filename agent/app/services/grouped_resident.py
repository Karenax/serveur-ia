"""Separate group adapter; copied canonical direct resident stays unchanged."""
import json
import re
import time
import uuid

from .live_speech import ResidentWhisper, lease
from scripts.grouped_pcm_core import CONTRACT, GroupRefused, map_words, validate_group
from scripts.grouped_response_evidence import validate_native_evidence


def validate_response(group, event):
    if event.get('contract') != CONTRACT or event.get('group_id') != group.id:
        raise ValueError('Grouped response contract or identity differs')
    if (type(event.get("duration_ms")) is not int or event["duration_ms"] * 16 != group.frames
            or event.get("grouped_frames") != group.frames or event.get("offset_ms") != group.offset_ms):
        raise ValueError("Grouped response duration or clock differs")
    sources = event.get("source_pcm_metadata")
    if not isinstance(sources, list) or len(sources) != len(group.members):
        raise ValueError("Grouped source acknowledgements missing")
    for source, member in zip(sources, group.members, strict=True):
        if (source.get("chunk_id"), source.get("frames"), source.get("file_sha256")) != (
                member.id, member.decoded_frames, member.sha256):
            raise ValueError("Grouped source acknowledgement differs")
        if not isinstance(source.get("pcm_sha256"), str) or not re.fullmatch(r"[a-f0-9]{64}", source["pcm_sha256"]):
            raise ValueError("Grouped PCM acknowledgement missing")
    if not isinstance(event.get("grouped_pcm_sha256"), str) or not re.fullmatch(r"[a-f0-9]{64}", event["grouped_pcm_sha256"]):
        raise ValueError("Grouped PCM identity missing")
    profile = event.get("loaded_model_profile", {})
    if profile.get("actual_device") != "cpu" or profile.get("actual_compute_type") not in {"int8", "int8_float32"}:
        raise ValueError("Grouped loaded CPU precision differs")
    validate_native_evidence(group, event)
    try:
        expected = map_words(group, event.get("retained_words"))
    except GroupRefused as exc:
        if (event.get("mapping_status"), event.get("segments"), event.get("mapping_refusal")) != (
                "refused", [], str(exc)):
            raise ValueError("Ambiguous grouped mapping was not refused") from exc
    else:
        if (event.get("mapping_status"), event.get("segments"), event.get("mapping_refusal")) != (
                "mapped", expected, None):
            raise ValueError("Grouped native-word mapping differs")
    return event


class GroupedResidentWhisper(ResidentWhisper):
    def transcribe_group(self, group, *, timeout=180, cancel=None):
        validate_group(group)
        request_id = uuid.uuid4().hex
        request = {"op": CONTRACT, "request_id": request_id, "group_id": group.id,
                   "manifest": group.manifest}
        line = json.dumps(request) + "\n"
        if len(line) > 16384:
            raise ValueError("Grouped command exceeds resident command bound")
        deadline = time.monotonic() + timeout
        while not self._request_lock.acquire(timeout=min(.2, self._remaining(deadline, cancel))):
            pass
        try:
            with lease("speech:local-cpu", priority=0, timeout=self._remaining(deadline, cancel), cancel=cancel):
                try:
                    self.start(timeout=min(120, self._remaining(deadline, cancel)), cancel=cancel, deadline=deadline)
                    self._remaining(deadline, cancel)
                    self.process.stdin.write(line)
                    self.process.stdin.flush()
                    event = self._next_event(deadline, cancel)
                    if (event.get("kind"), event.get("request_id"), event.get("group_id"), event.get("contract")) != (
                            "result", request_id, group.id, CONTRACT):
                        raise RuntimeError(event.get("error", "Grouped response identity differs"))
                    self._remaining(deadline, cancel)
                    validated = validate_response(group, event)
                    self._remaining(deadline, cancel)
                    return validated
                except Exception:
                    self.close()
                    raise
        finally:
            self._request_lock.release()
