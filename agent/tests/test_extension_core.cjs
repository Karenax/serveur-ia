/* Pure source tests; Firefox/Infomaniak account qualification is separate. */
const test = require('node:test');
const assert = require('node:assert/strict');
const C = require('../extensions/infomaniak-auto-local/core.js');
const path = '/api/mail/12345678-abcd-abcd-abcd-123456789abc/folder/INBOX/message/1';
const detail = 'https://mail.infomaniak.com'+path+'?prefered_format=html';
test('only exact Infomaniak originals are accepted', () => {
  const d = C.detail(detail);
  assert.ok(d);
  assert.equal(C.detail(detail.replace('mail.infomaniak.com','evil.example')),null);
  assert.equal(C.detail('https://mail.infomaniak.com@evil.example'+path+'?prefered_format=html'),null);
  assert.throws(()=>C.message(d,{msg_id:'id',download_resource:'https://evil.example/mail'}));
  assert.throws(()=>C.message(d,{msg_id:'id',is_draft:true,download_resource:path+'/download'}));
  assert.equal(C.message(d,{msg_id:'id',download_resource:path+'/download'}).download,
               'https://mail.infomaniak.com'+path+'/download');
});
test('filenames and EML validation reject traversal and login responses', () => {
  const filename = C.filename('../../bad:*?<>|\\name','0123456789abcdef','2026-09-30');
  assert.equal(filename.split('/').length,2);
  assert.equal(C.eml('<html>login</html>','text/html'),false);
  assert.equal(C.eml('{"error":401}','application/json'),false);
  assert.equal(C.eml('From: a@example.test\r\nSubject: Test\r\n\r\nMessage'),true);
});
