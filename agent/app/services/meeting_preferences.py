"""Preferences keyed by the server-authenticated operator, never by request data."""
from sqlalchemy import func, literal, select
from sqlalchemy.dialects.sqlite import insert

from ..models import AppSetting
from .settings_service import MEETING_PREFERENCES_PREFIX, get_section

FLAGS = ('live_transcription_enabled', 'proactive_enabled', 'auto_enhancement_enabled')


def _key(operator_id):
    return MEETING_PREFERENCES_PREFIX + operator_id


def preferences(db, operator_id):
    defaults = get_section(db, 'foresight')
    row = db.get(AppSetting, _key(operator_id))
    values = {**defaults, **(row.value if row else {})}
    return {**{flag: values.get(flag) is True for flag in FLAGS},
            'mode': 'local' if values.get('mode') == 'local' else 'network'}


def any_enabled(db, flag):
    if get_section(db, 'foresight').get(flag) is True:
        return True
    return db.scalar(select(AppSetting.key).where(AppSetting.key.startswith(MEETING_PREFERENCES_PREFIX),
        AppSetting.value[flag].as_boolean().is_(True)).limit(1)) is not None


def enabled_for_session(db, flag):
    from ..meeting_session_models import MeetingSession
    personal = select(AppSetting.value[flag].as_boolean()).where(
        AppSetting.key == literal(MEETING_PREFERENCES_PREFIX) + MeetingSession.operator_id).scalar_subquery()
    return func.coalesce(personal, get_section(db, 'foresight').get(flag) is True).is_(True)


def save(db, operator_id, values):
    command = insert(AppSetting).values(key=_key(operator_id), value=values)
    db.execute(command.on_conflict_do_update(index_elements=[AppSetting.key],
        set_={'value': command.excluded.value, 'updated_at': command.excluded.updated_at}))
    db.commit()
