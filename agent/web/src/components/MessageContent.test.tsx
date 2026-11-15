import {describe,it,expect} from 'vitest';
import {messageDocument} from './MessageContent';
describe('messageDocument',()=>{
it('preserves plain text',()=>expect(messageDocument('Bonjour\nCommande <ABC>')).toBeNull());
it('preserves tables and removes active content and tracking',()=>{
const html=messageDocument('<table width="600"><tr><td onclick="alert(1)">Accord</td></tr></table><script>alert(1)</script><img src="https://tracker.test/pixel"><a href="javascript:alert(1)">Lien</a>')!;
expect(html).toContain('>Accord</td>');expect(html).not.toContain('onclick');expect(html).not.toContain('<script');expect(html).not.toContain('tracker.test');expect(html).not.toContain('javascript:');expect(html).toContain("default-src 'none'");
});
it('isolates web links',()=>expect(messageDocument('<p><a href="https://example.com">Document</a></p>')).toContain('noopener noreferrer'));
});


describe('original email layout',()=>{
 it('keeps sender CSS and HTML presentation attributes without imposing table layout',()=>{
  const html=messageDocument('<html><head><style>.brand{background:#0085ad;font-family:Verdana}</style></head><body bgcolor="#e8e8e8"><table width="600" cellpadding="0" cellspacing="0" class="brand"><tr><td style="padding:25px;color:white" align="center">Approbation</td></tr></table></body></html>')!;
  expect(html).toContain('.brand{background:#0085ad;font-family:Verdana}');
  expect(html).toContain('bgcolor="#e8e8e8"');expect(html).toContain('width="600"');expect(html).toContain('cellpadding="0"');expect(html).toContain('style="padding:25px;color:white"');expect(html).not.toContain('table-layout:fixed');
 });
 it('resolves embedded images and requires an explicit choice for remote images',()=>{
  const text='<p><img src="cid:logo"><img src="https://images.example.com/logo.png"></p>';
  const html=messageDocument(text,{inlineImages:{logo:'data:image/png;base64,YQ=='}})!;
  expect(html).toContain('src="data:image/png;base64,YQ=="');expect(html).not.toContain('https://images.example.com');
  expect(messageDocument(text,{showRemote:true})).toContain('src="https://images.example.com/logo.png"');
 });
 it('removes active embedded documents and keeps CSS network access blocked',()=>{
  const html=messageDocument('<body onload="bad()"><style>@import url(https://tracker.test/);</style><iframe srcdoc="bad"></iframe><object data="bad"></object><p style="color:red" onclick="bad()">Mail</p></body>')!;
  expect(html).not.toContain('onload');expect(html).not.toContain('onclick');expect(html).not.toContain('<iframe');expect(html).not.toContain('<object');expect(html).toContain("img-src data:;");expect(html).toContain("script-src 'none'");
 });
});
