import assert from 'node:assert/strict';
import {test} from 'node:test';
import {measureInitial, withinBudget} from './web-initial-budget.mjs';

test('counts shared static modules once, excludes deferred modules, and includes CSS',()=>{
  const manifest={
    'index.html':{isEntry:true,file:'entry.js',imports:['a','b'],dynamicImports:['deferred'],css:['main.css']},
    a:{file:'a.js',imports:['shared']}, b:{file:'b.js',imports:['shared'],css:['main.css']},
    shared:{file:'shared.js'}, deferred:{file:'deferred.js'}
  };
  const data={'entry.js':'one','a.js':'two','b.js':'three','shared.js':'four','main.css':'css','deferred.js':'excluded'};
  const result=measureInitial(manifest,name=>Buffer.from(data[name]));
  assert.deepEqual(result.files.map(file=>file.name),['a.js','b.js','entry.js','main.css','shared.js']);
  assert.equal(result.jsBytes,15);assert.equal(result.cssBytes,3);
  assert.ok(withinBudget(result));
});

test('fails closed for a missing static dependency and checks both limits',()=>{
  assert.throws(()=>measureInitial({'index.html':{isEntry:true,file:'entry.js',imports:['absent']}},()=>Buffer.alloc(1)),/absent/);
  assert.equal(withinBudget({jsBytes:462001,jsGzipBytes:1}),false);
  assert.equal(withinBudget({jsBytes:1,jsGzipBytes:143001}),false);
});
