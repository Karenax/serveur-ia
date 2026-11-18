// WebKitGTK reports the unshifted French 0 key as "à". Tauri's zoom
// handler matches the character "0", so forward its standard shortcut while
// preserving the built-in zoom state and reset behavior.
window.addEventListener('keydown', (event) => {
  if (event.ctrlKey && !event.altKey && !event.metaKey &&
      event.code === 'Digit0' && event.key !== '0') {
    event.preventDefault();
    window.dispatchEvent(new KeyboardEvent('keydown', { key: '0', ctrlKey: true }));
  }
}, true);
