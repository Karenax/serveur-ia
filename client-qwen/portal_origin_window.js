/* Select the fixed script for this protected temporary transfer window. */
(() => {
  'use strict';
  const role=window.__kiaraRecoveryRole;
  const mode=window.__kiaraRecoveryMode;
  if ((role !== 'sender' && role !== 'receiver') || (mode !== 'transfer' && mode !== 'snapshot' && mode !== 'manifest')
      || (mode==='manifest' && role!=='sender')) return;
  const script=document.createElement('script');
  script.src=role === 'receiver' ? '/portal_origin_receiver.js'
    : mode === 'snapshot' ? '/portal_origin_snapshot.js' : mode === 'manifest' ? '/portal_origin_manifest.js' : '/portal_origin_sender_result.js';
  document.head.appendChild(script);
})();
