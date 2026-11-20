import {useEffect, useRef, useState} from 'react';

type PanelWindow = Window & {
  kiaraShowDeviceSetting?: (section: string) => boolean;
  kiaraSetDeviceSettingActive?: (active: boolean) => void;
};

export function DeviceSettingsPanel({path, section, title}: {
  path: string;
  section?: string;
  title: string;
}) {
  const frame = useRef<HTMLIFrameElement>(null);
  const observer = useRef<ResizeObserver | null>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [attempt, setAttempt] = useState(0);
  const [height, setHeight] = useState(1);

  function showSection() {
    const view = frame.current?.contentWindow as PanelWindow | null;
    try {
      if (!section || !view?.kiaraShowDeviceSetting?.(section)) return false;
      setHeight(Math.max(1, Math.ceil(view.document.body.getBoundingClientRect().height)));
      return true;
    } catch {
      return false;
    }
  }

  function loaded() {
    observer.current?.disconnect();
    const view = frame.current?.contentWindow as PanelWindow | null;
    if (!frame.current?.contentDocument || !view?.kiaraShowDeviceSetting) {
      setStatus('error');
      return;
    }
    observer.current = new ResizeObserver(() => {
      setHeight(Math.max(1, Math.ceil(view.document.body.getBoundingClientRect().height)));
    });
    observer.current.observe(view.document.body);
    setStatus('ready');
  }

  useEffect(() => {
    if (status !== 'ready') return;
    const view = frame.current?.contentWindow as PanelWindow | null;
    view?.kiaraSetDeviceSettingActive?.(!!section);
    if (section && !showSection()) setStatus('error');
  }, [section, status]);

  useEffect(() => {
    const protectSettings = (event: BeforeUnloadEvent) => {
      const panel = frame.current;
      if (status === 'ready' && panel?.contentDocument &&
          !panel.contentWindow?.dispatchEvent(new Event('beforeunload', {cancelable:true}))) {
        event.preventDefault();
        event.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', protectSettings);
    return () => window.removeEventListener('beforeunload', protectSettings);
  }, [status]);
  useEffect(() => () => observer.current?.disconnect(), []);

  return <div className="card" hidden={!section}>
    {status === 'loading' && <p role="status">Chargement des réglages…</p>}
    {status === 'error' && <div role="alert">
      <p>Impossible de charger ces réglages.</p>
      <button type="button" className="button secondary" onClick={() => {
        setStatus('loading');
        setAttempt(value => value + 1);
      }}>Réessayer</button>
    </div>}
    <iframe key={attempt} ref={frame} src={path} title={title}
      className="workspace-device-settings-frame" height={height}
      hidden={status === 'error'} onLoad={loaded}/>
  </div>;
}
