import {test} from 'node:test';
import assert from 'node:assert/strict';
import {evidenceRows} from '../src/evidence.js';
const records=[{row_reference:1,route:'a',outcome:'failure',timestamp:'2026-01-01T23:00:00+00:00',original:{message:'Needle'}},{row_reference:2,route:'b',outcome:'unknown',timestamp:null},{row_reference:3,route:'a',outcome:'success',timestamp:'2026-01-02T01:00:00+00:00'}];
test('Evidence filters search and UTC dates without mutating source or metrics',()=>{
  assert.deepEqual(evidenceRows(records,{start:'2026-01-01',end:'2026-01-01'},null,'','row_reference','asc').map(r=>r.row_reference),[1]);
  assert.deepEqual(evidenceRows(records,{},null,'needle','row_reference','asc').map(r=>r.row_reference),[1]);
  assert.deepEqual(evidenceRows(records,{},null,'','row_reference','desc').map(r=>r.row_reference),[3,2,1]);
  assert.deepEqual(evidenceRows(records,{}, {source_record_references:[2]},'','row_reference','asc').map(r=>r.row_reference),[2]);
  assert.deepEqual(evidenceRows(records,{route:'a',outcome:'unknown'},null,'','row_reference','asc'),[]);
  assert.deepEqual(records.map(r=>r.row_reference),[1,2,3]);
});
