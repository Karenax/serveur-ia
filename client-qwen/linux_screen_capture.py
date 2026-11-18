"""Request an explicitly previewed screenshot through the Linux desktop portal."""
import asyncio
import base64
import secrets
from pathlib import Path
from urllib.parse import unquote, urlsplit


def _encode_uri(uri):
    from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt
    from PySide6.QtGui import QImage

    parts = urlsplit(uri)
    if parts.scheme != 'file' or parts.netloc not in ('', 'localhost') or parts.query or parts.fragment:
        raise ValueError('Le portail a retourné une capture inaccessible.')
    path = Path(unquote(parts.path))
    if not path.is_absolute():
        raise ValueError('Le portail a retourné une capture inaccessible.')
    with path.open('rb') as source:
        data = source.read(32 * 1024 * 1024 + 1)
    if len(data) > 32 * 1024 * 1024:
        raise ValueError('Cette capture est trop volumineuse. Choisissez une zone plus petite.')
    image = QImage.fromData(data)
    if image.isNull() or image.width() < 8 or image.height() < 8:
        raise ValueError('La capture est illisible ou trop petite.')
    if max(image.width(), image.height()) > 2048:
        image = image.scaled(2048, 2048, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
    image = image.convertToFormat(QImage.Format.Format_RGB888)
    encoded = QByteArray()
    buffer = QBuffer(encoded)
    if not buffer.open(QIODevice.OpenModeFlag.WriteOnly) or not image.save(buffer, 'JPEG', 82):
        raise ValueError('La capture ne peut pas être préparée.')
    buffer.close()
    if encoded.size() > 2 * 1024 * 1024:
        raise ValueError('Cette capture est trop volumineuse. Choisissez une zone plus petite.')
    return 'data:image/jpeg;base64,' + base64.b64encode(bytes(encoded)).decode('ascii')


async def _portal_capture():
    from dbus_next import BusType, Message, MessageType, Variant
    from dbus_next.aio import MessageBus

    bus = await MessageBus(bus_type=BusType.SESSION).connect()
    handle = None
    finished = False
    try:
        # Pin the unique owner: a different process on the same session bus must
        # not be able to inject a directed Response signal for this request.
        async def get_owner():
            return await bus.call(Message(destination='org.freedesktop.DBus', path='/org/freedesktop/DBus',
                                          interface='org.freedesktop.DBus', member='GetNameOwner',
                                          signature='s', body=['org.freedesktop.portal.Desktop']))

        owner = await get_owner()
        if owner.message_type != MessageType.METHOD_RETURN:
            activate = await bus.call(Message(destination='org.freedesktop.DBus', path='/org/freedesktop/DBus',
                                              interface='org.freedesktop.DBus', member='StartServiceByName',
                                              signature='su', body=['org.freedesktop.portal.Desktop', 0]))
            if activate.message_type != MessageType.METHOD_RETURN:
                raise ValueError('Le portail de capture est indisponible.')
            owner = await get_owner()
        if owner.message_type != MessageType.METHOD_RETURN or len(owner.body) != 1:
            raise ValueError('Le portail de capture est indisponible.')
        portal_owner = owner.body[0]
        token = 'kiara_' + secrets.token_hex(16)
        handle = '/org/freedesktop/portal/desktop/request/' + bus.unique_name[1:].replace('.', '_') + '/' + token
        response = asyncio.get_running_loop().create_future()

        def receive(message):
            if (message.message_type == MessageType.SIGNAL and message.sender == portal_owner and message.path == handle
                    and message.interface == 'org.freedesktop.portal.Request'
                    and message.member == 'Response' and not response.done()):
                response.set_result(message.body)

        bus.add_message_handler(receive)
        rule = ("type='signal',sender='" + portal_owner + "',"
                "interface='org.freedesktop.portal.Request',member='Response',path='" + handle + "'")
        matched = await bus.call(Message(destination='org.freedesktop.DBus', path='/org/freedesktop/DBus',
                                         interface='org.freedesktop.DBus', member='AddMatch', signature='s', body=[rule]))
        if matched.message_type != MessageType.METHOD_RETURN:
            raise ValueError('Le portail de capture est indisponible.')
        reply = await bus.call(Message(destination='org.freedesktop.portal.Desktop',
                                       path='/org/freedesktop/portal/desktop',
                                       interface='org.freedesktop.portal.Screenshot', member='Screenshot',
                                       signature='sa{sv}', body=['', {'handle_token': Variant('s', token),
                                                                     'interactive': Variant('b', True)}]))
        if reply.message_type != MessageType.METHOD_RETURN or reply.sender != portal_owner or reply.body != [handle]:
            raise ValueError('Le portail de capture est indisponible ou incompatible.')
        values = await response
        finished = True
        if len(values) != 2:
            raise ValueError('La réponse du portail de capture est invalide.')
        if values[0] == 1:
            return {'cancelled': True}
        if values[0] != 0 or 'uri' not in values[1] or values[1]['uri'].signature != 's':
            raise ValueError('La capture a échoué. Choisissez une image enregistrée ou réessayez.')
        return {'cancelled': False, 'image': _encode_uri(values[1]['uri'].value)}
    finally:
        if handle and not finished:
            try:
                # Closing the request also dismisses an outstanding portal dialog.
                await asyncio.wait_for(bus.call(Message(destination='org.freedesktop.portal.Desktop', path=handle,
                                     interface='org.freedesktop.portal.Request', member='Close')), timeout=1)
            except (Exception, asyncio.CancelledError):
                pass
        bus.disconnect()
        try:
            await asyncio.wait_for(bus.wait_for_disconnect(), timeout=1)
        finally:
            # dbus-next 0.2.3 shuts down, but does not close, its socket/stream.
            bus._stream.close()
            bus._sock.close()


def capture():
    try:
        return asyncio.run(asyncio.wait_for(_portal_capture(), timeout=58))
    except ValueError:
        raise
    except Exception:
        raise ValueError('Le portail de capture Linux est indisponible. Choisissez une image enregistrée ou réessayez.') from None
